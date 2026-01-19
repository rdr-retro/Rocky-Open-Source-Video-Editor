from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, 
                             QPushButton, QComboBox, QCheckBox, QSpinBox, QGridLayout, QSpacerItem, QSizePolicy, QWidget)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QFont

class SettingsDialog(QDialog):
    """
    Highly refined Project Settings dialog.
    Following professional NLE standards with tabs at the top,
    grouped controls, and high-contrast premium aesthetics.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Proyecto")
        self.resize(1000, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
                margin-top: 10px;
            }
            QTabBar::tab {
                background: transparent;
                color: #555;
                padding: 10px 20px;
                margin-right: 15px;
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                font-weight: 500;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: #00a3ff;
                border-bottom: 2px solid #00a3ff;
            }
            QTabBar::tab:hover:!selected {
                color: #888;
            }
            
            QFrame.SectionFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin-bottom: 30px;
            }
            
            QLabel.SectionTitle {
                color: #333;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 20px;
            }
            
            QLabel.ControlLabel {
                color: #999;
                font-size: 11px;
            }
            
            QComboBox, QSpinBox {
                background-color: #111;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
                color: #eee;
                padding: 4px 8px;
                min-width: 140px;
                font-size: 10px;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #222;
                background-color: #141414;
            }
            QComboBox::drop-down {
                border: none;
            }
            
            QCheckBox {
                color: #777;
                font-size: 11px;
                spacing: 12px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #0a0a0a;
                border: 1px solid #222;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #00a3ff;
                border-color: #00a3ff;
            }
            
            QPushButton#SaveBtn {
                background-color: #ffffff;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 8px 25px;
                font-weight: 700;
                font-size: 10px;
            }
            QPushButton#SaveBtn:hover {
                background-color: #dddddd;
            }
            
            QPushButton#CancelBtn {
                background-color: transparent;
                color: #444;
                border: none;
                padding: 8px 15px;
                font-size: 10px;
            }
            QPushButton#CancelBtn:hover {
                color: #888;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 0)
        layout.setSpacing(15)

        # Header
        top_label = QLabel("Ajustes del Proyecto")
        top_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(top_label)

        # Tabs System (Positioned at TOP)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(False)

        # 1. Video Settings
        self.tabs.addTab(self._create_video_tab(), "Vídeo")
        
        # 2. Audio Settings
        self.tabs.addTab(self._create_audio_tab(), "Audio")
        
        # 3. Proxy Settings
        self.tabs.addTab(self._create_proxy_tab(), "Proxies")
        
        # 4. Preview Settings
        self.tabs.addTab(self._create_preview_tab(), "Visor")

        layout.addWidget(self.tabs)

        # Bottom Action Bar
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 15, 0, 20)
        action_layout.setSpacing(12)
        
        action_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Guardar Cambios")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self.accept)
        
        action_layout.addWidget(cancel_btn)
        action_layout.addWidget(save_btn)
        action_layout.addStretch() # Center buttons too
        
        layout.addWidget(action_bar)

    def _create_section(self, title):
        frame = QFrame()
        frame.setProperty("class", "SectionFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "SectionTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        return frame, layout

    def _create_video_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 1. Title
        title_lbl = QLabel("FORMATO DE PROYECTO")
        title_lbl.setStyleSheet("color: #00a3ff; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(title_lbl)

        # 2. Format Cards Container
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.format_group = []
        
        formats = [
            ("Panorámico", "16:9", 1920, 1080, 1.77),
            ("Cinemático", "21:9", 2560, 1080, 2.33),
            ("Clásico", "4:3", 1440, 1080, 1.33),
            ("Vertical", "9:16", 1080, 1920, 0.56),
            ("Cuadrado", "1:1", 1080, 1080, 1.0),
            ("Personalizado", "...", 1920, 1080, 0.0)
        ]

        for name, ratio_text, w, h, ratio_val in formats:
            btn = FormatCard(name, ratio_text, ratio_val, parent=page)
            btn.clicked.connect(lambda w=w, h=h, n=name: self.apply_preset(w, h, n))
            cards_layout.addWidget(btn)
            self.format_group.append(btn)
            
        cards_layout.addStretch()

        layout.addLayout(cards_layout)
        
        # 3. Manual Resolution Controls (Subtle)
        res_frame = QFrame()
        res_frame.setStyleSheet("background: transparent;")
        res_layout = QHBoxLayout(res_frame)
        res_layout.setContentsMargins(0, 20, 0, 0)
        res_layout.setSpacing(20)
        
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 8192)
        self.w_spin.setSuffix(" px")
        self.w_spin.valueChanged.connect(lambda: self.check_custom())
        
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 8192)
        self.h_spin.setSuffix(" px")
        self.h_spin.valueChanged.connect(lambda: self.check_custom())

        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["23.976 Hz", "24.0 Hz", "25.0 Hz", "29.97 Hz", "30.0 Hz", "50.0 Hz", "60.0 Hz"])
        self.fps_combo.setCurrentIndex(4) # 30fps default

        # Add labels and widgets
        lbl_style = "color: #666; font-size: 11px; font-weight: bold;"
        
        l_w = QLabel("ANCHURA"); l_w.setStyleSheet(lbl_style)
        l_h = QLabel("ALTURA"); l_h.setStyleSheet(lbl_style)
        l_f = QLabel("FPS"); l_f.setStyleSheet(lbl_style)
        
        res_layout.addWidget(l_w); res_layout.addWidget(self.w_spin)
        res_layout.addWidget(l_h); res_layout.addWidget(self.h_spin)
        res_layout.addWidget(l_f); res_layout.addWidget(self.fps_combo)
        res_layout.addStretch()
        
        layout.addWidget(res_frame)
        layout.addStretch()

        # Set default
        self.apply_preset(1920, 1080, "Panorámico")
        
        return page

    def apply_preset(self, w, h, name):
        # Block signals to prevent 'check_custom' loop if needed, but here it's fine
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)
        
        for btn in self.format_group:
            btn.set_selected(btn.name == name)
            
    def check_custom(self):
        # Logic to highlight 'Personalizado' if W/H don't match any preset
        # For simplicity, if user touches spinbox, we select "Personalizado" visually
        # unless it matches exactly. 
        # For now, just ensuring 'Personalizado' connects visually could be done here.
        pass

class FormatCard(QPushButton):
    def __init__(self, name, ratio_text, aspect_ratio, parent=None):
        super().__init__(parent)
        self.name = name
        self.ratio_text = ratio_text
        self.aspect_ratio = aspect_ratio
        self.is_selected = False
        
        self.setCheckable(True)
        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_selected(self, selected):
        self.is_selected = selected
        self.setChecked(selected)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background & Border
        rect = self.rect().adjusted(1, 1, -1, -1)
        bg = QColor("#0a0a0a") # Transparent/Dark
        border = QColor("#333333")
        
        if self.isUnderMouse():
            border = QColor("#666666")
            
        if self.is_selected:
            border = QColor("#00a3ff")
            bg = QColor(0, 163, 255, 20) # Subtle blue tint
            
        painter.setBrush(bg)
        painter.setPen(QPen(border, 2 if self.is_selected else 1))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Draw Icon (Shape)
        icon_cx = rect.center().x()
        icon_cy = rect.top() + 60
        
        painter.setPen(QPen(QColor("#00a3ff"), 2))
        painter.setBrush(Qt.NoBrush)
        
        w, h = 40, 40
        if self.aspect_ratio > 1.5: # Wide
            w, h = 50, 28
        elif self.aspect_ratio > 1.1: # Classic
            w, h = 44, 33
        elif self.aspect_ratio == 1.0: # Square
            w, h = 36, 36
        elif self.aspect_ratio > 0: # Vertical
            w, h = 24, 42
        else: # Custom
            pass 
            
        if self.aspect_ratio > 0:
            r = QRect(int(icon_cx - w/2), int(icon_cy - h/2), w, h)
            painter.drawRect(r)
        else:
             # Draw dotted box for Custom
            painter.setPen(QPen(QColor("#00a3ff"), 2, Qt.PenStyle.DashLine))
            r = QRect(int(icon_cx - 20), int(icon_cy - 20), 40, 40)
            painter.drawRect(r)

        # Text
        painter.setPen(QColor("#ffffff") if self.is_selected else QColor("#cccccc"))
        painter.setFont(QFont("Inter", 11, QFont.Bold))
        painter.drawText(QRect(0, 100, self.width(), 20), Qt.AlignCenter, self.name)
        
        painter.setPen(QColor("#666666"))
        painter.setFont(QFont("Inter", 10))
        painter.drawText(QRect(0, 122, self.width(), 20), Qt.AlignCenter, self.ratio_text)

    def _create_audio_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sec_audio, sub_layout = self._create_section("CONFIGURACIÓN DE SALIDA")
        
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        grid.addWidget(QLabel("Sample Rate:"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        sr_combo = QComboBox()
        sr_combo.addItems(["44.100 Hz", "48.000 Hz", "96.000 Hz"])
        sr_combo.setCurrentIndex(1)
        grid.addWidget(sr_combo, 0, 1, Qt.AlignmentFlag.AlignCenter)
        
        grid.addWidget(QLabel("Profundidad de bits:"), 1, 0, Qt.AlignmentFlag.AlignCenter)
        bits_combo = QComboBox()
        bits_combo.addItems(["16-bit Integer", "24-bit Integer", "32-bit Float (Mastering)"])
        grid.addWidget(bits_combo, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_audio)
        # Removed stretch
        return page

    def _create_proxy_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sec_proxy, sub_layout = self._create_section("FLUJO DE TRABAJO PROXY")
        
        cb_auto = QCheckBox("Generar proxies automáticamente al importar nuevos clips")
        cb_auto.setChecked(True)
        sub_layout.addWidget(cb_auto, 0, Qt.AlignmentFlag.AlignCenter)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        grid.addWidget(QLabel("Resolución de Proxy:"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        res_combo = QComboBox()
        res_combo.addItems(["360p", "540p", "720p"])
        res_combo.setCurrentIndex(1)
        grid.addWidget(res_combo, 0, 1, Qt.AlignmentFlag.AlignCenter)
        
        grid.addWidget(QLabel("Codec de Proxy:"), 1, 0, Qt.AlignmentFlag.AlignCenter)
        codec_combo = QComboBox()
        codec_combo.addItems(["H.264 (Compacto)", "ProRes 422 Proxy (Rápido)"])
        grid.addWidget(codec_combo, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_proxy)
        # Removed stretch
        return page

    def _create_preview_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sec_vis, sub_layout = self._create_section("OPTIMIZACIÓN DEL VISOR")
        
        cb_hw = QCheckBox("Habilitar aceleración por hardware (Metal / DX12)")
        cb_hw.setChecked(True)
        sub_layout.addWidget(cb_hw, 0, Qt.AlignmentFlag.AlignCenter)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        grid.addWidget(QLabel("Resolución de Preview:"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        sc_combo = QComboBox()
        sc_combo.addItems(["Completa", "1/2", "1/4", "1/8"])
        grid.addWidget(sc_combo, 0, 1, Qt.AlignmentFlag.AlignCenter)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_vis)
        # Removed stretch
        return page

