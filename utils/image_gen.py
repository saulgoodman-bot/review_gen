"""
Image generation engine for the movie-review Instagram post generator.

Produces two 1080x1350 portrait PNGs from user input:
  1. cover image  -> the supplied clapperboard cover artwork with the
                      uploaded movie poster inserted into the slate and the
                      entered movie title added at the upper-left.
  2. review image -> the second movie image as a dimmed backdrop with the
                      review text and a 5-star (0.5-increment) rating on top.

The cover template and bundled open-source fonts are packaged with the app,
so the whole thing is self-contained and safe to deploy anywhere (e.g. Render).
"""

import math
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps

CANVAS = 1080
HEIGHT = 1350
REVIEW_BACKGROUND = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "review-background.png")
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

ANTON = os.path.join(FONT_DIR, "Anton-Regular.ttf")
POPPINS_SEMI = os.path.join(FONT_DIR, "Poppins-SemiBold.ttf")
POPPINS_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
PLAYFAIR_VAR = os.path.join(FONT_DIR, "PlayfairDisplay-Variable.ttf")
COVER_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "images", "cover-portrait.png"
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
    """Preserve paragraph breaks and split words wider than the text area."""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
                continue
            if current:
                lines.append(current)
            current = ""
            for char in word:
                if current and draw.textlength(current + char, font=font) > max_width:
                    lines.append(current)
                    current = ""
                current += char
        lines.append(current)
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
        if total_h <= max_height and all(draw.textlength(line, font=font) <= max_width for line in lines):
            return font, lines, line_h
        size -= 2
    font = _playfair(minimum, weight)
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.getbbox("Ag")[3] * line_gap
    raise ValueError("Review is too long to fit. Please shorten it or add fewer paragraph breaks.")


# ---- star rating ---------------------------------------------------------
def _star_points(cx, cy, r_outer, r_inner):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def make_star(size, fraction, gold=(255, 165, 0), empty=(255, 255, 255, 0)):
    """Return an RGBA star image, `fraction` (0/0.5/1) filled gold left-to-right."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = _star_points(size / 2, size / 2, size * 0.49, size * 0.22)
    d.polygon(pts, fill=empty, outline=(0, 0, 0, 255), width=7)

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
    ImageDraw.Draw(img).line(pts + [pts[0]], fill=(0, 0, 0, 255), width=7, joint="curve")
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
def generate_cover_image(image1: Image.Image, movie_name: str) -> Image.Image:
    """Add the uploaded poster and title to the supplied cover artwork."""
    with Image.open(COVER_TEMPLATE) as template:
        canvas = cover_resize(template, CANVAS, HEIGHT)

    # The panel below the clapper sticks is the poster window in the supplied
    # artwork.  Keeping the coordinates relative preserves the template's
    # composition at its native resolution.
    poster_x = int(canvas.width * 0.09)
    poster_y = int(canvas.height * 0.447)
    poster_w = int(canvas.width * 0.728)
    poster_h = int(canvas.height * 0.328)
    poster = cover_resize(image1, poster_w, poster_h)
    canvas.paste(poster, (poster_x, poster_y))

    draw = ImageDraw.Draw(canvas)
    max_width = int(canvas.width * 0.83)
    max_height = int(canvas.height * 0.058)
    size = int(canvas.height * 0.058)
    while size > 10:
        font = _font(POPPINS_BOLD, size)
        bbox = draw.textbbox((0, 0), movie_name.upper(), font=font)
        if bbox[2] <= max_width and bbox[3] <= max_height:
            break
        size -= 2
    else:
        font = _font(POPPINS_BOLD, 10)

    draw.text(
        (int(canvas.width * 0.05), int(canvas.height * 0.135)),
        movie_name.upper(),
        font=font,
        fill=(255, 255, 255),
    )
    return canvas


# ---- review image ----------------------------------------------------------
def generate_review_image(image2: Image.Image, review_text: str, rating: float,
                           brand="SCENE & OPINION") -> Image.Image:
    bg = cover_resize(image2, CANVAS, HEIGHT)
    canvas = Image.blend(bg, Image.new("RGB", bg.size, "white"), 0.88).convert("RGBA")
    with Image.open(REVIEW_BACKGROUND) as source:
        logo = cover_resize(source, CANVAS, HEIGHT).convert("RGBA")
    # White pixels leave the movie backdrop visible; dark logo pixels become a faint watermark.
    ink = ImageOps.invert(logo.convert("L")).point(lambda value: round(value * 0.18))
    logo.putalpha(ink)
    canvas = Image.alpha_composite(canvas, logo)
    draw = ImageDraw.Draw(canvas)
    font, lines, line_h = fit_text_block(
        draw, review_text, 864, 970, start=50, minimum=28, line_gap=1.3)
    y = 100
    for line in lines:
        draw.text((108, y), line, font=font, fill="black", anchor="lt")
        y += line_h
    draw_rating_row(canvas, rating, CANVAS // 2, 1130, star_size=136, gap=18)
    return canvas.convert("RGB")


def image_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
