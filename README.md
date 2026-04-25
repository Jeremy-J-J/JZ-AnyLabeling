# JZ-AnyLabeling

基于 X-AnyLabeling 的自动化标注 Web 服务，提供图片和视频的目标检测、分割、OCR 等标注功能。

## 功能特性

- **目标检测**: 支持 YOLO 系列模型（YOLOv5-v12、DAMO-YOLO、RT-DETR 等）
- **图像分割**: SAM、YOLO-Seg 等分割模型
- **姿态估计**: YOLO-Pose 等姿态检测模型
- **文字识别**: PP-OCR 文字识别
- **旋转检测**: OBB 旋转目标检测
- **双模式标注**:
  - 自动识别模式：自动检测并标注所有识别到的类别
  - 配置类别模式：只标注指定的类别

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r web_service/requirements.txt

# 安装 anylabeling 包（开发模式）
pip install -e ".[cpu]"
```

### 2. 启动服务

```bash
bash web_service/start.sh
```

服务启动后访问 http://localhost:8000

### 3. 使用标注功能

1. 上传图片或视频
2. 选择检测模型（如 YOLOv8n）
3. 选择输出格式（如 VOC）
4. 选择标注模式：
   - **自动识别**：检测并标注所有类别
   - **配置类别**：只标注指定的类别（逗号分隔，如 `person, car, truck`）
5. 点击"开始处理"
6. 标注结果保存在 `results/` 目录

## 项目结构

```
JZ-AnyLabeling/
├── anylabeling/              # 核心推理服务
│   ├── services/             # 模型服务（检测、分割等）
│   ├── configs/              # 模型配置文件
│   └── views/                # 标注视图组件
├── web_service/              # Web 服务
│   ├── api/                  # API 路由
│   ├── services/             # 业务服务
│   ├── ui/                   # 前端界面
│   └── main.py               # 服务入口
└── pyproject.toml            # 项目配置
```

## 常用模型

| 模型 | 类型 | 说明 |
|------|------|------|
| yolov8n | 检测 | 轻量级 YOLOv8 |
| yolov8n_oiv7 | 检测 | OpenImageV7 数据集 |
| sam_hq_vit_l | 分割 | SAM 高质量分割 |
| yolov8n_pose | 姿态 | 人体姿态估计 |
| ch_ppocr_v4 | OCR | 中英文文字识别 |

## 配置

模型会自动下载到 `~/.xanylabeling/` 目录。

## 开发

```bash
# 安装开发依赖
pip install -e ".[cpu,dev]"

# 运行测试
pytest tests/
```

## 许可证

GPL-3.0
