from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QMenu, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize
from . import design_tokens as dt

class RockyPanelHeader(QFrame):
    """
    Blender-style header bar for panels.
    Contains: [Type Icon] [Title] [       Spacer       ] [Action Buttons]
    """
    def __init__(self, title="Panel", parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-bottom: 1px solid #1a1a1a;
            }}
            QLabel {{
                color: #e0e0e0;
                font-family: 'Inter';
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)
        
        # 1. Type Switcher (Change Panel Type) - Circular Button
        self.btn_type = QPushButton("⋮") 
        self.btn_type.setFixedSize(20, 20)
        self.btn_type.setStyleSheet("""
            QPushButton {
                color: #ff9900; 
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                background-color: rgba(255, 153, 0, 0.15);
                border: 1px solid rgba(255, 153, 0, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(255, 153, 0, 0.3);
                border: 1px solid rgba(255, 153, 0, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 153, 0, 0.4);
            }
        """)
        self.btn_type.setToolTip("Cambiar Tipo de Panel")
        
        # 2. Close Action (Close/Join Panel) - Circular Button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #ff9900; 
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                background-color: rgba(255, 153, 0, 0.15);
                border: 1px solid rgba(255, 153, 0, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(255, 80, 80, 0.3);
                border: 1px solid rgba(255, 80, 80, 0.5);
                color: #ff5050;
            }
            QPushButton:pressed {
                background-color: rgba(255, 80, 80, 0.4);
            }
        """)
        self.btn_close.setToolTip("Cerrar Panel")
        
        # 3. Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("margin-left: 4px; font-weight: 600;")
        
        layout.addWidget(self.btn_type)
        layout.addWidget(self.btn_close)
        layout.addWidget(self.lbl_title)
        layout.addStretch()
        
        # Menu for Type Switcher
        self.type_menu = QMenu(self)
        self._populate_menu()
        self.btn_type.setMenu(self.type_menu)

    def _populate_menu(self):
        """Populate the panel type switcher menu."""
        types = [
            ("Visor de Video", "Viewer"),
            ("Línea de Tiempo", "Timeline"),
            ("Propiedades", "Properties"),
            ("Efectos", "Effects"),
            ("Explorador de Archivos", "FileBrowser"),
        ]
        for label, panel_type in types:
            action = self.type_menu.addAction(label)
            # Connect each action to emit the type change signal
            action.triggered.connect(lambda checked=False, t=panel_type, l=label: self.on_type_selected(t, l))

    def on_type_selected(self, panel_type, label):
        """Handle panel type selection from menu."""
        self.set_title(label.upper())
        # Emit signal to parent RockyPanel
        parent = self.parent()
        if parent and hasattr(parent, 'change_panel_type'):
            parent.change_panel_type(panel_type)

    def set_title(self, text):
        """Update the panel title."""
        self.lbl_title.setText(text)



class RockyPanel(QFrame):
    """
    Standard container for a UI region.
    - Rounded corners (8px) on the OUTSIDE.
    - Header bar.
    - Content area.
    """
    def __init__(self, content_widget, title="Editor", parent=None):
        super().__init__(parent)
        self.setObjectName("RockyPanelContainer")
        
        # Styling: The 8px radius applies to this container
        self.setStyleSheet(f"""
            #RockyPanelContainer {{
                background-color: #2b2b2b;
                border-radius: {dt.RADIUS_CONTAINER}px;
                margin: 2px; /* Slight gap between panels */
                border: 1px solid #111;
            }}
        """)
        
        # Shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Header
        self.header = RockyPanelHeader(title, self)
        layout.addWidget(self.header)
        
        # 2. Content
        # We wrap content in a container to handle margins/clipping if needed
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0) # Content flush with panel edges
        content_layout.setSpacing(0)
        
        if content_widget:
            content_layout.addWidget(content_widget)
            
        layout.addWidget(self.content_area)

    def set_title(self, text):
        self.header.set_title(text)

    def change_panel_type(self, panel_type):
        """Change the panel content based on selected type."""
        # Unregister old content if needed
        if self.content_area.layout().count() > 0:
            old_widget = self.content_area.layout().itemAt(0).widget()
            if old_widget:
                # Check if it's a viewer and unregister it
                if hasattr(old_widget, 'display_frame'):
                    self._unregister_viewer(old_widget)
                # Check if it contains a timeline and unregister it
                self._unregister_timeline_from_widget(old_widget)
                self.content_area.layout().removeWidget(old_widget)
                old_widget.deleteLater()
        
        # Create new content based on panel type
        new_widget = self._create_panel_content(panel_type)
        if new_widget:
            self.content_area.layout().addWidget(new_widget)
            # Register new viewer if it's one
            if hasattr(new_widget, 'display_frame'):
                self._register_viewer(new_widget)
            # Register timeline if it contains one
            self._register_timeline_from_widget(new_widget)
    
    def _register_timeline_from_widget(self, widget):
        """Find and register timeline widgets recursively."""
        try:
            from .timeline.simple_timeline import SimpleTimeline
            from PySide6.QtWidgets import QApplication
            
            # Check if widget itself is a timeline
            if isinstance(widget, SimpleTimeline):
                app = QApplication.instance()
                for top_widget in app.topLevelWidgets():
                    if hasattr(top_widget, 'register_timeline'):
                        top_widget.register_timeline(widget)
                        return
            
            # Search children recursively
            if hasattr(widget, 'children'):
                for child in widget.findChildren(SimpleTimeline):
                    app = QApplication.instance()
                    for top_widget in app.topLevelWidgets():
                        if hasattr(top_widget, 'register_timeline'):
                            top_widget.register_timeline(child)
                            break
        except:
            pass
    
    def _unregister_timeline_from_widget(self, widget):
        """Find and unregister timeline widgets recursively."""
        try:
            from .timeline.simple_timeline import SimpleTimeline
            from PySide6.QtWidgets import QApplication
            
            # Check if widget itself is a timeline
            if isinstance(widget, SimpleTimeline):
                app = QApplication.instance()
                for top_widget in app.topLevelWidgets():
                    if hasattr(top_widget, 'unregister_timeline'):
                        top_widget.unregister_timeline(widget)
                        return
            
            # Search children recursively
            if hasattr(widget, 'children'):
                for child in widget.findChildren(SimpleTimeline):
                    app = QApplication.instance()
                    for top_widget in app.topLevelWidgets():
                        if hasattr(top_widget, 'unregister_timeline'):
                            top_widget.unregister_timeline(child)
                            break
        except:
            pass
    
    def _register_viewer(self, viewer_widget):
        """Register a viewer with the main application."""
        try:
            # Find the RockyApp instance
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'register_viewer'):
                    widget.register_viewer(viewer_widget)
                    break
        except:
            pass
    
    def _unregister_viewer(self, viewer_widget):
        """Unregister a viewer from the main application."""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'unregister_viewer'):
                    widget.unregister_viewer(viewer_widget)
                    break
        except:
            pass
    
    def _create_panel_content(self, panel_type):
        """Factory method to create panel content based on type."""
        from PySide6.QtWidgets import QLabel
        
        if panel_type == "Viewer":
            # Import and create ViewerPanel
            try:
                from .viewer import ViewerPanel
                return ViewerPanel()
            except:
                pass
        elif panel_type == "Timeline":
            # Create a complete timeline using the shared model
            try:
                from .timeline.simple_timeline import SimpleTimeline
                from .models import TimelineModel
                from .ruler import TimelineRuler
                from .sidebar import SidebarPanel
                from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QSplitter, QApplication
                
                # Get the shared model from the main application
                model = None
                app = QApplication.instance()
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'model'):
                        model = widget.model
                        break
                
                # Fallback: create new model if app not found
                if model is None:
                    model = TimelineModel()
                
                # Create horizontal splitter for sidebar + timeline
                splitter = QSplitter(Qt.Orientation.Horizontal)
                splitter.setStyleSheet("QSplitter::handle { background-color: #1a1a1a; }")
                
                # Create sidebar
                sidebar = SidebarPanel(model)
                
                # Create timeline container (ruler + timeline)
                timeline_container = QWidget()
                t_layout = QVBoxLayout(timeline_container)
                t_layout.setContentsMargins(0, 0, 0, 0)
                t_layout.setSpacing(0)
                
                # Create timeline widget
                timeline_widget = SimpleTimeline(model)
                sidebar.timeline = timeline_widget  # Connect sidebar to timeline
                
                # Create ruler
                timeline_ruler = TimelineRuler(timeline_widget)
                timeline_ruler.setAutoFillBackground(True)
                t_layout.addWidget(timeline_ruler, 0)
                
                # Create scroll area for timeline
                timeline_scroll = QScrollArea()
                timeline_scroll.setWidgetResizable(True)
                timeline_scroll.setWidget(timeline_widget)
                timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
                timeline_scroll.setStyleSheet("""
                    QScrollArea { border: 0px; background-color: #242424; }
                    QScrollBar:horizontal { height: 14px; background: #2b2b2b; }
                    QScrollBar::handle:horizontal { background: #555555; min-width: 20px; border-radius: 2px; }
                    QScrollBar:vertical { width: 14px; background: #2b2b2b; }
                    QScrollBar::handle:vertical { background: #555555; min-height: 20px; border-radius: 2px; }
                """)
                t_layout.addWidget(timeline_scroll, 1)
                
                # Add sidebar and timeline to splitter
                splitter.addWidget(sidebar)
                splitter.addWidget(timeline_container)
                splitter.setStretchFactor(1, 1)  # Timeline takes more space
                
                return splitter
            except Exception as e:
                # Fallback to message if timeline creation fails
                label = QLabel(f"Error creando timeline: {str(e)}")
                label.setStyleSheet("color: #ff5050; padding: 20px; font-size: 11px;")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                return label
        elif panel_type == "Properties":
            # Import and create EditorPanel
            try:
                from .editor_panel import EditorPanel
                return EditorPanel()
            except:
                pass
        elif panel_type == "Effects":
            # Import and create AssetTabsPanel
            try:
                from .asset_tabs import AssetTabsPanel
                return AssetTabsPanel()
            except:
                pass
        elif panel_type == "FileBrowser":
            # Create placeholder for file browser
            label = QLabel("Explorador de Archivos\n(En desarrollo)")
            label.setStyleSheet("color: #888; padding: 20px; font-size: 12px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return label
        
        # Default fallback
        label = QLabel(f"Panel: {panel_type}")
        label.setStyleSheet("color: #888; padding: 20px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
