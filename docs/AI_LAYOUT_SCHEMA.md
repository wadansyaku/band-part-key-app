# AI_LAYOUT_SCHEMA

AI精度モードで使用する **画像ベースのレイアウト推定結果** のJSONスキーマです。PDFページを画像化し、AIがパート領域のbboxを推定します。

## スキーマ概要
- **JSON Schema Draft 2020-12** を前提。
- bboxは **画像ピクセル座標**（左上原点、右・下方向が正）で表します。
- `parts` はパート領域の配列で、`part_name` は `vocal` または `keyboard` のみ許可。
- `confidence` は 0.0〜1.0 の範囲。

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "page_index",
    "image_width",
    "image_height",
    "confidence",
    "parts"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "page_index": {
      "type": "integer",
      "minimum": 0
    },
    "image_width": {
      "type": "integer",
      "minimum": 1
    },
    "image_height": {
      "type": "integer",
      "minimum": 1
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "parts": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["part_name", "bbox", "confidence"],
        "properties": {
          "part_name": {
            "type": "string",
            "enum": ["vocal", "keyboard"]
          },
          "bbox": {
            "type": "object",
            "additionalProperties": false,
            "required": ["x", "y", "width", "height"],
            "properties": {
              "x": {"type": "number", "minimum": 0},
              "y": {"type": "number", "minimum": 0},
              "width": {"type": "number", "minimum": 1},
              "height": {"type": "number", "minimum": 1}
            }
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        }
      }
    }
  }
}
```

## 例
```json
{
  "schema_version": "1.0",
  "page_index": 0,
  "image_width": 1654,
  "image_height": 2339,
  "confidence": 0.82,
  "parts": [
    {
      "part_name": "vocal",
      "bbox": {"x": 90, "y": 140, "width": 1480, "height": 760},
      "confidence": 0.84
    },
    {
      "part_name": "keyboard",
      "bbox": {"x": 90, "y": 940, "width": 1480, "height": 740},
      "confidence": 0.8
    }
  ]
}
```
