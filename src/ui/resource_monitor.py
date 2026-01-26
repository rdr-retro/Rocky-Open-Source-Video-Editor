import os
import random
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QPixmap, QColor, QLinearGradient, QMovie
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
        self.main_layout.setContentsMargins(10, 10, 10, 10) # Reduced from 15
        self.main_layout.setSpacing(0)
        
        # Flat layout - no decorative boxes
        main_content = QWidget()
        content_layout = QHBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10) # Reduced from 20
        
        # --- LEFT: Bars + DNA (FLATTENED) ---
        left_column = QWidget()
        left_layout = QHBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        # Tight spacing so they look like they belong in the same "box"
        left_layout.setSpacing(0) 
        
        self.cpu_bar = self._create_resource_bar("CPU")
        self.ram_bar = self._create_resource_bar("RAM")
        
        # DNA directly to the right, same parent layout
        self.dna_container = QFrame()
        self.dna_container.setFixedSize(66, 110) # Adjusted width for 300x500 GIF
        self.dna_container.setStyleSheet("border: none; background: transparent;")
        dna_layout = QVBoxLayout(self.dna_container)
        dna_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ani_label = QLabel()
        self.ani_label.setAlignment(Qt.AlignCenter)
        dna_layout.addWidget(self.ani_label)
        
        # Add all to same layout, align bottom to keep labels and DNA aligned
        left_layout.addWidget(self.cpu_bar, 0, Qt.AlignBottom)
        left_layout.addWidget(self.ram_bar, 0, Qt.AlignBottom)
        left_layout.addWidget(self.dna_container, 0, Qt.AlignBottom)
        
        content_layout.addWidget(left_column, 1)
        
        # --- RIGHT: Text (no box) ---
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4) # Reduced from 8
        
        self.tech_labels = []
        tech_lines = [
            "KERNEL_HOST: ROCKY_X86_64",
            "STATUS: OPTIMIZED",
            "CPU_THREAD_POOL: 9_THREADS",
            "IO_STREAM: ASYNC_ACTIVE",
            "MEM_PROTECT: ENABLED"
        ]
        for line in tech_lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("color: #49d4e5; font-family: 'Courier New'; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            text_layout.addWidget(lbl)
            self.tech_labels.append(lbl)
        
        text_layout.addStretch()
        content_layout.addWidget(text_widget, 2)
        
        self.main_layout.addWidget(main_content)
        self.main_layout.addStretch()
        
        # --- LOGIC & ANIMATION ---
        self.movie = None
        self._load_gif()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_telemetry)
        self.update_timer.start(66) # 15 FPS
        
    def _create_resource_bar(self, label):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(1) # Reduced from 6 to 1 to keep label close to bar
        
        bar_frame = QFrame()
        bar_frame.setFixedSize(18, 120)
        bar_frame.setStyleSheet("background-color: #0d0d0d; border: none;")
        
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

    def _load_gif(self):
        gif_path = os.path.join(os.getcwd(), "src", "img", "adn.gif")
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            # Aspect ratio 300x500 -> 66x110
            self.movie.setScaledSize(QSize(66, 110))
            self.ani_label.setMovie(self.movie)
            self.movie.start()

    def _update_telemetry(self):
        # 1. Update DNA Animation (handled by QMovie now)
        pass
            
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
