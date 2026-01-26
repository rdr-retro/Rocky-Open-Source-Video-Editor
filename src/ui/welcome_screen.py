from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QWidget, QFrame, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPixmap, QColor, QFont, QPainter, QBrush, QPainterPath, QRegion
import os

from . import design_tokens as dt

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
                border-radius: 12px;
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
        
        # Resolve welcome.png path
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        img_path = os.path.join(base_path, "src", "img", "welcome.png")
        
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            # Use KeepAspectRatioByExpanding to fill the width, then we'll crop/center
            # This avoids horizontal stretching
            scaled_pixmap = pixmap.scaled(600, 350, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            # Crop to exactly 600x350 if it expanded vertically
            if scaled_pixmap.height() > 350:
                y_offset = (scaled_pixmap.height() - 350) // 2
                scaled_pixmap = scaled_pixmap.copy(0, y_offset, 600, 350)
            
            self.img_label.setPixmap(scaled_pixmap)
            self.img_label.setFixedSize(600, 350)
        else:
            self.img_label.setText("Rocky Video Editor")
            self.img_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #888; background-color: #111;")
            self.img_label.setFixedHeight(350)

        container_layout.addWidget(self.img_label)
        
        # --- ROBUST ROUNDING MASK ---
        # Apply a mask to the container to ensure ALL child widgets (including image)
        # follow the 12px rounding without protrusions.
        path = QPainterPath()
        path.addRoundedRect(0, 0, 600, 500, 12, 12)
        self.container.setMask(QRegion(path.toFillPolygon().toPolygon()))
        
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
