"""
Image generation engine for the movie-review Instagram post generator.

Produces two 1080x1080 PNG images from user input:
  1. cover image  -> a clapperboard graphic with the user's movie image
                      set into the board, plus brand/tag text.
  2. review image -> the second movie image as a dimmed backdrop with the
                      review text and a 5-star (0.5-increment) rating on top.

All drawing is done with Pillow only (no external image assets besides the
bundled open-source fonts), so the whole thing is self-contained and safe
to deploy anywhere (e.g. Render).
"""

import math
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

CANVAS = 1080
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

ANTON = os.path.join(FONT_DIR, "Anton-Regular.ttf")
POPPINS_REG = os.path.join(FONT_DIR, "Poppins-Regular.ttf")
POPPINS_SEMI = os.path.join(FONT_DIR, "Poppins-SemiBold.ttf")
POPPINS_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
PLAYFAIR_VAR = os.path.join(FONT_DIR, "PlayfairDisplay-Variable.ttf")

# ---- brand palette -----------------------------------------------------
INK = (14, 16, 20)          # near-black background
PAPER = (245, 242, 235)     # clapperboard slate paper color
GOLD = (238, 178, 60)       # star fill / accent
STRIPE_COLORS = [
    (37, 41, 48), (60, 179, 113), (240, 176, 44),
    (58, 123, 213), (203, 68, 63), (235, 232, 224),
    (176, 176, 176), (90, 92, 96),
]


# ---- font helpers -------------------------------------------------------
def _playfair(size, weight="Bold"):
    font = ImageFont.truetype(PLAYFAIR_VAR, size)
    try:
        font.set_variation_by_name(weight)
    except Exception:
        pass
    return font


def _font(path, size):
    return ImageFont.truetype(path, size)


# ---- generic image helpers ---------------------------------------------
def cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    """Resize + center-crop `img` so it exactly fills a w x h box."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    src_w, src_h = img.size
    scale = max(w / src_w, h / src_h)
    new_w, new_h = math.ceil(src_w * scale), math.ceil(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    x0 = (new_w - w) // 2
    y0 = (new_h - h) // 2
    return img.crop((x0, y0, x0 + w, y0 + h))


def rounded_mask(w, h, radius):
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return mask


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_text_block(draw, text, max_width, max_height, start=64, minimum=30,
                    weight="Bold", line_gap=1.28):
    """Shrink font size until the wrapped text fits in max_width x max_height."""
    size = start
    while size >= minimum:
        font = _playfair(size, weight)
        lines = wrap_text(draw, text, font, max_width)
        line_h = font.getbbox("Ag")[3] * line_gap
        total_h = line_h * len(lines)
        if total_h <= max_height:
            return font, lines, line_h
        size -= 2
    font = _playfair(minimum, weight)
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.getbbox("Ag")[3] * line_gap
    return font, lines, line_h


# ---- star rating ---------------------------------------------------------
def _star_points(cx, cy, r_outer, r_inner):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def make_star(size, fraction, gold=GOLD, empty=(255, 255, 255, 70)):
    """Return an RGBA star image, `fraction` (0/0.5/1) filled gold left-to-right."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = _star_points(size / 2, size / 2, size * 0.49, size * 0.19)
    d.polygon(pts, fill=empty, outline=(255, 255, 255, 140), width=2)

    if fraction > 0:
        gold_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gold_layer)
        gd.polygon(pts, fill=(*gold, 255))
        if fraction < 1:
            mask = Image.new("L", (size, size), 0)
            md = ImageDraw.Draw(mask)
            md.rectangle([0, 0, int(size * fraction), size], fill=255)
            empty_alpha = Image.new("L", (size, size), 0)
            gold_layer.putalpha(Image.composite(gold_layer.split()[3], empty_alpha, mask))
        img = Image.alpha_composite(img, gold_layer)
    return img


def draw_rating_row(canvas: Image.Image, rating: float, center_x: int, y: int,
                     star_size=76, gap=16):
    rating = max(0.0, min(5.0, round(rating * 2) / 2))
    total_w = star_size * 5 + gap * 4
    x = center_x - total_w // 2
    for i in range(5):
        frac = max(0.0, min(1.0, rating - i))
        if 0 < frac < 1:
            frac = 0.5
        star = make_star(star_size, frac)
        canvas.paste(star, (x, y), star)
        x += star_size + gap
    return rating


