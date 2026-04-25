/**
 * X-AnyLabeling Web Service - Main Application
 */

// Curated model prefixes per task (2 best models each)
const CURATED_MODEL_PREFIXES = {
    detection: [
        { prefix: 'yolov8n', name: 'YOLOv8n' },
        { prefix: 'yolov8s', name: 'YOLOv8s' }
    ],
    segmentation: [
        { prefix: 'sam_hq_vit_l', name: 'SAM-HQ Vit-L' },
        { prefix: 'yolov8m_seg', name: 'YOLOv8m-Seg' }
    ],
    pose: [
        { prefix: 'yolov8s_pose', name: 'YOLOv8s-Pose' },
        { prefix: 'yolov8x_pose_p6', name: 'YOLOv8x-Pose-P6' }
    ],
    ocr: [
        { prefix: 'ch_ppocr_v5', name: 'PP-OCRv5' },
        { prefix: 'ch_ppocr_v4', name: 'PP-OCRv4' }
    ],
    grounding: [
        { prefix: 'grounding_dino_api', name: 'Grounding DINO API' },
        { prefix: 'groundingdino_swint_sam2_large', name: 'Grounding DINO + SAM2' }
    ],
    classification: [
        { prefix: 'internimage', name: 'InternImage' },
        { prefix: 'yolov8s_cls', name: 'YOLOv8s-Cls' }
    ]
};

class App {
    constructor() {
        this.api = new APIClient();
        this.sessionId = null;
        this.files = [];
        this.models = [];
        this.formats = [];
        this.selectedModel = null;
        this.selectedFormat = null;
        this.currentJobId = null;
        this.pollingInterval = null;
        this.currentPreviewIndex = -1;
        this.customSavePath = null;

        this.init();
    }

    async init() {
        await this.loadModels();
        await this.loadFormats();
        this.setupEventListeners();
        this.checkHealth();
    }

    async checkHealth() {
        try {
            const health = await this.api.health();
            console.log('Service is healthy:', health);
        } catch (e) {
            console.error('Service health check failed:', e);
        }
    }

    // Load models
    async loadModels() {
        try {
            const response = await this.api.getModels();
            this.models = response.models || [];
            this.renderModels();
        } catch (e) {
            console.error('Failed to load models:', e);
            document.getElementById('model-grid').innerHTML =
                '<div class="loading">加载模型失败</div>';
        }
    }

    // Load formats
    async loadFormats() {
        try {
            const response = await this.api.getFormats();
            this.formats = response.formats || [];
            this.renderFormats();
        } catch (e) {
            console.error('Failed to load formats:', e);
        }
    }

    // Get curated models for a task
    getCuratedModelsForTask(task) {
        const prefixes = CURATED_MODEL_PREFIXES[task] || [];
        const result = [];

        for (const { prefix } of prefixes) {
            // Find first model that starts with this prefix
            const model = this.models.find(m => m.id.startsWith(prefix));
            if (model) {
                result.push(model);
            }
        }

        return result;
    }

