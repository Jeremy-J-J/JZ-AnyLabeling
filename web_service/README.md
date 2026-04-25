# X-AnyLabeling Web Service

基于 X-AnyLabeling 的自动化标注 Web 服务

## 特性

- 一键启动本地 Web 服务
- 支持图片和视频上传预览
- 支持 100+ 预训练 AI 模型
- 支持多种标注格式导出 (YOLO, VOC, COCO, DOTA, MOT, MOTS, MASK, PPOCR)
- 简洁的 Web UI

## 快速开始

### 1. 启动服务

```bash
cd /Users/jeremyj_pc/mac/project/X-AnyLabeling
bash web_service/start.sh
```

### 2. 访问服务

打开浏览器访问: http://localhost:8000

### 3. 使用流程

1. **上传文件**: 拖拽或选择图片/视频文件
2. **选择模型**: 从列表中选择需要的标注模型
3. **选择格式**: 选择导出格式 (YOLO, VOC, COCO 等)
4. **开始处理**: 点击按钮开始自动标注
5. **下载结果**: 处理完成后下载标注文件

## 系统要求

- Python 3.8+
- ffmpeg (用于视频处理)
- 建议 8GB+ RAM
- 推荐 GPU 加速 (CUDA)

## API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 获取所有可用模型 |
| GET | `/api/formats` | 获取支持的导出格式 |
| POST | `/api/upload` | 上传文件 |
| POST | `/api/process` | 开始处理任务 |
| GET | `/api/status/{job_id}` | 获取任务状态 |
| GET | `/api/download/{job_id}` | 下载标注结果 |

完整的 API 文档请访问: http://localhost:8000/docs

## 支持的模型类型

- **目标检测**: YOLOv5-v12, DAMO-YOLO, RT-DETR, D-FINE 等
- **实例分割**: SAM, SAM2, YOLO-Seg 等
- **姿态估计**: YOLOv8-Pose, RTMDET-Pose 等
- **文字识别**: PP-OCRv4, PP-OCRv5
- **Grounding**: Grounding DINO, Grounding SAM
- **旋转检测**: YOLO-OBB 系列
- **图像标签**: RAM, RAM++
- **深度估计**: Depth Anything V2
- **目标跟踪**: BoT-SORT, ByteTrack

## 支持的导出格式

| 格式 | 扩展名 | 支持任务 |
|------|--------|----------|
| YOLO | .txt | 检测/分割/姿态/OBB |
| Pascal VOC | .xml | 检测/分割 |
| COCO JSON | .json | 检测/分割/姿态 |
| DOTA | .txt | 检测/OBB |
| MOT CSV | .csv | 跟踪 |
| MOTS PNG | .png | 分割 |
| Mask PNG | .png | 分割 |
| PaddleOCR | .json | OCR |

## 目录结构

```
web_service/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置文件
├── start.sh            # 启动脚本
├── requirements.txt    # Python 依赖
├── api/                 # API 路由
│   └── routes/         # 具体路由实现
├── services/           # 业务逻辑
│   ├── session_manager.py   # 会话管理
│   ├── model_service.py     # 模型服务
│   └── label_service.py      # 标注服务
├── schemas/            # Pydantic 模型
└── ui/                 # Web 前端
    ├── index.html
    ├── css/styles.css
    └── js/
        ├── api-client.js
        └── app.js
```

## 配置

修改 `config.py` 可以调整:
- 上传文件大小限制
- 支持的文件格式
- 上传/会话/结果目录路径

## 故障排除

### 启动失败

确保已安装所有依赖:
```bash
pip install -r requirements.txt
```

### 模型加载慢

首次使用模型时会下载模型文件，请耐心等待。

### 视频处理失败

确保已安装 ffmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```
