from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QPushButton, QComboBox, QCheckBox, QGridLayout, QWidget)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    """
    Premium Export/Render dialog with multi-resolution support.
    Follows the same minimalist aesthetic as the settings dialog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar Proyecto")
        self.resize(500, 450)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                color: #ffffff;
            }
            QLabel {
                font-family: 'Inter', sans-serif;
            }
            QLabel#Title {
                font-size: 18px;
                font-weight: 700;
                color: #fff;
                margin-bottom: 20px;
            }
            QLabel.SectionTitle {
                color: #333;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-top: 10px;
                margin-bottom: 15px;
            }
            QComboBox {
                background-color: #111;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
                color: #eee;
                padding: 10px 12px;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #222;
                background-color: #141414;
            }
            QComboBox::drop-down {
                border: none;
            }
            QCheckBox {
                color: #777;
                font-size: 11px;
                spacing: 12px;
                margin-top: 10px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #0a0a0a;
                border: 1px solid #222;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #00a3ff;
                border-color: #00a3ff;
            }
            QPushButton#ActionBtn {
                background-color: #ffffff;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 12px 35px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton#ActionBtn:hover {
                background-color: #dddddd;
            }
            QPushButton#SecondaryBtn {
                background-color: transparent;
                color: #444;
                border: none;
                padding: 10px 20px;
                font-size: 11px;
            }
            QPushButton#SecondaryBtn:hover {
                color: #888;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Configuración de Exportación")
        title.setObjectName("Title")
        layout.addWidget(title)

        # 1. Format & Resolution Section
        sec_res = QLabel("RESOLUCIÓN Y FORMATO")
        sec_res.setProperty("class", "SectionTitle")
        layout.addWidget(sec_res)

        self.res_combo = QComboBox()
        self.res_combo.addItems([
            "4K Ultra HD (3840 x 2160)",
            "2K Quad HD (2560 x 1440)",
            "Full HD 1080p (1920 x 1080)",
            "HD 720p (1280 x 720)",
            "SD 480p (854 x 480)",
            "Instagram Vertical (1080 x 1920)",
            "Instagram Square (1080 x 1080)",
            "TikTok / Reels (720 x 1280)",
            "Twitter / X (1280 x 720)",
            "YouTube Shorts (1080 x 1920)",
            "Cinematic 21:9 (2560 x 1080)",
            "Cinematic 4K (4096 x 1714)"
        ])
        self.res_combo.setCurrentIndex(2) # Default 1080p
        layout.addWidget(self.res_combo)

        # 2. Codec Section
        sec_codec = QLabel("CÓDEC Y CALIDAD")
        sec_codec.setProperty("class", "SectionTitle")
        layout.addWidget(sec_codec)

        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "H.264 / AVC (Alta Compatibilidad)",
            "H.265 / HEVC (Máxima Compresión)",
            "Apple ProRes 422 (Calidad Máster)",
            "GIF Animado (Baja Resolución)"
        ])
        layout.addWidget(self.codec_combo)

        self.cb_hq = QCheckBox("Exportación de alta fidelidad (VBR 2-Pass)")
        self.cb_hq.setChecked(True)
        layout.addWidget(self.cb_hq)

        layout.addStretch()

        # Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        
        export_btn = QPushButton("Iniciar Exportación")
        export_btn.setObjectName("ActionBtn")
        export_btn.clicked.connect(self.accept)
        
        action_bar.addStretch()
        action_bar.addWidget(cancel_btn)
        action_bar.addWidget(export_btn)
        
        layout.addLayout(action_bar)

    def get_selected_config(self):
        """Returns the dimensions and codec selected by the user."""
        res_text = self.res_combo.currentText()
        # Parse dimensions from string like "(1920 x 1080)"
        import re
        dims = re.findall(r'\d+', res_text)
        if len(dims) >= 2:
            w, h = int(dims[-2]), int(dims[-1])
        else:
            w, h = 1920, 1080
            
        return {
            "width": w,
            "height": h,
            "codec": self.codec_combo.currentText(),
            "high_quality": self.cb_hq.isChecked()
        }
