from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class EffectsDialog(QDialog):
    """
    A placeholder dialog for managing clip effects (FX).
    Currently empty as requested.
    """
    def __init__(self, clip, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.setWindowTitle(f"Video Event FX: {clip.name}")
        self.resize(600, 400)
        self.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Placeholder content
        label = QLabel("No effects added.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #808080; font-style: italic; font-size: 14px;")
        
        layout.addWidget(label)
