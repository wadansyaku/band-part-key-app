import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import fitz  # PyMuPDF

class OCRProcessor:
    """OCR処理のコアクラス"""
    
    def __init__(self):
        # 利用可能な言語を確認して設定
        try:
            import subprocess
            result = subprocess.run(['tesseract', '--list-langs'], 
                                  capture_output=True, text=True)
            langs = result.stdout.lower()
            
            if 'jpn' in langs and 'eng' in langs:
                self.lang = 'jpn+eng'
            elif 'jpn' in langs:
                self.lang = 'jpn'
            else:
                self.lang = 'eng'  # デフォルトは英語
                
            print(f"OCR言語設定: {self.lang}")
        except:
            self.lang = 'eng'  # エラー時は英語
        
        # 楽器名のキーワード（OCR誤認識を考慮）
        self.instrument_patterns = {
            'keyboard': [
                'KEYBOARD', 'KEYBOARDS', 'KEY', 'KEYS', 'キーボード', 'キーボ一ド',
                'Kb', 'KB', 'K.B.', 'Keyb', 'KEY BOARD', 'Key.', 'key'
            ],
            'piano': [
                'PIANO', 'PIANOS', 'Pf', 'Pno', 'ピアノ', 'ピアノ', 
                'pf.', 'Piano', 'P.f.', 'Pno.', 'ACOUSTIC PIANO', 'A.Piano', 'A.Pf'
            ],
            'synth': [
                'SYNTH', 'SYNTHESIZER', 'シンセ', 'シンセサイザー', 'シンセサイザ一',
                'Syn', 'SYN.', 'SYNTH.', 'Synthesizer', 'Syn.'
            ],
            'organ': [
                'ORGAN', 'ORG', 'オルガン', 'オルガソ', 'Org', 'ORG.', 'HAMMOND', 'Ham.'
            ],
            'electric_piano': [
                'ELECTRIC PIANO', 'E.PIANO', 'EP', 'エレピ', 'エレクトリックピアノ',
                'E.P.', 'E-PIANO', 'ELEC.PIANO', 'ELECTRIC P.', 'El.Piano', 'E.Pf'
            ],
            'vocal': [
                'VOCAL', 'VOCALS', 'ボーカル', 'ボ一カル', 'Vo', 'Vo.', 'VOC', 
                'VOICE', 'LEAD VOCAL', 'L.Vo', 'MELODY', 'メロディ', '歌'
            ],
            'guitar': [
                'GUITAR', 'GUITARS', 'ギター', 'ギタ一', 'Gt', 'Gt.', 'GTR',
                'E.GUITAR', 'A.GUITAR', 'ELEC.GUITAR', 'ACOUSTIC GUITAR'
            ],
            'bass': [
                'BASS', 'ベース', 'ベ一ス', 'Ba', 'Ba.', 'E.BASS', 'ELECTRIC BASS',
                'E.Ba', 'BASS GUITAR', 'B.Gt'
            ],
            'drums': [
                'DRUMS', 'DRUM', 'ドラム', 'ドラムス', 'Dr', 'Dr.', 'Ds', 'Ds.',
                'PERCUSSION', 'PERC', 'パーカッション'
            ],
            'chord': [
                'CHORD', 'CHORDS', 'コード', 'コ一ド', 'C', 'Ch', 'CHO', 'HARMONY'
            ]
        }
        
    def extract_text_from_page(self, pdf_path, page_num):
        """PDFページからOCRでテキストを抽出"""
        try:
            # PDFページを画像に変換
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[page_num]
            
            # 高解像度で画像化（OCR精度向上のため）
            mat = fitz.Matrix(300/72.0, 300/72.0)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            pdf_document.close()
            
            # PIL Imageに変換
            img = Image.open(io.BytesIO(img_data))
            
            # 画像の前処理（OCR精度向上）
            processed_img = self._preprocess_image(img)
            
            # OCR実行
            try:
                text = pytesseract.image_to_string(processed_img, lang=self.lang)
                return text
            except Exception as e:
                print(f"OCRエラー: {str(e)}")
                return ""
                
        except Exception as e:
            print(f"ページ処理エラー: {str(e)}")
            return ""
    
    def _preprocess_image(self, img):
        """OCR前の画像前処理"""
        # PIL ImageをOpenCV形式に変換
        img_array = np.array(img)
        
        # グレースケール変換
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # ノイズ除去
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 二値化（楽譜は通常白背景に黒い音符）
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # モルフォロジー処理でテキストを強調
        kernel = np.ones((2,2), np.uint8)
        morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # PIL Imageに戻す
        return Image.fromarray(morphed)
    
    def find_instrument_regions(self, pdf_path, page_num):
        """ページ内の楽器名が記載されている領域を検出"""
        try:
            # PDFページを画像に変換
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[page_num]
            
            # 画像化
            mat = fitz.Matrix(150/72.0, 150/72.0)  # 150 DPI（領域検出用）
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            pdf_document.close()
            
            # OpenCV形式に変換
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # テキスト領域の検出
            # 楽器名は通常、楽譜の左端または上部に記載
            height, width = gray.shape
            
            # 左端領域（幅の20%）
            left_region = gray[:, :int(width * 0.2)]
            
            # 上部領域（高さの15%）
            top_region = gray[:int(height * 0.15), :]
            
            regions = {
                'left': left_region,
                'top': top_region,
                'full': gray  # フルページも念のため
            }
            
            # 各領域でOCRを実行
            detected_instruments = []
            for region_name, region_img in regions.items():
                # PIL Imageに変換してOCR
                pil_img = Image.fromarray(region_img)
                text = pytesseract.image_to_string(pil_img, lang=self.lang)
                
                # 楽器名を検索
                instruments = self._search_instruments_in_text(text)
                if instruments:
                    detected_instruments.extend(instruments)
            
            return list(set(detected_instruments))  # 重複を除去
            
        except Exception as e:
            print(f"楽器領域検出エラー: {str(e)}")
            return []
    
    def _search_instruments_in_text(self, text):
        """テキストから楽器名を検索"""
        detected = []
        text_upper = text.upper()
        
        # 各楽器のパターンをチェック
        for instrument, patterns in self.instrument_patterns.items():
            for pattern in patterns:
                if pattern in text_upper:
                    detected.append(instrument)
                    break
        
        return detected
    
    def detect_keyboard_parts(self, pdf_path, page_num):
        """キーボードパートの存在を検出"""
        # ページ全体のOCR
        full_text = self.extract_text_from_page(pdf_path, page_num)
        
        # 楽器領域の検出
        region_instruments = self.find_instrument_regions(pdf_path, page_num)
        
        # 結果を統合
        all_instruments = self._search_instruments_in_text(full_text)
        all_instruments.extend(region_instruments)
        
        # キーボード系楽器の存在確認
        keyboard_instruments = ['keyboard', 'piano', 'synth', 'organ', 'electric_piano']
        has_keyboard = any(inst in all_instruments for inst in keyboard_instruments)
        
        return {
            'has_keyboard': has_keyboard,
            'detected_instruments': list(set(all_instruments)),
            'ocr_text_preview': full_text[:200] if full_text else "テキスト検出なし"
        }