from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QMenu
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction
import os
from .styles import PUSH_BUTTON_STYLE, TOOLBAR_STYLE, UI_FONT, MENU_STYLE

class RockyToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self.setFixedHeight(28)
        self.setStyleSheet(TOOLBAR_STYLE)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 10, 0)
        layout.setSpacing(0)
        
        # Logo Button (Branding)
        self.btn_logo = QPushButton()
        icon_path = os.path.join(os.getcwd(), "src", "img", "icon.png")
        if os.path.exists(icon_path):
            self.btn_logo.setIcon(QIcon(icon_path))
            self.btn_logo.setIconSize(QSize(18, 18))
        
        self.btn_logo.setFixedSize(24, 24)
        self.btn_logo.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                border: none; 
                padding: 2px; 
            } 
            QPushButton:hover { 
                background: rgba(255,255,255,15); 
                border-radius: 4px; 
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)
        
        # Logo Menu
        self.menu_logo = QMenu(self)
        self.menu_logo.setStyleSheet(MENU_STYLE)
        self.action_welcome = self.menu_logo.addAction("Pantalla de bienvenida")
        self.action_about_logo = self.menu_logo.addAction("Acerca de Rocky video editor")
        self.btn_logo.setMenu(self.menu_logo)
        
        layout.addWidget(self.btn_logo)
        
        layout.addSpacing(4)

        # Style for Menu-like Buttons (matching the reference image)
        MENU_BTN_SS = f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 2px 8px;
                font-family: {UI_FONT};
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #444444;
                border-radius: 3px;
            }}
            QPushButton::menu-indicator {{
                image: none;
            }}
        """

        # ARCHIVO
        self.btn_archivo = QPushButton("Archivo")
        self.btn_archivo.setStyleSheet(MENU_BTN_SS)
        self.menu_archivo = QMenu(self)
        self.menu_archivo.setStyleSheet(MENU_STYLE)
        self.action_open = self.menu_archivo.addAction("Abrir")
        self.action_save = self.menu_archivo.addAction("Guardar")
        self.action_save_as = self.menu_archivo.addAction("Guardar como...")
        self.menu_archivo.addSeparator()
        self.action_settings = self.menu_archivo.addAction("Ajustes")
        self.btn_archivo.setMenu(self.menu_archivo)
        layout.addWidget(self.btn_archivo)

        # EDITAR
        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setStyleSheet(MENU_BTN_SS)
        self.menu_editar = QMenu(self)
        self.menu_editar.setStyleSheet(MENU_STYLE)
        self.menu_editar.addAction("Deshacer")
        self.menu_editar.addAction("Rehacer")
        self.btn_editar.setMenu(self.menu_editar)
        layout.addWidget(self.btn_editar)

        # PROCESAR
        self.btn_procesar = QPushButton("Procesar")
        self.btn_procesar.setStyleSheet(MENU_BTN_SS)
        self.menu_procesar = QMenu(self)
        self.menu_procesar.setStyleSheet(MENU_STYLE)
        self.action_render = self.menu_procesar.addAction("Renderizar")
        self.btn_procesar.setMenu(self.menu_procesar)
        layout.addWidget(self.btn_procesar)

        # VENTANA
        self.btn_ventana = QPushButton("Ventana")
        self.btn_ventana.setStyleSheet(MENU_BTN_SS)
        self.menu_ventana = QMenu(self)
        self.menu_ventana.setStyleSheet(MENU_STYLE)
        self.menu_ventana.addAction("Timeline")
        self.menu_ventana.addAction("Visor")
        self.btn_ventana.setMenu(self.menu_ventana)
        layout.addWidget(self.btn_ventana)

        # AYUDA
        self.btn_ayuda = QPushButton("Ayuda")
        self.btn_ayuda.setStyleSheet(MENU_BTN_SS)
        self.menu_ayuda = QMenu(self)
        self.menu_ayuda.setStyleSheet(MENU_STYLE)
        self.menu_ayuda.addAction("Manual")
        self.menu_ayuda.addAction("Acerca de...")
        self.btn_ayuda.setMenu(self.menu_ayuda)
        layout.addWidget(self.btn_ayuda)

        layout.addStretch()

        # PX (Proxy) Toggle remains visible as requested
        self.btn_proxy = QPushButton("PX")
        self.btn_proxy.setCheckable(True)
        self.btn_proxy.setChecked(True)
        self.btn_proxy.setToolTip("Modo Proxy: Usa copias de baja calidad para edición fluida")
        self.btn_proxy.setStyleSheet(PUSH_BUTTON_STYLE)
        layout.addWidget(self.btn_proxy)
        
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
        # If the button is NOT checked (OFF), it's always black/default style
        # showing that proxies are globally disabled.
        if not self.btn_proxy.isChecked():
            self.btn_proxy.setStyleSheet(base_style)
            return

        # If ON, use the mapped status color
        style = color_map.get(status_color, base_style)
        if status_color != 'black':
            self.btn_proxy.setStyleSheet(f"{base_style} {style}")
        else:
            self.btn_proxy.setStyleSheet(base_style)
