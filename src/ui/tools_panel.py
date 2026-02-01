from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
import os
from . import design_tokens as dt

class ToolsPanel(QWidget):
    """
    Panel for video editing tools (Selection, Blade, Slip, etc.)
    Designed to be thin ("fino") with horizontal pill-shaped buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolsPanel")
        # self.setFixedHeight(32) # Removed for header integration
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._init_ui()

    def _init_ui(self):
        # Transparent background to blend with header
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #444;
                border-radius: 9px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: dt.ACCENT_PRIMARY;
            }
            QPushButton:checked {
                background-color: dt.ACCENT_PRIMARY;
                border-color: dt.ACCENT_PRIMARY;
                color: #000;
            }
        """.replace("dt.ACCENT_PRIMARY", dt.ACCENT_PRIMARY))

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # Zero margins for perfect integration
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Tool categories with tooltips
        tools = [
            ("selection.png", "Selección (V)", "select"),
            ("blade.png", "Cuchilla (C)", "cut"),
            ("transform.png", "Transformar (T)", "transform"),
            ("hand.png", "Mano (H)", "pan"),
            ("zoom.png", "Lupa (Z)", "zoom")
        ]

        for icon_name, tooltip_text, tool_id in tools:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(44, 18) # Matching pill shape from switcher
            btn.setToolTip(tooltip_text)
            
            icon_path = os.path.join(os.getcwd(), "src", "img", icon_name)
            if os.path.exists(icon_path):
                pix = QPixmap(icon_path).scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                btn.setIcon(QIcon(pix))
                btn.setIconSize(QSize(12, 12))
            
            self.layout.addWidget(btn)

        # self.layout.addStretch() # Removed to force strict left compaction
