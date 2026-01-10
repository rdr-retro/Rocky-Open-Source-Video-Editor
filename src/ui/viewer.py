from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QImage, QPixmap

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
        self.setObjectName("ViewerPanel")
        self.setStyleSheet("background-color: #333333; color: #ffffff;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Rendering Surface (The Screen)
        self.rendering_surface = self._create_rendering_surface()
        main_layout.addWidget(self.rendering_surface, stretch=1)
        
        # 2. Playback Controls
        self.controls_bar = self._create_controls_bar()
        main_layout.addWidget(self.controls_bar)
        
        # 3. Project Information Panel
        self.info_panel = self._create_info_panel()
        main_layout.addWidget(self.info_panel)
        


    def _create_rendering_surface(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet("background-color: #000000; border: 1px solid #333333;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("background-color: black;")
        # Fix: Prevent the label from growing and pushing the timeline down during playback
        from PyQt5.QtWidgets import QSizePolicy
        self.display_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.display_label)
        return container
        
    def _create_controls_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(45)
        bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333333;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setAlignment(Qt.AlignCenter)
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
        layout.addWidget(self.btn_fullscreen)
        layout.addStretch()
            
        return bar

    def _create_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333333;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Performance metadata only
        row2 = QHBoxLayout()
        lbl_engine = QLabel("Engine: Rocky Core C++ (Hardware Accelerated)")
        lbl_engine.setStyleSheet("color: #6272a4; font-family: 'Inter'; font-size: 10px;")
        row2.addWidget(lbl_engine)
        row2.addStretch()
        
        layout.addLayout(row2)
        return panel



    def display_frame(self, frame_buffer):
        """
        Efficiently converts project RAW buffers into QPixmap for presentation.
        Optimizes aspect-ratio scaling to maintain visual integrity.
        
        :param frame_buffer: A numpy array (Height, Width, 4) in RGBA format.
        """
        if frame_buffer is None:
            return

        try:
            height, width, channels = frame_buffer.shape
            bytes_per_line = channels * width
            
            # Create QImage directly from buffer memory (No-copy)
            image = QImage(frame_buffer.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image)
            
            if not self.display_label.size().isEmpty():
                # Perform smooth scaling into the view area
                scaled_pixmap = pixmap.scaled(
                    self.display_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.display_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Viewer Error: Failed to render frame: {e}")

