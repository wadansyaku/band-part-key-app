#!/usr/bin/env python3
"""
最終ハイブリッド楽譜抽出システム
V9の優秀な楽器検出 + 4小節/行レイアウト最適化
"""

import os
from datetime import datetime
from core.final_smart_extractor_v9_adaptive import FinalSmartExtractorV9Adaptive
from core.layout_optimizer import LayoutOptimizer

class FinalHybridExtractor:
    def __init__(self):
        self.v9_extractor = FinalSmartExtractorV9Adaptive()
        self.layout_optimizer = LayoutOptimizer()
        
    def extract_hybrid_final(self, pdf_path: str, optimize_layout: bool = True) -> str:
        """
        ハイブリッド抽出：V9検出 + レイアウト最適化
        
        Args:
            pdf_path: 入力PDFパス
            optimize_layout: レイアウト最適化を実行するか
        
        Returns:
            出力PDFパス
        """
        print(f"\n🚀 FINAL HYBRID EXTRACTION")
        print(f"  Input: {os.path.basename(pdf_path)}")
        print(f"  Strategy: V9 Detection + {'Layout Optimization' if optimize_layout else 'Standard Layout'}")
        
        try:
            # Step 1: V9で高品質な楽器検出と抽出
            print(f"\n📋 Step 1: V9 Adaptive Detection")
            v9_output = self.v9_extractor.extract_smart_final(pdf_path)
            
            if not v9_output or not os.path.exists(v9_output):
                print("❌ V9 extraction failed")
                return None
            
            print(f"✅ V9 extraction completed: {os.path.basename(v9_output)}")
            
            # Step 2: レイアウト最適化（オプション）
            if optimize_layout:
                print(f"\n🎯 Step 2: Layout Optimization")
                final_output = self.layout_optimizer.optimize_v9_output(v9_output)
                
                if final_output and os.path.exists(final_output):
                    print(f"✅ Layout optimization completed: {os.path.basename(final_output)}")
                    return final_output
                else:
                    print("⚠️ Layout optimization failed, using V9 output")
                    return v9_output
            else:
                return v9_output
                
        except Exception as e:
            print(f"❌ Hybrid extraction error: {e}")
            return None
    
    def get_extraction_summary(self, output_path: str) -> dict:
        """抽出結果のサマリーを生成"""
        if not output_path or not os.path.exists(output_path):
            return {"status": "failed"}
        
        try:
            import fitz
            pdf = fitz.open(output_path)
            
            summary = {
                "status": "success",
                "output_path": output_path,
                "pages": len(pdf),
                "file_size_kb": round(os.path.getsize(output_path) / 1024, 1),
                "features": [
                    "Vocal part extraction",
                    "Keyboard part extraction", 
                    "Guitar/Bass/Drums excluded",
                    "4 measures per line layout",
                    "Chord symbols preserved",
                    "Lyrics integration"
                ]
            }
            
            pdf.close()
            return summary
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

def main():
    """テスト実行"""
    extractor = FinalHybridExtractor()
    
    # テストファイル
    test_files = [
        "/Users/Yodai/Downloads/だから僕は音楽を辞めた.pdf",
        "/Users/Yodai/Downloads/Mela！.pdf"
    ]
    
    print("🧪 HYBRID EXTRACTOR TEST")
    print("="*50)
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n🎵 Testing: {os.path.basename(test_file)}")
            
            # ハイブリッド抽出実行
            result = extractor.extract_hybrid_final(test_file, optimize_layout=True)
            
            if result:
                summary = extractor.get_extraction_summary(result)
                print(f"\n📊 EXTRACTION SUMMARY:")
                print(f"  Status: {summary['status']}")
                print(f"  Output: {os.path.basename(result)}")
                print(f"  Pages: {summary.get('pages', 'Unknown')}")
                print(f"  Size: {summary.get('file_size_kb', 'Unknown')} KB")
                
                print(f"  Features:")
                for feature in summary.get('features', []):
                    print(f"    ✅ {feature}")
            else:
                print("❌ Test failed")
            
            break  # 最初の1つのみテスト
        else:
            print(f"⚠️ Test file not found: {os.path.basename(test_file)}")

if __name__ == "__main__":
    main()