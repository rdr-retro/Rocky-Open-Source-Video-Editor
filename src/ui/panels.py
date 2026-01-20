from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsOpacityEffect, 
                               QPushButton, QFrame, QMenu, QGraphicsDropShadowEffect, QGridLayout)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QCursor
from . import design_tokens as dt

class PanelTypeGridMenu(QFrame):
    """Blender-style grid menu for switching panel types."""
    type_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: transparent;
                border-radius: 4px;
                color: #ddd;
                padding: 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 153, 0, 0.2);
                color: white;
            }}
        """)
        
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        types = [
            ("📽️", "Visor", "Viewer"),
            ("🎞️", "Timeline", "Timeline"),
            ("⚙️", "Ajustes", "Properties"),
            ("✨", "Efectos", "Effects"),
            ("📊", "Audio", "MasterMeter"),
            ("📁", "Archivos", "FileBrowser"),
        ]
        
        for i, (icon, label, p_type) in enumerate(types):
            btn = QPushButton(f"{icon}\n{label}")
            btn.setFixedSize(70, 60)
            btn.clicked.connect(lambda checked=False, t=p_type: self._on_selected(t))
            layout.addWidget(btn, i // 3, i % 3)

    def _on_selected(self, p_type):
        self.type_selected.emit(p_type)
        self.close()

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
        layout.setSpacing(6)
        
        # 1. Type Switcher (Now on the LEFT)
        self.btn_type = QPushButton("📽️") # Default icon
        self.btn_type.setFixedSize(24, 24)
        self.btn_type.setStyleSheet("""
            QPushButton {
                color: #ff9900; 
                font-size: 14px;
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 153, 0, 0.1);
                border-radius: 4px;
            }
        """)
        self.btn_type.setToolTip("Cambiar Tipo de Panel")
        
        # 2. Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("margin-left: 2px; font-weight: 600; color: #888;")
        
        layout.addWidget(self.btn_type)
        layout.addWidget(self.lbl_title)
        
        # 3. Minimal Expansion Button (Built-in '+' button)
        self.btn_expand = QPushButton("+")
        self.btn_expand.setFixedSize(20, 20)
        self.btn_expand.setStyleSheet(f"""
            QPushButton {{
                color: {dt.ACCENT_PRIMARY};
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 153, 0, 0.2);
            }}
        """)
        self.btn_expand.clicked.connect(self.toggle_collapse)
        self.btn_expand.hide() # Hidden by default
        layout.addWidget(self.btn_expand)
        
        layout.addStretch()

        # Connect events
        self.btn_type.clicked.connect(self.show_grid_menu)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_header_context_menu)

    def mouseDoubleClickEvent(self, event):
        """Header collapse on double click."""
        self.toggle_collapse()

    def toggle_collapse(self):
        """Collapse header to 8px solid line with a '+' button or expand back."""
        if self.height() > 8:
            self.old_height = self.height()
            self.setFixedHeight(8) # Robust indicator strip
            self.btn_type.hide()
            self.lbl_title.hide()
            self.btn_expand.show()
            self.btn_expand.setFixedSize(16, 16)
            self.btn_expand.setStyleSheet(f"""
                QPushButton {{
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    background-color: rgba(0, 0, 0, 0.4);
                    border-radius: 8px;
                    border: none;
                }}
            """)
            # Apply Solid Orange with Depth
            self.setStyleSheet(f"QFrame {{ background-color: #ff9900; border: 1px solid #c87800; border-radius: 4px; }}") 
            
            # Add Shadow Effect for "Protrusion"
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(8)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            shadow.setColor(QColor(0, 0, 0, 180))
            self.setGraphicsEffect(shadow)
        else:
            self.setGraphicsEffect(None) # Remove shadow
            self.setFixedHeight(self.old_height if hasattr(self, 'old_height') else 28)
            self.btn_type.show()
            self.lbl_title.show()
            self.btn_expand.hide()
            self.setStyleSheet(f"QFrame {{ background-color: transparent; border-bottom: 1px solid #1a1a1a; }}")

    def show_grid_menu(self):
        """Show the Blender-style grid menu."""
        menu = PanelTypeGridMenu(self)
        menu.type_selected.connect(self._on_type_selected)
        
        pos = self.btn_type.mapToGlobal(QPoint(0, self.btn_type.height()))
        menu.move(pos)
        menu.show()

    def _on_type_selected(self, p_type):
        """Forward selection to parent panel."""
        parent = self.parent()
        if parent and hasattr(parent, 'change_panel_type'):
            parent.change_panel_type(p_type)
            self.update_type_icon(p_type)

    def show_header_context_menu(self, pos):
        """Right-click menu for header options."""
        menu = QMenu(self)
        flip_action = menu.addAction("Flip to Bottom" if self.parent().layout().indexOf(self) == 0 else "Flip to Top")
        flip_action.triggered.connect(self.toggle_position)
        menu.exec(self.mapToGlobal(pos))

    def toggle_position(self):
        """Move header between top and bottom of the panel."""
        parent = self.parent()
        layout = parent.layout()
        idx = layout.indexOf(self)
        layout.removeWidget(self)
        if idx == 0:
            layout.addWidget(self) # Add to end (bottom)
        else:
            layout.insertWidget(0, self) # Add to start (top)

    def update_type_icon(self, panel_type):
        """Update the icon based on current panel type."""
        icons = {
            "Viewer": "📽️",
            "Timeline": "🎞️",
            "Properties": "⚙️",
            "Effects": "✨",
            "MasterMeter": "📊",
            "FileBrowser": "📂"
        }
        icon = icons.get(panel_type, "📽️")
        self.btn_type.setText(icon)

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
        self.update_type_icon(panel_type)
        # Emit signal to parent RockyPanel
        parent = self.parent()
        if parent and hasattr(parent, 'change_panel_type'):
            parent.change_panel_type(panel_type)

    def set_title(self, text):
        """Update the panel title."""
        self.lbl_title.setText(text)



class LayoutAnimator:
    """Helper to animate QSplitter sizes smoothly."""
    def __init__(self, splitter, duration=250, easing=QEasingCurve.Type.OutQuart):
        self.splitter = splitter
        self.duration = duration
        self.easing = easing
        self.animation = QVariantAnimation()
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(easing)
        self.animation.valueChanged.connect(self._update_sizes)

    def animate(self, start_sizes, end_sizes):
        self.start_sizes = start_sizes
        self.end_sizes = end_sizes
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def _update_sizes(self, value):
        new_sizes = []
        for s, e in zip(self.start_sizes, self.end_sizes):
            new_sizes.append(int(s + (e - s) * value))
        self.splitter.setSizes(new_sizes)


class SplitPreviewOverlay(QWidget):
    """Overlay for drawing a solid orange split marker ON TOP of everything."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.split_rect = None # Global coordinates
        self.hide()

    def set_preview(self, rect):
        """Expects rect in parent (main window) coordinates."""
        self.split_rect = rect
        # Cover the entire parent window
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.update()

    def paintEvent(self, event):
        if not self.split_rect: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw everything in global (overlay) coordinates
        target = QRectF(self.split_rect)
        
        # 1. Intense Neon Glow (Multi-layered bloom)
        glow_color = QColor(255, 100, 0, 25) 
        for i in range(1, 9):
            painter.setPen(QPen(glow_color, 1 + i * 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawRect(target.adjusted(1, 1, -1, -1))
            
        # 2. Hard Black Shadow
        painter.setPen(QPen(QColor(0, 0, 0, 220), 4, Qt.PenStyle.SolidLine))
        painter.drawRect(target.adjusted(1, 1, 0, 0))
        
        # 3. Main Neon Core Line
        painter.setPen(QPen(QColor(255, 153, 0), 2, Qt.PenStyle.SolidLine))
        painter.drawRect(target.adjusted(0, 0, -1, -1))
        
        # Note: No fillRect here to keep panel content visible ("sin perder la forma")


class JoinOverlay(QWidget):
    """Semi-transparent arrow overlay with Pulsing Animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForInput)
        self.direction = 'right'
        self.target_rect = None
        self.pulse_val = 1.0 # For pulsing animation
        
        self.pulse_anim = QVariantAnimation(self)
        self.pulse_anim.setDuration(800)
        self.pulse_anim.setStartValue(0.6)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1) # Infinite loop
        self.pulse_anim.valueChanged.connect(self._update_pulse)
        self.hide()

    def _update_pulse(self, val):
        self.pulse_val = val
        self.update()

    def set_join(self, target_rect, direction):
        self.target_rect = target_rect
        self.direction = direction
        self.setGeometry(target_rect)
        self.show()
        self.pulse_anim.start()
        self.update()

    def hide(self):
        self.pulse_anim.stop()
        super().hide()

    def paintEvent(self, event):
        if not self.target_rect: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Dark Ghosting wash (Blender Style)
        # We use a dark semi-transparent black to "dim" the victim
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        
        # 2. Neon Orange Border for the Victim Area
        painter.setPen(QPen(QColor(255, 156, 0, 200), 2, Qt.PenStyle.SolidLine))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # 3. High-Contrast Pulsing Arrow
        alpha = int(255 * self.pulse_val)
        glow_alpha = int(100 * self.pulse_val)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        base_size = min(w, h) * 0.25
        size = base_size * (0.9 + 0.1 * self.pulse_val) # Subtle pulse scale
        
        head_size = size * 0.7
        
        # Draw Arrow Shadow/Glow first
        painter.setPen(QPen(QColor(0, 0, 0, alpha), 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        self._draw_arrow_shape(painter, cx, cy, size, head_size)
        
        # Draw Main Arrow Line
        painter.setPen(QPen(QColor(255, 156, 0, alpha), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        self._draw_arrow_shape(painter, cx, cy, size, head_size)

    def _draw_arrow_shape(self, painter, cx, cy, size, head_size):
        """Helper to draw the arrow geometry."""
        if self.direction == 'right': 
            painter.drawLine(cx - size, cy, cx + size, cy)
            painter.drawLine(cx + size, cy, cx + size - head_size, cy - head_size)
            painter.drawLine(cx + size, cy, cx + size - head_size, cy + head_size)
        elif self.direction == 'left':
            painter.drawLine(cx + size, cy, cx - size, cy)
            painter.drawLine(cx - size, cy, cx - size + head_size, cy - head_size)
            painter.drawLine(cx - size, cy, cx - size + head_size, cy + head_size)
        elif self.direction == 'bottom':
            painter.drawLine(cx, cy - size, cx, cy + size)
            painter.drawLine(cx, cy + size, cx - head_size, cy + size - head_size)
            painter.drawLine(cx, cy + size, cx + head_size, cy + size - head_size)
        elif self.direction == 'top':
            painter.drawLine(cx, cy + size, cx, cy - size)
            painter.drawLine(cx, cy - size, cx - head_size, cy - size + head_size)
            painter.drawLine(cx, cy - size, cx + head_size, cy - size + head_size)


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
        
        # Interactive Corner Size
        self.CORNER_SIZE = 8
        
        # Interaction States
        self.is_corner_dragging = False
        self.active_corner = None
        self.drag_start_pos = None
        self.split_preview_rect = None
        self.is_maximized = False
        self.pending_join_target = None
        self.gesture_mode = None 
        self.locked_orient = None
        self.active_splitter = None # For live tracking
        self.split_index = 0 # Which side of the splitter are we?
        
        # Styling: The 8px radius applies to this container
        self.setStyleSheet(f"""
            #RockyPanelContainer {{
                background-color: #1a1a1a;
                border-radius: 12px;
                margin: 2px;
                border: 1px solid #333;
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
        
        # Sync initial icon
        self.header.update_type_icon(self.current_type)
        
        # Phase 1: Corners & Areas (Blender-style)
        self.setMouseTracking(True)

        # Install event filter to catch splitter handle context menu
        QTimer.singleShot(100, self._setup_splitter_filter)

    def _setup_splitter_filter(self):
        """Find the splitter handle if this is in a splitter and install filter."""
        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        if isinstance(parent, QSplitter):
            # We want to catch the handle BEFORE this widget
            idx = parent.indexOf(self)
            if idx > 0:
                handle = parent.handle(idx)
                handle.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                handle.customContextMenuRequested.connect(lambda pos, h=handle: self._show_handle_menu(pos, h))

    def _show_handle_menu(self, pos, handle):
        """Show the 'Join Areas' menu on the splitter handle."""
        menu = QMenu(self)
        join_action = menu.addAction("Join Areas")
        join_action.triggered.connect(lambda: self._start_join_from_handle(handle))
        menu.exec(handle.mapToGlobal(pos))

    def _start_join_from_handle(self, handle):
        """Trigger the join arrow from a handle context menu."""
        # This is a bit complex as we need to know which way to join.
        # Manual says "Aparece una flecha, click hacia el área que quieres eliminar".
        # We'll initiate the JoinOverlay mode.
        self.is_corner_dragging = True # Simulate a drag
        self.drag_start_pos = self.mapFromGlobal(QCursor.pos())
        self.active_corner = 'br' # Arbitrary corner to trigger logic
        # Force the next mouse move to trigger join feedback

    def _get_neighbor(self, direction):
        """Find the adjacent panel in the given direction within the splitter tree."""
        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        if not isinstance(parent, QSplitter):
            return None
        
        idx = parent.indexOf(self)
        orient = parent.orientation()
        
        if orient == Qt.Orientation.Horizontal:
            if direction == 'left' and idx > 0: return parent.widget(idx - 1)
            if direction == 'right' and idx < parent.count() - 1: return parent.widget(idx + 1)
        else:
            if direction == 'top' and idx > 0: return parent.widget(idx - 1)
            if direction == 'bottom' and idx < parent.count() - 1: return parent.widget(idx + 1)
            
        return None

    def _get_corner_at(self, pos):
        """Identify which corner (if any) the position is in."""
        w, h = self.width(), self.height()
        s = self.CORNER_SIZE
        if pos.x() < s and pos.y() < s: return 'tl'
        if pos.x() > w - s and pos.y() < s: return 'tr'
        if pos.x() < s and pos.y() > h - s: return 'bl'
        if pos.x() > w - s and pos.y() > h - s: return 'br'
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            corner = self._get_corner_at(event.pos())
            if corner:
                self.active_corner = corner
                self.is_corner_dragging = True
                self.drag_start_pos = event.pos()
                self.grabMouse() # Take control for the entire gesture
                return # Intercept for corner gesture
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        
        # 1. Cursor Feedback
        if not self.is_corner_dragging:
            corner = self._get_corner_at(pos)
            if corner:
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.unsetCursor()
        
        # 2. Gesture Handling
        if self.is_corner_dragging:
            diff = pos - self.drag_start_pos
            dist = diff.manhattanLength()
            
            # Initial Mode Locking (Refined Sensitivity)
            if dist > 5 and self.gesture_mode is None:
                is_inward = self.rect().contains(pos)
                if is_inward:
                    self.gesture_mode = 'split'
                    # LOCK AXIS: If horizontal movement is greater, we do a vertical split
                    if abs(diff.x()) > abs(diff.y()):
                        self.locked_orient = Qt.Orientation.Horizontal # Vertical line
                    else:
                        self.locked_orient = Qt.Orientation.Vertical # Horizontal line
                elif dist > 12: # Higher threshold for outward JOIN
                    self.gesture_mode = 'join'
            
            # Executing Locked Mode
            if self.gesture_mode == 'split':
                self._hide_join_overlay()
                
                # 1. Trigger Initial Split (Atomic)
                if self.active_splitter is None:
                    w, h = self.width(), self.height()
                    SAFE = 40
                    if self.locked_orient == Qt.Orientation.Horizontal:
                        pt = max(SAFE, min(w - SAFE, pos.x()))
                    else:
                        pt = max(SAFE, min(h - SAFE, pos.y()))
                        
                    self.active_splitter = self.split(self.locked_orient, pt)
                    # Determine side (0 or 1)
                    idx = self.active_splitter.indexOf(self)
                    self.split_index = idx
                
                # 2. Track Handle Live (High-Precision Mapping)
                if self.active_splitter:
                    # Map local mouse to splitter space for 1:1 precision
                    split_pt = self.mapTo(self.active_splitter, pos)
                    total = self.active_splitter.width() if self.active_splitter.orientation() == Qt.Orientation.Horizontal else self.active_splitter.height()
                    
                    val = split_pt.x() if self.active_splitter.orientation() == Qt.Orientation.Horizontal else split_pt.y()
                    val = max(40, min(total - 40, val)) # Enforce 40px safe zone
                    
                    # Apply live sizes
                    new_sizes = [val, total - val]
                    self.active_splitter.setSizes(new_sizes)
                self.update()
                
            elif self.gesture_mode == 'join':
                self.split_preview_rect = None
                self.update()
                
                # Check for direction based on major displacement
                # REQUIRE 15px PENETRATION (Safety Buffer)
                w, h = self.width(), self.height()
                SIDE_BUFFER = 15
                side = None
                if pos.x() < -SIDE_BUFFER: side = 'left'
                elif pos.x() > w + SIDE_BUFFER: side = 'right'
                elif pos.y() < -SIDE_BUFFER: side = 'top'
                elif pos.y() > h + SIDE_BUFFER: side = 'bottom'
                
                if side:
                    neighbor = self._get_neighbor(side)
                    if neighbor:
                        self._show_join_overlay(neighbor, side)
                    else:
                        self._hide_join_overlay()
                else:
                    self._hide_join_overlay()
            return
        
        super().mouseMoveEvent(event)

    def _show_join_overlay(self, neighbor, direction):
        """Display the arrow overlay over the panel to be absorbed."""
        # FIND THE ROOT WINDOW (Robust Blender Style)
        main_win = self.window()
        if not main_win: return
        
        # Ensure RockyApp attributes exist
        if not hasattr(main_win, 'global_join_overlay'):
            main_win.global_join_overlay = JoinOverlay(main_win)
        
        overlay = main_win.global_join_overlay
        
        # Map neighbor's geometry to main_win's coordinate space
        glob_pos = neighbor.mapTo(main_win, neighbor.rect().topLeft())
        overlay.set_join(QRect(glob_pos, neighbor.size()), direction)
        overlay.raise_()
        self.pending_join_target = neighbor

    def _show_split_preview(self, rect):
        """Show the top-level split preview overlay."""
        # FIND THE ROOT WINDOW (Robust Blender Style)
        main_win = self.window()
        if not main_win: return
        
        if not hasattr(main_win, 'global_split_overlay'):
            main_win.global_split_overlay = SplitPreviewOverlay(main_win)
            
        overlay = main_win.global_split_overlay
        # Map local rect (panel space) to main_win coordinates
        glob_pos = self.mapTo(main_win, rect.topLeft())
        overlay.set_preview(QRect(glob_pos, rect.size()))
        overlay.raise_()

    def _hide_join_overlay(self):
        main_win = self.window()
        if not main_win: return
        
        if hasattr(main_win, 'global_join_overlay'):
            main_win.global_join_overlay.hide()
        if hasattr(main_win, 'global_split_overlay'):
            main_win.global_split_overlay.hide()
        self.pending_join_target = None

    def _execute_join(self, target_panel):
        """Ghost Collapse: Absorb another panel with animation."""
        parent = self.parentWidget()
        from PySide6.QtWidgets import QSplitter
        if not isinstance(parent, QSplitter):
            target_panel.close_panel()
            return
            
        # 1. Darken the victim (Ghost Effect)
        target_panel.content_area.hide()
        target_panel.header.hide()
        # Apply a deep fade-out look for the animation
        target_panel.setStyleSheet("background-color: #000000; border: none;")
        target_panel.update()
        
        # 2. Animate Splitter
        idx_victim = parent.indexOf(target_panel)
        idx_survivor = parent.indexOf(self)
        
        old_sizes = parent.sizes()
        new_sizes = list(old_sizes)
        total = old_sizes[idx_victim] + old_sizes[idx_survivor]
        
        new_sizes[idx_victim] = 0
        new_sizes[idx_survivor] = total
        
        self.animator = LayoutAnimator(parent, duration=350, easing=QEasingCurve.Type.OutQuart)
        self.animator.animation.finished.connect(target_panel.close_panel)
        self.animator.animate(old_sizes, new_sizes)

    def mouseReleaseEvent(self, event):
        if self.is_corner_dragging:
            self.releaseMouse() # Release control
            # 1. Join Execution
            if self.gesture_mode == 'join':
                if hasattr(self, 'pending_join_target') and self.pending_join_target:
                    self._execute_join(self.pending_join_target)
            
            # 2. Split Execution (On Release)
            elif self.gesture_mode == 'split' and self.split_preview_rect:
                # The line followed our cursor, now we finalize
                if self.pending_orientation == Qt.Orientation.Horizontal:
                    split_pos = self.split_preview_rect.x()
                else:
                    split_pos = self.split_preview_rect.y()
                self.split(self.pending_orientation, split_pos)
        
        self._hide_join_overlay()
        self.is_corner_dragging = False
        self.active_corner = None
        self.split_preview_rect = None
        self.gesture_mode = None
        self.locked_orient = None
        self.active_splitter = None
        self.update()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle hotkeys for Pie Menu (Space) and Maximize (Ctrl+Space)."""
        if event.key() == Qt.Key.Key_Space:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.toggle_maximize()
            else:
                self._show_pie_menu()
        elif event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._show_pie_menu() # Blender alternate pie menu hotkey
        else:
            super().keyPressEvent(event)

    def toggle_maximize(self):
        """Make this panel fill the entire application window."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        main_win = None
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'register_viewer'):
                main_win = widget
                break
        
        if not main_win: return

        if not self.is_maximized:
            # SAVE STATE and Maximize
            self._old_parent = self.parentWidget()
            self._old_index = self._old_parent.indexOf(self) if hasattr(self._old_parent, 'indexOf') else 0
            
            # Use a fullscreen overlay approach or replace the root layout
            # For simplicity in this mock-up, we'll just move it to a high-Z layer or 
            # hide everything else in the main window central widget.
            self.setParent(main_win)
            self.setGeometry(main_win.rect())
            self.show()
            self.raise_()
            self.is_maximized = True
        else:
            # RESTORE
            if hasattr(self, '_old_parent'):
                self.setParent(self._old_parent)
                # Re-insert into splitter if needed
                from PySide6.QtWidgets import QSplitter
                if isinstance(self._old_parent, QSplitter):
                    self._old_parent.insertWidget(self._old_index, self)
                self.is_maximized = False
                # RockyApp layout will handle the rest on next resize

    def paintEvent(self, event):
        """Standard paint event (Hatched corners removed for a cleaner look)."""
        super().paintEvent(event)
        
        # Split preview is now handled by the top-level global_split_overlay

    def _show_pie_menu(self):
        """Generate and show the radial pie menu."""
        from .radial_menu import RadialMenu
        from PySide6.QtGui import QCursor
        
        items = [
            ("Split H", "⬒", lambda: self.split(Qt.Orientation.Vertical)),
            ("Split V", "⬔", lambda: self.split(Qt.Orientation.Horizontal)),
            ("Join", "🔗", lambda: print("Drag corner outward to join")), # Tutorial entry
            ("Viewer", "📽️", lambda: self.change_panel_type("Viewer")),
            ("Timeline", "🎞️", lambda: self.change_panel_type("Timeline")),
            ("Close", "×", lambda: self.close_panel())
        ]
        
        menu = RadialMenu(self.window(), items)
        menu.show_at(QCursor.pos())

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

    def split(self, orientation, split_pos=None):
        """Partitions this panel space into two using a QSplitter with slide-in animation."""
        from PySide6.QtWidgets import QSplitter, QVBoxLayout, QHBoxLayout
        
        parent = self.parentWidget()
        if not parent: return
        
        # 1. Create a neuen splitter
        new_splitter = QSplitter(orientation)
        new_splitter.setHandleWidth(4)
        new_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1a1a1a;
                background-image: radial-gradient(circle, #444 1px, transparent 1.5px);
                background-position: center;
                background-repeat: repeat-y;
            }
            QSplitter::handle:horizontal {
                background-repeat: repeat-y;
            }
            QSplitter::handle:vertical {
                background-repeat: repeat-x;
            }
            QSplitter::handle:hover {
                background-color: #ff9900;
            }
        """)
        
        # 2. Insert splitter into our current spot
        if isinstance(parent, QSplitter):
            # Capture parent state for stability
            original_sizes = parent.sizes()
            idx = parent.indexOf(self)
            
            parent.insertWidget(idx, new_splitter)
            
            # Re-apply sizes to parent so other parts don't move
            parent.setSizes(original_sizes)
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
        
        # 4. Move self to the new splitter and add new panel with CORRECT ORDER
        # Order depends on which corner we dragged from
        new_panel_index = 1 # Default (New panel on right/bottom)
        
        if orientation == Qt.Orientation.Horizontal:
            if self.active_corner in ['tl', 'bl']:
                new_panel_index = 0
        else: # Vertical
            if self.active_corner in ['tl', 'tr']:
                new_panel_index = 0
                
        if new_panel_index == 0:
            new_splitter.addWidget(new_panel)
            new_splitter.addWidget(self)
        else:
            new_splitter.addWidget(self)
            new_splitter.addWidget(new_panel)
        
        # 5. Slide-In Transition (Matches Release Position)
        total_size = new_splitter.width() if orientation == Qt.Orientation.Horizontal else new_splitter.height()
        
        if split_pos is None:
            final_split_point = total_size // 2
        else:
            final_split_point = split_pos
            
        initial_sizes = [total_size, 0] if new_panel_index == 1 else [0, total_size]
        target_sizes = [final_split_point, total_size - final_split_point]
        
        # User said "se crea y no se mueve mas": 
        # Set final sizes immediately for manual release, skipping bounce
        new_splitter.setSizes(target_sizes)
        
        # Fade-In the content for the "birth" appearance
        opacity_effect = QGraphicsOpacityEffect(new_panel)
        new_panel.setGraphicsEffect(opacity_effect)
        fade_anim = QVariantAnimation(new_panel)
        fade_anim.setDuration(250)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.valueChanged.connect(opacity_effect.setOpacity)
        fade_anim.start()
        new_panel._fade_anim = fade_anim
        
        # 6. Fix registries for the newly created brother
        if hasattr(new_content, 'display_frame'):
            self._register_viewer(new_content)
        from .master_meter import MasterMeterPanel
        if isinstance(new_content, MasterMeterPanel):
            self._register_master_meter(new_content)
        self._register_timeline_from_widget(new_content)
        
        self.show()
        new_panel.show()
        new_splitter.show()
        return new_splitter

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
                splitter.setHandleWidth(4)
                splitter.setStyleSheet("""
                    QSplitter::handle {
                        background-color: #1a1a1a;
                        background-image: radial-gradient(circle, #444 1px, transparent 1.5px);
                        background-position: center;
                        background-repeat: repeat-y;
                    }
                    QSplitter::handle:horizontal {
                        background-repeat: repeat-y;
                    }
                    QSplitter::handle:vertical {
                        background-repeat: repeat-x;
                    }
                    QSplitter::handle:hover {
                        background-color: #ff9900;
                    }
                """)
                
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
