from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QMenu, QInputDialog
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction
import os
import random
from .styles import PUSH_BUTTON_STYLE, TOOLBAR_STYLE, UI_FONT, MENU_STYLE, ACCENT_PRIMARY, WORKSPACE_BTN_STYLE, TOOLBAR_MENU_BTN_STYLE
from . import design_tokens as dt

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
        # We now use the unified TOOLBAR_MENU_BTN_STYLE from styles.py
        MENU_BTN_SS = TOOLBAR_MENU_BTN_STYLE

        # ARCHIVO
        self.btn_archivo = QPushButton("Archivo")
        self.btn_archivo.setStyleSheet(MENU_BTN_SS)
        self.menu_archivo = QMenu(self)
        self.menu_archivo.setStyleSheet(MENU_STYLE)
        self.action_open = self.menu_archivo.addAction("Abrir")
        self.action_save = self.menu_archivo.addAction("Guardar")
        self.action_save_as = self.menu_archivo.addAction("Guardar como...")
        self.btn_archivo.setMenu(self.menu_archivo)
        layout.addWidget(self.btn_archivo)

        # EDITAR
        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setStyleSheet(MENU_BTN_SS)
        self.menu_editar = QMenu(self)
        self.menu_editar.setStyleSheet(MENU_STYLE)
        self.menu_editar.addAction("Deshacer")
        self.menu_editar.addAction("Rehacer")
        self.menu_editar.addSeparator()
        self.action_preferences = self.menu_editar.addAction("Preferencias...")
        self.action_preferences.setShortcut("Ctrl+,")
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
        
        # Separator
        self.separator = QLabel("|")
        self.separator.setStyleSheet(f"color: #ffffff; background: transparent; font-family: {UI_FONT}; font-size: 11px; padding: 0 4px 2px 4px;")
        layout.addWidget(self.separator)

        # Workspace Bar (Moved next to menus as requested)
        self.workspace_bar = WorkspaceBar(self)
        layout.addWidget(self.workspace_bar)

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
            'orange': f"background-color: {dt.ACCENT_WARNING}; color: {dt.BG_DEEPEST}; border: 1px solid {dt.ACCENT_WARNING};",
            'green': f"background-color: {dt.ACCENT_SUCCESS}; color: {dt.BG_DEEPEST}; border: 1px solid {dt.ACCENT_SUCCESS};",
            'red': f"background-color: {dt.ACCENT_ERROR}; color: {dt.TEXT_PRIMARY}; border: 1px solid {dt.ACCENT_ERROR};",
            'black': base_style
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

class WorkspaceButton(QPushButton):
    def __init__(self, name, layout_data, parent=None):
        super().__init__(name, parent)
        self.layout_data = layout_data
        self.setCheckable(True)
        self.setStyleSheet(WORKSPACE_BTN_STYLE)

class WorkspaceBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceBar")
        self.on_save_requested = None # Callback to RockyApp.save_current_layout_to_workspace()
        self.on_load_requested = None # Callback to RockyApp.load_layout_from_workspace(data)
        self.workspaces = {}
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Container for dynamic buttons
        self.btn_container = QFrame()
        self.btn_container.setObjectName("WorkspaceContainer")
        self.btn_container.setStyleSheet("background: transparent; border: none;")
        self.btn_layout = QHBoxLayout(self.btn_container)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_layout.setSpacing(0)
        self.layout.addWidget(self.btn_container)
        
        # Add Button
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(24, 24)
        self.btn_add.setStyleSheet(TOOLBAR_MENU_BTN_STYLE)
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.layout.addWidget(self.btn_add)
        
        # Ensure WorkspaceBar itself is transparent
        self.setStyleSheet("background: transparent; border: none;")
        
    def add_workspace(self, name, layout_data):
        if name in self.workspaces:
            # Overwrite? For now just create unique
            name = f"{name}_{random.randint(1,99)}"
            
        btn = WorkspaceButton(name, layout_data, self)
        btn.clicked.connect(lambda: self.set_active(name))
        self.btn_layout.addWidget(btn)
        self.workspaces[name] = btn
        return btn

    def set_active(self, name):
        if name not in self.workspaces: return
        
        # Uncheck others
        for k, btn in self.workspaces.items():
            btn.setChecked(k == name)
            
        # Trigger load
        if self.on_load_requested:
            self.on_load_requested(self.workspaces[name].layout_data)

    def _on_add_clicked(self):
        name, ok = QInputDialog.getText(self, "Nuevo Workspace", "Nombre del Workspace:", text="Layout")
        if ok and name:
            if self.on_save_requested:
                layout_data = self.on_save_requested()
                if layout_data:
                    self.add_workspace(name, layout_data)
                    self.set_active(name)
