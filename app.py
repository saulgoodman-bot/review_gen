import base64
import os

from werkzeug.exceptions import RequestEntityTooLarge

from flask import Flask, jsonify, render_template, request
from PIL import Image

from utils.image_gen import (generate_cover_image, generate_review_image,
                              image_to_bytes)

app = Flask(__name__)
# Phone photos are commonly larger than 20MB.  The browser also resizes photos
# before submission, but retain a reasonable server-side guard for clients that
# do not run JavaScript.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB total upload cap

# ---- edit these two lines to match your own brand ----------------------
BRAND_HANDLE = os.environ.get("BRAND_HANDLE", "@YOURHANDLE")
BRAND_WATERMARK = os.environ.get("BRAND_WATERMARK", "SCENE & OPINION")
# --------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html", brand_handle=BRAND_HANDLE)


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error):
    """Return JSON so the browser never tries to parse an HTML 413 page."""
    return jsonify(
        error="Your images are too large. Choose smaller images and try again."
    ), 413


@app.route("/generate", methods=["POST"])
def generate():
    try:
        cover_file = request.files.get("image1")
        image2 = request.files.get("image2")
        movie_name = (request.form.get("movie_name") or "").strip()
        review_text = (request.form.get("review_text") or "").strip()
        rating_raw = request.form.get("rating", "0")

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
        except ValueError:
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
        review = generate_review_image(img2, review_text, rating, brand=BRAND_WATERMARK)

        cover_b64 = base64.b64encode(image_to_bytes(cover)).decode("ascii")
        review_b64 = base64.b64encode(image_to_bytes(review)).decode("ascii")

        return jsonify(
            cover=f"data:image/png;base64,{cover_b64}",
            review=f"data:image/png;base64,{review_b64}",
            rating=rating,
        )
    except RequestEntityTooLarge:
        # Let the application-level handler return its JSON 413 response.
        raise
    except Exception as exc:  # pragma: no cover - safety net for prod
        app.logger.exception("generate failed")
        return jsonify(error=f"Something went wrong: {exc}"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
