import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

import utils.image_gen as image_gen
from app import app


class GenerateEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.template_path = Path(self.temp_dir.name) / "cover-template.png"
        Image.new("RGB", (1000, 1000), (35, 70, 95)).save(self.template_path)
        self.original_template = image_gen.COVER_TEMPLATE
        image_gen.COVER_TEMPLATE = str(self.template_path)
        self.client = app.test_client()

    def tearDown(self):
        image_gen.COVER_TEMPLATE = self.original_template
        self.temp_dir.cleanup()

    @staticmethod
    def image_upload(color, filename):
        image = Image.new("RGB", (320, 240), color)
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output, filename

    def test_generate_places_cover_upload_in_first_slide(self):
        response = self.client.post(
            "/generate",
            data={
                "movie_name": "Test Movie",
                "image1": self.image_upload((220, 30, 40), "poster.png"),
                "image2": self.image_upload((30, 40, 220), "backdrop.png"),
                "review_text": "An engaging test review.",
                "rating": "4.5",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        cover_bytes = base64.b64decode(response.get_json()["cover"].split(",", 1)[1])
        cover = Image.open(BytesIO(cover_bytes))
        self.assertEqual(cover.size, (1000, 1000))
        self.assertEqual(cover.getpixel((470, 600)), (220, 30, 40))

    def test_generate_requires_cover_upload(self):
        response = self.client.post(
            "/generate",
            data={"movie_name": "Test Movie"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Please upload a cover image."})

    def test_oversized_upload_returns_json_error(self):
        original_limit = app.config["MAX_CONTENT_LENGTH"]
        app.config["MAX_CONTENT_LENGTH"] = 1
        try:
            response = self.client.post(
                "/generate",
                data={"movie_name": "Test Movie"},
                content_type="multipart/form-data",
            )
        finally:
            app.config["MAX_CONTENT_LENGTH"] = original_limit

        # Confirm Flask returns JSON rather than an HTML error document.
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json(), {
            "error": "Your images are too large. Choose smaller images and try again."
        })


if __name__ == "__main__":
    unittest.main()
