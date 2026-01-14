import fitz  # PyMuPDF
import os
from PIL import Image
import io
import numpy as np

class PDFProcessor:
    """PDF処理のコアクラス"""
    
    def __init__(self):
        self.temp_dir = 'temp'
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_page_count(self, pdf_path):
        """PDFのページ数を取得"""
        try:
            pdf_document = fitz.open(pdf_path)
            page_count = len(pdf_document)
            pdf_document.close()
            return page_count
        except Exception as e:
            raise Exception(f"PDFの読み込みに失敗しました: {str(e)}")
    
    def extract_pages(self, pdf_path, page_numbers, output_id):
        """指定されたページを抽出して新しいPDFを作成"""
        try:
            # 入力PDFを開く
            input_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()  # 新しいPDF
            
            # 指定されたページを追加
            for page_num in sorted(page_numbers):
                if 0 <= page_num < len(input_pdf):
                    output_pdf.insert_pdf(input_pdf, from_page=page_num, to_page=page_num)
            
            # 保存
            output_path = os.path.join(self.temp_dir, f"{output_id}_extracted.pdf")
            output_pdf.save(output_path)
            
            # クリーンアップ
            input_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            raise Exception(f"ページ抽出に失敗しました: {str(e)}")
    
    def generate_preview(self, pdf_path, page_num, file_id=None, dpi=150):
        """指定ページのプレビュー画像を生成"""
        try:
            pdf_document = fitz.open(pdf_path)
            
            if page_num < 0 or page_num >= len(pdf_document):
                raise ValueError("無効なページ番号です")
            
            # ページを取得
            page = pdf_document[page_num]
            
            # 画像に変換
            mat = fitz.Matrix(dpi/72.0, dpi/72.0)
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Imageに変換
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # プレビュー画像を保存
            preview_prefix = file_id or "preview"
            preview_path = os.path.join(self.temp_dir, f"{preview_prefix}_preview_p{page_num}.png")
            img.save(preview_path, "PNG")
            
            pdf_document.close()
            return preview_path
            
        except Exception as e:
            raise Exception(f"プレビュー生成に失敗しました: {str(e)}")
    
    def get_page_size(self, pdf_path, page_num=0):
        """ページサイズを取得"""
        try:
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[page_num]
            rect = page.rect
            width = rect.width
            height = rect.height
            pdf_document.close()
            return {"width": width, "height": height}
        except Exception as e:
            raise Exception(f"ページサイズの取得に失敗しました: {str(e)}")
    
    def merge_pdfs(self, pdf_paths, output_path):
        """複数のPDFを結合"""
        try:
            output_pdf = fitz.open()
            
            for pdf_path in pdf_paths:
                input_pdf = fitz.open(pdf_path)
                output_pdf.insert_pdf(input_pdf)
                input_pdf.close()
            
            output_pdf.save(output_path)
            output_pdf.close()
            
        except Exception as e:
            raise Exception(f"PDF結合に失敗しました: {str(e)}")
