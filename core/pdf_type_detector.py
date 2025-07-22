#!/usr/bin/env python3
"""
PDFの種類を自動検出
テキストベース、画像ベース、ハイブリッドを識別
"""

import fitz
import os

class PDFTypeDetector:
    """PDFの種類を検出"""
    
    def __init__(self):
        self.min_text_blocks = 5  # テキストベースと判定する最小ブロック数
        self.min_text_ratio = 0.1  # テキストベースと判定する最小テキスト面積比
    
    def detect_pdf_type(self, pdf_path):
        """PDFのタイプを検出"""
        result = {
            'type': 'unknown',
            'confidence': 0,
            'details': {
                'has_text': False,
                'has_images': False,
                'text_block_count': 0,
                'image_count': 0,
                'average_text_ratio': 0,
                'recommendations': []
            }
        }
        
        try:
            pdf = fitz.open(pdf_path)
            
            total_text_blocks = 0
            total_images = 0
            total_text_area = 0
            total_page_area = 0
            
            # 最初の5ページを分析
            for page_num in range(min(5, len(pdf))):
                page = pdf[page_num]
                page_rect = page.rect
                page_area = page_rect.width * page_rect.height
                total_page_area += page_area
                
                # テキストブロックの検出
                text_dict = page.get_text("dict")
                text_blocks = text_dict.get("blocks", [])
                
                page_text_area = 0
                for block in text_blocks:
                    if "lines" in block:
                        total_text_blocks += 1
                        # テキストエリアの計算
                        bbox = block.get("bbox", [0, 0, 0, 0])
                        block_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                        page_text_area += block_area
                
                total_text_area += page_text_area
                
                # 画像の検出
                images = page.get_images()
                total_images += len(images)
            
            pdf.close()
            
            # 結果の集計
            result['details']['text_block_count'] = total_text_blocks
            result['details']['image_count'] = total_images
            result['details']['has_text'] = total_text_blocks > 0
            result['details']['has_images'] = total_images > 0
            
            # テキスト面積比の計算
            if total_page_area > 0:
                text_ratio = total_text_area / total_page_area
                result['details']['average_text_ratio'] = text_ratio
            
            # PDFタイプの判定
            if total_text_blocks >= self.min_text_blocks and text_ratio > self.min_text_ratio:
                if total_images > 0:
                    result['type'] = 'hybrid'
                    result['confidence'] = 0.8
                    result['details']['recommendations'].append('テキストベース抽出を推奨')
                else:
                    result['type'] = 'text_based'
                    result['confidence'] = 0.9
                    result['details']['recommendations'].append('通常の抽出方法を使用')
            elif total_images > 0 and total_text_blocks < self.min_text_blocks:
                result['type'] = 'image_based'
                result['confidence'] = 0.9
                result['details']['recommendations'].append('画像ベース抽出（OCR）を推奨')
            else:
                result['type'] = 'unknown'
                result['confidence'] = 0.3
                result['details']['recommendations'].append('手動で抽出方法を選択してください')
            
            # 詳細な推奨事項
            if result['type'] == 'image_based':
                result['details']['recommendations'].append('OCRの精度向上のため、高解像度スキャンを推奨')
                result['details']['recommendations'].append('楽器名が正しく認識されない場合は手動調整が必要')
            elif result['type'] == 'text_based':
                result['details']['recommendations'].append('楽器ラベルが検出可能です')
                result['details']['recommendations'].append('プリセット抽出が利用可能')
            
            return result
            
        except Exception as e:
            print(f"PDF type detection error: {str(e)}")
            result['details']['error'] = str(e)
            return result
    
    def analyze_for_extraction(self, pdf_path):
        """抽出に適した設定を分析"""
        type_info = self.detect_pdf_type(pdf_path)
        
        extraction_config = {
            'recommended_method': 'standard',
            'use_ocr': False,
            'use_image_processing': False,
            'preset_available': False,
            'confidence': type_info['confidence']
        }
        
        if type_info['type'] == 'image_based':
            extraction_config['recommended_method'] = 'image_based'
            extraction_config['use_ocr'] = True
            extraction_config['use_image_processing'] = True
        elif type_info['type'] == 'text_based':
            extraction_config['recommended_method'] = 'measure_based'
            extraction_config['preset_available'] = True
        elif type_info['type'] == 'hybrid':
            extraction_config['recommended_method'] = 'smart'
            extraction_config['use_ocr'] = True
            extraction_config['preset_available'] = True
        
        return {
            'pdf_type': type_info,
            'extraction_config': extraction_config
        }