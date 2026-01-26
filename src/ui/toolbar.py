import os
import random
from typing import List, Optional, Callable

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QLabel, 
    QSpacerItem, QSizePolicy, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction, QPixmap

from .styles import (
    PUSH_BUTTON_STYLE, TOOLBAR_STYLE, UI_FONT, 
    MENU_STYLE, ACCENT_PRIMARY, WORKSPACE_BTN_STYLE, 
    TOOLBAR_MENU_BTN_STYLE
)
from . import design_tokens as dt

# ============================================================================
# UI COMPONENTS
# ============================================================================

class ToolbarMenuButton(QPushButton):
    """
    Standardized menu button for the toolbar with integrated QMenu.
    """
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setFlat(True)
        self.setStyleSheet(TOOLBAR_MENU_BTN_STYLE)
        
        # Initialize Menu
        self.menu = QMenu(self)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.menu.setStyleSheet(MENU_STYLE)
        self.setMenu(self.menu)

    def add_action(self, text: str, callback: Optional[Callable] = None, shortcut: str = "") -> QAction:
        """Helper to quickly add actions to the associated menu."""
        action = self.menu.addAction(text)
        if callback:
            action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        return action

class WorkspaceButton(QPushButton):
    """
    Represents an individual workspace layout toggle.
    """
    def __init__(self, name: str, layout_data: dict, parent=None):
        super().__init__(name, parent)
        self.layout_data = layout_data
        self.setCheckable(True)
        self.setFlat(True)
        self.setStyleSheet(WORKSPACE_BTN_STYLE)

# ============================================================================
# TOOLBAR CONTAINERS
# ============================================================================

