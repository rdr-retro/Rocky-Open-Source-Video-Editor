from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QPushButton, QComboBox, QCheckBox, QSpinBox, QGridLayout, 
                             QSizePolicy, QWidget, QListWidget, QListWidgetItem, QStackedWidget)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QFont

class PreferencesDialog(QDialog):
    """
    macOS-style Preferences dialog with sidebar navigation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferencias")
        self.resize(900, 600)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: none;
                border-right: 1px solid #1f1f1f;
                outline: none;
                padding: 8px 0;
            }
            QListWidget::item {
                color: #b8b8b8;
                padding: 10px 20px;
                border: none;
                font-size: 13px;
                border-radius: 6px;
                margin: 2px 8px;
            }
            QListWidget::item:selected {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a9fd4, stop:1 #4a8fc4);
                color: #ffffff;
            }
            QListWidget::item:hover:!selected {
                background-color: #3a3a3a;
            }
        """)
        
        # Add sidebar items
        categories = ["Vídeo", "Audio", "Proxies", "Visor"]
        for cat in categories:
            item = QListWidgetItem(cat)
            self.sidebar.addItem(item)
        
        # Content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #3a3a3a;
            }
        """)
        
        # Create content pages (without theme page)
        self.content_stack.addWidget(self._create_video_page())
        self.content_stack.addWidget(self._create_audio_page())
        self.content_stack.addWidget(self._create_proxy_page())
        self.content_stack.addWidget(self._create_preview_page())
        
        # Connect sidebar selection
        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        
        # Add to main layout
        main_layout.addWidget(self.sidebar)
        
        # Right side container (Stack + Action Bar)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        right_layout.addWidget(self.content_stack)
        
        # Action Bar
        action_bar = QFrame()
        action_bar.setStyleSheet("background-color: #2d2d2d; border-top: 1px solid #1f1f1f;")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(20, 15, 20, 15)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b8b8b8;
                border: 1px solid #4f4f4f;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: white;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Guardar Cambios")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #00a3ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #33b5ff;
            }
        """)
        btn_save.clicked.connect(self.accept)
        
        action_layout.addStretch()
        action_layout.addWidget(btn_cancel)
        action_layout.addWidget(btn_save)
        
        right_layout.addWidget(action_bar)
        
        main_layout.addWidget(right_container)
        
        # Apply enhanced dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #3a3a3a;
                border-radius: 10px;
            }
            QLabel {
                color: #e8e8e8;
                font-size: 12px;
            }
            QComboBox, QSpinBox {
                background-color: #4f4f4f;
                border: 1px solid #2f2f2f;
                border-radius: 6px;
                color: #e8e8e8;
                padding: 6px 10px;
                min-width: 140px;
                min-height: 24px;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #5a9fd4;
                background-color: #555555;
            }
            QComboBox:focus, QSpinBox:focus {
                border-color: #5a9fd4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #b8b8b8;
                margin-right: 8px;
            }
            QCheckBox {
                color: #e8e8e8;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background-color: #4f4f4f;
                border: 1px solid #2f2f2f;
                border-radius: 4px;
            }
            QCheckBox::indicator:hover {
                border-color: #5a9fd4;
            }
            QCheckBox::indicator:checked {
                background-color: #5a9fd4;
                border-color: #5a9fd4;
                image: none;
            }
            QCheckBox::indicator:checked:after {
                content: "✓";
                color: white;
            }
        """)


    def _create_content_page(self):
        """Create a base content page with proper styling."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return page, layout

    def _create_section(self, title):
        """Create a section header with enhanced styling."""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(16, 12, 16, 16)
        section_layout.setSpacing(16)
        
        # Section title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: #ffffff;
            background: transparent;
        """)
        section_layout.addWidget(title_label)
        
        return section, section_layout

    def _create_video_page(self):
        page, layout = self._create_content_page()
        
        # Resolution section
        section, sec_layout = self._create_section("Formato de Proyecto")
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Anchura:"), 0, 0)
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 8192)
        self.w_spin.setValue(1920)
        self.w_spin.setSuffix(" px")
        grid.addWidget(self.w_spin, 0, 1)
        
        grid.addWidget(QLabel("Altura:"), 1, 0)
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 8192)
        self.h_spin.setValue(1080)
        self.h_spin.setSuffix(" px")
        grid.addWidget(self.h_spin, 1, 1)
        
        grid.addWidget(QLabel("FPS:"), 2, 0)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["23.976", "24.0", "25.0", "29.97", "30.0", "50.0", "60.0"])
        self.fps_combo.setCurrentIndex(4)
        grid.addWidget(self.fps_combo, 2, 1)
        
        # ---------------------------------------------------------------------
        # RECOGNITION SYSTEM (User Request)
        # ---------------------------------------------------------------------
        self.btn_detect = QPushButton("Auto-Detectar desde archivo...")
        self.btn_detect.setStyleSheet("""
            QPushButton {
                background-color: #00a3ff;
                color: white;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton:hover { background-color: #33b5ff; }
        """)
        self.btn_detect.clicked.connect(self._on_auto_detect_clicked)
        
        sec_layout.addLayout(grid)
        sec_layout.addWidget(self.btn_detect)
        layout.addWidget(section)
        layout.addStretch()
        
        return page

    def _on_auto_detect_clicked(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from ..infrastructure.ffmpeg_utils import FFmpegUtils
        import rocky_core
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar medio para reconocer formato", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if file_path:
            # STAGE 1: Fast Probe (Returns NATIVE params)
            specs = FFmpegUtils.get_media_specs(file_path)
            w, h, rot = specs['width'], specs['height'], specs['rotation']
            
            # STAGE 2: Engine Fallback (Returns VISUAL params directly)
            if w <= 0 or h <= 0:
                try:
                    temp_src = rocky_core.VideoSource(file_path)
                    if temp_src.isValid():
                        w = temp_src.get_width()
                        h = temp_src.get_height()
                        rot = temp_src.get_rotation()
                except: pass
            
            # Application of effective visual resolution (Safety if Stage 2 succeeded but was somehow 0)
            if w <= 0 or h <= 0:
                w, h = 1920, 1080 

            # THE FIX: Apply rotation to dimensions for visual check
            vis_w = w
            vis_h = h
            if abs(rot) == 90 or abs(rot) == 270:
                vis_w, vis_h = h, w
            
            self.w_spin.setValue(vis_w)
            self.h_spin.setValue(vis_h)
            
            # FPS matching
            fps_val = specs.get('fps', 30.0)
            fps_str = f"{fps_val:.3f}" if fps_val % 1 != 0 else f"{int(fps_val)}.0"
            idx = self.fps_combo.findText(fps_str, Qt.MatchFlag.MatchStartsWith)
            if idx >= 0: self.fps_combo.setCurrentIndex(idx)
            
            # Calculate aspect ratio
            from math import gcd
            divisor = gcd(vis_w, vis_h)
            aspect_w = vis_w // divisor
            aspect_h = vis_h // divisor
            
            is_vertical = vis_h > vis_w
            format_type = "Vertical" if is_vertical else "Panorámico"
            
            QMessageBox.information(
                self, 
                "Formato Detectado", 
                f"Se ha detectado una resolución de {vis_w}x{vis_h}.\n\n"
                f"• Aspecto: {aspect_w}:{aspect_h}\n"
                f"• Formato: {format_type}\n"
                f"• FPS: {fps_val}\n\n"
                f"Presiona OK para aplicar a los controles."
            )

    def _create_audio_page(self):
        page, layout = self._create_content_page()
        
        section, sec_layout = self._create_section("Configuración de Audio")
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Sample Rate:"), 0, 0)
        sr_combo = QComboBox()
        sr_combo.addItems(["44.100 Hz", "48.000 Hz", "96.000 Hz"])
        sr_combo.setCurrentIndex(1)
        grid.addWidget(sr_combo, 0, 1)
        
        grid.addWidget(QLabel("Profundidad de bits:"), 1, 0)
        bits_combo = QComboBox()
        bits_combo.addItems(["16-bit", "24-bit", "32-bit Float"])
        grid.addWidget(bits_combo, 1, 1)
        
        sec_layout.addLayout(grid)
        layout.addWidget(section)
        layout.addStretch()
        
        return page

    def _create_proxy_page(self):
        page, layout = self._create_content_page()
        
        section, sec_layout = self._create_section("Flujo de Trabajo Proxy")
        
        cb_auto = QCheckBox("Generar proxies automáticamente")
        cb_auto.setChecked(True)
        sec_layout.addWidget(cb_auto)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Resolución:"), 0, 0)
        res_combo = QComboBox()
        res_combo.addItems(["360p", "540p", "720p"])
        res_combo.setCurrentIndex(1)
        grid.addWidget(res_combo, 0, 1)
        
        grid.addWidget(QLabel("Codec:"), 1, 0)
        codec_combo = QComboBox()
        codec_combo.addItems(["H.264", "ProRes 422 Proxy"])
        grid.addWidget(codec_combo, 1, 1)
        
        sec_layout.addLayout(grid)
        layout.addWidget(section)
        layout.addStretch()
        
        return page

    def _create_preview_page(self):
        page, layout = self._create_content_page()
        
        section, sec_layout = self._create_section("Optimización del Visor")
        
        cb_hw = QCheckBox("Aceleración por hardware (Metal / DX12)")
        cb_hw.setChecked(True)
        sec_layout.addWidget(cb_hw)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Resolución de Preview:"), 0, 0)
        sc_combo = QComboBox()
        sc_combo.addItems(["Completa", "1/2", "1/4", "1/8"])
        grid.addWidget(sc_combo, 0, 1)
        
        sec_layout.addLayout(grid)
        layout.addWidget(section)
        layout.addStretch()
        
        return page




    def get_settings(self):
        """Returns a dictionary with all current settings."""
        fps_str = self.fps_combo.currentText()
        try:
            fps = float(fps_str)
        except:
            fps = 30.0

        return {
            "width": self.w_spin.value(),
            "height": self.h_spin.value(),
            "fps": fps,
            # Audio
            # "sample_rate": ... (Not yet bound to member vars in _create_audio_page, but video is critical right now)
            # Viewer
            # "hw_accel": ...
        }

# Alias for compatibility
SettingsDialog = PreferencesDialog
