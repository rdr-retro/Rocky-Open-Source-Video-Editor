from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, 
                             QPushButton, QComboBox, QCheckBox, QSpinBox, QGridLayout, QSpacerItem, QSizePolicy, QWidget)
from PyQt5.QtCore import Qt

class SettingsDialog(QDialog):
    """
    Highly refined Project Settings dialog.
    Following professional NLE standards with tabs at the top,
    grouped controls, and high-contrast premium aesthetics.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Proyecto")
        self.resize(750, 550)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0c0c;
                color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #222;
                background: #111111;
                border-radius: 4px;
                top: -1px;
            }
            QTabWidget {
                background: #0c0c0c;
            }
            QTabBar::tab {
                background: #1a1a1a;
                color: #777;
                padding: 12px 30px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #222;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #111111;
                color: #00a3ff;
                border-bottom: 2px solid #00a3ff;
            }
            QTabBar::tab:hover:!selected {
                color: #bbb;
                background: #222;
            }
            
            QFrame.SectionFrame {
                background-color: #161616;
                border: 1px solid #252525;
                border-radius: 6px;
                padding: 15px;
            }
            
            QLabel.SectionTitle {
                color: #555;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-bottom: 10px;
            }
            
            QLabel.ControlLabel {
                color: #ccc;
                font-size: 11px;
            }
            
            QComboBox, QSpinBox {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
                color: #fff;
                padding: 6px 12px;
                min-width: 180px;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #444;
            }
            QComboBox::drop-down {
                border: none;
            }
            
            QCheckBox {
                color: #aaa;
                font-size: 11px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #00a3ff;
                border-color: #00a3ff;
            }
            
            QPushButton#SaveBtn {
                background-color: #00a3ff;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#SaveBtn:hover {
                background-color: #00c3ff;
            }
            
            QPushButton#CancelBtn {
                background-color: transparent;
                color: #777;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 10px 25px;
            }
            QPushButton#CancelBtn:hover {
                color: white;
                background-color: #222;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 0)
        layout.setSpacing(20)

        # Header
        top_label = QLabel("Ajustes del Proyecto")
        top_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(top_label)

        # Tabs System (Positioned at TOP)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
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
        action_layout.setContentsMargins(0, 20, 0, 25)
        action_layout.setSpacing(12)
        
        action_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Guardar Cambios")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self.accept)
        
        action_layout.addWidget(cancel_btn)
        action_layout.addWidget(save_btn)
        
        layout.addWidget(action_bar)

    def _create_section(self, title):
        frame = QFrame()
        frame.setProperty("class", "SectionFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(15)
        
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "SectionTitle")
        layout.addWidget(title_lbl)
        return frame, layout

    def _create_video_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Section 1: Resolution & FPS
        sec_render, sub_layout = self._create_section("PROPIEDADES DE RENDERIZADO")
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        grid.addWidget(QLabel("Frecuencia de imagen:"), 0, 0)
        fps_combo = QComboBox()
        fps_combo.addItems(["23.976 Hz (Film)", "24.0 Hz", "25.0 Hz (PAL)", "29.97 Hz (NTSC)", "30.0 Hz", "50.0 Hz", "60.0 Hz (Pro)"])
        fps_combo.setCurrentIndex(6)
        grid.addWidget(fps_combo, 0, 1)

        # Resolution - New Fields
        grid.addWidget(QLabel("Anchura de fotograma:"), 1, 0)
        w_spin = QSpinBox()
        w_spin.setRange(100, 8192)
        w_spin.setValue(1920)
        w_spin.setSuffix(" px")
        grid.addWidget(w_spin, 1, 1)

        grid.addWidget(QLabel("Altura de fotograma:"), 2, 0)
        h_spin = QSpinBox()
        h_spin.setRange(100, 8192)
        h_spin.setValue(1080)
        h_spin.setSuffix(" px")
        grid.addWidget(h_spin, 2, 1)
        
        grid.addWidget(QLabel("Motor de escalado:"), 3, 0)
        inter_combo = QComboBox()
        inter_combo.addItems(["Bilineal (Rápido)", "Bicúbico (Suave)", "Lanczos (Máxima Calidad)"])
        grid.addWidget(inter_combo, 3, 1)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_render)

        layout.addStretch()
        return page

    def _create_audio_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        sec_audio, sub_layout = self._create_section("CONFIGURACIÓN DE SALIDA")
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        grid.addWidget(QLabel("Sample Rate:"), 0, 0)
        sr_combo = QComboBox()
        sr_combo.addItems(["44.100 Hz", "48.000 Hz", "96.000 Hz"])
        sr_combo.setCurrentIndex(1)
        grid.addWidget(sr_combo, 0, 1)
        
        grid.addWidget(QLabel("Profundidad de bits:"), 1, 0)
        bits_combo = QComboBox()
        bits_combo.addItems(["16-bit Integer", "24-bit Integer", "32-bit Float (Mastering)"])
        grid.addWidget(bits_combo, 1, 1)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_audio)

        layout.addStretch()
        return page

    def _create_proxy_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        sec_proxy, sub_layout = self._create_section("FLUJO DE TRABAJO PROXY")
        
        cb_auto = QCheckBox("Generar proxies automáticamente al importar nuevos clips")
        cb_auto.setChecked(True)
        sub_layout.addWidget(cb_auto)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.addWidget(QLabel("Resolución de Proxy:"), 0, 0)
        res_combo = QComboBox()
        res_combo.addItems(["360p", "540p", "720p"])
        res_combo.setCurrentIndex(1)
        grid.addWidget(res_combo, 0, 1)
        
        grid.addWidget(QLabel("Codec de Proxy:"), 1, 0)
        codec_combo = QComboBox()
        codec_combo.addItems(["H.264 (Compacto)", "ProRes 422 Proxy (Rápido)"])
        grid.addWidget(codec_combo, 1, 1)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_proxy)

        layout.addStretch()
        return page

    def _create_preview_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        sec_vis, sub_layout = self._create_section("OPTIMIZACIÓN DEL VISOR")
        
        cb_hw = QCheckBox("Habilitar aceleración por hardware (Metal / DX12)")
        cb_hw.setChecked(True)
        sub_layout.addWidget(cb_hw)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.addWidget(QLabel("Resolución de Preview:"), 0, 0)
        sc_combo = QComboBox()
        sc_combo.addItems(["Completa", "1/2", "1/4", "1/8"])
        grid.addWidget(sc_combo, 0, 1)
        
        sub_layout.addLayout(grid)
        layout.addWidget(sec_vis)

        layout.addStretch()
        return page
