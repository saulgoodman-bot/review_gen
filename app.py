import base64
import os

from flask import Flask, jsonify, render_template, request
from PIL import Image

from utils.image_gen import (generate_cover_image, generate_review_image,
                              image_to_bytes)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB total upload cap

# ---- edit these two lines to match your own brand ----------------------
BRAND_HANDLE = os.environ.get("BRAND_HANDLE", "@YOURHANDLE")
BRAND_WATERMARK = os.environ.get("BRAND_WATERMARK", "SCENE & OPINION")
# --------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html", brand_handle=BRAND_HANDLE)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        image2 = request.files.get("image2")
        movie_name = (request.form.get("movie_name") or "").strip()
        review_text = (request.form.get("review_text") or "").strip()
        rating_raw = request.form.get("rating", "0")

        if not movie_name:
            return jsonify(error="Please enter the movie name."), 400
        if not image2:
            return jsonify(error="Please upload a backdrop image."), 400
        if not review_text:
            return jsonify(error="Please write a short review."), 400

        try:
            rating = float(rating_raw)
        except ValueError:
            return jsonify(error="Invalid rating value."), 400
        rating = max(0.0, min(5.0, round(rating * 2) / 2))

        try:
            img2 = Image.open(image2.stream)
            img2.load()
        except Exception:
            return jsonify(error="Image 2 could not be read. Try a different file."), 400

        cover = generate_cover_image(movie_name)
        review = generate_review_image(img2, review_text, rating, brand=BRAND_WATERMARK)

        cover_b64 = base64.b64encode(image_to_bytes(cover)).decode("ascii")
        review_b64 = base64.b64encode(image_to_bytes(review)).decode("ascii")

        return jsonify(
            cover=f"data:image/png;base64,{cover_b64}",
            review=f"data:image/png;base64,{review_b64}",
            rating=rating,
        )
    except Exception as exc:  # pragma: no cover - safety net for prod
        app.logger.exception("generate failed")
        return jsonify(error=f"Something went wrong: {exc}"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
