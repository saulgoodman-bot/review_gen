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
        self.assertEqual(cover.size, (1080, 1350))
        self.assertEqual(cover.getpixel((470, 800)), (220, 30, 40))

    def test_nonfinite_rating_is_rejected(self):
        response = self.client.post("/generate", data={
            "movie_name": "Test", "review_text": "Review", "rating": "nan",
            "image1": self.image_upload("red", "a.png"),
            "image2": self.image_upload("blue", "b.png"),
        })
        self.assertEqual(response.status_code, 400)

    def test_review_dimensions_and_long_word_wrapping(self):
        image = image_gen.generate_review_image(
            Image.new("RGB", (200, 300), "red"), "A" * 180 + "\n\nA second paragraph.", 3.5)
        self.assertEqual(image.size, (1080, 1350))

    def test_excessive_paragraphs_are_rejected(self):
        with self.assertRaises(ValueError):
            image_gen.generate_review_image(Image.new("RGB", (100, 100)), "a\n" * 200, 4)

    def test_generate_requires_cover_upload(self):
        response = self.client.post(
            "/generate",
            data={"movie_name": "Test Movie"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Please upload a cover image."})


if __name__ == "__main__":
    unittest.main()
