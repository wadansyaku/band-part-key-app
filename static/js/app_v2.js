// グローバル変数
let currentFileId = null;
let analysisData = null;
let aiLayoutData = null;
let aiPreviewLoaded = false;

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    setupUploadArea();
    setupModeControls();
    updateAiMargin();
});

// アップロードエリアの設定
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (!uploadArea || !fileInput) {
        console.error('Upload area or file input not found');
        return;
    }
    
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

function setupModeControls() {
    const modeFast = document.getElementById('mode-fast');
    const modeAi = document.getElementById('mode-ai');
    const previewImage = document.getElementById('ai-preview-image');

    if (!modeFast || !modeAi) {
        return;
    }

    const updateModeView = () => {
        const aiPanel = document.getElementById('ai-panel');
        if (!aiPanel) {
            return;
        }
        if (modeAi.checked) {
            aiPanel.style.display = 'block';
            setAiPreviewMessage('AI解析ボタンを押してレイアウトを確認してください。');
            if (currentFileId) {
                const previewImage = document.getElementById('ai-preview-image');
                previewImage.src = `/api/preview/${currentFileId}/0`;
            }
        } else {
            aiPanel.style.display = 'none';
        }
    };

    modeFast.addEventListener('change', updateModeView);
    modeAi.addEventListener('change', updateModeView);

    if (previewImage) {
        previewImage.addEventListener('load', () => {
            if (aiPreviewLoaded) {
                renderAiOverlay();
            }
        });
    }
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
        
        // 成功メッセージを表示
        showSuccess(`ファイル「${file.name}」をアップロードしました`);
        
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
    
    if (!analysisSection || !resultsDiv) {
        console.error('Analysis section not found');
        return;
    }
    
    // 結果をクリア
    resultsDiv.innerHTML = '';
    
    // 基本情報
    const infoHtml = `
        <div class="result-item">
            <div>
                <h5><i class="bi bi-file-pdf"></i> PDF情報</h5>
                <p class="mb-0">ページ数: ${analysis.page_count}ページ</p>
            </div>
            <span class="status-badge status-ready">準備完了</span>
        </div>
    `;
    resultsDiv.innerHTML += infoHtml;
    
    // PDFタイプ情報（存在する場合）
    if (analysis.pdf_type) {
        const typeHtml = `
            <div class="result-item">
                <div>
                    <h5><i class="bi bi-info-circle"></i> PDFタイプ</h5>
                    <p class="mb-0">タイプ: ${analysis.pdf_type.type} (信頼度: ${analysis.pdf_type.confidence}%)</p>
                    ${analysis.pdf_type.details?.recommendations ? 
                        `<small class="text-muted">${analysis.pdf_type.details.recommendations.join(', ')}</small>` : ''}
                </div>
                <span class="status-badge status-complete">検出済</span>
            </div>
        `;
        resultsDiv.innerHTML += typeHtml;
    }
    
    // 抽出可能なパート
    const partsHtml = `
        <div class="result-item">
            <div>
                <h5><i class="bi bi-music-note-list"></i> 抽出されるパート</h5>
                <p class="mb-0">• ボーカル（コード・メロディ・歌詞統合）</p>
                <p class="mb-0">• キーボード</p>
            </div>
            <span class="status-badge status-ready">自動選択</span>
        </div>
    `;
    resultsDiv.innerHTML += partsHtml;
    
    // 解析セクションを表示
    analysisSection.style.display = 'block';

    const modeFast = document.getElementById('mode-fast');
    if (modeFast) {
        modeFast.checked = true;
    }

    const aiPanel = document.getElementById('ai-panel');
    if (aiPanel) {
        aiPanel.style.display = 'none';
    }

    const previewImage = document.getElementById('ai-preview-image');
    if (previewImage) {
        previewImage.src = `/api/preview/${currentFileId}/0`;
    }
    
    // 抽出ボタンを有効化
    const extractButton = document.getElementById('extract-button');
    if (extractButton) {
        extractButton.disabled = false;
    }
}

function getSelectedMode() {
    const modeAi = document.getElementById('mode-ai');
    if (modeAi && modeAi.checked) {
        return 'ai_precision';
    }
    return 'fast';
}

async function loadAiPreview() {
    if (!currentFileId) {
        showError('ファイルが選択されていません');
        return;
    }

    const message = document.getElementById('ai-preview-message');
    if (message) {
        message.textContent = 'AI解析中...';
    }

    try {
        const response = await fetch(`/api/ai-layout/${currentFileId}/0`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'AI解析に失敗しました');
        }
        const data = await response.json();
        aiLayoutData = data.layout;
        aiPreviewLoaded = true;
        renderAiOverlay();
        setAiPreviewMessage('bboxを確認し、必要ならマージンを調整してください。');
    } catch (error) {
        aiLayoutData = null;
        aiPreviewLoaded = false;
        setAiPreviewMessage(error.message);
    }
}

