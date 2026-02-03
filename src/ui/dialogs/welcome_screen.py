from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QWidget, QFrame, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPixmap, QColor, QFont, QPainter, QBrush, QPainterPath, QRegion
import os

from ..core import design_tokens as dt

class WelcomeScreen(QDialog):
    """
    Blender-style Welcome Screen (Splash).
    Shows the welcome image and disappears when clicking outside.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Window Flags: Frameless, stay on top, Tool (to avoid taskbar entry)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. Main Layout (Full Screen / Relative to Parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 3. Main Container (The actual Splash Card)
        self.container = QFrame()
        self.container.setObjectName("SplashCard")
        self.container.setFixedSize(600, 500)
        self.container.setStyleSheet(f"""
            #SplashCard {{
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 20px;
            }}
        """)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # --- TOP SECTION: IMAGE ---
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.img_label.setScaledContents(False)
        self._welcome_pixmap = None
        
        # Resolve welcome.png path
        from ..core.utils import get_resource_path
        img_path = get_resource_path("welcome.png")
        
        if os.path.exists(img_path):
            self._welcome_pixmap = QPixmap(img_path)
            self._update_image()
        else:
            self.img_label.setText("Rocky Video Editor")
            self.img_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #888; background-color: #111;")
            self.img_label.setFixedHeight(350)

        container_layout.addWidget(self.img_label)
        
        # --- ROBUST ROUNDING MASK ---
        # Apply a mask to the container to ensure ALL child widgets (including image)
        # follow the 12px rounding without protrusions.
        self._update_container_mask()
        
        # --- BOTTOM SECTION: INFO ---
        self.info_area = QWidget()
        self.info_area.setFixedHeight(150)
        info_layout = QVBoxLayout(self.info_area)
        info_layout.setContentsMargins(20, 15, 20, 15)
        info_layout.setSpacing(10)
        
        # Version & Title
        title_row = QHBoxLayout()
        name_label = QLabel("ROCKY VIDEO EDITOR")
        name_label.setStyleSheet("font-size: 14px; font-weight: 800; color: #ddd; letter-spacing: 1px;")
        
        ver_label = QLabel("indev 0.01")
        ver_label.setStyleSheet("font-size: 11px; color: #888; font-weight: 400;")
        
        title_row.addWidget(name_label)
        title_row.addStretch()
        title_row.addWidget(ver_label)
        info_layout.addLayout(title_row)
        
        # Muted separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #333; max-height: 1px;")
        info_layout.addWidget(line)
        
        # Tagline / Credits
        tagline = QLabel("Potencia para creadores")
        tagline.setStyleSheet("font-size: 12px; color: #aaa; font-style: italic;")
        info_layout.addWidget(tagline)
        
        # GitHub Link
        repo_link = QLabel('<a href="https://github.com/rdr-retro/Rocky-Open-Source-Video-Editor" style="color: #4b7dbb; text-decoration: none;">GitHub Repository</a>')
        repo_link.setStyleSheet("font-size: 11px;")
        repo_link.setOpenExternalLinks(True)
        info_layout.addWidget(repo_link)
        
        info_layout.addStretch()
        
        # Footer
        footer_label = QLabel("Creado por Raúl Díaz y la comunidad de Rocky.")
        footer_label.setStyleSheet("font-size: 10px; color: #666;")
        info_layout.addWidget(footer_label)
        
        container_layout.addWidget(self.info_area)
        
        # Center the container in the full-screen dialog
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.container)
        center_layout.addStretch()
        
        self.layout.addStretch()
        self.layout.addLayout(center_layout)
        self.layout.addStretch()

    def _update_container_mask(self):
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.container.width(), self.container.height(), 20, 20)
        self.container.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _update_image(self):
        if not self._welcome_pixmap or self._welcome_pixmap.isNull():
            return
        
        # Match image area to container width and 70% of height
        target_w = self.container.width()
        target_h = int(self.container.height() * 0.7)
        if target_w <= 0 or target_h <= 0:
            return
        
        self.img_label.setFixedSize(target_w, target_h)
        
        # Fill the area without stretching, crop from center if needed
        scaled = self._welcome_pixmap.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        if scaled.width() != target_w or scaled.height() != target_h:
            x_off = max(0, (scaled.width() - target_w) // 2)
            y_off = max(0, (scaled.height() - target_h) // 2)
            scaled = scaled.copy(x_off, y_off, target_w, target_h)
        
        self.img_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_container_mask()
        self._update_image()

    def mousePressEvent(self, event):
        """Close if clicking outside the container."""
        # Convert click position to container coordinates
        pos_in_container = self.container.mapFromGlobal(event.globalPos())
        if not self.container.rect().contains(pos_in_container):
            self.close()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Dim the background slightly."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 120)))
        painter.end()
