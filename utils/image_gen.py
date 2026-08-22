"""
Image generation engine for the movie-review Instagram post generator.

Produces a supplied square cover template and a 1080x1080 review PNG from user input:
  1. cover image  -> the supplied clapperboard cover artwork with the
                      entered movie title added at the upper-left.
  2. review image -> the second movie image as a dimmed backdrop with the
                      review text and a 5-star (0.5-increment) rating on top.

The cover template and bundled open-source fonts are packaged with the app,
so the whole thing is self-contained and safe to deploy anywhere (e.g. Render).
"""

import math
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

CANVAS = 1080
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

ANTON = os.path.join(FONT_DIR, "Anton-Regular.ttf")
POPPINS_SEMI = os.path.join(FONT_DIR, "Poppins-SemiBold.ttf")
POPPINS_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
PLAYFAIR_VAR = os.path.join(FONT_DIR, "PlayfairDisplay-Variable.ttf")
COVER_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "images", "cover-template.png"
)

# ---- brand palette -----------------------------------------------------
GOLD = (238, 178, 60)       # star fill / accent


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


# ---- cover image ----------------------------------------------------------
def generate_cover_image(movie_name: str) -> Image.Image:
    """Return the supplied cover artwork with the movie title at upper-left.

    The artwork is deliberately used as-is: only the movie name is added in the
    otherwise open upper-left portion, mirroring the large "OPINION" wordmark.
    """
    with Image.open(COVER_TEMPLATE) as template:
        canvas = ImageOps.exif_transpose(template).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    max_width = int(canvas.width * 0.66)
    max_height = int(canvas.height * 0.075)
    size = int(canvas.height * 0.075)
    while size > 36:
        font = _font(ANTON, size)
        bbox = draw.textbbox((0, 0), movie_name.upper(), font=font)
        if bbox[2] <= max_width and bbox[3] <= max_height:
            break
        size -= 2
    else:
        font = _font(ANTON, 36)

    draw.text(
        (int(canvas.width * 0.05), int(canvas.height * 0.025)),
        movie_name.upper(),
        font=font,
        fill=(255, 255, 255),
    )
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
