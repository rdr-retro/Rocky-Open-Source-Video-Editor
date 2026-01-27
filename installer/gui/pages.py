from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QLineEdit, QHBoxLayout, QFileDialog, QProgressBar, QCheckBox)
from PySide6.QtGui import QPixmap, Qt 
from PySide6.QtCore import Qt, Signal
import sys
import os

def get_img_path(name):
    """Helper to find images in src/ui/assets for both dev and bundled modes."""
    # 1. Try bundled path
    if getattr(sys, 'frozen', False):
        p = os.path.join(sys._MEIPASS, "src", "ui", "assets", name)
        if os.path.exists(p): return p
        # Fallback to root of bundle
        p = os.path.join(sys._MEIPASS, name)
        if os.path.exists(p): return p

    # 2. Try dev paths
    base = os.path.dirname(os.path.abspath(__file__))
    paths = [
        os.path.join(base, "..", "..", "src", "ui", "assets", name),
        os.path.join(base, "..", "..", "src", "img", name),
        os.path.join(base, "..", "..", name)
    ]
    for p in paths:
        if os.path.exists(p): return p
    return name

class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10) # No margins for full image
        layout.setSpacing(0)
        
        # Welcome Image (Full Header)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        img_path = get_img_path("welcome.png")
        if os.path.exists(img_path):
            pix = QPixmap(img_path)
            # Fills the entire top area (600x320 approx)
            scaled = pix.scaled(600, 320, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled)
            # No mask = Sharp square corners
        
        layout.addWidget(self.img_label)
        
        desc_container = QWidget()
        desc_lay = QVBoxLayout(desc_container)
        desc = QLabel("Este asistente preparará tu entorno para Rocky Editor.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 14px; color: #ffffff; padding: 10px;")
        desc.setWordWrap(True)
        desc_lay.addWidget(desc)
        layout.addWidget(desc_container)
        layout.addStretch()

class LicensePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Manifiesto de Transparencia y Seguridad:"))
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setText(
            "ROCKY VIDEO EDITOR - COMPROMISO DE CÓDIGO ABIERTO\n\n"
            "1. SEGURIDAD GARANTIZADA:\n"
            "Rocky Video Editor es una herramienta creada para la comunidad. Garantizamos que este "
            "software no contiene virus, troyanos, mineros de criptomonedas ni ningún tipo de "
            "código malintencionado que pueda comprometer la privacidad o el rendimiento de su equipo.\n\n"
            "2. FILOSOFÍA OPEN SOURCE:\n"
            "Creemos en la transparencia total. Por ello, Rocky Video Editor es de código abierto. "
            "Esto significa que cualquier persona tiene el derecho de estudiar como funciona el programa.\n\n"
            "3. VERIFICACIÓN PÚBLICA:\n"
            "Usted puede consultar, auditar y contribuir al código fuente íntegro de este editor "
            "en nuestro repositorio oficial de GitHub:\n"
            "https://github.com/rdr-retro/Rocky-Open-Source-Video-Editor\n\n"
            "Al continuar con la instalación, usted reconoce que este software se proporciona 'tal cual', "
            "bajo la licencia MIT, buscando ofrecer la mejor experiencia de edición de video gratuita."
        )
        layout.addWidget(self.text)

class PathPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("Selecciona la carpeta de instalación:"))
        h_lay = QHBoxLayout()
        self.path_edit = QLineEdit(os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "RockyEditor"))
        self.btn_browse = QPushButton("Explorar...")
        self.btn_browse.clicked.connect(self._browse)
        h_lay.addWidget(self.path_edit)
        h_lay.addWidget(self.btn_browse)
        layout.addLayout(h_lay)
        
        self.check_shortcut = QCheckBox("Crear acceso directo en el escritorio")
        self.check_shortcut.setChecked(True)
        layout.addWidget(self.check_shortcut)
        
        layout.addStretch()

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if d: self.path_edit.setText(d)

class ProgressPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)
        
        # 1. Welcome Image (Full Header)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        
        img_path = get_img_path("welcome.png")
        if os.path.exists(img_path):
            pix = QPixmap(img_path)
            scaled = pix.scaled(600, 320, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled)
        
        layout.addWidget(self.img_label)
        
        # 2. Status Text
        self.status = QLabel("Preparando instalación...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True) # Allow long errors to wrap
        self.status.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff40; margin: 10px;")
        layout.addWidget(self.status)
        
        layout.addStretch()
        
        # 3. Hidden Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.hide() 
        layout.addWidget(self.log)
        
        # 4. Animated Progress Bar (Standard Indeterminate)
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(12)
        # Setting range to 0,0 enables the native "marquee" / indeterminate animation
        self.pbar.setRange(0, 0) 
        self.pbar.setTextVisible(False)
        
        # Style for the indeterminate bar
        self.pbar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2d2d2d;
                border-radius: 6px;
                background: #1a1a1a;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #06b025;
                width: 20px; 
            }
        """)

        bar_container = QWidget()
        bar_lay = QVBoxLayout(bar_container)
        bar_lay.setContentsMargins(30, 0, 30, 0)
        bar_lay.addWidget(self.pbar)
        layout.addWidget(bar_container)

class SuccessPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("¡Instalación Completada!")
        title.setStyleSheet("font-size: 20px; color: green; font-weight: bold;")
        self.info = QLabel("Rocky Video Editor se ha instalado correctamente.")
        layout.addWidget(title)
        layout.addWidget(self.info)
        layout.addStretch()
import os
