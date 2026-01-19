from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPalette, QBrush, QFont

class AudioEnhancerPanel(QFrame):
    """
    Premium Audio Enhancement Panel with 'Antigravity' effects.
    """
    effect_applied = Signal(str, float) # effect_name, intensity

    def __init__(self):
        super().__init__()
        self.setObjectName("AudioEnhancer")
        self.setStyleSheet("""
            #AudioEnhancer {
                background-color: #0d041a;
                border-left: 1px solid #1a0b2e;
                border-right: 1px solid #1a0b2e;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Inter', sans-serif;
            }
            QPushButton {
                background-color: #1a0b2e;
                color: #00a3ff;
                border: 1px solid #3d1f5c;
                border-radius: 6px;
                padding: 10px;
                font-size: 11px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #2a124a;
                border-color: #00a3ff;
            }
            QPushButton#AntigravityBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a0b2e, stop:1 #4c1d95);
                color: #ffffff;
                border: 1px solid #a855f7;
            }
            QPushButton#AntigravityBtn:hover {
                border-color: #ffffff;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2a124a, stop:1 #5b21b6);
            }
            QSlider::handle:horizontal {
                background: #00a3ff;
                border: 1px solid #00a3ff;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #1a0b2e;
                height: 4px;
                background: #05020a;
                margin: 2px 0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("AUDIO INTELLIGENCE")
        header.setFont(QFont("Inter", 12, QFont.Bold))
        header.setStyleSheet("color: #00a3ff; letter-spacing: 1px;")
        layout.addWidget(header)

        desc = QLabel("Procesamiento avanzado para voz y ambiente.")
        desc.setStyleSheet("color: #888888; font-size: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # --- Effects Section ---
        
        # 1. Enhance Speech
        self.btn_enhance = QPushButton("✨ Enhance Speech\nLimpia ruido y eco de sala.")
        self.btn_enhance.clicked.connect(lambda: self.effect_applied.emit("enhance", self.slider_intensity.value()/100.0))
        layout.addWidget(self.btn_enhance)

        # 2. Studio EQ
        self.btn_studio = QPushButton("🎙 Studio Presence\nEcualización de podcast profesional.")
        self.btn_studio.clicked.connect(lambda: self.effect_applied.emit("studio", self.slider_intensity.value()/100.0))
        layout.addWidget(self.btn_studio)

        # 3. Antigravity (Special)
        self.btn_antigravity = QPushButton("🌌 Antigravity Mode\nEspacial, shimmer y flotación.")
        self.btn_antigravity.setObjectName("AntigravityBtn")
        self.btn_antigravity.clicked.connect(lambda: self.effect_applied.emit("antigravity", self.slider_intensity.value()/100.0))
        
        # Add a glow effect to Antigravity button
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(QColor(168, 85, 247, 150))
        glow.setOffset(0,0)
        self.btn_antigravity.setGraphicsEffect(glow)
        
        layout.addWidget(self.btn_antigravity)

        layout.addSpacing(20)

        # --- Controls ---
        intensity_label = QLabel("INTENSITY")
        intensity_label.setFont(QFont("Inter", 10, QFont.Bold))
        layout.addWidget(intensity_label)

        self.slider_intensity = QSlider(Qt.Orientation.Horizontal)
        self.slider_intensity.setRange(0, 100)
        self.slider_intensity.setValue(80)
        layout.addWidget(self.slider_intensity)

        layout.addStretch()

        # Footer / Info
        footer = QLabel("Powered by Rocky Engine 2.0")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #3d1f5c; font-size: 9px; font-weight: bold;")
        layout.addWidget(footer)
