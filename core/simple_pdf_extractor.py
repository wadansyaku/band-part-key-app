"""
最小限のPDF抽出機能（フォールバック用）
"""

import fitz
import os

class SimplePDFExtractor:
    """シンプルなPDF抽出（依存関係最小）"""
    
    def extract_pages(self, pdf_path, pages=None, output_name=None):
        """単純なページ抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力ファイル名
            if not output_name:
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_name = f"{base_name}_extracted.pdf"
            
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                output_name
            )
            
            # ページを抽出
            if pages:
                for page_num in pages:
                    if page_num < len(src_pdf):
                        output_pdf.insert_pdf(src_pdf, from_page=page_num, to_page=page_num)
            else:
                # 全ページ
                output_pdf.insert_pdf(src_pdf)
            
            # 保存
            if len(output_pdf) > 0:
                output_pdf.save(output_path)
                src_pdf.close()
                output_pdf.close()
                return output_path
            else:
                src_pdf.close()
                output_pdf.close()
                return None
                
        except Exception as e:
            print(f"SimplePDFExtractor error: {e}")
            return None