class WorkspaceBar(QFrame):
    """
    Manages dynamic workspace layout buttons and the 'add' functionality.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceBar")
        self.setStyleSheet("background: transparent; border: none;")
        
        self.on_save_requested = None 
        self.on_load_requested = None
        self.workspaces = {}
        
        # Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._initialize_ui()

    def _initialize_ui(self):
        """Creates the container for buttons and the add button."""
        # Dynamic Button Container
        self.btn_container = QFrame()
        self.btn_container.setObjectName("WorkspaceContainer")
        self.btn_container.setStyleSheet("background: transparent; border: none;")
        
        self.btn_layout = QHBoxLayout(self.btn_container)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_layout.setSpacing(0)
        
        # Add Button (+) with centered container
        self.add_container = QFrame()
        self.add_container.setFixedSize(24, 24)
        add_layout = QHBoxLayout(self.add_container)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setAlignment(Qt.AlignCenter)

        self.btn_add = QPushButton("+")
        self.btn_add.setFlat(True)
        self.btn_add.setFixedSize(24, 24)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet(TOOLBAR_MENU_BTN_STYLE + """
            QPushButton { 
                font-size: 15px; 
                font-weight: 500; 
                padding: 0px; 
                color: white;
            }
        """)
        self.btn_add.clicked.connect(self._on_add_clicked)
        add_layout.addWidget(self.btn_add)
        
        self.main_layout.addWidget(self.btn_container)
        self.main_layout.addWidget(self.add_container)

    def add_workspace(self, name: str, layout_data: dict):
        """Creates and registers a new workspace button."""
        if name in self.workspaces:
            name = f"{name}_{random.randint(1,99)}"
            
        btn = WorkspaceButton(name, layout_data, self)
        btn.clicked.connect(lambda: self.set_active(name))
        
        self.btn_layout.addWidget(btn)
        self.workspaces[name] = btn
        return btn

    def set_active(self, name: str):
        """Toggles the visual state of buttons and triggers layout loading."""
        if name not in self.workspaces:
            return
        
        for k, btn in self.workspaces.items():
            btn.setChecked(k == name)
            
        if self.on_load_requested:
            self.on_load_requested(self.workspaces[name].layout_data)

    def _on_add_clicked(self):
        """Prompts user for a name and saves the current layout."""
        name, ok = QInputDialog.getText(self, "Nuevo Workspace", "Nombre del Workspace:", text="Layout")
        if ok and name:
            if self.on_save_requested:
                layout_data = self.on_save_requested()
                if layout_data:
                    self.add_workspace(name, layout_data)
                    self.set_active(name)

class RockyToolbar(QFrame):
    """
    Main Application Toolbar containing brand logo, menu actions, and workspace selectors.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self.setFixedHeight(32)
        self.setStyleSheet(TOOLBAR_STYLE)
        
        # Public Action Access (for connectivity in RockyApp)
        self.actions = {} 
        
        self._initialize_ui()

    def _initialize_ui(self):
        """Constructs the toolbar layout in logical segments using Golden Ratio proportions."""
        layout = QHBoxLayout(self)
        
        # Compact Layout
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8) 
        layout.setAlignment(Qt.AlignVCenter)
        
        self._add_logo_section(layout)
        self._add_menus_section(layout)
        self._add_workspace_section(layout)
        
        layout.addStretch()
        
        self._add_proxy_section(layout)

    def _add_logo_section(self, layout: QHBoxLayout):
        """Adds the branding button in a centered container."""
        logo_container = QFrame()
        logo_container.setFixedSize(24, 24)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignCenter)

        self.btn_logo = QPushButton()
        self.btn_logo.setFlat(True)
        self.btn_logo.setFixedSize(24, 24)
        self.btn_logo.setCursor(Qt.PointingHandCursor)
        self.btn_logo.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                border: none; 
                padding: 0px; 
                margin: 0px;
            } 
            QPushButton:hover { 
                background: rgba(255,255,255,0.1); 
                border-radius: 4px; 
            }
            QPushButton::menu-indicator { image: none; }
        """)

        # Custom Icon Centering Hack (Native setIcon is often displaced on Windows/Mac)
        self.btn_logo_layout = QHBoxLayout(self.btn_logo)
        self.btn_logo_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_logo_layout.setSpacing(0)
        self.btn_logo_layout.setAlignment(Qt.AlignCenter)

        self.logo_icon_label = QLabel()
        self.logo_icon_label.setFixedSize(16, 16) 
        self.logo_icon_label.setStyleSheet("background: transparent; border: none;")
        self.logo_icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Icon Path resolution
        icon_path = os.path.join(os.getcwd(), "src", "img", "icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon_label.setPixmap(pix)
        
        self.btn_logo_layout.addWidget(self.logo_icon_label)

        # Internal Logo Menu
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(MENU_STYLE)
        self.action_welcome = menu.addAction("Pantalla de bienvenida")
        menu.addAction("Acerca de Rocky video editor")
        self.btn_logo.setMenu(menu)
        
        logo_layout.addWidget(self.btn_logo)
        layout.addWidget(logo_container)
        layout.addSpacing(8)

    def _add_menus_section(self, layout: QHBoxLayout):
        """Generates the primary application menu buttons."""
        
        # 1. ARCHIVO
        btn_archivo = ToolbarMenuButton("Archivo", self)
        self.action_open = btn_archivo.add_action("Abrir")
        self.action_save = btn_archivo.add_action("Guardar")
        self.action_save_as = btn_archivo.add_action("Guardar como...")
        layout.addWidget(btn_archivo)

        # 2. EDITAR
        btn_editar = ToolbarMenuButton("Editar", self)
        btn_editar.add_action("Deshacer")
        btn_editar.add_action("Rehacer")
        btn_editar.menu.addSeparator()
        self.action_preferences = btn_editar.add_action("Preferencias...", shortcut="Ctrl+,")
        btn_editar.menu.addSeparator()
        self.action_rot_cw = btn_editar.add_action("Rotar 90° Derecha")
        self.action_rot_ccw = btn_editar.add_action("Rotar 90° Izquierda")
        self.action_rot_180 = btn_editar.add_action("Girar 180° (Voltear)")
        layout.addWidget(btn_editar)

        # 3. PROCESAR
        btn_procesar = ToolbarMenuButton("Procesar", self)
        self.action_render = btn_procesar.add_action("Renderizar")
        layout.addWidget(btn_procesar)

        # 4. VENTANA
        btn_ventana = ToolbarMenuButton("Ventana", self)
        btn_ventana.add_action("Timeline")
        btn_ventana.add_action("Visor")
        layout.addWidget(btn_ventana)

        # 5. AYUDA
        btn_ayuda = ToolbarMenuButton("Ayuda", self)
        btn_ayuda.add_action("Manual")
        btn_ayuda.add_action("Acerca de...")
        layout.addWidget(btn_ayuda)

    def _add_workspace_section(self, layout: QHBoxLayout):
        """Adds the separator and the workspace bar."""
        # Visual Separator
        separator = QLabel("|")
        separator.setStyleSheet(
            f"color: #ffffff; background: transparent; "
            f"font-family: {UI_FONT}; font-size: 11px; padding: 0 4px 0 4px;"
        )
        
        self.workspace_bar = WorkspaceBar(self)
        
        layout.addWidget(separator, 0, Qt.AlignVCenter)
        layout.addWidget(self.workspace_bar, 0, Qt.AlignVCenter)

    def _add_proxy_section(self, layout: QHBoxLayout):
        """Adds the PX (Proxy) toggle button."""
        self.btn_proxy = QPushButton("PX")
        self.btn_proxy.setCheckable(True)
        self.btn_proxy.setChecked(True)
        self.btn_proxy.setToolTip("Modo Proxy: Usa copias de baja calidad para edición fluida")
        self.btn_proxy.setStyleSheet(PUSH_BUTTON_STYLE)
        layout.addWidget(self.btn_proxy)

    def set_proxy_status_color(self, status_color: str):
        """Updates the PX button styling to reflect global proxy state."""
        base_style = PUSH_BUTTON_STYLE
        color_map = {
            'orange': f"background-color: {dt.ACCENT_WARNING}; color: {dt.BG_DEEPEST}; border: 1px solid {dt.ACCENT_WARNING};",
            'green': f"background-color: {dt.ACCENT_SUCCESS}; color: {dt.BG_DEEPEST}; border: 1px solid {dt.ACCENT_SUCCESS};",
            'red': f"background-color: {dt.ACCENT_ERROR}; color: {dt.TEXT_PRIMARY}; border: 1px solid {dt.ACCENT_ERROR};",
            'black': base_style
        }
        
        if not self.btn_proxy.isChecked():
            self.btn_proxy.setStyleSheet(base_style)
            return

        style = color_map.get(status_color, base_style)
        final_style = f"{base_style} {style}" if status_color != 'black' else base_style
        self.btn_proxy.setStyleSheet(final_style)
