from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from .styles import PUSH_BUTTON_STYLE, TOOLBAR_STYLE

class RockyToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self.setFixedHeight(35)
        self.setStyleSheet(TOOLBAR_STYLE)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(5)
        
        self.btn_open = QPushButton("Abrir")
        self.btn_save = QPushButton("Guardar")
        self.btn_save_as = QPushButton("Guardar como...")
        self.btn_render = QPushButton("Renderizar")
        self.btn_settings = QPushButton("Ajustes")
        self.btn_proxy = QPushButton("PX")
        self.btn_proxy.setCheckable(True)
        self.btn_proxy.setChecked(True)
        self.btn_proxy.setToolTip("Modo Proxy: Usa copias de baja calidad para edición fluida")
        
        for btn in [self.btn_open, self.btn_save, self.btn_save_as, self.btn_render, self.btn_settings, self.btn_proxy]:
            btn.setStyleSheet(PUSH_BUTTON_STYLE)
            layout.addWidget(btn)
            
        layout.addStretch()
        
    def set_proxy_status_color(self, status_color):
        """
        Updates the PX button styling to reflect global proxy state.
        status_color: 'orange' (generating), 'green' (ready), 'red' (error), 'black' (off)
        """
        base_style = PUSH_BUTTON_STYLE
        
        color_map = {
            'orange': "background-color: #ff9900; color: #000; border: 1px solid #cc7a00;",
            'green': "background-color: #00cc66; color: #000; border: 1px solid #00994d;",
            'red': "background-color: #ff3333; color: #fff; border: 1px solid #cc0000;",
            'black': base_style # Default dark style
        }
        
        # If toggled ON, we use the status color. If OFF, we use standard style (maybe dimmed)
        if self.btn_proxy.isChecked():
            style = color_map.get(status_color, base_style)
            # Merge with base properties if needed, but PUSH_BUTTON_STYLE is a string block.
            # We'll just override the background/border for now.
            # Simpler: Just append the color override to the base style
            if status_color != 'black':
                self.btn_proxy.setStyleSheet(f"{base_style} {style}")
            else:
                self.btn_proxy.setStyleSheet(base_style)
        else:
             self.btn_proxy.setStyleSheet(base_style)
