from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QStackedWidget, QFrame, 
                               QScrollArea, QPushButton, QHBoxLayout, QGridLayout, 
                               QLineEdit, QSlider, QSpinBox, QComboBox, QCheckBox, QDialog)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from . import design_tokens as dt

# --- Helper Classes (Duplicated/Shared) ---

class FlowLayout(QGridLayout):
    """
    Simplified grid layout for aspect ratio cards.
    Using QGridLayout for stability instead of complex flow logic for now.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

class CustomResolutionDialog(QDialog):
    """
    Advanced dialog for custom project resolution settings.
    (Duplicated from asset_tabs.py to ensure independence)
    """
    def __init__(self, parent=None, current_w=1920, current_h=1080):
        super().__init__(parent)
        self.setWindowTitle("Resolución Personalizada")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog { background-color: #111111; color: #ffffff; }
            QLabel { color: #999; font-size: 11px; font-family: 'Inter', sans-serif; }
            QLabel#Header { color: #fff; font-size: 16px; font-weight: bold; margin-bottom: 20px; }
            QSpinBox, QComboBox { background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px; color: #fff; padding: 8px; font-size: 12px; }
            QSpinBox:focus, QComboBox:focus { border-color: #00a3ff; }
            QPushButton#ActionBtn { background-color: #00a3ff; color: #000; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
            QPushButton#ActionBtn:hover { background-color: #33b5ff; }
            QPushButton#CancelBtn { background-color: transparent; color: #666; border: none; padding: 10px; }
            QPushButton#CancelBtn:hover { color: #999; }
            QCheckBox { color: #888; font-size: 11px; spacing: 8px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        header = QLabel("Ajustes de Fotograma")
        header.setObjectName("Header")
        layout.addWidget(header)

        # Presets
        layout.addWidget(QLabel("PREAJUSTES COMUNES"))
        self.preset_combo = QComboBox()
        self.presets = {
            "Personalizado": (current_w, current_h),
            "YouTube 4K (3840x2160)": (3840, 2160),
            "YouTube Full HD (1920x1080)": (1920, 1080),
            "Instagram/TikTok (1080x1920)": (1080, 1920),
            "Instagram Square (1080x1080)": (1080, 1080),
            "DCI 4K (4096x2160)": (4096, 2160),
            "Twitter HD (1280x720)": (1280, 720)
        }
        self.preset_combo.addItems(self.presets.keys())
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addWidget(self.preset_combo)

        # Width & Height
        dims_layout = QHBoxLayout()
        v_w = QVBoxLayout()
        v_w.addWidget(QLabel("ANCHO (PX)"))
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 8192)
        self.w_spin.setValue(current_w)
        self.w_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.w_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.w_spin.valueChanged.connect(self._on_dims_manually_changed)
        v_w.addWidget(self.w_spin)
        
        v_h = QVBoxLayout()
        v_h.addWidget(QLabel("ALTO (PX)"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 8192)
        self.h_spin.setValue(current_h)
        self.h_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.h_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_spin.valueChanged.connect(self._on_dims_manually_changed)
        v_h.addWidget(self.h_spin)

        dims_layout.addLayout(v_w)
        dims_layout.addLayout(v_h)
        layout.addLayout(dims_layout)

        # Aspect Ratio Lock
        self.cb_lock = QCheckBox("Bloquear relación de aspecto")
        self.cb_lock.setChecked(True)
        self.current_ratio = current_w / current_h if current_h else 1.77
        layout.addWidget(self.cb_lock)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Aplicar Resolución")
        ok_btn.setObjectName("ActionBtn")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_preset_changed(self, index):
        preset_name = self.preset_combo.currentText()
        if preset_name != "Personalizado":
            w, h = self.presets[preset_name]
            self.w_spin.blockSignals(True)
            self.h_spin.blockSignals(True)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            self.w_spin.blockSignals(False)
            self.h_spin.blockSignals(False)
            self.current_ratio = w / h

    def _on_dims_manually_changed(self):
        self.preset_combo.setCurrentText("Personalizado")
        if self.cb_lock.isChecked():
            sender = self.sender()
            if sender == self.w_spin:
                self.h_spin.blockSignals(True)
                self.h_spin.setValue(int(self.w_spin.value() / self.current_ratio))
                self.h_spin.blockSignals(False)
            else:
                self.w_spin.blockSignals(True)
                self.w_spin.setValue(int(self.h_spin.value() * self.current_ratio))
                self.w_spin.blockSignals(False)
        else:
            self.current_ratio = self.w_spin.value() / self.h_spin.value()

    def get_resolution(self):
        return self.w_spin.value(), self.h_spin.value()


class EditorPanel(QWidget):
    """
    Contextual Properties Panel (Blender Style).
    Switches between 'Project Settings' and 'Clip Properties' based on selection.
    """
    resolution_changed = Signal(int, int) # Re-export signal

    def __init__(self):
        super().__init__()
        self.current_selection = []
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QLabel {{ font-family: 'Inter'; }}
            QLineEdit {{
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: {dt.RADIUS_ELEMENT}px;
                padding: 6px;
                color: #fff;
            }}
            QLineEdit:focus {{ border-color: #00a3ff; }}
            
            QSlider::groove:horizontal {{
                border: 1px solid #333;
                height: 4px;
                background: #1a1a1a;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #00a3ff;
                width: 12px;
                margin: -4px 0; 
                border-radius: 6px;
            }}
            
             /* Aspect Ratio Card Styling (Copied from AssetTabs) */
            QPushButton.AspectCard {{
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: {dt.RADIUS_ELEMENT}px; /* 0px */
                min-width: 80px;
                max-width: 120px;
                min-height: 80px;
                padding: 10px;
            }}
            QPushButton.AspectCard:hover {{
                background-color: #222;
                border-color: #00a3ff;
            }}
            QPushButton.AspectCard:pressed {{
                background-color: #00a3ff;
            }}
            
            QLabel.AspectTitle {{
                color: #e0e0e0;
                font-size: 10px;
                font-weight: 600;
                margin-top: 8px;
            }}
            QFrame.RatioBox {{
                background-color: #333;
                border: 1px solid #555;
            }}
            QPushButton.AspectCard:hover QFrame.RatioBox {{
                border-color: #00a3ff;
            }}
            
            QLabel.SectionHeader {{
                color: #00a3ff;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.2px;
                margin-bottom: 10px;
                text-transform: uppercase;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Page 0: Project Settings (Default)
        self.page_project = self._create_project_view()
        self.stack.addWidget(self.page_project)
        
        # Page 1: Clip Properties
        self.page_clip = self._create_clip_view()
        self.stack.addWidget(self.page_clip)

    def _create_project_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QLabel("FORMATO DE PROYECTO")
        header.setProperty("class", "SectionHeader")
        layout.addWidget(header)
        
        # Grid of aspect ratios
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Using a simpler grid than flow layout for the robust vertical panel
        # Row 0
        grid.addWidget(self._create_aspect_card("Panorámico", "16:9", 40, 22, 1920, 1080), 0, 0)
        grid.addWidget(self._create_aspect_card("Cinemático", "21:9", 44, 18, 2560, 1080), 0, 1)
        
        # Row 1
        grid.addWidget(self._create_aspect_card("Clásico", "4:3", 32, 24, 1440, 1080), 1, 0)
        grid.addWidget(self._create_aspect_card("Vertical", "9:16", 20, 36, 1080, 1920), 1, 1)
        
        # Row 2
        grid.addWidget(self._create_aspect_card("Cuadrado", "1:1", 30, 30, 1080, 1080), 2, 0)
        grid.addWidget(self._create_aspect_card("Manual", "...", 30, 30, 0, 0, True), 2, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        return container

    def _create_aspect_card(self, title, ratio_text, w_icon, h_icon, res_w, res_h, is_custom=False):
        card = QPushButton()
        card.setProperty("class", "AspectCard")
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)
        layout.setContentsMargins(5,5,5,5)

        visual_box = QFrame()
        visual_box.setFixedSize(w_icon, h_icon)
        visual_box.setProperty("class", "RatioBox")
        visual_box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(visual_box, 0, Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setProperty("class", "AspectTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title_label)
        
        if is_custom:
            card.clicked.connect(self._on_custom_resolution)
        else:
            card.clicked.connect(lambda: self.resolution_changed.emit(res_w, res_h))

        return card

    def _on_custom_resolution(self):
        dlg = CustomResolutionDialog(self)
        if dlg.exec():
            w, h = dlg.get_resolution()
            self.resolution_changed.emit(w, h)

    def _create_clip_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        header = QLabel("PROPIEDADES DEL CLIP")
        header.setProperty("class", "SectionHeader")
        layout.addWidget(header)
        
        # Name Input
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Nombre del Clip")
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.inp_name)
        
        # Opacity
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        layout.addWidget(QLabel("Opacidad"))
        layout.addWidget(self.slider_opacity)
        
        # Info
        self.lbl_info = QLabel("Duración: --")
        self.lbl_info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.lbl_info)
        
        layout.addStretch()
        return container

    def update_context(self, selected_clips):
        """Slot called when timeline selection changes."""
        self.current_selection = selected_clips
        
        if not selected_clips:
            self.stack.setCurrentIndex(0) # Project Settings
        else:
            self.stack.setCurrentIndex(1) # Clip Properties
            self._bind_clip_data(selected_clips[0])

    def _bind_clip_data(self, clip):
        """Populates the form with clip data."""
        self.inp_name.setText(clip.name)
        self.slider_opacity.setValue(int(clip.opacity_level * 100))
        self.lbl_info.setText(f"Frame: {clip.start_frame} | Duración: {clip.duration_frames}")
        
        # Disconnect previous to avoid loops (simple pattern)
        try: self.inp_name.textChanged.disconnect()
        except: pass
        try: self.slider_opacity.valueChanged.disconnect()
        except: pass
        
        # Connect new
        self.inp_name.textChanged.connect(lambda text: setattr(clip, 'name', text))
        self.slider_opacity.valueChanged.connect(lambda val: self._update_opacity(clip, val))

    def _update_opacity(self, clip, val):
        clip.opacity_level = val / 100.0
        # Trigger repaint via parent if possible, or wait for timeline tick
