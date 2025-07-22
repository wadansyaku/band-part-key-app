# Core Modules

This directory contains the essential extraction modules for Band Part Key App.

## Active Modules (Currently Used)

### Main Extractors
- `final_smart_extractor.py` - **Primary extractor** using 4-measure fixed layout with integrated vocal parts
- `pdf_type_detector.py` - Automatic detection of PDF type (image-based vs text-based)
- `pdf_processor.py` - Basic PDF processing utilities

### Supporting Modules
- `measure_based_extractor.py` - Measure-based extraction logic (used as fallback)
- `__init__.py` - Module initialization

## Archived Modules

Other experimental extractors have been moved to `archive/extractors/` for reference.
These include various approaches tried during development:
- Advanced extractors with OCR
- Fast image processing variants
- Instrument-specific extractors
- Experimental vocal/keyboard separators

## Usage

The main entry point is `final_smart_extractor.py`:

```python
from core.final_smart_extractor import FinalSmartExtractor

extractor = FinalSmartExtractor()
output_path = extractor.extract_smart_final(pdf_path)
```