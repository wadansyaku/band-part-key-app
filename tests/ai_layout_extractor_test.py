import os
import tempfile
import unittest
from unittest import mock

import fitz
from PIL import Image

from core.ai_layout_extractor import AILayoutExtractor, AILayoutError


def create_sample_pdf(path: str) -> None:
    pdf = fitz.open()
    pdf.new_page(width=400, height=400)
    pdf.save(path)
    pdf.close()


class AILayoutExtractorTest(unittest.TestCase):
    def setUp(self):
        self.config = {
            "AI_API_KEY": "test-key",
            "AI_CONFIDENCE_THRESHOLD": 0.6,
            "AI_IMAGE_DPI": 72,
            "AI_MAX_PAGES": 1,
            "AI_REQUEST_TIMEOUT": 5,
        }

    def test_extract_parts_pdf_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "input.pdf")
            output_path = os.path.join(temp_dir, "output.pdf")
            create_sample_pdf(pdf_path)

            layout = {
                "schema_version": "1.0",
                "page_index": 0,
                "image_width": 400,
                "image_height": 400,
                "confidence": 0.9,
                "parts": [
                    {
                        "part_name": "vocal",
                        "bbox": {"x": 10, "y": 10, "width": 180, "height": 180},
                        "confidence": 0.9,
                    },
                    {
                        "part_name": "keyboard",
                        "bbox": {"x": 10, "y": 210, "width": 180, "height": 180},
                        "confidence": 0.8,
                    },
                ],
            }

            extractor = AILayoutExtractor(self.config)
            sample_image = Image.new("RGB", (400, 400), color="white")

            with mock.patch.object(extractor, "_render_page_image", return_value=sample_image), \
                mock.patch.object(extractor, "_call_ai_for_layout", return_value=layout), \
                mock.patch.object(extractor, "_validate_layout", return_value=None):
                result = extractor.extract_parts_pdf(pdf_path, output_path, margin_px=10)

            self.assertTrue(os.path.exists(output_path))
            self.assertEqual(result["total_pages"], 1)
            self.assertEqual(result["total_regions"], 2)

    def test_extract_parts_pdf_low_confidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "input.pdf")
            output_path = os.path.join(temp_dir, "output.pdf")
            create_sample_pdf(pdf_path)

            layout = {
                "schema_version": "1.0",
                "page_index": 0,
                "image_width": 400,
                "image_height": 400,
                "confidence": 0.4,
                "parts": [
                    {
                        "part_name": "vocal",
                        "bbox": {"x": 10, "y": 10, "width": 180, "height": 180},
                        "confidence": 0.4,
                    }
                ],
            }

            extractor = AILayoutExtractor(self.config)
            sample_image = Image.new("RGB", (400, 400), color="white")

            with mock.patch.object(extractor, "_render_page_image", return_value=sample_image), \
                mock.patch.object(extractor, "_call_ai_for_layout", return_value=layout), \
                mock.patch.object(extractor, "_validate_layout", return_value=None):
                with self.assertRaises(AILayoutError):
                    extractor.extract_parts_pdf(pdf_path, output_path, margin_px=0)


if __name__ == "__main__":
    unittest.main()
