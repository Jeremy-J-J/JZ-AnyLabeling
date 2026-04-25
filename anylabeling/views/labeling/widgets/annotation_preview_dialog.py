"""
Annotation Preview Dialog - Visualize auto-labeling results
"""
import os
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt

from anylabeling.views.labeling.shape import Shape
from anylabeling.views.labeling.label_file import LabelFile
from anylabeling.views.labeling.utils.qt import new_icon


def get_preview_dialog_style():
    return """
        QDialog {
            background-color: #2b2b2b;
        }
        QLabel {
            color: #ffffff;
            font-size: 13px;
        }
        QPushButton {
            background-color: #3d3d3d;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        QPushButton:disabled {
            background-color: #2b2b2b;
            color: #666666;
        }
        QListWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QListWidget::item:selected {
            background-color: #0d7dd4;
        }
        QScrollArea {
            background-color: #1e1e1e;
            border: none;
        }
    """


def get_canvas_style():
    return """
        QWidget#imageCanvas {
            background-color: #1e1e1e;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
    """


def get_info_panel_style():
    return """
        QLabel#infoLabel {
            color: #aaaaaa;
            font-size: 12px;
            padding: 4px;
        }
        QLabel#shapeLabel {
            color: #ffffff;
            font-size: 13px;
            padding: 4px;
            background-color: #2b2b2b;
            border-radius: 3px;
            margin: 2px;
        }
        QLabel#shapeLabel:hover {
            background-color: #3d3d3d;
        }
    """


