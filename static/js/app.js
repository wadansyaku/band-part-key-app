// グローバル変数
let currentFileId = null;
let selectedPages = new Set();
let analysisData = null;

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    setupUploadArea();
    setupExtractionModeHandlers();
});

// アップロードエリアの設定
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    // ドラッグ&ドロップイベント
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
    
    // ファイル選択イベント
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

// ファイルアップロード処理
async function handleFileUpload(file) {
    // ファイルタイプチェック
    if (file.type !== 'application/pdf') {
        showError('PDFファイルのみアップロード可能です');
        return;
    }
    
    // ファイルサイズチェック（50MB）
    if (file.size > 50 * 1024 * 1024) {
        showError('ファイルサイズが大きすぎます（最大50MB）');
        return;
    }
    
    // アップロード開始
    showUploadProgress();
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'アップロードに失敗しました');
        }
        
        const data = await response.json();
        currentFileId = data.id;
        
        // 解析を開始
        await analyzeScore();
        
    } catch (error) {
        showError(error.message);
        hideUploadProgress();
    }
}

// 楽譜解析
async function analyzeScore() {
    try {
        const response = await fetch(`/api/analyze/${currentFileId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '解析に失敗しました');
        }
        
        analysisData = await response.json();
        hideUploadProgress();
        displayAnalysisResults(analysisData.analysis);
        
    } catch (error) {
        showError(error.message);
        hideUploadProgress();
    }
}

// 解析結果の表示
function displayAnalysisResults(analysis) {
    const analysisSection = document.getElementById('analysis-section');
    const resultsDiv = document.getElementById('analysis-results');
    
    // 簡易表示モード
    let html = '';
    
    // ページ数を表示
    if (analysis.page_count) {
        html += '<div class="mb-4">';
        html += `<h4>PDF情報</h4>`;
        html += `<p>ページ数: ${analysis.page_count}ページ</p>`;
        html += `<p class="text-success">✓ 全ページを自動的に処理します</p>`;
        html += '</div>';
    }
    
    // PDFタイプの検出結果を表示
    if (analysis.pdf_type) {
        html += '<div class="mb-4 p-3 bg-light rounded">';
        html += '<h5><i class="fas fa-info-circle"></i> PDFタイプ自動検出</h5>';
        
        const pdfType = analysis.pdf_type;
        let typeLabel = '';
        let typeClass = '';
        
        switch(pdfType.type) {
            case 'image_based':
                typeLabel = '画像ベースPDF';
                typeClass = 'text-warning';
                break;
            case 'text_based':
                typeLabel = 'テキストベースPDF';
                typeClass = 'text-success';
                break;
            case 'hybrid':
                typeLabel = 'ハイブリッドPDF';
                typeClass = 'text-info';
                break;
            default:
                typeLabel = '不明なタイプ';
                typeClass = 'text-secondary';
        }
        
        html += `<p class="${typeClass}"><strong>タイプ: ${typeLabel}</strong> (信頼度: ${Math.round(pdfType.confidence * 100)}%)</p>`;
        
        // 詳細情報
        if (pdfType.details) {
            html += '<small class="text-muted">';
            html += `テキストブロック数: ${pdfType.details.text_block_count}、`;
            html += `画像数: ${pdfType.details.image_count}`;
            html += '</small>';
        }
        
        // 推奨事項
        if (pdfType.details && pdfType.details.recommendations) {
            html += '<div class="mt-2">';
            html += '<strong>推奨:</strong>';
            html += '<ul class="mb-0">';
            pdfType.details.recommendations.forEach(rec => {
                html += `<li><small>${rec}</small></li>`;
            });
            html += '</ul>';
            html += '</div>';
        }
        
        html += '</div>';
    }
    
    // 抽出方法の推奨を表示
    if (analysis.extraction_recommendation) {
        const rec = analysis.extraction_recommendation;
        
        // 推奨される抽出方法を自動選択
        if (rec.recommended_method === 'image_based') {
            // 画像ベース抽出を推奨
            document.getElementById('use-image-based-check')?.click();
        } else if (rec.recommended_method === 'measure_based' || rec.recommended_method === 'smart') {
            // スマート抽出を推奨
            document.getElementById('smartMode')?.click();
        }
        
        // OCRが必要な場合は警告を表示
        if (rec.use_ocr) {
            html += '<div class="alert alert-warning">';
            html += '<i class="fas fa-exclamation-triangle"></i> ';
            html += 'このPDFは画像ベースのため、OCR処理が必要です。処理に時間がかかる場合があります。';
            html += '</div>';
        }
    }
    
    // 抽出オプションを表示
    html += '<div class="extraction-options">';
    html += '<h4>抽出設定</h4>';
    html += '<p class="mb-3">以下の設定でキーボードパートを抽出します：</p>';
    html += '</div>';
    
    resultsDiv.innerHTML = html;
    analysisSection.style.display = 'block';
    analysisSection.classList.add('fade-in');
    
    // 全ページを自動選択
    for (let i = 0; i < analysis.page_count; i++) {
        selectedPages.add(i);
    }
    
    // 抽出ボタンを有効化
    document.getElementById('extract-btn').disabled = false;
}

// ページ選択の切り替え（現在は使用しない）
function togglePageSelection(pageNum) {
    // 自動全ページ処理のため不要
}

// プレビュー表示
function showPreview(pageNum) {
    event.stopPropagation(); // ページ選択を防ぐ
    
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    const previewImage = document.getElementById('preview-image');
    
    previewImage.src = `/api/preview/${currentFileId}/${pageNum}`;
    modal.show();
}

// パート抽出
async function extractParts() {
    if (selectedPages.size === 0) {
        showError('ページを選択してください');
        return;
    }
    
    showLoading('楽譜を抽出中...');
    
    try {
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                selected_pages: Array.from(selectedPages).sort((a, b) => a - b),
                mode: 'smart',
                selected_parts: ['vocal', 'keyboard'],
                measures_per_line: 4,
                show_lyrics: true,
                score_preset: '',
                integrated_vocal: true,
                use_image_based: false,
                use_final_smart: true
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '抽出に失敗しました');
        }
        
        const data = await response.json();
        hideLoading();
        
        // ダウンロードを開始
        window.location.href = `/api/download/${data.output_id}`;
        
        // 成功メッセージ
        showSuccess('PDFの抽出が完了しました！');
        
    } catch (error) {
        showError(error.message);
        hideLoading();
    }
}

// ユーティリティ関数
function showUploadProgress() {
    document.getElementById('upload-progress').style.display = 'block';
    document.getElementById('upload-area').style.display = 'none';
    
    // プログレスバーをアニメーション
    const progressBar = document.querySelector('#upload-progress .progress-bar');
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress > 90) {
            progress = 90;
            clearInterval(interval);
        }
        progressBar.style.width = progress + '%';
        progressBar.textContent = Math.floor(progress) + '%';
    }, 300);
}

function hideUploadProgress() {
    document.getElementById('upload-progress').style.display = 'none';
    document.getElementById('upload-area').style.display = 'block';
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <strong>エラー:</strong> ${message}
        <button type="button" class="btn-close float-end" onclick="this.parentElement.style.display='none'"></button>
    `;
    errorDiv.style.display = 'block';
    
    // スクロールしてエラーを表示
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 8000);
}

function showSuccess(message) {
    // 成功メッセージ用の要素を作成
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    successDiv.style.zIndex = '9999';
    successDiv.style.maxWidth = '500px';
    successDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(successDiv);
    
    // アニメーションで表示
    setTimeout(() => {
        successDiv.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        successDiv.remove();
    }, 5000);
}

function showLoading(message = '処理中です...') {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-overlay';
    loadingDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-light" role="status" style="width: 4rem; height: 4rem;">
                <span class="visually-hidden">処理中...</span>
            </div>
            <p class="text-light mt-3 fs-5">${message}</p>
            <div class="progress mt-3" style="width: 300px; margin: 0 auto;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 100%"></div>
            </div>
        </div>
    `;
    document.body.appendChild(loadingDiv);
}

function hideLoading() {
    const loadingDiv = document.querySelector('.loading-overlay');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// 楽器名の表示用変換
function getInstrumentDisplayName(instrument) {
    const displayNames = {
        'keyboard': 'キーボード',
        'piano': 'ピアノ',
        'synth': 'シンセサイザー',
        'organ': 'オルガン',
        'electric_piano': 'エレクトリックピアノ',
        'vocal': 'ボーカル',
        'guitar': 'ギター',
        'bass': 'ベース',
        'drums': 'ドラム',
        'chord': 'コード'
    };
    return displayNames[instrument] || instrument;
}

// 組み合わせ選択（現在は使用しない）
function selectCombination(index) {
    // 簡易モードでは使用しない
    return;
}

// カスタムパート検索
async function searchCustomPart() {
    const input = document.getElementById('custom-part-input').value.trim();
    if (!input) {
        showError('検索キーワードを入力してください');
        return;
    }
    
    // カンマで区切られたキーワードを配列に変換
    const keywords = input.split(',').map(k => k.trim()).filter(k => k);
    
    // カスタム検索APIを呼び出す
    try {
        const response = await fetch('/api/search_custom_parts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                keywords: keywords
            })
        });
        
        if (!response.ok) {
            throw new Error('検索に失敗しました');
        }
        
        const data = await response.json();
        
        // 検索結果に基づいてページを選択
        selectedPages.clear();
        data.matching_pages.forEach(pageNum => {
            selectedPages.add(pageNum);
            const pageItem = document.querySelector(`[data-page="${pageNum}"]`);
            if (pageItem) {
                pageItem.classList.add('selected');
            }
        });
        
        // 他のページの選択を解除
        document.querySelectorAll('.page-item').forEach(item => {
            const pageNum = parseInt(item.dataset.page);
            if (!selectedPages.has(pageNum)) {
                item.classList.remove('selected');
            }
        });
        
        // 抽出ボタンの有効/無効
        document.getElementById('extract-btn').disabled = selectedPages.size === 0;
        
        // 結果をフィードバック
        if (data.matching_pages.length > 0) {
            showSuccess(`${data.matching_pages.length}ページで「${keywords.join(', ')}」が見つかりました`);
        } else {
            showError(`「${keywords.join(', ')}」を含むページが見つかりませんでした`);
        }
        
    } catch (error) {
        showError(error.message);
    }
}

// 抽出モードハンドラーの設定
function setupExtractionModeHandlers() {
    const modeRadios = document.querySelectorAll('input[name="extractMode"]');
    const smartPartSelection = document.getElementById('smart-part-selection');
    
    if (!modeRadios || !smartPartSelection) return;
    
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            // スマートモードの場合のみパート選択を表示
            if (this.value === 'smart') {
                smartPartSelection.style.display = 'block';
            } else {
                smartPartSelection.style.display = 'none';
            }
        });
    });
    
    // 初期状態の設定
    const selectedMode = document.querySelector('input[name="extractMode"]:checked');
    if (selectedMode && selectedMode.value === 'smart') {
        smartPartSelection.style.display = 'block';
    } else {
        smartPartSelection.style.display = 'none';
    }
}