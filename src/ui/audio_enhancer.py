from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from . import design_tokens as dt

# ============================================================================
# CONSTANTS & STYLES
# ============================================================================

ENHANCER_STYLES = f"""
    #AudioEnhancer {{
        background-color: #0d041a;
        border-left: 1px solid #1a0b2e;
        border-right: 1px solid #1a0b2e;
    }}
    QLabel {{
        color: #e0e0e0;
        font-family: {dt.FONT_FAMILY_UI};
    }}
    QSlider::handle:horizontal {{
        background: {dt.ACCENT_PRIMARY};
        border: 1px solid {dt.ACCENT_PRIMARY};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::groove:horizontal {{
        border: 1px solid #1a0b2e;
        height: 4px;
        background: #05020a;
        margin: 2px 0;
    }}
"""

EFFECT_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: #1a0b2e;
        color: #00a3ff;
        border: 1px solid #3d1f5c;
        border-radius: 6px;
        padding: 10px;
        font-size: 11px;
        font-weight: bold;
        text-align: left;
    }}
    QPushButton:hover {{
        background-color: #2a124a;
        border-color: #00a3ff;
    }}
"""

ANTIGRAVITY_LEVEL_STYLE = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a0b2e, stop:1 #4c1d95);
        color: #ffffff;
        border: 1px solid #a855f7;
    }}
    QPushButton:hover {{
        border-color: #ffffff;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2a124a, stop:1 #5b21b6);
    }}
"""

# ============================================================================
# UI COMPONENTS
# ============================================================================

class EffectButton(QPushButton):
    """
    Custom button specialized for audio effects with title and description.
    """
    def __init__(self, title: str, description: str, special: bool = False, parent=None):
        text = f" {title}\n{description}"
        super().__init__(text, parent)
        
        self.setStyleSheet(ANTIGRAVITY_LEVEL_STYLE if special else EFFECT_BUTTON_STYLE)
        
        if special:
            self._apply_glow_effect()

    def _apply_glow_effect(self):
        """Adds a subtle purple glow to highlight premium effects."""
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(15)
        glow.setColor(QColor(168, 85, 247, 150))
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

class AudioEnhancerPanel(QFrame):
    """
    High-end Audio Intelligence panel that provides advanced processing controls.
    Refactored to follow Clean Code principles and modular architecture.
    """
    effect_triggered = Signal(str, float) # (effect_type, intensity_normalized)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AudioEnhancer")
        
        # State
        self.slider_intensity = None
        
        self._initialize_ui()
        self._apply_styles()

    def _initialize_ui(self):
        """Orchestrates the creation of all UI elements."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 20)
        main_layout.setSpacing(15)

        self._add_header_section(main_layout)
        self._add_effects_section(main_layout)
        self._add_controls_section(main_layout)
        
        main_layout.addStretch()
        self._add_footer_section(main_layout)

    def _add_header_section(self, layout: QVBoxLayout):
        """Creates the title and introductory description."""
        header = QLabel("AUDIO INTELLIGENCE")
        header.setFont(QFont("Inter", 12, QFont.Bold))
        header.setStyleSheet(f"color: {dt.ACCENT_PRIMARY}; letter-spacing: 1px;")
        
        desc = QLabel("Advanced processing powered by Rocky Audio Engine.")
        desc.setStyleSheet("color: #888888; font-size: 10px;")
        desc.setWordWrap(True)
        
        layout.addWidget(header)
        layout.addWidget(desc)
        layout.addSpacing(10)

    def _add_effects_section(self, layout: QVBoxLayout):
        """Populates the panel with available audio processing buttons."""
        
        # 1. Speech Enhancement
        btn_enhance = EffectButton(
            "Enhance Speech", 
            "Cleans background noise and room echo."
        )
        btn_enhance.clicked.connect(lambda: self._on_effect_clicked("enhance"))
        
        # 2. Studio EQ
        btn_studio = EffectButton(
            "🎙 Studio Presence", 
            "Professional podcast-grade equalization."
        )
        btn_studio.clicked.connect(lambda: self._on_effect_clicked("studio"))
        
        # 3. Antigravity Mode (Special)
        btn_antigravity = EffectButton(
            "🌌 Antigravity Mode", 
            "Spatial shimmer and floating harmonics.",
            special=True
        )
        btn_antigravity.clicked.connect(lambda: self._on_effect_clicked("antigravity"))

        layout.addWidget(btn_enhance)
        layout.addWidget(btn_studio)
        layout.addWidget(btn_antigravity)

    def _add_controls_section(self, layout: QVBoxLayout):
        """Creates the global intensity controls."""
        layout.addSpacing(20)
        
        label = QLabel("PROCESS INTENSITY")
        label.setFont(QFont("Inter", 10, QFont.Bold))
        
        self.slider_intensity = QSlider(Qt.Orientation.Horizontal)
        self.slider_intensity.setRange(0, 100)
        self.slider_intensity.setValue(80)
        
        layout.addWidget(label)
        layout.addWidget(self.slider_intensity)

    def _add_footer_section(self, layout: QVBoxLayout):
        """Adds branding at the bottom of the panel."""
        footer = QLabel("Rocky Engine 2.0")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #3d1f5c; font-size: 9px; font-weight: bold;")
        layout.addWidget(footer)

    def _apply_styles(self):
        """Sets the widget stylesheet."""
        self.setStyleSheet(ENHANCER_STYLES)

    def _on_effect_clicked(self, effect_type: str):
        """Normalizes and emits signal when an effect is selected."""
        intensity = self.slider_intensity.value() / 100.0
        self.effect_triggered.emit(effect_type, intensity)
