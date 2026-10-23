import base64
import os
import math

from flask import Flask, jsonify, render_template, request
from PIL import Image

from utils.image_gen import (generate_cover_image, generate_review_image,
                              image_to_bytes)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB total upload cap

# ---- edit these two lines to match your own brand ----------------------
BRAND_HANDLE = os.environ.get("BRAND_HANDLE", "@SCENEANDOPINION")
BRAND_WATERMARK = os.environ.get("BRAND_WATERMARK", "SCENE & OPINION")
# --------------------------------------------------------------------------


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify(error="Uploads must be under 20 MB total."), 413


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/")
def index():
    return render_template("index.html", brand_handle=BRAND_HANDLE)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        cover_file = request.files.get("image1")
        image2 = request.files.get("image2")
        movie_name = (request.form.get("movie_name") or "").strip()
        review_text = (request.form.get("review_text") or "").strip()
        rating_raw = request.form.get("rating", "0")

        if len(movie_name) > 80 or len(review_text) > 1200:
            return jsonify(error="Use up to 80 characters for the title and 1200 for the review."), 400
        if not movie_name:
            return jsonify(error="Please enter the movie name."), 400
        if not cover_file:
            return jsonify(error="Please upload a cover image."), 400
        if not image2:
            return jsonify(error="Please upload a backdrop image."), 400
        if not review_text:
            return jsonify(error="Please write a short review."), 400

        try:
            rating = float(rating_raw)
        except (ValueError, TypeError):
            return jsonify(error="Invalid rating value."), 400
        if not math.isfinite(rating):
            return jsonify(error="Invalid rating value."), 400
        rating = max(0.0, min(5.0, round(rating * 2) / 2))

        try:
            img1 = Image.open(cover_file.stream)
            img1.load()
        except Exception:
            return jsonify(error="Cover image could not be read. Try a different file."), 400
        try:
            img2 = Image.open(image2.stream)
            img2.load()
        except Exception:
            return jsonify(error="Image 2 could not be read. Try a different file."), 400

        cover = generate_cover_image(img1, movie_name)
        try:
            review = generate_review_image(img2, review_text, rating, brand=BRAND_WATERMARK)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        cover_b64 = base64.b64encode(image_to_bytes(cover)).decode("ascii")
        review_b64 = base64.b64encode(image_to_bytes(review)).decode("ascii")

        return jsonify(
            cover=f"data:image/png;base64,{cover_b64}",
            review=f"data:image/png;base64,{review_b64}",
            rating=rating,
        )
    except Exception as exc:  # pragma: no cover - safety net for prod
        app.logger.exception("generate failed")
        return jsonify(error="Image generation failed. Please try smaller images."), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
