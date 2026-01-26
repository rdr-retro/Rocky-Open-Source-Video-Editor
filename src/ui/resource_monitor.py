import os
import random
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QPixmap, QColor, QLinearGradient
try:
    import psutil
except ImportError:
    psutil = None

class ResourceMonitorPanel(QWidget):
    """
    Independent Rocky Panel for system telemetry.
    Replicates the 'Lab ADN' UI exactly from the reference image.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ResourceMonitor")
        self.setStyleSheet("background-color: #0d0d0d;")
        
        # Outer container for centering/padding
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(0)
        
        # 1. Main Horizontal Interface Container
        self.ui_container = QFrame()
        self.ui_container.setStyleSheet("background-color: rgba(10, 40, 50, 0.2); border: 1px solid #1a3a40; border-radius: 4px;")
        ui_layout = QHBoxLayout(self.ui_container)
        ui_layout.setContentsMargins(15, 15, 15, 15)
        ui_layout.setSpacing(25) # Professional spacing between modules
        
        # --- MODULE 1: BARS (Left) ---
        bars_container = QWidget()
        bars_layout = QHBoxLayout(bars_container)
        bars_layout.setContentsMargins(0, 0, 0, 0)
        bars_layout.setSpacing(8)
        
        self.cpu_bar = self._create_resource_bar("CPU")
        self.ram_bar = self._create_resource_bar("RAM")
        
        bars_layout.addWidget(self.cpu_bar)
        bars_layout.addWidget(self.ram_bar)
        ui_layout.addWidget(bars_container)
        
        # --- MODULE 2: ADN SEQUENCE (Center) ---
        self.dna_container = QFrame()
        self.dna_container.setFixedSize(160, 160) # Larger size for the DNA
        self.dna_container.setStyleSheet("border: 1px solid #1e5a61; background: rgba(0, 0, 0, 0.3);")
        dna_layout = QVBoxLayout(self.dna_container)
        dna_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ani_label = QLabel()
        self.ani_label.setAlignment(Qt.AlignCenter)
        dna_layout.addWidget(self.ani_label)
        
        ui_layout.addWidget(self.dna_container)
        
        # --- MODULE 3: TELEMETRY TABLE (Right) ---
        self.info_box = QFrame()
        self.info_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 50, 60, 0.4);
                border: 1px solid #1e5a61;
                border-radius: 4px;
            }
        """)
        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(15, 12, 15, 12)
        info_layout.setSpacing(5)
        
        self.tech_labels = []
        # Professional Technical Lines
        tech_lines = [
            "KERNEL_HOST: ROCKY_X86_64",
            "STATUS: OPTIMIZED",
            "CPU_THREAD_POOL: 9_THREADS",
            "IO_STREAM: ASYNC_ACTIVE",
            "MEM_PROTECT: ENABLED"
        ]
        for line in tech_lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("color: #49d4e5; font-family: 'Courier New'; font-size: 10px; font-weight: bold; border: none; background: transparent;")
            info_layout.addWidget(lbl)
            self.tech_labels.append(lbl)
            
        ui_layout.addWidget(self.info_box, 1) # Information expands to fill
        
        self.main_layout.addWidget(self.ui_container)
        self.main_layout.addStretch() # Content stays top-aligned
        
        # --- LOGIC & ANIMATION ---
        self.frames = []
        self.current_frame = 0
        self._load_sequence()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_telemetry)
        self.update_timer.start(66) # 15 FPS
        
    def _create_resource_bar(self, label):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(6)
        
        bar_frame = QFrame()
        bar_frame.setFixedSize(18, 120)
        bar_frame.setStyleSheet("background-color: #0d0d0d; border: 1px solid #1e5a61; border-radius: 2px;")
        
        # Internal progress level
        self.level_rect = QFrame(bar_frame)
        self.level_rect.setFixedWidth(18)
        self.level_rect.setStyleSheet("background-color: #49d4e5; border-radius: 1px;")
        
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #49d4e5; font-family: 'Courier New'; font-size: 9px; font-weight: bold;")
        
        v_layout.addWidget(bar_frame)
        v_layout.addWidget(lbl)
        
        container.level_indicator = self.level_rect
        return container

    def _load_sequence(self):
        adn_dir = os.path.join(os.getcwd(), "src", "img", "adn")
        if os.path.exists(adn_dir):
            for i in range(123, 141):
                fpath = os.path.join(adn_dir, f"{i:04d}.png")
                if os.path.exists(fpath):
                    # Scale according to the central ADN module size
                    pix = QPixmap(fpath).scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.frames.append(pix)

    def _update_telemetry(self):
        # 1. Update DNA Animation
        if self.frames:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.ani_label.setPixmap(self.frames[self.current_frame])
            
        # 2. Real System Monitoring (CPU/RAM)
        cpu_val = 0
        ram_val = 0
        
        if psutil:
            cpu_val = psutil.cpu_percent()
            ram_val = psutil.virtual_memory().percent
        else:
            self.tech_labels[1].setText("STATUS: PSUTIL_NOT_FOUND")

        self._set_bar_level(self.cpu_bar, cpu_val)
        self._set_bar_level(self.ram_bar, ram_val)
        
        # 3. Dynamic Technical Mood Updates
        if random.random() > 0.95:
             self.tech_labels[0].setText(f"KERNEL_HOST: NODE_{random.randint(10, 99)}")

    def _set_bar_level(self, bar_container, percent):
        max_h = 120
        new_h = int(max_h * (max(1, percent) / 100.0))
        bar_container.level_indicator.setFixedHeight(new_h)
        bar_container.level_indicator.move(0, max_h - new_h)
