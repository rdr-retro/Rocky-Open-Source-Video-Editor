from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes del Proyecto")
        self.resize(600, 400)
        self.setStyleSheet("background-color: #333333; color: white;")
        
        layout = QVBoxLayout(self)
        label = QLabel("Configuración (En construcción)")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
