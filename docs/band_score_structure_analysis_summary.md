# Band Score Structure Analysis Summary

## Overview
Analysis of band score PDFs from `/Users/Yodai/band_part_key_app/input_example/` reveals important structural characteristics that need to be considered for keyboard part extraction.

## Key Findings

### 1. Multiple Instruments on Same Page
Band scores typically display **multiple instrument parts vertically on the same page**. Each page is divided into several "staff systems" containing different instruments:

- **忘れられないの.pdf**: 
  - Page 1: 7 instruments (Vocal, Guitar I, Guitar II, Keyboard I, Synth, Bass, Drums)
  - Pages 2-3: 6 instruments repeated twice per page (12 total instances)
  
- **だから僕は音楽を辞めた.pdf**: 
  - Uses a different layout with instrument names on the left margin
  - Multiple instruments share each page but text extraction was limited
  
- **イエスタデイ バンドスコア.pdf**: 
  - Similar multi-instrument layout but text extraction was challenging

### 2. Instrument Labeling
Instruments are labeled on the **left side of their staff lines**. Common keyboard-related labels found:
- Keyboard I / Keyb. I
- Piano / Pf / Pno
- Synth / (Synth.)
- Organ
- Electric Piano

### 3. Staff System Organization
Each page contains one or more "staff systems" where:
- A staff system is a complete set of all instruments playing together
- Systems are separated by larger vertical gaps
- Each instrument within a system has its own staff (typically 2 staves for keyboard instruments)

### 4. Extraction Requirements

#### Current Limitation
The current application extracts **entire pages**, which is problematic because:
- It includes all instruments on the page, not just keyboard parts
- Creates unnecessary content in the extracted PDF
- Makes it harder for musicians to read only their part

#### Recommended Solution
**Extract specific regions (rows/sections) instead of full pages:**

1. **Identify keyboard instruments** by their labels (e.g., "Keyboard", "Piano", "Synth")
2. **Define extraction zones** that include:
   - The instrument label
   - The staff lines for that instrument
   - A small margin above and below
   - The full width of the page

3. **Extract multiple zones per page** when keyboards appear in multiple staff systems

### 5. Visual Examples

The analysis generated visualization images showing:
- **Red boxes**: Detected instrument labels
- **Green zones**: Recommended extraction areas for keyboard parts
- **Blue dashed boxes**: Complete staff systems

Example extraction zones for "忘れられないの.pdf":
- Page 1: Two keyboard zones detected
  - Synth: Y position 1241-1456 pixels
  - Keyboard I: Y position 1275-1490 pixels
- Page 2: Two Keyb. I instances (in different staff systems)
- Page 3: Similar to page 2

## Implementation Recommendations

1. **Modify PDF extraction logic** to:
   - Parse pages to find instrument labels
   - Calculate bounding boxes for keyboard-related instruments
   - Extract only those regions instead of full pages

2. **Handle multiple keyboard parts**:
   - Some scores have multiple keyboard instruments (e.g., Keyboard I and Synth)
   - Allow users to select which keyboard parts to extract

3. **Preserve quality**:
   - Ensure extracted regions maintain original resolution
   - Include sufficient margins to capture all musical notation

4. **User interface improvements**:
   - Show preview with highlighted extraction zones
   - Allow manual adjustment of extraction boundaries if needed

## Conclusion

The analysis confirms that **band scores require region-based extraction rather than page-based extraction**. Each page contains multiple instruments arranged vertically, and extracting entire pages includes unwanted content from other instruments. The application should be updated to identify and extract only the keyboard-specific regions from each page.