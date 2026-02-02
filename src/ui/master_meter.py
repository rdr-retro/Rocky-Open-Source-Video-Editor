from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QLinearGradient
from .styles import SLIDER_STYLE

class MasterMeterPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Optimized: Allow shrinking, max compact width
        self.setMinimumWidth(40) 
        self.setMaximumWidth(80)
        self.setObjectName("MasterMeterPanel")
        self.setStyleSheet("""
            #MasterMeterPanel { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a0b2e, stop:1 #120820); 
                border-left: 1px solid #0a0412; 
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(2)
        
        self.fader = QSlider(Qt.Orientation.Vertical)
        self.fader.setRange(0, 100)
        self.fader.setValue(75)
        self.fader.setFixedWidth(18)
        self.fader.setStyleSheet(SLIDER_STYLE)
        
        layout.addWidget(self.fader)
        self.meter = MeterDisplay()
        layout.addWidget(self.meter)

class MeterDisplay(QWidget):
    def __init__(self):
        super().__init__()
        # Flexible width instead of fixed 35
        self.setMinimumWidth(20) 
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
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # Professional Constants
        BAR_WIDTH = 6
        SEGMENT_HEIGHT = 2
        SEGMENT_GAP = 1
        MARGIN_TOP = 4
        MARGIN_BOTTOM = 4
        
        # Background
        p.fillRect(self.rect(), QColor("#121212")) # Ultra dark background
        
        # Meter Channels positions
        # Center the numeric scale, put bars on sides
        center_x = w / 2
        bar_l_x = center_x - 10 - BAR_WIDTH
        bar_r_x = center_x + 10
        
        # Draw Dark Tracks (Empty State)
        track_color = QColor("#1a1a1a")
        eff_h = h - MARGIN_TOP - MARGIN_BOTTOM
        p.fillRect(int(bar_l_x), MARGIN_TOP, BAR_WIDTH, eff_h, track_color)
        p.fillRect(int(bar_r_x), MARGIN_TOP, BAR_WIDTH, eff_h, track_color)
        
        # --- DRAW SCALE ---
        p.setPen(QColor("#666666"))
        font = QFont("Inter", 7)
        font.setBold(True)
        p.setFont(font)
        
        # dB Scale mapping positions (0.0=top, 1.0=bottom)
        # We'll use a linear mapping for visuals, but label it logarithmic-ish
        labels = [
            ("0", 0.0, "#ff4444"), 
            ("-6", 0.15, "#ffcc00"), 
            ("-12", 0.30, "#00ff00"), 
            ("-24", 0.50, "#00cc00"), 
            ("-48", 0.75, "#008800"), 
            ("-∞", 0.95, "#004400")
        ]
        
        for text, rel_y, color in labels:
            y = MARGIN_TOP + (rel_y * eff_h)
            # Center text
            p.setPen(QColor(color))
            p.drawText(int(center_x - 10), int(y) - 4, 20, 10, Qt.AlignmentFlag.AlignCenter, text)
            # Ticks
            p.setPen(QColor("#333333"))
            p.drawLine(int(bar_l_x) + BAR_WIDTH + 1, int(y), int(bar_r_x) - 1, int(y))

        # --- DRAW BARS (Segmented Style) ---
        def get_color_for_height(normalized_y):
            # 0.0 (Bottom) -> 1.0 (Top)
            if normalized_y > 0.85: return QColor("#ff3333") # Red (Clip)
            if normalized_y > 0.70: return QColor("#ffba00") # Yellow (Warning)
            return QColor("#00ff44") # Green (Normal)

        def render_channel(x_pos, level):
            if level <= 0: return
            normalized_level = max(0.0, min(1.0, level))
            
            # Calculate total segments
            total_segments = eff_h // (SEGMENT_HEIGHT + SEGMENT_GAP)
            lit_segments = int(total_segments * normalized_level)
            
            for i in range(lit_segments):
                # Build from bottom up
                seg_y = (h - MARGIN_BOTTOM) - (i * (SEGMENT_HEIGHT + SEGMENT_GAP)) - SEGMENT_HEIGHT
                
                # Color calculation based on height
                rel_height = i / total_segments
                col = get_color_for_height(rel_height)
                
                p.fillRect(int(x_pos), int(seg_y), BAR_WIDTH, SEGMENT_HEIGHT, col)

        # Draw L/R
        render_channel(bar_l_x, self.l_level)
        render_channel(bar_r_x, self.r_level)