function renderAiOverlay() {
    const overlay = document.getElementById('ai-overlay');
    const img = document.getElementById('ai-preview-image');
    if (!overlay || !img || !aiLayoutData) {
        return;
    }

    const margin = getAiMargin();
    const imageWidth = aiLayoutData.image_width;
    const imageHeight = aiLayoutData.image_height;

    const scaleX = img.clientWidth / imageWidth;
    const scaleY = img.clientHeight / imageHeight;

    overlay.style.width = `${img.clientWidth}px`;
    overlay.style.height = `${img.clientHeight}px`;
    overlay.innerHTML = '';

    aiLayoutData.parts.forEach((part) => {
        const bbox = applyMargin(part.bbox, margin, imageWidth, imageHeight);
        const box = document.createElement('div');
        box.className = 'bbox-overlay';
        box.style.left = `${bbox.x * scaleX}px`;
        box.style.top = `${bbox.y * scaleY}px`;
        box.style.width = `${bbox.width * scaleX}px`;
        box.style.height = `${bbox.height * scaleY}px`;

        const label = document.createElement('div');
        label.className = 'bbox-label';
        label.textContent = `${part.part_name} (${Math.round(part.confidence * 100)}%)`;
        box.appendChild(label);
        overlay.appendChild(box);
    });
}

function applyMargin(bbox, margin, maxWidth, maxHeight) {
    const x = Math.max(bbox.x - margin, 0);
    const y = Math.max(bbox.y - margin, 0);
    const width = Math.min(bbox.width + margin * 2, maxWidth - x);
    const height = Math.min(bbox.height + margin * 2, maxHeight - y);
    return { x, y, width, height };
}

function getAiMargin() {
    const slider = document.getElementById('ai-margin');
    if (!slider) {
        return 20;
    }
    return parseInt(slider.value, 10);
}

function updateAiMargin() {
    const valueLabel = document.getElementById('ai-margin-value');
    if (valueLabel) {
        valueLabel.textContent = getAiMargin();
    }
    if (aiPreviewLoaded) {
        renderAiOverlay();
    }
}

function setAiPreviewMessage(text) {
    const message = document.getElementById('ai-preview-message');
    if (message) {
        message.textContent = text;
    }
}

// 抽出処理を開始
async function startExtraction() {
    if (!currentFileId) {
        showError('ファイルが選択されていません');
        return;
    }
    
    // 抽出ボタンを無効化
    const extractButton = document.getElementById('extract-button');
    if (extractButton) {
        extractButton.disabled = true;
    }
    
    // 処理中表示
    showExtractionProgress();
    
    try {
        const mode = getSelectedMode();
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                mode: mode,
                margin: getAiMargin()
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '抽出に失敗しました');
        }
        
        const result = await response.json();
        
        // 処理完了
        hideExtractionProgress();
        if (result.fallback) {
            showSuccess(`AI精度モードから高速モードへ切り替えました: ${result.fallback_message}`);
        } else {
            showSuccess('抽出が完了しました！ダウンロードを開始します...');
        }
        
        // ダウンロード
        downloadResult(result.output_id);
        
    } catch (error) {
        showError(error.message);
        hideExtractionProgress();
        if (extractButton) {
            extractButton.disabled = false;
        }
    }
}

// 結果のダウンロード
function downloadResult(outputId) {
    const downloadUrl = `/api/download/${outputId}`;
    
    // ダウンロードリンクを作成
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `extracted_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// UI表示関数
function showUploadProgress() {
    const progressDiv = document.getElementById('upload-progress');
    if (progressDiv) {
        progressDiv.style.display = 'block';
        // プログレスバーアニメーション
        const progressBar = progressDiv.querySelector('.progress-bar');
        if (progressBar) {
            let width = 0;
            const interval = setInterval(() => {
                width += 10;
                progressBar.style.width = width + '%';
                if (width >= 90) {
                    clearInterval(interval);
                }
            }, 100);
        }
    }
}

function hideUploadProgress() {
    const progressDiv = document.getElementById('upload-progress');
    if (progressDiv) {
        progressDiv.style.display = 'none';
        const progressBar = progressDiv.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = '0%';
        }
    }
}

function showExtractionProgress() {
    const progressDiv = document.getElementById('extraction-progress');
    if (progressDiv) {
        progressDiv.style.display = 'block';
    }
}

function hideExtractionProgress() {
    const progressDiv = document.getElementById('extraction-progress');
    if (progressDiv) {
        progressDiv.style.display = 'none';
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    if (errorDiv && errorText) {
        errorText.textContent = message;
        errorDiv.style.display = 'flex !important';
        
        // 5秒後に自動で非表示
        setTimeout(() => {
            errorDiv.style.display = 'none !important';
        }, 5000);
    }
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    const successText = document.getElementById('success-text');
    
    if (successDiv && successText) {
        successText.textContent = message;
        successDiv.style.display = 'flex !important';
        
        // 5秒後に自動で非表示
        setTimeout(() => {
            successDiv.style.display = 'none !important';
        }, 5000);
    }
}
