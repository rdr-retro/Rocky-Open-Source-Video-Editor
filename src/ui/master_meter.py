from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSlider
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QLinearGradient
from .styles import SLIDER_STYLE

class MasterMeterPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(100)
        self.setObjectName("MasterMeterPanel")
        self.setStyleSheet("""
            #MasterMeterPanel { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a0b2e, stop:1 #120820); 
                border-left: 2px solid #0a0412; 
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(12)
        
        self.fader = QSlider(Qt.Vertical)
        self.fader.setRange(0, 100)
        self.fader.setValue(75)
        self.fader.setStyleSheet(SLIDER_STYLE)
        
        layout.addWidget(self.fader)
        self.meter = MeterDisplay()
        layout.addWidget(self.meter)

class MeterDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(50)
        self.l_level, self.r_level = 0.0, 0.0
        self.target_l, self.target_r = 0.0, 0.0
        
        # Timer for smooth decay (like professional analog/digital meters)
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self.process_decay)
        self.decay_timer.start(33) # ~30 FPS UI refresh

    def set_levels(self, l, r):
        # We take the peak if higher, or update target for decay
        self.target_l = max(self.target_l, l)
        self.target_r = max(self.target_r, r)
        # Immediate boost
        self.l_level = max(self.l_level, l)
        self.r_level = max(self.r_level, r)
        self.update()

    def process_decay(self):
        # Smooth falloff
        decay_factor = 0.85 
        self.l_level *= decay_factor
        self.r_level *= decay_factor
        self.target_l *= decay_factor
        self.target_r *= decay_factor
        
        if self.l_level < 0.001: self.l_level = 0.0
        if self.r_level < 0.001: self.r_level = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = 7
        
        # Background channels
        dark_bg = QColor("#120820")
        p.fillRect(0, 0, bar_w, h, dark_bg)
        p.fillRect(w - bar_w, 0, bar_w, h, dark_bg)
        
        # Grid and Labels
        p.setPen(QColor("#dcd0ff"))
        font = QFont("Arial", 6)
        font.setPixelSize(9)
        p.setFont(font)
        
        labels = [("0", 0.0), ("-6", 0.1), ("-12", 0.25), ("-24", 0.45), ("-48", 0.70), ("-Inf.", 1.0)]
        margin_y = 10
        eff_h = h - 2 * margin_y
        
        for text, pos in labels:
            y = margin_y + eff_h * pos
            p.drawText(bar_w + 2, int(y) + 4, w - 2*bar_w - 4, 10, Qt.AlignCenter, text)
            p.setPen(QColor("#333333"))
            p.drawLine(0, int(y), bar_w, int(y))
            p.drawLine(w - bar_w, int(y), w, int(y))
            p.setPen(QColor("#dcd0ff"))

        # Gradients (Green -> Yellow -> Red)
        def draw_bar(x, level):
            if level <= 0: return
            normalized_level = min(1.0, level)
            bar_h = int(eff_h * normalized_level)
            
            grad = QLinearGradient(0, h - margin_y, 0, margin_y)
            grad.setColorAt(0, QColor("#00ff44")) # Green
            grad.setColorAt(0.7, QColor("#ffff00")) # Yellow
            grad.setColorAt(0.9, QColor("#ff0000")) # Red
            
            p.fillRect(x, h - margin_y - bar_h, bar_w, bar_h, grad)

        draw_bar(0, self.l_level)
        draw_bar(w - bar_w, self.r_level)
        
        # Subtle "glass" scanlines
        p.setPen(QColor(0,0,0,100))
        for y in range(margin_y, h - margin_y, 3):
            p.drawLine(0, y, bar_w, y)
            p.drawLine(w - bar_w, y, w, y)
