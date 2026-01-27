from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QLineEdit, QHBoxLayout, QFileDialog, QProgressBar, QCheckBox)
from PySide6.QtGui import QPixmap, Qt 
from PySide6.QtCore import Qt, Signal
import sys
import os

class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Bienvenido al Instalador de Rocky Video Editor")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        desc = QLabel("Este asistente preparará tu entorno y descargará Rocky Editor.\n"
                      "Se requiere conexión a Internet.")
        desc.setWordWrap(True)
        layout.addWidget(title)
        
        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Try to find logo in multiple possible locations
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 1. Running from source (installer/gui/../../logo.png)
        logo_path = os.path.join(base_path, "..", "..", "logo.png")
        if not os.path.exists(logo_path):
             # 2. Frozen/Installed (root/logo.png because we added it to datas)
            if getattr(sys, 'frozen', False):
                logo_path = os.path.join(sys._MEIPASS, "logo.png")
            else:
                 logo_path = "logo.png"

        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_label.setPixmap(pix.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        layout.addWidget(logo_label)
        
        layout.addWidget(desc)
        layout.addStretch()

class LicensePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Términos y Condiciones:"))
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setText("MIT License\n\nCopyright (c) 2026 Raúl Díaz Gutiérrez\n\n"
                          "Permission is hereby granted, free of charge...")
        layout.addWidget(self.text)

class PathPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
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
        self.status = QLabel("Preparando...")
        self.pbar = QProgressBar()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background: #000; color: #0f0; font-family: monospace;")
        layout.addWidget(self.status)
        layout.addWidget(self.pbar)
        layout.addWidget(self.log)

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