    // Render models
    renderModels(filter = 'all') {
        const grid = document.getElementById('model-grid');

        let filteredModels;
        if (filter === 'all') {
            // Show all curated models
            filteredModels = [];
            for (const prefixes of Object.values(CURATED_MODEL_PREFIXES)) {
                for (const { prefix } of prefixes) {
                    const model = this.models.find(m => m.id.startsWith(prefix));
                    if (model && !filteredModels.find(f => f.id === model.id)) {
                        filteredModels.push(model);
                    }
                }
            }
        } else {
            filteredModels = this.getCuratedModelsForTask(filter);
        }

        if (filteredModels.length === 0) {
            grid.innerHTML = '<div class="loading">没有找到匹配的模型</div>';
            return;
        }

        grid.innerHTML = filteredModels.map(model => `
            <div class="model-card" data-model-id="${model.id}">
                <h3>${model.display_name}</h3>
                <p>${this.getTaskLabel(model.task)}</p>
            </div>
        `).join('');

        // Add click handlers
        grid.querySelectorAll('.model-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectModel(card.dataset.modelId);
            });
        });
    }

    // Render formats filtered by task
    renderFormats(task = null) {
        const grid = document.getElementById('format-grid');

        // Format support mapping by task
        const taskFormats = {
            detection: ['yolo', 'coco', 'voc', 'dota'],
            segmentation: ['yolo', 'coco', 'voc', 'mask'],
            pose: ['yolo', 'coco'],
            ocr: ['ppocr'],
            grounding: ['yolo', 'coco', 'voc', 'dota'],
            classification: [],
            obb: ['dota', 'yolo'],
            tagging: [],
            depth: [],
            tracking: ['mot', 'mots']
        };

        let formatsToShow = this.formats;
        if (task && taskFormats[task]) {
            formatsToShow = this.formats.filter(f => taskFormats[task].includes(f.id));
        }

        if (formatsToShow.length === 0) {
            grid.innerHTML = '<div class="loading">该任务无需输出格式</div>';
        } else {
            grid.innerHTML = formatsToShow.map(format => `
                <div class="format-card" data-format-id="${format.id}">
                    <h3>${format.name}</h3>
                    <p>.${format.extension}</p>
                </div>
            `).join('');
        }

        // Clear selected format when formats change
        this.selectedFormat = null;
        document.querySelectorAll('.format-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectFormat(card.dataset.formatId);
            });
        });

        this.updateProcessButton();
    }

    // Select model
    selectModel(modelId) {
        this.selectedModel = modelId;

        // Update UI
        document.querySelectorAll('.model-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.modelId === modelId);
        });

        // Find selected model and update formats based on its task
        const model = this.models.find(m => m.id === modelId);
        if (model) {
            this.renderFormats(model.task);
        }

        this.updateProcessButton();
    }

    // Select format
    selectFormat(formatId) {
        this.selectedFormat = formatId;

        // Update UI
        document.querySelectorAll('.format-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.formatId === formatId);
        });

        this.updateProcessButton();
    }

    // Update process button state
    updateProcessButton() {
        const btn = document.getElementById('process-btn');
        const canProcess = this.sessionId &&
            this.files.length > 0 &&
            this.selectedModel &&
            this.selectedFormat;
        btn.disabled = !canProcess;
    }

    // Setup event listeners
    setupEventListeners() {
        // File input
        const fileInput = document.getElementById('file-input');
        const selectBtn = document.getElementById('select-files-btn');

        selectBtn.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {
            const files = Array.from(fileInput.files);
            this.handleFiles(files);
            fileInput.value = ''; // Reset for re-selection
        });

        // Folder input - using showOpenDirectoryPicker when available
        const folderInput = document.getElementById('folder-input');
        const selectFolderBtn = document.getElementById('select-folder-btn');

        // Modern approach using showOpenDirectoryPicker
        if ('showDirectoryPicker' in window) {
            selectFolderBtn.addEventListener('click', async () => {
                try {
                    const dirHandle = await window.showDirectoryPicker();
                    this.customSavePath = dirHandle.name;
                    document.getElementById('save-path-display').textContent = dirHandle.name;
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        console.error('Directory picker error:', e);
                    }
                }
            });
        } else {
            // Fallback for browsers without showDirectoryPicker
            selectFolderBtn.addEventListener('click', () => {
                folderInput.click();
            });

            folderInput.addEventListener('change', () => {
                const files = Array.from(folderInput.files);
                if (files.length > 0) {
                    const path = files[0].webkitRelativePath.split('/')[0];
                    this.customSavePath = path;
                    document.getElementById('save-path-display').textContent = path;
                }
            });
        }

        // Model filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filter = btn.dataset.filter;
                this.selectedModel = null;
                this.selectedFormat = null;
                this.renderModels(filter);

                // Filter formats based on the selected task
                const taskForFormats = filter === 'all' ? null : filter;
                this.renderFormats(taskForFormats);

                document.querySelectorAll('.model-card').forEach(c => c.classList.remove('selected'));
                document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
                this.updateProcessButton();
            });
        });

        // Labeling mode radio buttons
        document.querySelectorAll('input[name="labeling_mode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const specificClassesContainer = document.getElementById('specific-classes-container');
                if (e.target.value === 'configured') {
                    specificClassesContainer.classList.remove('hidden');
                } else {
                    specificClassesContainer.classList.add('hidden');
                }
            });
        });

        // Process button
        document.getElementById('process-btn').addEventListener('click', () => {
            this.startProcessing();
        });

        // Reset button
        document.getElementById('reset-btn').addEventListener('click', () => {
            this.reset();
        });
    }

    // Handle uploaded files
    async handleFiles(files) {
        if (files.length === 0) return;

        // Create session if needed
        if (!this.sessionId) {
            this.sessionId = this.generateSessionId();
        }

        // Store files
        for (const file of files) {
            if (!this.files.find(f => f.name === file.name)) {
                this.files.push(file);
            }
        }

        // Show preview area and update file list
        this.showPreviewArea();
        this.renderFileList();
        this.updateFileCount();
        this.updateVideoSettings();

        // Auto preview first file
        if (this.currentPreviewIndex < 0 && this.files.length > 0) {
            this.currentPreviewIndex = 0;
            this.showPreview(0);
        }

        this.updateProcessButton();
    }

    // Update video settings visibility
    updateVideoSettings() {
        const hasVideo = this.files.some(f => f.type.startsWith('video/'));
        const videoSettings = document.getElementById('video-settings');
        if (hasVideo) {
            videoSettings.classList.add('show');
        } else {
            videoSettings.classList.remove('show');
        }
    }

    // Show preview area
    showPreviewArea() {
        document.getElementById('preview-placeholder').classList.add('hidden');
        document.getElementById('preview-content').classList.remove('hidden');
    }

    // Hide preview area
    hidePreviewArea() {
        document.getElementById('preview-placeholder').classList.remove('hidden');
        document.getElementById('preview-content').classList.add('hidden');
    }

    // Update file count
    updateFileCount() {
        document.getElementById('file-count').textContent = `${this.files.length} 个文件`;
    }

    // Render file list
    renderFileList() {
        const fileList = document.getElementById('file-list');

        fileList.innerHTML = this.files.map((file, index) => {
            const isImage = file.type.startsWith('image/');
            const isVideo = file.type.startsWith('video/');
            const isSelected = index === this.currentPreviewIndex;

            let thumbnail;
            if (isImage) {
                thumbnail = `<img src="${URL.createObjectURL(file)}" alt="${file.name}">`;
            } else if (isVideo) {
                thumbnail = `<div class="video-badge">▶</div>`;
            }

            return `
                <div class="file-item ${isSelected ? 'selected' : ''}" data-index="${index}">
                    ${thumbnail}
                    <span class="file-name">${file.name}</span>
                    <span class="file-remove" data-index="${index}">&times;</span>
                </div>
            `;
        }).join('');

        // Add click handlers for preview
        fileList.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('file-remove')) {
                    const index = parseInt(item.dataset.index);
                    this.currentPreviewIndex = index;
                    this.showPreview(index);
                    this.renderFileList(); // Re-render to update selected state
                }
            });
        });

        // Add remove handlers
        fileList.querySelectorAll('.file-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                this.removeFile(index);
            });
        });
    }

    // Remove file
    removeFile(index) {
        this.files.splice(index, 1);

        // Adjust current preview index
        if (this.currentPreviewIndex >= this.files.length) {
            this.currentPreviewIndex = this.files.length - 1;
        }

        if (this.files.length === 0) {
            this.currentPreviewIndex = -1;
            this.hidePreviewArea();
        } else {
            this.renderFileList();
            this.showPreview(this.currentPreviewIndex);
        }

        this.updateFileCount();
        this.updateProcessButton();
    }

    // Show preview
    showPreview(index) {
        if (index < 0 || index >= this.files.length) return;

        const file = this.files[index];
        const img = document.getElementById('preview-image');
        const video = document.getElementById('preview-video');
        const info = document.getElementById('preview-info');

        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');

        if (isImage) {
            img.src = URL.createObjectURL(file);
            img.classList.remove('hidden');
            video.classList.add('hidden');
            video.src = '';
        } else if (isVideo) {
            video.src = URL.createObjectURL(file);
            video.classList.remove('hidden');
            img.classList.add('hidden');
            img.src = '';
        }

        info.textContent = `${file.name} (${this.formatSize(file.size)})`;
    }

    // Start processing
    async startProcessing() {
        if (!this.sessionId || this.files.length === 0 || !this.selectedModel || !this.selectedFormat) {
            return;
        }

        // Show progress panel
        document.getElementById('progress-panel').classList.remove('hidden');
        document.getElementById('process-panel').classList.add('hidden');

        // Update progress
        this.updateProgress(0, '准备上传文件...');

        try {
            // Upload files
            for (const file of this.files) {
                await this.api.uploadFile(file, this.sessionId);
            }

            // Get frame interval for video processing
            const frameInterval = parseInt(document.getElementById('frame-interval').value) || 30;

            // Get labeling mode and specific classes
            const labelingMode = document.querySelector('input[name="labeling_mode"]:checked').value;
            let specificClasses = null;
            if (labelingMode === 'configured') {
                const classesInput = document.getElementById('specific-classes').value;
                if (classesInput.trim()) {
                    specificClasses = classesInput.split(',').map(c => c.trim()).filter(c => c);
                }
            }

            // Build options
            const options = { frame_interval: frameInterval };
            if (this.customSavePath) {
                options.save_path = this.customSavePath;
            }

            // Start processing with options
            const response = await this.api.startProcessing(
                this.sessionId,
                this.selectedModel,
                this.selectedFormat,
                options,
                labelingMode,
                specificClasses
            );

            this.currentJobId = response.job_id;
            this.pollJobStatus();

        } catch (e) {
            console.error('Processing failed:', e);
            this.updateProgress(0, `错误: ${e.message}`);
        }
    }

    // Poll job status
    async pollJobStatus() {
        if (!this.currentJobId) return;

        this.pollingInterval = setInterval(async () => {
            try {
                const status = await this.api.getJobStatus(this.currentJobId);
                this.updateProgress(status.progress, status.current_file || '');

                if (status.status === 'completed') {
                    clearInterval(this.pollingInterval);
                    this.showResult();
                } else if (status.status === 'failed') {
                    clearInterval(this.pollingInterval);
                    this.showError(status.error || '处理失败');
                }
            } catch (e) {
                console.error('Status check failed:', e);
            }
        }, 1000);
    }

    // Update progress
    updateProgress(progress, currentFile) {
        document.getElementById('progress-fill').style.width = `${progress}%`;
        document.getElementById('progress-text').textContent = `${progress}%`;
        document.getElementById('current-file').textContent = currentFile || '';
    }

    // Show result
    showResult() {
        document.getElementById('progress-panel').classList.add('hidden');
        document.getElementById('result-panel').classList.remove('hidden');

        const message = document.getElementById('result-message');
        const path = document.getElementById('result-path');

        if (this.customSavePath) {
            message.textContent = '标注已完成！';
            path.textContent = `结果已保存到: ${this.customSavePath}`;
        } else {
            message.textContent = '标注已完成！';
            path.textContent = '结果已保存到 results 目录';
        }
    }

    // Show error
    showError(message) {
        document.getElementById('progress-panel').classList.add('hidden');
        document.getElementById('process-panel').classList.remove('hidden');

        alert(`处理失败: ${message}`);
    }

    // Reset
    reset() {
        this.sessionId = null;
        this.files = [];
        this.selectedModel = null;
        this.selectedFormat = null;
        this.currentJobId = null;
        this.currentPreviewIndex = -1;
        this.customSavePath = null;

        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        this.hidePreviewArea();
        this.updateFileCount();
        document.getElementById('save-path-display').textContent = '默认保存到 results 目录';
        document.querySelectorAll('.model-card').forEach(c => c.classList.remove('selected'));
        document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
        document.getElementById('progress-panel').classList.add('hidden');
        document.getElementById('result-panel').classList.add('hidden');
        document.getElementById('process-panel').classList.remove('hidden');
        document.getElementById('process-btn').disabled = true;

        // Reset labeling mode to auto
        document.querySelector('input[name="labeling_mode"][value="auto"]').checked = true;
        document.getElementById('specific-classes').value = '';
        document.getElementById('specific-classes-container').classList.add('hidden');
    }

    // Generate session ID
    generateSessionId() {
        return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Get task label
    getTaskLabel(task) {
        const labels = {
            detection: '目标检测',
            segmentation: '实例分割',
            pose: '姿态估计',
            ocr: '文字识别',
            grounding: 'Grounding',
            obb: '旋转检测',
            tagging: '图像标签',
            depth: '深度估计',
            tracking: '目标跟踪',
            classification: '图像分类'
        };
        return labels[task] || task;
    }

    // Format file size
    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
