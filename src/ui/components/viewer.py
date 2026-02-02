import sys
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRectF, QRect
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QImage,
    QPixmap,
)
from ..core.design_tokens import SPACE_SM


class VideoScreen(QWidget):
    """
    Clean implementation of video display widget.
    CRITICAL PRINCIPLE: Project resolution defines aspect ratio, NOT pixmap size.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Widget configuration
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 180)
        
        # State
        self.pixmap = None
        self.project_width = 1920
        self.project_height = 1080
        self.scaling_mode = "fit"  # 'fit' or 'fill'
        self.fast_mode = False

    def set_project_resolution(self, width: int, height: int):
        """Set the project resolution that defines the aspect ratio."""
        self.project_width = max(1, width)
        self.project_height = max(1, height)
        self.update()

    def set_pixmap(self, pixmap: QPixmap, fast_mode: bool = False):
        """Update the displayed frame."""
        self.pixmap = pixmap
        self.fast_mode = fast_mode
        self.update()

    def set_scaling_mode(self, mode: str):
        """Set scaling mode: 'fit' or 'fill'."""
        self.scaling_mode = mode
        self.update()

    def paintEvent(self, event):
        """
        Paint the video frame with correct aspect ratio.
        CRITICAL: ALWAYS uses project resolution for aspect ratio calculation.
        The pixmap size (which changes between draft/full mode) is IRRELEVANT for sizing.
        """
        painter = QPainter(self)
        
        # Fill background with black
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # Early exit if no frame
        if not self.pixmap or self.pixmap.isNull():
            return
        
        # CRITICAL: Calculate aspect ratio from PROJECT resolution ONLY
        # This ensures the video size stays constant even when pixmap size changes
        # (e.g., 1920x1080 in full mode vs 960x540 in draft mode)
        aspect_ratio = float(self.project_width) / float(self.project_height)
        
        # Get widget dimensions (the available space)
        widget_width = float(self.width())
        widget_height = float(self.height())
        
        # Calculate target rectangle based on scaling mode
        # This rectangle defines WHERE and HOW BIG the video appears
        if self.scaling_mode == "fill":
            target_rect = self._calculate_fill_rect(widget_width, widget_height, aspect_ratio)
        else:
            target_rect = self._calculate_fit_rect(widget_width, widget_height, aspect_ratio)
        
        # Set rendering quality
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, not self.fast_mode)
        
        # Draw the pixmap scaled to target rectangle
        # Qt automatically scales the pixmap (whatever its size) to fit the target_rect
        painter.drawPixmap(target_rect, self.pixmap, QRectF(self.pixmap.rect()))

    def _calculate_fit_rect(self, widget_w: float, widget_h: float, aspect: float) -> QRectF:
        """
        Calculate rectangle that fits entire content (letterbox/pillarbox if needed).
        """
        widget_aspect = widget_w / widget_h
        
        if aspect > widget_aspect:
            # Content is wider than widget - fit to width
            target_w = widget_w
            target_h = widget_w / aspect
        else:
            # Content is taller than widget - fit to height
            target_h = widget_h
            target_w = widget_h * aspect
        
        # Center the rectangle
        x = (widget_w - target_w) / 2.0
        y = (widget_h - target_h) / 2.0
        
        return QRectF(x, y, target_w, target_h)

    def _calculate_fill_rect(self, widget_w: float, widget_h: float, aspect: float) -> QRectF:
        """
        Calculate rectangle that fills entire widget (crop if needed).
        """
        widget_aspect = widget_w / widget_h
        
        if aspect > widget_aspect:
            # Content is wider - fit to height and crop sides
            target_h = widget_h
            target_w = widget_h * aspect
        else:
            # Content is taller - fit to width and crop top/bottom
            target_w = widget_w
            target_h = widget_w / aspect
        
        # Center the rectangle
        x = (widget_w - target_w) / 2.0
        y = (widget_h - target_h) / 2.0
        
        return QRectF(x, y, target_w, target_h)


class ViewerPanel(QWidget):
    """
    Complete viewer panel with video screen and controls.
    """

    def __init__(self):
        super().__init__()
        self._current_pixmap = None
        self._last_fast_mode = False
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        self.setObjectName("ViewerPanel")
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setStyleSheet("""
            #ViewerPanel {
                background-color: #0d0d0d;
                border: none;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video screen (expandable)
        self.video_screen = VideoScreen()
        layout.addWidget(self.video_screen, stretch=1)
        
        # Controls bar (fixed height)
        self.controls_bar = self._create_controls_bar()
        layout.addWidget(self.controls_bar, stretch=0)
        
        # Info panel (hidden by default)
        self.info_panel = self._create_info_panel()
        layout.addWidget(self.info_panel, stretch=0)
        self.info_panel.hide()

    def _create_controls_bar(self) -> QFrame:
        """Create the control buttons bar."""
        bar = QFrame()
        bar.setFixedHeight(45)
        bar.setStyleSheet("background-color: #111111; border: none;")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        # Button font
        button_font = QFont("Apple Symbols", 20) if sys.platform == "darwin" else QFont("Segoe UI Symbol", 16)
        
        # Button style
        btn_style = """
            QPushButton { 
                background-color: transparent; 
                color: #e0e0e0; 
                border: none; 
                border-radius: 4px;
            } 
            QPushButton:hover { 
                background-color: #333333; 
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #222222;
                color: #00a3ff;
            }
        """
        
        # Create buttons
        self.btn_rewind = QPushButton("⏮")
        self.btn_rewind.setFixedSize(32, 32)
        self.btn_rewind.setFont(button_font)
        self.btn_rewind.setStyleSheet(btn_style)
        self.btn_rewind.setToolTip("Ir al inicio")
        
        self.btn_play_pause = QPushButton("▶")
        self.btn_play_pause.setFixedSize(40, 40)
        self.btn_play_pause.setFont(button_font)
        self.btn_play_pause.setStyleSheet(btn_style)
        self.btn_play_pause.setToolTip("Reproducir/Pausar (Espacio)")
        
        self.btn_scaling = QPushButton("⚃")
        self.btn_scaling.setFixedSize(32, 32)
        self.btn_scaling.setFont(button_font)
        self.btn_scaling.setStyleSheet(btn_style)
        self.btn_scaling.setToolTip("Cambiar modo de escalado")
        self.btn_scaling.clicked.connect(self._toggle_scaling_mode)
        
        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(32, 32)
        self.btn_fullscreen.setFont(button_font)
        self.btn_fullscreen.setStyleSheet(btn_style)
        self.btn_fullscreen.setToolTip("Pantalla completa")
        
        # Playback rate control
        rate_container = QWidget()
        rate_layout = QHBoxLayout(rate_container)
        rate_layout.setContentsMargins(15, 0, 15, 0)
        rate_layout.setSpacing(8)
        
        self.lbl_rate = QLabel("1.0x")
        self.lbl_rate.setStyleSheet(
            "color: #888; font-family: 'Inter'; font-size: 10px; "
            "font-weight: bold; min-width: 30px;"
        )
        
        self.slider_rate = QSlider(Qt.Orientation.Horizontal)
        self.slider_rate.setRange(20, 300)
        self.slider_rate.setValue(100)
        self.slider_rate.setFixedWidth(100)
        self.slider_rate.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 3px;
                background: #111;
                margin: 2px 0;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #00a3ff;
                border: 1px solid #00a3ff;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
        """)
        
        rate_layout.addWidget(self.lbl_rate)
        rate_layout.addWidget(self.slider_rate)
        
        # Add all to layout
        layout.addStretch()
        layout.addWidget(self.btn_rewind)
        layout.addWidget(self.btn_play_pause)
        layout.addWidget(rate_container)
        layout.addWidget(self.btn_scaling)
        layout.addWidget(self.btn_fullscreen)
        layout.addStretch()
        
        return bar

    def _create_info_panel(self) -> QFrame:
        """Create the information panel."""
        panel = QFrame()
        panel.setFixedHeight(30)
        panel.setStyleSheet("background-color: #0a0a0a; border-top: 1px solid #222;")
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.lbl_format = QLabel("Proyecto: 1920x1080 (16:9 - Horizontal)")
        self.lbl_format.setStyleSheet("color: #666; font-size: 10px;")
        
        layout.addWidget(self.lbl_format)
        layout.addStretch()
        
        return panel

    def _toggle_scaling_mode(self):
        """Toggle between fit and fill scaling modes."""
        current_mode = self.video_screen.scaling_mode
        new_mode = "fill" if current_mode == "fit" else "fit"
        self.video_screen.set_scaling_mode(new_mode)
        
        # Update button tooltip
        mode_text = "Rellenar" if new_mode == "fill" else "Ajustar"
        self.btn_scaling.setToolTip(f"Modo: {mode_text}")

    def _reset_rate(self):
        """Reset playback rate to 1.0x."""
        self.slider_rate.setValue(100)
        self.lbl_rate.setText("1.0x")

    def set_project_resolution(self, width: int, height: int):
        """Update project resolution for the viewer."""
        self.video_screen.set_project_resolution(width, height)
        self.update_format_label(width, height)

    def update_format_label(self, width: int, height: int):
        """Update the format information label."""
        from math import gcd
        
        divisor = gcd(width, height)
        aspect_w = width // divisor
        aspect_h = height // divisor
        is_vertical = height > width
        format_type = "Vertical" if is_vertical else "Horizontal"
        
        if hasattr(self, "lbl_format"):
            self.lbl_format.setText(
                f"Proyecto: {width}x{height} ({aspect_w}:{aspect_h} - {format_type})"
            )

    def display_frame(self, frame_buffer, fast_mode: bool = False):
        """
        Display a video frame from numpy buffer.
        
        Args:
            frame_buffer: numpy array (Height, Width, 4) in RGBA format
            fast_mode: If True, use nearest-neighbor scaling (faster, pixelated)
        """
        if frame_buffer is None:
            return
        
        try:
            height, width, channels = frame_buffer.shape
            bytes_per_line = channels * width
            
            # Create QImage from buffer
            image = QImage(
                frame_buffer.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGBA8888,
            )
            
            # Convert to QPixmap
            pixmap = QPixmap.fromImage(image)
            
            # Display on screen
            self.video_screen.set_pixmap(pixmap, fast_mode)
            
            # Cache for resize events
            self._current_pixmap = pixmap
            self._last_fast_mode = fast_mode
            
        except Exception as e:
            print(f"Viewer Error: Failed to render frame: {e}")

    def resizeEvent(self, event):
        """Handle widget resize by redrawing current frame."""
        super().resizeEvent(event)
        
        # Redraw current frame if available
        if hasattr(self, "_current_pixmap") and self._current_pixmap and not self._current_pixmap.isNull():
            self.video_screen.set_pixmap(self._current_pixmap, self._last_fast_mode)
