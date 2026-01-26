from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QLineEdit, QHBoxLayout, QFileDialog, QProgressBar, QCheckBox)
from PySide6.QtCore import Qt, Signal

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
