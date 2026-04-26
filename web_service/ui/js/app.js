/**
 * X-AnyLabeling Web Service - Main Application
 */

// Curated model prefixes per task (best models each)
const CURATED_MODEL_PREFIXES = {
    detection: [
        { prefix: 'yolov8n', name: 'YOLOv8n (最小)' },
        { prefix: 'yolov8s', name: 'YOLOv8s (小)' },
        { prefix: 'yolov8m', name: 'YOLOv8m (中)' },
        { prefix: 'yolov8l', name: 'YOLOv8l (大)' },
        { prefix: 'yolov8x', name: 'YOLOv8x (最大)' }
    ],
    segmentation: [
        { prefix: 'sam_hq_vit_l', name: 'SAM-HQ Vit-L (推荐)' },
        { prefix: 'sam_hq_vit_b', name: 'SAM-HQ Vit-B' },
        { prefix: 'sam2_hiera_large', name: 'SAM2 Large' },
        { prefix: 'sam2_hiera_base', name: 'SAM2 Base' },
        { prefix: 'yolov8x_seg', name: 'YOLOv8x-Seg' },
        { prefix: 'yolov8m_seg', name: 'YOLOv8m-Seg' },
        { prefix: 'yolov8s_seg', name: 'YOLOv8s-Seg' }
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
        this.lastResultPath = null;

        // Annotation preview mode
        this.previewMode = 'labeling'; // 'labeling' or 'preview'
        this.previewFolder = null;
        this.previewFolderHandle = null;
        this.previewImages = [];
        this.previewCurrentIndex = 0;
        this.previewAnnotations = [];
        this.defaultResultPath = null;

        this.init();
    }

    async init() {
        await this.loadModels();
        await this.loadFormats();
        await this.loadConfig();
        this.setupEventListeners();
        this.checkHealth();
    }

    async loadConfig() {
        try {
            console.log('Loading config...');
            const response = await this.api.getLatestResultDir();
            console.log('Config response:', response);
            // Use latest_subdir if available, otherwise fall back to result_dir
            this.defaultResultPath = response.latest_subdir || response.result_dir;
            document.getElementById('preview-folder-path').textContent = this.defaultResultPath || '未设置默认路径';
        } catch (e) {
            console.error('Failed to load config:', e);
            document.getElementById('preview-folder-path').textContent = '加载失败';
        }
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

        // Confidence slider
        const confidenceSlider = document.getElementById('confidence-slider');
        const confidenceValue = document.getElementById('confidence-value');
        confidenceSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            confidenceValue.textContent = (val / 100).toFixed(2);
        });

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

        // Preview mode toggle
        document.getElementById('labeling-mode-btn').addEventListener('click', () => {
            this.setPreviewMode('labeling');
        });

        document.getElementById('preview-mode-btn').addEventListener('click', () => {
            this.setPreviewMode('preview');
        });

        // Annotation preview folder selection
        document.getElementById('select-folder-preview-btn').addEventListener('click', async () => {
            if ('showDirectoryPicker' in window) {
                try {
                    const dirHandle = await window.showDirectoryPicker();
                    await this.loadAnnotationFolder(dirHandle);
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        console.error('Directory picker error:', e);
                    }
                }
            } else {
                // Fallback: use file input
                const input = document.createElement('input');
                input.type = 'file';
                input.webkitdirectory = true;
                input.addEventListener('change', async (e) => {
                    const files = Array.from(e.target.files);
                    if (files.length > 0) {
                        // Get folder path from first file
                        const folderPath = files[0].webkitRelativePath.split('/')[0];
                        await this.loadAnnotationFolderFromPath(folderPath);
                    }
                });
                input.click();
            }
        });

        // Annotation navigation
        document.getElementById('annotation-prev-btn').addEventListener('click', () => {
            this.showAnnotationImage(this.previewCurrentIndex - 1);
        });

        document.getElementById('annotation-next-btn').addEventListener('click', () => {
            this.showAnnotationImage(this.previewCurrentIndex + 1);
        });
    }

    // Set preview mode
    setPreviewMode(mode) {
        this.previewMode = mode;

        document.getElementById('labeling-mode-btn').classList.toggle('active', mode === 'labeling');
        document.getElementById('preview-mode-btn').classList.toggle('active', mode === 'preview');

        document.getElementById('labeling-panel').classList.toggle('hidden', mode !== 'labeling');
        document.getElementById('annotation-preview-panel').classList.toggle('hidden', mode !== 'preview');

        // When entering preview mode, auto-load from last result path (or default)
        if (mode === 'preview') {
            const folderToLoad = this.lastResultPath || this.defaultResultPath;
            if (folderToLoad && this.previewImages.length === 0) {
                this.loadAnnotationFolderFromPath(folderToLoad);
            }
        }
    }

    // Load annotation folder using File System Access API
    async loadAnnotationFolder(dirHandle) {
        this.previewFolder = dirHandle;
        this.previewFolderHandle = dirHandle;
        document.getElementById('preview-folder-path').textContent = dirHandle.name;

        try {
            const images = [];
            for await (const entry of dirHandle.values()) {
                if (entry.kind === 'file') {
                    const ext = entry.name.toLowerCase().split('.').pop();
                    if (['jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp'].includes(ext)) {
                        // Store object with name and fileHandle
                        images.push({
                            name: entry.name,
                            fileHandle: entry
                        });
                    }
                }
            }

            if (images.length === 0) {
                alert('未找到图片文件');
                return;
            }

            // Show loading
            document.getElementById('annotation-preview-placeholder').classList.add('hidden');
            document.getElementById('annotation-preview-content').classList.remove('hidden');
            document.getElementById('annotation-controls').classList.remove('hidden');
            document.getElementById('shape-list').classList.remove('hidden');

            this.previewImages = images;
            this.previewCurrentIndex = 0;
            this.previewAnnotations = [];
            await this.showAnnotationImage(0);
            this.updateAnnotationSummary();

        } catch (e) {
            console.error('Error loading folder:', e);
            alert('加载文件夹失败');
        }
    }

    // Load annotation folder from path (for fallback using backend API)
    async loadAnnotationFolderFromPath(folderPath) {
        try {
            const response = await this.api.listPreviewFolder(folderPath);
            if (response.images_count === 0) {
                alert('未找到图片文件');
                return;
            }

            document.getElementById('preview-folder-path').textContent = folderPath;
            document.getElementById('annotation-preview-placeholder').classList.add('hidden');
            document.getElementById('annotation-preview-content').classList.remove('hidden');
            document.getElementById('annotation-controls').classList.remove('hidden');
            document.getElementById('shape-list').classList.remove('hidden');

            this.previewImages = response.images;
            this.previewCurrentIndex = 0;
            this.previewAnnotations = [];
            await this.showAnnotationImage(0);
            this.updateAnnotationSummary();

        } catch (e) {
            console.error('Error loading folder:', e);
            alert('加载文件夹失败: ' + e.message);
        }
    }

    // Show annotation image
    async showAnnotationImage(index) {
        if (index < 0 || index >= this.previewImages.length) return;

        this.previewCurrentIndex = index;
        const imageData = this.previewImages[index];

        // Check if using file handles (File System Access API) or paths
        if (imageData.fileHandle) {
            // Using File System Access API - load image directly
            try {
                const file = await imageData.fileHandle.getFile();
                const imageUrl = URL.createObjectURL(file);

                const img = document.getElementById('annotation-preview-image');
                img.src = imageUrl;
                img.classList.remove('hidden');

                // Try to load annotations from JSON sidecar file
                const labelName = imageData.name.replace(/\.[^.]+$/, '.json');
                let annotations = { features: [] };
                let shapes = [];

                // Look for label file in the same folder
                if (this.previewFolderHandle) {
                    for await (const entry of this.previewFolderHandle.values()) {
                        if (entry.kind === 'file' && entry.name === labelName) {
                            const labelFile = await entry.getFile();
                            const labelText = await labelFile.text();
                            const labelData = JSON.parse(labelText);
                            shapes = labelData.shapes || [];

                            // Get image dimensions
                            const width = labelData.imageWidth || 1920;
                            const height = labelData.imageHeight || 1080;

                            // Convert to GeoJSON
                            annotations = this.shapesToGeoJSON(shapes, width, height);
                            break;
                        }
                    }
                }

                // Draw annotations after a brief delay to ensure image is ready
                setTimeout(() => {
                    this.drawAnnotations(annotations);
                }, 50);

                this.previewAnnotations = shapes;
                this.renderShapeList(shapes);

                // Update navigation
                document.getElementById('annotation-page-info').textContent =
                    `${index + 1} / ${this.previewImages.length}`;
                document.getElementById('annotation-prev-btn').disabled = index === 0;
                document.getElementById('annotation-next-btn').disabled = index === this.previewImages.length - 1;
                document.getElementById('shape-count').textContent = `${shapes.length} 个标注`;

            } catch (e) {
                console.error('Error loading image from file handle:', e);
                alert('加载图片失败');
            }
        } else {
            // Using path-based approach (backend API)
            try {
                const response = await this.api.getPreviewImage(imageData.path, true);

                // Show image
                const img = document.getElementById('annotation-preview-image');
                img.src = response.data;
                img.classList.remove('hidden');

                // Draw annotations after a brief delay to ensure image dimensions are loaded
                setTimeout(() => {
                    this.drawAnnotations(response.annotations);
                }, 50);

                this.previewAnnotations = response.shapes || [];

                // Update navigation
                document.getElementById('annotation-page-info').textContent =
                    `${index + 1} / ${this.previewImages.length}`;
                document.getElementById('annotation-prev-btn').disabled = index === 0;
                document.getElementById('annotation-next-btn').disabled = index === this.previewImages.length - 1;

                // Update shape list
                this.renderShapeList(response.shapes || []);
                document.getElementById('shape-count').textContent = `${response.shapes?.length || 0} 个标注`;

            } catch (e) {
                console.error('Error loading image:', e);
                alert('加载图片失败: ' + e.message);
            }
        }
    }

    // Convert shapes to GeoJSON (client-side version)
    shapesToGeoJSON(shapes, width, height) {
        const features = [];
        shapes.forEach((shape, i) => {
            const label = shape.label || 'unknown';
            const shapeType = shape.shape_type || 'rectangle';
            let points = shape.points || [];

            if (!points || points.length < 3) return;

            // Handle both [{"x":..., "y":...}] and [[x,y]] formats
            const coords = points.map(p => {
                if (Array.isArray(p) && p.length >= 2) return [p[0] / width, p[1] / height];
                if (typeof p === 'object' && p.x !== undefined) return [p.x / width, p.y / height];
                return null;
            }).filter(c => c !== null);

            if (coords.length < 3) return;

            features.push({
                type: 'Feature',
                properties: {
                    id: i,
                    label: label,
                    score: shape.score,
                    shape_type: shapeType,
                },
                geometry: {
                    type: 'Polygon',
                    coordinates: [coords]
                }
            });
        });

        return { type: 'FeatureCollection', features };
    }

    // Draw annotations on SVG overlay
    drawAnnotations(annotations, imgWidth, imgHeight) {
        const svg = document.getElementById('annotation-overlay');
        svg.innerHTML = '';

        if (!annotations || !annotations.features) return;

        // Get actual displayed image dimensions for proper scaling
        const img = document.getElementById('annotation-preview-image');
        const container = document.getElementById('annotation-canvas-container');
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        // Get the actual displayed image size (natural dimensions)
        const imgDisplayWidth = img.naturalWidth || img.clientWidth;
        const imgDisplayHeight = img.naturalHeight || img.clientHeight;

        // Calculate image position within container (for centering/letterboxing)
        const scale = Math.min(containerWidth / imgDisplayWidth, containerHeight / imgDisplayHeight);
        const scaledWidth = imgDisplayWidth * scale;
        const scaledHeight = imgDisplayHeight * scale;
        const offsetX = (containerWidth - scaledWidth) / 2;
        const offsetY = (containerHeight - scaledHeight) / 2;

        // Create SVG namespace
        const svgNS = 'http://www.w3.org/2000/svg';

        annotations.features.forEach((feature, i) => {
            const props = feature.properties;
            const geom = feature.geometry;

            if (geom.type === 'Polygon') {
                const coords = geom.coordinates[0];

                // Scale coordinates to actual displayed image position
                let pathD = coords.map((c, idx) => {
                    // c[0] and c[1] are normalized (0-1) relative to original image dimensions
                    // Map to actual displayed position
                    const x = offsetX + c[0] * scaledWidth;
                    const y = offsetY + c[1] * scaledHeight;
                    return (idx === 0 ? `M${x},${y}` : `L${x},${y}`);
                }).join(' ') + ' Z';

                const path = document.createElementNS(svgNS, 'path');
                path.setAttribute('d', pathD);
                path.setAttribute('fill', 'rgba(102, 126, 234, 0.3)');
                path.setAttribute('stroke', 'rgba(102, 126, 234, 0.8)');
                path.setAttribute('stroke-width', '2');
                path.setAttribute('data-index', i);
                path.style.cursor = 'pointer';
                path.style.pointerEvents = 'auto';
                path.addEventListener('click', () => this.selectShape(i));

                svg.appendChild(path);

                // Add label
                if (coords.length > 0) {
                    const labelX = offsetX + coords[0][0] * scaledWidth;
                    const labelY = offsetY + coords[0][1] * scaledHeight - 10;

                    const text = document.createElementNS(svgNS, 'text');
                    text.setAttribute('x', labelX);
                    text.setAttribute('y', labelY);
                    text.setAttribute('fill', 'white');
                    text.setAttribute('font-size', '12px');
                    text.setAttribute('font-weight', 'bold');
                    text.setAttribute('style', 'text-shadow: 1px 1px 2px black; pointer-events: none;');
                    text.textContent = props.label;
                    svg.appendChild(text);
                }
            } else if (geom.type === 'Point') {
                const cx = offsetX + geom.coordinates[0] * scaledWidth;
                const cy = offsetY + geom.coordinates[1] * scaledHeight;

                const circle = document.createElementNS(svgNS, 'circle');
                circle.setAttribute('cx', cx);
                circle.setAttribute('cy', cy);
                circle.setAttribute('r', '6');
                circle.setAttribute('fill', '#667eea');
                circle.setAttribute('stroke', 'white');
                circle.setAttribute('stroke-width', '2');
                circle.setAttribute('data-index', i);
                circle.style.cursor = 'pointer';
                circle.style.pointerEvents = 'auto';
                circle.addEventListener('click', () => this.selectShape(i));

                svg.appendChild(circle);
            }
        });
    }

    // Render shape list
    renderShapeList(shapes) {
        const listEl = document.getElementById('shape-list');

        if (!shapes || shapes.length === 0) {
            listEl.innerHTML = '<div style="text-align: center; color: #888; padding: 20px;">无标注</div>';
            return;
        }

        listEl.innerHTML = shapes.map((shape, i) => `
            <div class="shape-item" data-index="${i}">
                <span class="shape-label">${shape.label || 'Unknown'}</span>
                <span class="shape-score">${shape.score ? shape.score.toFixed(2) : ''}</span>
                <span class="shape-type">${shape.shape_type || 'rectangle'}</span>
            </div>
        `).join('');

        // Add click handlers
        listEl.querySelectorAll('.shape-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.selectShape(index);
            });
        });
    }

    // Select shape
    selectShape(index) {
        // Highlight in list
        document.querySelectorAll('.shape-item').forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });

        // Highlight on SVG (pulse animation could be added)
        document.querySelectorAll('#annotation-overlay path, #annotation-overlay circle').forEach((el, i) => {
            if (i === index) {
                el.setAttribute('stroke-width', '4');
                el.setAttribute('fill', 'rgba(255, 200, 0, 0.4)');
            } else {
                el.setAttribute('stroke-width', '2');
                el.setAttribute('fill', 'rgba(102, 126, 234, 0.3)');
            }
        });
    }

    // Update annotation summary
    async updateAnnotationSummary() {
        if (!this.previewFolder && !this.previewFolderHandle) return;

        // Count labels - only for path-based approach
        const labelCounts = {};
        for (const img of this.previewImages) {
            if (img.path) {
                try {
                    const response = await this.api.getPreviewImage(img.path, true);
                    if (response.shapes) {
                        for (const shape of response.shapes) {
                            const label = shape.label || 'Unknown';
                            labelCounts[label] = (labelCounts[label] || 0) + 1;
                        }
                    }
                } catch (e) {
                    // Skip errors
                }
            }
        }

        // Render summary
        const summaryEl = document.getElementById('annotation-summary');
        const distEl = document.getElementById('label-distribution');

        if (Object.keys(labelCounts).length > 0) {
            distEl.innerHTML = Object.entries(labelCounts).map(([label, count]) => `
                <span class="label-tag">${label} <span class="count">${count}</span></span>
            `).join('');
            summaryEl.classList.remove('hidden');
        } else {
            summaryEl.classList.add('hidden');
        }
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
            const confidenceThreshold = parseInt(document.getElementById('confidence-slider').value) / 100;
            const options = {
                frame_interval: frameInterval,
                conf_threshold: confidenceThreshold
            };
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

        this.lastResultPath = null;

        this.pollingInterval = setInterval(async () => {
            try {
                const status = await this.api.getJobStatus(this.currentJobId);
                this.updateProgress(status.progress, status.current_file || '');

                if (status.status === 'completed') {
                    clearInterval(this.pollingInterval);
                    this.lastResultPath = status.result_path;
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

        message.textContent = '标注已完成！';
        if (this.lastResultPath) {
            path.textContent = `结果已保存到: ${this.lastResultPath}`;
        } else if (this.customSavePath) {
            path.textContent = `结果已保存到: ${this.customSavePath}`;
        } else {
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
        this.lastResultPath = null;

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