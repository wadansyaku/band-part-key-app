import base64
import io
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import fitz
from PIL import Image

AI_LAYOUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "page_index",
        "image_width",
        "image_height",
        "confidence",
        "parts",
    ],
    "properties": {
        "schema_version": {"type": "string", "const": "1.0"},
        "page_index": {"type": "integer", "minimum": 0},
        "image_width": {"type": "integer", "minimum": 1},
        "image_height": {"type": "integer", "minimum": 1},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "parts": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["part_name", "bbox", "confidence"],
                "properties": {
                    "part_name": {
                        "type": "string",
                        "enum": ["vocal", "keyboard"],
                    },
                    "bbox": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["x", "y", "width", "height"],
                        "properties": {
                            "x": {"type": "number", "minimum": 0},
                            "y": {"type": "number", "minimum": 0},
                            "width": {"type": "number", "minimum": 1},
                            "height": {"type": "number", "minimum": 1},
                        },
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
            },
        },
    },
}


@dataclass
class AILayoutResult:
    layout: Dict
    image: Image.Image


class AILayoutError(RuntimeError):
    pass


class AILayoutExtractor:
    def __init__(self, config: Dict):
        self.api_key = config.get("AI_API_KEY")
        self.api_base_url = config.get("AI_BASE_URL", "https://api.openai.com/v1/responses")
        self.model = config.get("AI_MODEL", "gpt-4o-mini")
        self.confidence_threshold = float(config.get("AI_CONFIDENCE_THRESHOLD", 0.6))
        self.image_dpi = int(config.get("AI_IMAGE_DPI", 200))
        self.max_pages = int(config.get("AI_MAX_PAGES", 10))
        self.request_timeout = int(config.get("AI_REQUEST_TIMEOUT", 60))

    def extract_layout_for_page(self, pdf_path: str, page_index: int) -> AILayoutResult:
        pdf = fitz.open(pdf_path)
        try:
            image = self._render_page_image(pdf, page_index)
            layout = self._call_ai_for_layout(image, page_index)
            self._validate_layout(layout)
            return AILayoutResult(layout=layout, image=image)
        finally:
            pdf.close()

    def extract_parts_pdf(self, pdf_path: str, output_path: str, margin_px: int) -> Dict:
        if not self.api_key:
            raise AILayoutError("AI_API_KEYが設定されていません")

        pdf = fitz.open(pdf_path)
        layouts: List[Tuple[Dict, Image.Image]] = []

        try:
            page_count = min(self.max_pages, len(pdf))
            for page_index in range(page_count):
                image = self._render_page_image(pdf, page_index)
                layout = self._call_ai_for_layout(image, page_index)
                self._validate_layout(layout)
                layouts.append((layout, image))

            overall_confidence = min(layout["confidence"] for layout, _ in layouts)
            if overall_confidence < self.confidence_threshold:
                raise AILayoutError("AIレイアウトの信頼度が低いため高速モードに切り替えます")

            output_pdf = fitz.open()
            total_regions = 0

            for layout, image in layouts:
                for part in layout["parts"]:
                    bbox = part["bbox"]
                    crop_box = self._apply_margin(
                        bbox,
                        margin_px,
                        layout["image_width"],
                        layout["image_height"],
                    )
                    cropped = image.crop(
                        (
                            int(crop_box["x"]),
                            int(crop_box["y"]),
                            int(crop_box["x"] + crop_box["width"]),
                            int(crop_box["y"] + crop_box["height"]),
                        )
                    )
                    self._append_image_page(output_pdf, cropped)
                    total_regions += 1

            output_pdf.save(output_path)
            output_pdf.close()

            return {
                "total_pages": page_count,
                "total_regions": total_regions,
                "confidence": overall_confidence,
            }
        finally:
            pdf.close()

    def _render_page_image(self, pdf: fitz.Document, page_index: int) -> Image.Image:
        page = pdf[page_index]
        matrix = fitz.Matrix(self.image_dpi / 72, self.image_dpi / 72)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_data = pix.tobytes("png")
        return Image.open(io.BytesIO(img_data))

    def _call_ai_for_layout(self, image: Image.Image, page_index: int) -> Dict:
        import requests

        if not self.api_key:
            raise AILayoutError("AI_API_KEYが設定されていません")

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = (
            "あなたはバンドスコアのページ画像から、ボーカルとキーボードの領域を抽出する"
            "レイアウト解析AIです。必ず指定のJSON Schemaに厳密準拠したJSONのみを返してください。"
            "領域は画像ピクセル座標で、左上原点のbbox(x,y,width,height)で返します。"
            "不明な場合でも推定し、confidenceを下げてください。"
        )

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": "You are a layout analysis assistant.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_text",
                            "text": (
                                "出力はJSON Schemaに従うこと。schema_versionは1.0固定。"
                                "page_indexはリクエストと同じ値にする。"
                                "image_width/image_heightは入力画像のピクセルサイズ。"
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_b64}",
                        },
                    ],
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ai_layout_schema",
                    "schema": AI_LAYOUT_SCHEMA,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.api_base_url,
            headers=headers,
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        response_json = response.json()
        layout_text = self._extract_layout_text(response_json)
        layout = json.loads(layout_text)
        layout["page_index"] = page_index
        return layout

    def _extract_layout_text(self, response_json: Dict) -> str:
        if "output" in response_json:
            for output in response_json["output"]:
                for content in output.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        return content.get("text", "")
        if "output_text" in response_json:
            return response_json["output_text"]
        raise AILayoutError("AIレスポンスからJSONを取得できませんでした")

    def _validate_layout(self, layout: Dict) -> None:
        from jsonschema import validate, ValidationError

        try:
            validate(instance=layout, schema=AI_LAYOUT_SCHEMA)
        except ValidationError as exc:
            raise AILayoutError(f"AI出力がスキーマに一致しません: {exc.message}") from exc

        for part in layout.get("parts", []):
            if part["confidence"] < self.confidence_threshold:
                raise AILayoutError("AIレイアウトの信頼度が低いため高速モードに切り替えます")

    def _apply_margin(self, bbox: Dict, margin_px: int, max_width: int, max_height: int) -> Dict:
        x = max(bbox["x"] - margin_px, 0)
        y = max(bbox["y"] - margin_px, 0)
        width = min(bbox["width"] + margin_px * 2, max_width - x)
        height = min(bbox["height"] + margin_px * 2, max_height - y)
        return {"x": x, "y": y, "width": width, "height": height}

    def _append_image_page(self, output_pdf: fitz.Document, image: Image.Image) -> None:
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        img_data = image_bytes.getvalue()
        width, height = image.size

        page = output_pdf.new_page(width=width, height=height)
        page.insert_image(fitz.Rect(0, 0, width, height), stream=img_data)
