from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QSlider, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QImage, QPixmap

class ViewerPanel(QWidget):
    """
    Component responsible for rendering and displaying the final video output
    from the C++ engine. Handles pixel buffer conversion and aspect ratio scaling.
    """
    def __init__(self):
        super().__init__()
        self.initialize_ui()
        
    def initialize_ui(self):
        """Standardized UI initialization following Clean Code standards."""
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)  # CRITICAL: Ensure minimum height
        self.setObjectName("ViewerPanel")
        
        # CRITICAL FIX: Force the viewer to expand and take all available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setStyleSheet("""
            #ViewerPanel {
                background-color: #000000;
                border: none;
            }

        """)



        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Rendering Surface (The Screen) - MUST take all available space
        self.rendering_surface = self._create_rendering_surface()
        main_layout.addWidget(self.rendering_surface, stretch=10)  # High stretch factor
        
        # 2. Playback Controls - Fixed height
        self.controls_bar = self._create_controls_bar()
        main_layout.addWidget(self.controls_bar, stretch=0)
        
        # 3. Project Information Panel - Fixed height
        self.info_panel = self._create_info_panel()
        main_layout.addWidget(self.info_panel, stretch=0)
        


    def _create_rendering_surface(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet("background-color: #000000; border: none;")
        
        # CRITICAL: Container must expand to fill available space
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("background-color: black;")
        # CRITICAL FIX: Allow the label to expand to fill available space
        # This ensures vertical videos scale properly to fill the viewer
        self.display_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.display_label.setScaledContents(False)  # We handle scaling manually
        self.display_label.setMinimumSize(1, 1)  # Allow shrinking
        
        layout.addWidget(self.display_label, stretch=1)
        return container
        
    def _create_controls_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(45)
        bar.setStyleSheet("background-color: #111111; border: none;")


        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        control_btn_style = """
            QPushButton { 
                background-color: transparent; 
                color: #e0e0e0; 
                border: none; 
                border-radius: 4px;
                font-size: 20px;
                font-family: "Segoe UI Symbol", "Apple Symbols", sans-serif;
            } 
            QPushButton:hover { 
                background-color: #333333; 
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #222222;
                color: #00a3ff;
            }
        """
        
        
        self.btn_rewind = QPushButton("⏮")
        self.btn_play_pause = QPushButton("▶")
        self.btn_fullscreen = QPushButton("⛶")
        
        # Rate Control (Shuttle)
        self.rate_container = QWidget()
        rate_layout = QHBoxLayout(self.rate_container)
        rate_layout.setContentsMargins(15, 0, 15, 0)
        rate_layout.setSpacing(8)
        
        self.lbl_rate = QLabel("1.0x")
        self.lbl_rate.setStyleSheet("color: #888; font-family: 'Inter'; font-size: 10px; font-weight: bold; min-width: 30px;")
        
        self.slider_rate = QSlider(Qt.Orientation.Horizontal)
        self.slider_rate.setRange(20, 300) # 0.2x to 3.0x
        self.slider_rate.setValue(100)      # 1.0x
        self.slider_rate.setFixedWidth(100)
        self.slider_rate.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 3px;
                background: #111;
                margin: 2px 0;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #00a3ff;
                border: 1px solid #00a3ff;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
        """)
        
        # Spring-loaded behavior: Returns to 1.0x on release
        self.slider_rate.sliderReleased.connect(lambda: self._reset_rate())
        
        rate_layout.addWidget(self.lbl_rate)
        rate_layout.addWidget(self.slider_rate)

        
        # Rewind Button (Go to Start)
        self.btn_rewind.setFixedSize(32, 32)
        self.btn_rewind.setToolTip("Ir al inicio")
        self.btn_rewind.setStyleSheet(control_btn_style)
        
        # Play/Pause Toggle
        self.btn_play_pause.setFixedSize(40, 40) # Slightly larger
        self.btn_play_pause.setToolTip("Reproducir / Pausar")
        self.btn_play_pause.setStyleSheet(control_btn_style)
        
        # Fullscreen Button
        self.btn_fullscreen.setFixedSize(32, 32)
        self.btn_fullscreen.setToolTip("Pantalla Completa")
        self.btn_fullscreen.setStyleSheet(control_btn_style)
        
        layout.addStretch()
        layout.addWidget(self.btn_rewind)
        layout.addWidget(self.btn_play_pause)
        layout.addWidget(self.rate_container) # Insert between play and fullscreen
        layout.addWidget(self.btn_fullscreen)
        layout.addStretch()
            
        return bar

    def _reset_rate(self):
        self.slider_rate.setValue(100)
        self.lbl_rate.setText("1.0x")


    def _create_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333333;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Project format info
        row1 = QHBoxLayout()
        self.lbl_format = QLabel("Proyecto: 1920x1080 (16:9 - Horizontal)")
        self.lbl_format.setStyleSheet("color: #00a3ff; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
        row1.addWidget(self.lbl_format)
        row1.addStretch()
        
        # Performance metadata
        row2 = QHBoxLayout()
        lbl_engine = QLabel("Engine: Rocky Core C++ (Hardware Accelerated)")
        lbl_engine.setStyleSheet("color: #6272a4; font-family: 'Inter'; font-size: 10px;")
        row2.addWidget(lbl_engine)
        row2.addStretch()
        
        layout.addLayout(row1)
        layout.addLayout(row2)
        return panel



    def update_format_label(self, width, height):
        """Update the format label with current project resolution."""
        from math import gcd
        divisor = gcd(width, height)
        aspect_w = width // divisor
        aspect_h = height // divisor
        is_vertical = height > width
        format_type = "Vertical" if is_vertical else "Horizontal"
        
        if hasattr(self, 'lbl_format'):
            self.lbl_format.setText(f"Proyecto: {width}x{height} ({aspect_w}:{aspect_h} - {format_type})")

    def display_frame(self, frame_buffer):
        """
        Efficiently converts project RAW buffers into QPixmap for presentation.
        CRITICAL: Vertical videos MUST fill the entire height of the viewer.
        
        :param frame_buffer: A numpy array (Height, Width, 4) in RGBA format.
        """
        if frame_buffer is None:
            return

        try:
            height, width, channels = frame_buffer.shape
            bytes_per_line = channels * width
            
            # Create QImage directly from buffer memory (No-copy)
            image = QImage(frame_buffer.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image)
            
            if not self.display_label.size().isEmpty():
                label_size = self.display_label.size()
                
                # CRITICAL FIX: Scale to fill the ENTIRE label size
                # Qt will maintain aspect ratio and fit it within these bounds
                # For vertical videos, this means filling the height
                # For horizontal videos, this means filling the width
                scaled_pixmap = pixmap.scaled(
                    label_size.width(),
                    label_size.height(),
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Debug output with widget hierarchy
                is_vertical = height > width
                if is_vertical and not hasattr(self, '_printed_hierarchy'):
                    widget = self
                    depth = 0
                    while widget and depth < 10:
                        name = widget.objectName() or widget.__class__.__name__
                        size = widget.size()
                        policy = widget.sizePolicy()
                        print(f"{'  ' * depth}{name}: {size.width()}x{size.height()} (H:{policy.horizontalPolicy()}, V:{policy.verticalPolicy()})")
                        widget = widget.parentWidget()
                        depth += 1
                    print("========================")
                    self._printed_hierarchy = True
                elif is_vertical:
                    pass
                
                self.display_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Viewer Error: Failed to render frame: {e}")

