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
        
        # 2b. Split Buttons - Circular subtle buttons
        self.btn_split_h = QPushButton("⬒") # Looks like split horizontal
        self.btn_split_v = QPushButton("⬔") # Looks like split vertical
        for btn in [self.btn_split_h, self.btn_split_v]:
            btn.setFixedSize(20, 20)
            btn.setStyleSheet("""
                QPushButton {
                    color: #888; 
                    font-size: 14px;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 153, 0, 0.15);
                    color: #ff9900;
                }
            """)
        
        self.btn_split_h.setToolTip("Dividir Horizontal")
        self.btn_split_v.setToolTip("Dividir Vertical")
        
        # 3. Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("margin-left: 4px; font-weight: 600;")
        
        layout.addWidget(self.btn_type)
        layout.addWidget(self.btn_close)
        layout.addWidget(self.btn_split_h)
        layout.addWidget(self.btn_split_v)
        layout.addWidget(self.lbl_title)
        layout.addStretch()
        
        # Menu for Type Switcher
        self.type_menu = QMenu(self)
        self._populate_menu()
        self.btn_type.setMenu(self.type_menu)
        
        # Connect close button
        self.btn_close.clicked.connect(self.on_close_clicked)
        self.btn_split_h.clicked.connect(lambda: self.on_split_clicked(Qt.Orientation.Vertical)) # Divides vertically -> Splitter is vertical
        self.btn_split_v.clicked.connect(lambda: self.on_split_clicked(Qt.Orientation.Horizontal)) # Divides horizontally -> Splitter is horizontal

    def on_split_clicked(self, orientation):
        """Request parent to split."""
        parent = self.parent()
        if parent and hasattr(parent, 'split'):
            parent.split(orientation)

    def on_close_clicked(self):
        """Emit close signal to parent."""
        parent = self.parent()
        if parent and hasattr(parent, 'close_panel'):
            parent.close_panel()

    def mousePressEvent(self, event):
        """Detect start of drag operation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        """Start drag if moved enough pixels."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
            
        if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
            return
            
        from PySide6.QtGui import QDrag
        from PySide6.QtCore import QMimeData
        
        drag = QDrag(self)
        mime = QMimeData()
        
        # We store the memory address of the parent RockyPanel to identify it on drop
        parent_panel = self.parent()
        if parent_panel:
            mime.setText(f"rocky_panel:{id(parent_panel)}")
            drag.setMimeData(mime)
            
            # Optional: create a small pixmap for the drag icon
            drag.exec(Qt.DropAction.MoveAction)

    def _populate_menu(self):
        """Populate the panel type switcher menu."""
        types = [
            ("Visor de Video", "Viewer"),
            ("Línea de Tiempo", "Timeline"),
            ("Propiedades", "Properties"),
            ("Efectos", "Effects"),
            ("Vúmetro Maestro", "MasterMeter"),
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
        self.current_type = "Viewer" # Initial default
        if "TIEMPO" in title: self.current_type = "Timeline"
        elif "PROPIEDADES" in title: self.current_type = "Properties"
        elif "EFECTOS" in title: self.current_type = "Effects"
        elif "VÚMETRO" in title: self.current_type = "MasterMeter"
        elif "EXPLORADOR" in title: self.current_type = "FileBrowser"
        
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
        
        # Drag and drop support
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """Allow drops from other RockyPanels."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("rocky_panel:"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle the swap or docking of panel contents."""
        try:
            mime_text = event.mimeData().text()
            source_id = int(mime_text.split(":")[1])
            
            # Find the source panel in the application hierarchy
            from PySide6.QtWidgets import QApplication
            source_panel = None
            for widget in QApplication.instance().allWidgets():
                if id(widget) == source_id:
                    source_panel = widget
                    break
            
            if not source_panel or source_panel == self:
                return

            # Edge detection for DOCKING (Windows Snap style)
            pos = event.position().toPoint()
            w, h = self.width(), self.height()
            margin_x = w * 0.25
            margin_y = h * 0.25
            
            edge = None # None means center swap
            if pos.x() < margin_x: edge = "left"
            elif pos.x() > w - margin_x: edge = "right"
            elif pos.y() < margin_y: edge = "top"
            elif pos.y() > h - margin_y: edge = "bottom"
            
            if edge:
                # DOCK-SPLIT LOGIC
                orientation = Qt.Orientation.Horizontal if edge in ["left", "right"] else Qt.Orientation.Vertical
                
                # Store source info before it might be closed
                src_type = source_panel.current_type
                src_title = source_panel.header.lbl_title.text()
                
                # 1. Close/Remove source panel from its current position
                source_panel.close_panel()
                
                # 2. Split THIS panel
                self.split(orientation)
                
                # 3. The split creates a sibling. 
                # Find the newly created sibling in the splitter
                from PySide6.QtWidgets import QSplitter
                splitter = self.parentWidget()
                if isinstance(splitter, QSplitter):
                    idx = splitter.indexOf(self)
                    # For left/top, we want the new content on the left/top
                    # split() currently adds new panel to the RIGHT/BOTTOM (idx 1)
                    # We might need to rearrange
                    sibling_idx = 1 if idx == 0 else 0
                    sibling = splitter.widget(sibling_idx)
                    
                    if edge in ["left", "top"]:
                        # Swap positions in splitter: move self to index 1, sibling to 0
                        splitter.insertWidget(0, sibling)
                        splitter.insertWidget(1, self)
                        target_dock = sibling
                    else:
                        target_dock = sibling
                    
                    # 4. Set the docked panel to the source's type
                    target_dock.change_panel_type(src_type)
                    target_dock.set_title(src_title)
                
                event.acceptProposedAction()
            else:
                # CENTER SWAP LOGIC
                self.swap_with(source_panel)
                event.acceptProposedAction()
                
        except Exception as e:
            print(f"Drop Error: {e}")

    def swap_with(self, other):
        """Exchange content type and title with another panel."""
        # 1. Store current states
        my_type = self.current_type
        my_title = self.header.lbl_title.text()
        
        other_type = other.current_type
        other_title = other.header.lbl_title.text()
        
        # 2. Swap types
        self.change_panel_type(other_type)
        self.set_title(other_title)
        
        other.change_panel_type(my_type)
        other.set_title(my_title)

    def close_panel(self):
        """Logic to close and join panels."""
        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        
        if isinstance(parent, QSplitter):
            # If we are in a splitter, we can "join" by closing this widget
            # and letting the other widget take all space
            if parent.count() > 1:
                # Unregister self components from registries before deleting
                self._unregister_all_components()
                self.hide()
                self.deleteLater()
                # The splitter will automatically expand the other widget
            else:
                # Last widget in this branch? Hide parent splitter too
                self._unregister_all_components()
                parent.hide()
        else:
            # Fallback for root panel: just hide
            self._unregister_all_components()
            self.hide()

    def _unregister_all_components(self):
        """Helper to cleanup registries before deletion."""
        if self.content_area.layout().count() > 0:
            old_widget = self.content_area.layout().itemAt(0).widget()
            if old_widget:
                if hasattr(old_widget, 'display_frame'):
                    self._unregister_viewer(old_widget)
                from .master_meter import MasterMeterPanel
                if isinstance(old_widget, MasterMeterPanel):
                    self._unregister_master_meter(old_widget)
                self._unregister_timeline_from_widget(old_widget)

    def split(self, orientation):
        """Partitions this panel space into two using a QSplitter."""
        from PySide6.QtWidgets import QSplitter, QVBoxLayout, QHBoxLayout
        
        parent = self.parentWidget()
        if not parent: return
        
        # 1. Create a neuen splitter
        new_splitter = QSplitter(orientation)
        new_splitter.setHandleWidth(2)
        new_splitter.setStyleSheet("QSplitter::handle { background-color: #1a1a1a; }")
        
        # 2. Insert splitter into our current spot
        if isinstance(parent, QSplitter):
            # We are already in a splitter, insert new splitter at our index
            idx = parent.indexOf(self)
            parent.insertWidget(idx, new_splitter)
        else:
            # We are likely in the middle_section container or root
            layout = parent.layout()
            if layout:
                idx = layout.indexOf(self)
                layout.insertWidget(idx, new_splitter)
        
        # 3. Create sibling panel (clone current type)
        new_content = self._create_panel_content(self.current_type)
        new_panel = RockyPanel(new_content, title=self.header.lbl_title.text())
        new_panel.current_type = self.current_type
        
        # 4. Move self to the new splitter and add new panel
        new_splitter.addWidget(self)
        new_splitter.addWidget(new_panel)
        
        # 5. Fix registries for the newly created brother
        if hasattr(new_content, 'display_frame'):
            self._register_viewer(new_content)
        from .master_meter import MasterMeterPanel
        if isinstance(new_content, MasterMeterPanel):
            self._register_master_meter(new_content)
        self._register_timeline_from_widget(new_content)
        
        self.show()
        new_panel.show()
        new_splitter.show()

    def set_title(self, text):
        self.header.set_title(text)

    def change_panel_type(self, panel_type):
        """Change the panel content based on selected type."""
        self.current_type = panel_type
        # Unregister old content if needed
        if self.content_area.layout().count() > 0:
            old_widget = self.content_area.layout().itemAt(0).widget()
            if old_widget:
                # Check if it's a viewer and unregister it
                if hasattr(old_widget, 'display_frame'):
                    self._unregister_viewer(old_widget)
                # Check if it's a master meter
                from .master_meter import MasterMeterPanel
                if isinstance(old_widget, MasterMeterPanel):
                    self._unregister_master_meter(old_widget)
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
            # Register master meter if it's one
            from .master_meter import MasterMeterPanel
            if isinstance(new_widget, MasterMeterPanel):
                self._register_master_meter(new_widget)
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

    def _register_master_meter(self, meter_widget):
        """Register a master meter with the main application."""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'register_master_meter'):
                    widget.register_master_meter(meter_widget)
                    break
        except:
            pass

    def _unregister_master_meter(self, meter_widget):
        """Unregister a master meter with the main application."""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'unregister_master_meter'):
                    widget.unregister_master_meter(meter_widget)
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
                
                # Sincronización de scroll vertical (Sidebar <-> Timeline)
                timeline_scroll.verticalScrollBar().valueChanged.connect(
                    sidebar.scroll.verticalScrollBar().setValue
                )
                sidebar.scroll.verticalScrollBar().valueChanged.connect(
                    timeline_scroll.verticalScrollBar().setValue
                )
                
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
        elif panel_type == "MasterMeter":
            # Import and create MasterMeterPanel
            try:
                from .master_meter import MasterMeterPanel
                return MasterMeterPanel()
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