# ---- cover image (clapperboard) ------------------------------------------
def generate_cover_image(image1: Image.Image, brand="@YOURHANDLE",
                          eyebrow="MOVIE", corner_tag="REVIEW") -> Image.Image:
    canvas = Image.new("RGB", (CANVAS, CANVAS), INK)

    # subtle vertical vignette / gradient backdrop
    grad = Image.new("L", (1, CANVAS), color=0)
    for y in range(CANVAS):
        grad.putpixel((0, y), int(18 + 24 * (y / CANVAS)))
    grad = grad.resize((CANVAS, CANVAS))
    tint = Image.new("RGB", (CANVAS, CANVAS), (28, 22, 40))
    canvas = Image.composite(tint, canvas, grad)

    # faint film-strip sprocket holes down both edges (signature detail)
    draw = ImageDraw.Draw(canvas, "RGBA")
    hole_r = 14
    for edge_x in (46, CANVAS - 46):
        y = 40
        while y < CANVAS:
            draw.ellipse([edge_x - hole_r, y - hole_r, edge_x + hole_r, y + hole_r],
                         fill=(255, 255, 255, 26))
            y += hole_r * 3.6

    # ---- header text ----
    eyebrow_font = _font(ANTON, 92)
    draw.text((96, 70), eyebrow, font=eyebrow_font, fill=(250, 248, 244))
    handle_font = _font(POPPINS_SEMI, 30)
    hw = draw.textlength(brand, font=handle_font)
    draw.text((CANVAS - 96 - hw, 96), brand, font=handle_font, fill=(210, 205, 220))
    draw.line([(96, 190), (CANVAS - 96, 190)], fill=(255, 255, 255, 60), width=2)

    # ---- build the clapperboard on its own layer, then rotate as a unit ----
    L = 760
    layer = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer, "RGBA")

    board_x0, board_y0, board_x1, board_y1 = 40, 170, 720, 640
    board_w, board_h = board_x1 - board_x0, board_y1 - board_y0

    # drop shadow behind board
    shadow = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([board_x0 + 18, board_y0 + 24, board_x1 + 18, board_y1 + 24],
                          radius=18, fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    layer = Image.alpha_composite(layer, shadow)
    ld = ImageDraw.Draw(layer, "RGBA")

    # paper board
    ld.rounded_rectangle([board_x0, board_y0, board_x1, board_y1], radius=14,
                         fill=(*PAPER, 255), outline=(30, 28, 26, 255), width=6)

    # image inset inside the board (with a small paper margin, leaving a
    # label strip at the very top of the board for a "SCENE / TAKE" line)
    margin = 22
    label_h = 58
    img_x0, img_y0 = board_x0 + margin, board_y0 + label_h
    img_x1, img_y1 = board_x1 - margin, board_y1 - margin
    iw, ih = img_x1 - img_x0, img_y1 - img_y0
    photo = cover_resize(image1, iw, ih)
    mask = rounded_mask(iw, ih, 8)
    layer.paste(photo, (img_x0, img_y0), mask)
    ld.rounded_rectangle([img_x0, img_y0, img_x1, img_y1], radius=8,
                         outline=(30, 28, 26, 255), width=4)

    # label strip text ("SCENE / TAKE" flavor, like a real slate)
    label_font = _font(POPPINS_SEMI, 26)
    ld.text((board_x0 + margin, board_y0 + 12), "SCENE", font=label_font,
            fill=(40, 38, 36, 255))
    take_txt = "TAKE 1"
    tw = ld.textlength(take_txt, font=label_font)
    ld.text((board_x1 - margin - tw, board_y0 + 12), take_txt, font=label_font,
            fill=(40, 38, 36, 255))

    # ---- clapper stick (striped bar), built separately then tilted open ----
    bar_w, bar_h = board_w, 96
    bar = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    n = len(STRIPE_COLORS)
    stripe_w = bar_w / (n - 2)  # stripes run wider than the bar, slanted
    shift = bar_h * 0.55
    for i, color in enumerate(STRIPE_COLORS * 2):
        x0 = i * (stripe_w / 2) - stripe_w
        if x0 > bar_w:
            break
        bd.polygon([
            (x0 + shift, 0), (x0 + stripe_w + shift, 0),
            (x0 + stripe_w, bar_h), (x0, bar_h),
        ], fill=color)
    bd.rectangle([0, 0, bar_w - 1, bar_h - 1], outline=(20, 18, 16, 255), width=6)

    bar = bar.rotate(9, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    layer.alpha_composite(bar, (board_x0 - 4, board_y0 - bar.height + 20))

    # hinge screws
    for hx, hy in [(board_x0 + 30, board_y0 + 6), (board_x0 + 30, board_y0 - 34)]:
        ld = ImageDraw.Draw(layer, "RGBA")
        ld.ellipse([hx - 13, hy - 13, hx + 13, hy + 13], fill=(25, 24, 22, 255),
                   outline=(80, 78, 74, 255), width=2)

    layer = layer.rotate(-4, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    paste_x = (CANVAS - layer.width) // 2
    paste_y = 250
    canvas.paste(layer, (paste_x, paste_y), layer)

    # ---- footer ----
    draw = ImageDraw.Draw(canvas, "RGBA")
    tag_font = _font(POPPINS_SEMI, 30)
    tag_txt = "SWIPE TO REVIEW"
    draw.text((96, CANVAS - 118), tag_txt, font=tag_font, fill=(230, 226, 235))
    tag_w = draw.textlength(tag_txt, font=tag_font)
    ax = 96 + tag_w + 22
    ay = CANVAS - 118 + 18
    draw.line([(ax, ay), (ax + 26, ay)], fill=(230, 226, 235, 255), width=4)
    draw.polygon([(ax + 20, ay - 9), (ax + 34, ay), (ax + 20, ay + 9)],
                 fill=(230, 226, 235, 255))

    corner_font = _font(ANTON, 78)
    cw = draw.textlength(corner_tag, font=corner_font)
    draw.text((CANVAS - 96 - cw, CANVAS - 138), corner_tag, font=corner_font,
              fill=(250, 248, 244))

    return canvas


# ---- review image ----------------------------------------------------------
def generate_review_image(image2: Image.Image, review_text: str, rating: float,
                           brand="SCENE & OPINION") -> Image.Image:
    bg = cover_resize(image2, CANVAS, CANVAS)
    bg = bg.filter(ImageFilter.GaussianBlur(2))

    overlay = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(CANVAS):
        t = y / CANVAS
        # darker at top & bottom, a touch lighter in the middle band
        alpha = int(178 + 45 * abs(t - 0.5) * 2)
        od.line([(0, y), (CANVAS, y)], fill=(8, 8, 12, alpha))
    canvas = Image.alpha_composite(bg.convert("RGBA"), overlay)

    # diagonal watermark, low-opacity brand wordmark
    wm_font = _font(POPPINS_BOLD, 64)
    wm = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wm)
    wm_text = brand.upper()
    tw = wd.textlength(wm_text, font=wm_font)
    wd.text(((CANVAS - tw) / 2, CANVAS / 2 - 40), wm_text, font=wm_font,
             fill=(255, 255, 255, 28))
    wm = wm.rotate(-24, resample=Image.BICUBIC)
    wm = wm.resize((CANVAS, CANVAS))
    canvas = Image.alpha_composite(canvas, wm)

    draw = ImageDraw.Draw(canvas, "RGBA")

    # review text block, vertically centered-ish, above the stars
    text_area_w = CANVAS - 220
    text_area_h = 560
    font, lines, line_h = fit_text_block(draw, review_text, text_area_w,
                                          text_area_h, start=66, minimum=32)
    total_h = line_h * len(lines)
    start_y = 300 - total_h / 2 + 120
    y = start_y
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (CANVAS - lw) / 2
        # soft shadow for legibility
        draw.text((x + 2, y + 3), line, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h

    # small quote mark flourish above the text
    quote_font = _playfair(140, "Black" if False else "Bold")
    draw.text((CANVAS / 2 - 40, start_y - 150), "\u201c", font=quote_font,
              fill=(238, 178, 60, 200))

    rating = draw_rating_row(canvas, rating, CANVAS // 2, CANVAS - 200, star_size=78, gap=18)

    label_font = _font(POPPINS_SEMI, 30)
    label = f"{rating:g} / 5"
    lw = draw.textlength(label, font=label_font)
    draw.text(((CANVAS - lw) / 2, CANVAS - 108), label, font=label_font,
              fill=(235, 232, 225, 255))

    return canvas.convert("RGB")


def image_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