class ImageCanvas(QWidget):
    """Custom widget for rendering image with shape overlays"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.shapes = []
        self.selected_shape_index = -1
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.setObjectName("imageCanvas")
        self.setStyleSheet(get_canvas_style())

    def set_image(self, pixmap):
        """Set the image pixmap"""
        self.pixmap = pixmap
        self.update_scale()
        self.update()

    def set_shapes(self, shapes):
        """Set shapes to display"""
        self.shapes = shapes
        self.selected_shape_index = -1
        self.update()

    def select_shape(self, index):
        """Select a shape by index"""
        self.selected_shape_index = index
        self.update()

    def update_scale(self):
        """Calculate scale to fit image in widget"""
        if self.pixmap is None:
            return
        widget_size = self.size()
        pixmap_size = self.pixmap.size()

        if widget_size.width() <= 0 or widget_size.height() <= 0:
            return

        scale_x = widget_size.width() / pixmap_size.width()
        scale_y = widget_size.height() / pixmap_size.height()
        self.scale_factor = min(scale_x, scale_y) * 0.95  # 5% margin

        self.offset_x = (widget_size.width() - pixmap_size.width() * self.scale_factor) / 2
        self.offset_y = (widget_size.height() - pixmap_size.height() * self.scale_factor) / 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scale()

    def paintEvent(self, event):
        """Paint the image and shape overlays"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        if self.pixmap is None:
            return

        # Draw image
        scaled_width = self.pixmap.width() * self.scale_factor
        scaled_height = self.pixmap.height() * self.scale_factor
        scaled_pixmap = self.pixmap.scaled(
            int(scaled_width),
            int(scaled_height),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(int(self.offset_x), int(self.offset_y), scaled_pixmap)

        # Draw shapes
        if self.shapes:
            Shape.scale = self.scale_factor

            for i, shape_dict in enumerate(self.shapes):
                shape = self.create_shape_from_dict(shape_dict)
                if shape:
                    # Highlight selected shape
                    if i == self.selected_shape_index:
                        shape.selected = True
                        shape.line_color = QColor(255, 200, 0)
                        shape.fill_color = QColor(255, 200, 0, 80)
                    else:
                        shape.selected = False
                        shape.line_color = QColor(0, 255, 0, 180)
                        shape.fill_color = QColor(0, 255, 0, 50)
                    shape.paint(painter)

    def create_shape_from_dict(self, shape_dict):
        """Create a Shape object from dictionary"""
        shape = Shape(
            label=shape_dict.get("label", ""),
            score=shape_dict.get("score"),
            shape_type=shape_dict.get("shape_type", "rectangle"),
        )
        # Convert points from [[x, y], ...] to QPointF
        points = shape_dict.get("points", [])
        for p in points:
            if len(p) >= 2:
                x = p[0] * self.scale_factor + self.offset_x
                y = p[1] * self.scale_factor + self.offset_y
                shape.points.append(QtCore.QPointF(x, y))
        return shape

    def mousePressEvent(self, event):
        """Handle mouse click for shape selection"""
        if not self.shapes or self.pixmap is None:
            return

        click_pos = event.pos()
        # Check if click is within image bounds
        if not self.image_contains_point(click_pos):
            return

        # Transform click to image coordinates
        img_x = (click_pos.x() - self.offset_x) / self.scale_factor
        img_y = (click_pos.y() - self.offset_y) / self.scale_factor

        # Find clicked shape
        for i, shape_dict in enumerate(self.shapes):
            if self.shape_contains_point(shape_dict, img_x, img_y):
                self.select_shape(i)
                self.update()
                # Notify parent
                if hasattr(self.parent(), "on_shape_selected"):
                    self.parent().on_shape_selected(i)
                return

    def image_contains_point(self, point):
        """Check if point is within the displayed image area"""
        if self.pixmap is None:
            return False
        scaled_width = self.pixmap.width() * self.scale_factor
        scaled_height = self.pixmap.height() * self.scale_factor
        return (
            self.offset_x <= point.x() <= self.offset_x + scaled_width and
            self.offset_y <= point.y() <= self.offset_y + scaled_height
        )

    def shape_contains_point(self, shape_dict, x, y):
        """Check if point is inside shape (bounding box check)"""
        points = shape_dict.get("points", [])
        if not points:
            return False

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        margin = 5  # pixels tolerance
        return (min_x - margin <= x <= max_x + margin and
                min_y - margin <= y <= max_y + margin)


class ShapeInfoWidget(QWidget):
    """Widget displaying shape information in the info panel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shape_index = -1
        self.setStyleSheet(get_info_panel_style())

    def set_shape_info(self, index, shape_dict):
        """Set shape information to display"""
        self.shape_index = index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Label
        label = shape_dict.get("label", "Unknown")
        score = shape_dict.get("score")
        shape_type = shape_dict.get("shape_type", "rectangle")

        # Build info text
        info_text = f"<b>{label}</b>"
        if score is not None:
            info_text += f" <span style='color: #888;'>Score: {score:.2f}</span>"
        info_text += f"<br/><span style='color: #666;'>Type: {shape_type}</span>"

        label_widget = QLabel(info_text)
        label_widget.setObjectName("shapeLabel")
        label_widget.setWordWrap(True)

        layout.addWidget(label_widget)
        self.setLayout(layout)


class AnnotationPreviewDialog(QDialog):
    """Dialog for previewing annotation results"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation Preview")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)
        self.resize(1200, 700)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(get_preview_dialog_style())

        self.image_files = []
        self.label_files = []
        self.current_index = 0
        self.shapes = []

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # Main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(3)
        self.main_splitter.setStyleSheet(" QSplitter::handle { background-color: #3d3d3d; } ")

        # Left panel - Image with shapes
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # Header with folder selection
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.folder_button = QPushButton("Select Folder")
        self.folder_button.setIcon(QIcon(new_icon("folder", "svg")))
        self.folder_button.setFixedHeight(32)
        self.folder_button.clicked.connect(self.select_folder)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color: #888; font-size: 12px;")
        self.folder_label.setElideMode(Qt.TextElideMode.ElideMiddle)

        header_layout.addWidget(self.folder_button)
        header_layout.addWidget(self.folder_label, 1)

        left_layout.addWidget(header_widget)

        # Image canvas
        self.canvas = ImageCanvas(self)
        left_layout.addWidget(self.canvas, 1)

        self.main_splitter.addWidget(left_widget)

        # Right panel - Shape info
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Info header
        info_header = QLabel("Annotation Info")
        info_header.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(info_header)

        # File info
        self.file_info_label = QLabel("No image loaded")
        self.file_info_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px;")
        right_layout.addWidget(self.file_info_label)

        # Shape count
        self.shape_count_label = QLabel("Shapes: 0")
        self.shape_count_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px;")
        right_layout.addWidget(self.shape_count_label)

        # Shape list
        self.shape_list = QListWidget()
        self.shape_list.setAlternatingRowColors(True)
        self.shape_list.itemClicked.connect(self.on_shape_list_clicked)
        right_layout.addWidget(self.shape_list, 1)

        # Navigation
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 10, 0, 0)
        nav_layout.setSpacing(10)

        self.prev_button = QPushButton()
        self.prev_button.setIcon(QIcon(new_icon("arrow-left", "svg")))
        self.prev_button.setFixedSize(40, 32)
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(lambda: self.switch_image("prev"))

        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: #ffffff; font-size: 13px;")

        self.next_button = QPushButton()
        self.next_button.setIcon(QIcon(new_icon("arrow-right", "svg")))
        self.next_button.setFixedSize(40, 32)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(lambda: self.switch_image("next"))

        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.page_label, 1)
        nav_layout.addWidget(self.next_button)

        right_layout.addWidget(nav_widget)

        self.main_splitter.addWidget(right_widget)

        # Set splitter sizes
        total_width = self.width() - 40
        self.main_splitter.setSizes([int(total_width * 0.65), int(total_width * 0.35)])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self.main_splitter)

    def select_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder_path):
        """Load images and their label files from a folder"""
        self.folder_label.setText(folder_path)

        # Find all image files
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
        self.image_files = []
        self.label_files = []

        folder = Path(folder_path)
        for file in sorted(folder.iterdir()):
            if file.suffix.lower() in image_extensions:
                self.image_files.append(str(file))
                # Look for corresponding label file
                label_file = file.with_suffix(".json")
                if label_file.exists():
                    self.label_files.append(str(label_file))
                else:
                    self.label_files.append(None)

        if not self.image_files:
            self.file_info_label.setText("No images found")
            self.shape_list.clear()
            self.canvas.set_shapes([])
            return

        self.current_index = 0
        self.load_current_image()
        self.update_navigation_state()

    def load_current_image(self):
        """Load the image and shapes at current index"""
        if not self.image_files or self.current_index >= len(self.image_files):
            return

        image_path = self.image_files[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.file_info_label.setText(f"Failed to load: {image_path}")
            return

        self.canvas.set_image(pixmap)

        # Update file info
        filename = os.path.basename(image_path)
        self.file_info_label.setText(filename)

        # Load label file if exists
        label_path = self.label_files[self.current_index] if self.current_index < len(self.label_files) else None
        self.shapes = []

        if label_path and os.path.exists(label_path):
            try:
                label_file = LabelFile(label_path)
                self.shapes = label_file.shapes if hasattr(label_file, 'shapes') else []

                # Convert LabelFile shapes to dict format for canvas
                shapes_dict = []
                for shape in self.shapes:
                    if isinstance(shape, dict):
                        shapes_dict.append(shape)
                    elif hasattr(shape, 'to_dict'):
                        shapes_dict.append(shape.to_dict())
                    elif hasattr(shape, '__dict__'):
                        # It's a Shape object
                        shapes_dict.append({
                            "label": getattr(shape, 'label', ''),
                            "score": getattr(shape, 'score', None),
                            "points": [[p.x(), p.y()] for p in getattr(shape, 'points', [])],
                            "shape_type": getattr(shape, 'shape_type', 'rectangle'),
                            "group_id": getattr(shape, 'group_id', None),
                            "description": getattr(shape, 'description', ''),
                        })
                self.shapes = shapes_dict

            except Exception as e:
                print(f"Error loading label file: {e}")
                self.shapes = []

        self.canvas.set_shapes(self.shapes)
        self.update_shape_list()

    def update_shape_list(self):
        """Update the shape list in the info panel"""
        self.shape_list.clear()
        self.shape_count_label.setText(f"Shapes: {len(self.shapes)}")

        for i, shape in enumerate(self.shapes):
            if isinstance(shape, dict):
                label = shape.get("label", "Unknown")
                score = shape.get("score")
                shape_type = shape.get("shape_type", "rectangle")
            else:
                label = getattr(shape, 'label', 'Unknown')
                score = getattr(shape, 'score')
                shape_type = getattr(shape, 'shape_type', 'rectangle')

            text = f"{label}"
            if score is not None:
                text += f" ({score:.2f})"
            text += f" - {shape_type}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.shape_list.addItem(item)

    def switch_image(self, direction):
        """Switch to previous or next image"""
        if direction == "prev":
            if self.current_index > 0:
                self.current_index -= 1
        elif direction == "next":
            if self.current_index < len(self.image_files) - 1:
                self.current_index += 1

        self.load_current_image()
        self.update_navigation_state()

    def update_navigation_state(self):
        """Update navigation button states and page label"""
        total = len(self.image_files)
        current = self.current_index + 1 if total > 0 else 0

        self.page_label.setText(f"{current} / {total}")
        self.prev_button.setEnabled(current > 1)
        self.next_button.setEnabled(current < total)

    def on_shape_list_clicked(self, item):
        """Handle shape list item click"""
        index = item.data(Qt.ItemDataRole.UserRole)
        if index >= 0 and index < len(self.shapes):
            self.canvas.select_shape(index)
            # Scroll to item
            self.shape_list.setCurrentRow(index)

    def on_shape_selected(self, index):
        """Handle shape selection from canvas"""
        if index >= 0 and index < self.shape_list.count():
            self.shape_list.setCurrentRow(index)

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Update splitter sizes proportionally
        total_width = self.width() - 40
        self.main_splitter.setSizes([int(total_width * 0.65), int(total_width * 0.35)])