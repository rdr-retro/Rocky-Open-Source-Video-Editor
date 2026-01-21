"""
Simple Timeline Widget - Logic and Event Handling.
Rendering is delegated to TimelinePainter.
"""

from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRectF, QPointF, Property, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QPainter, QColor
from functools import partial
from ..styles import MENU_STYLE
from .timeline_painter import TimelinePainter

class SimpleTimeline(QWidget):
    """
    Ultra-simple timeline that is guaranteed to be visible.
    Handles user interaction and state. Rendering is done by TimelinePainter.
    """
    
    # Signals expected by rocky_ui.py
    time_updated = Signal(float, int, str, bool)
    structure_changed = Signal()
    view_updated = Signal()
    track_addition_requested = Signal(object)
    hover_x_changed = Signal(int)
    play_pause_requested = Signal()
    clip_proxy_toggled = Signal(object)
    clip_fx_toggled = Signal(object)
    selection_changed = Signal(list) # Emits list of selected TimelineClip objects
    
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._pixels_per_second = 100.0
        
        # Interaction state
        self.mouse_x = -1
        self.mouse_y = -1
        self.dragging_clip = None
        self.potential_drag_clip = None 
        self.potential_drag_start_pos = None 
        self.drag_start_x = 0
        self.drag_start_y = 0 
        self.drag_offset_x = 0
        self.drag_start_track = -1 
        self.selected_clips = []
        
        # Interaction Envelopes
        self.dragging_fade_in = False
        self.dragging_fade_out = False
        self.dragging_opacity = False 
        self.dragging_left_edge = False
        self.dragging_right_edge = False
        
        # Configure widget for visibility
        self.setMinimumSize(800, 400)
        self.setVisible(True)
        self.setEnabled(True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        
        # Force opaque painting
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAutoFillBackground(False)
        
        # Initialize Painter
        self.painter = TimelinePainter(self)
        
        # Repaint timer
        self.repaint_timer = QTimer(self)
        self.repaint_timer.timeout.connect(self.update)
        self.repaint_timer.start(16)  # 60 FPS
        
        # Animations
        self.zoom_anim = QPropertyAnimation(self, b"pixels_per_second")
        self.scroll_anim = None
        
        print("SimpleTimeline: Widget initialized with TimelinePainter", flush=True)

    def _handle_clip_click(self, event, clip):
        """Handle clicking directly on a clip (Selection, FX, PX)."""
        clip_x = self.frameToProjectedX(clip.start_frame)
        clip_w = self.frameToProjectedX(clip.duration_frames)
        track_y = self._get_track_y_positions()[clip.track_index]
        
        button_w, button_h, spacing = 14, 8, 2
        px_x = clip_x + clip_w - button_w - 4
        rect_px = QRectF(px_x, track_y + 2, button_w, button_h)
        rect_fx = QRectF(px_x - button_w - spacing, track_y + 2, button_w, button_h)
        
        if rect_fx.contains(event.position()):
            self.clip_fx_toggled.emit(clip)
            return
        if rect_px.contains(event.position()):
            self.clip_proxy_toggled.emit(clip)
            return

        if not (event.modifiers() & Qt.ShiftModifier):
            for c in self.model.clips: c.selected = False
        clip.selected = True
        
        self.potential_drag_clip = clip
        self.potential_drag_start_pos = event.position()
        self.drag_offset_x = event.x() - clip_x
        self.structure_changed.emit()
        self.selection_changed.emit([c for c in self.model.clips if c.selected])

    @Property(float)
    def pixels_per_second(self):
        return self._pixels_per_second

    @pixels_per_second.setter
    def pixels_per_second(self, value):
        self._pixels_per_second = value
        self.updateGeometry()
        self.view_updated.emit()
        self.update()

    @property
    def visible_start_time(self):
        """[VEGAS PRINCIPLE] Derived property for the exact time at viewport start."""
        scroll_area = self.get_scroll_area_context()
        if not scroll_area: return 0.0
        return self.screenXToTime(scroll_area.horizontalScrollBar().value())
        
    def calculate_adaptive_step(self, pps, fps):
        """
        [VEGAS PRINCIPLE] Quantitative Perceptual Constant.
        Chooses a human-friendly temporal step based on current zoom (PPS).
        """
        # Aim for 80-150 pixels between major ticks for clarity
        candidates = [
            1.0/fps, 2.0/fps, 5.0/fps, 10.0/fps, 15.0/fps, # Frames
            1.0, 2.0, 5.0, 10.0, 30.0,                     # Seconds
            60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0,     # Minutes / 1 Hour
            7200.0, 14400.0, 28800.0, 86400.0              # Hours / 1 Day
        ]
        
        chosen_step = candidates[-1]
        for s in candidates:
            if s * pps >= 100:
                chosen_step = s
                break
        
        # Subdivisions: 5 for most, 10 for frames/short seconds
        divs = 5
        if chosen_step <= 1.0 or chosen_step == 5.0 or chosen_step == 10.0: divs = 5 # or 10
        
        return chosen_step, divs
    
    def sizeHint(self):
        """Provide size based on timeline content."""
        max_frame = self.model.get_max_frame()
        if max_frame > 0:
            width = int((max_frame / self.get_fps()) * self.pixels_per_second) + 500  # Add padding
        else:
            width = 3000
        
        height = sum(self.model.track_heights) if self.model.track_heights else 600
        return QSize(max(width, 1200), max(height, 600))
    
    def minimumSizeHint(self):
        height = sum(self.model.track_heights) if self.model.track_heights else 400
        return QSize(800, max(height, 400))
    
    def paintEvent(self, event):
        """Delegate painting to TimelinePainter."""
        self.painter.paint(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press - select clips, move playhead, or EDIT ENVELOPES."""
        self.setFocus() 
        
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Check FADE/TRIM/OPACITY Hits
            if self._handle_interactive_element_click(event):
                return
            
            # 2. Selection/Playhead
            clip = self.find_clip_at(event.x(), event.y())
            if clip:
                self._handle_clip_click(event, clip)
            else:
                # Clear selection if clicking empty space (and not holding shift/ctrl if implemented later)
                for c in self.model.clips: c.selected = False
                self.selection_changed.emit([])
                self.update_playhead_to_x(event.x())
            self.update()
        else:
            super().mousePressEvent(event)
    
    def _handle_interactive_element_click(self, event):
        """Helper to check clicks on interactive elements (fades, opacity, trim)."""
        track_y_positions = self._get_track_y_positions()
        click_track_idx = -1
        
        for i, ty in enumerate(track_y_positions):
            th = self.model.track_heights[i]
            if ty <= event.y() < ty + th:
                click_track_idx = i
                break
        
        if click_track_idx != -1:
            track_h = self.model.track_heights[click_track_idx]
            click_track_y = track_y_positions[click_track_idx]
            
            for clip in self.model.clips:
                if clip.track_index == click_track_idx:
                    if self._check_clip_interactions(event, clip, click_track_y, track_h):
                        return True
        return False

    def _check_clip_interactions(self, event, clip, track_y, track_h):
        """Detailed check for clip interaction points."""
        clip_x = self.frameToProjectedX(clip.start_frame)
        clip_w = self.frameToProjectedX(clip.duration_frames)
        body_top_y = track_y + 13
        
        # Fade Handles
        if (clip_x <= event.x() <= clip_x + 6 and body_top_y <= event.y() <= body_top_y + 6):
            self.dragging_clip, self.dragging_fade_in = clip, True
            self.structure_changed.emit()
            return True
        if (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and body_top_y <= event.y() <= body_top_y + 6):
            self.dragging_clip, self.dragging_fade_out = clip, True
            self.structure_changed.emit()
            return True

        # Trim Edges
        edge_margin = 8
        if (abs(event.x() - clip_x) <= edge_margin and track_y <= event.y() <= track_y + track_h):
            self.dragging_clip, self.dragging_left_edge = clip, True
            return True
        if (abs(event.x() - (clip_x + clip_w)) <= edge_margin and track_y <= event.y() <= track_y + track_h):
            self.dragging_clip, self.dragging_right_edge = clip, True
            return True
            
        # Opacity Handle
        opacity_level = getattr(clip, 'opacity_level', 1.0)
        level_y = body_top_y + (1.0 - opacity_level) * (track_y + track_h - 1 - body_top_y)
        if (clip_x <= event.x() <= clip_x + clip_w) and (abs(event.y() - level_y) <= 5 or (abs(event.y() - body_top_y) <= 5 and opacity_level > 0.95)):
            self.dragging_clip, self.dragging_opacity = clip, True
            self.structure_changed.emit()
            return True
        
        return False

    def _handle_clip_click(self, event, clip):
        """Handle clicking directly on a clip (Selection, FX, PX)."""
        clip_x = self.frameToProjectedX(clip.start_frame)
        clip_w = self.frameToProjectedX(clip.duration_frames)
        track_y = self._get_track_y_positions()[clip.track_index]
        
        button_w, button_h, spacing = 14, 8, 2
        px_x = clip_x + clip_w - button_w - 4
        rect_px = QRectF(px_x, track_y + 2, button_w, button_h)
        rect_fx = QRectF(px_x - button_w - spacing, track_y + 2, button_w, button_h)
        
        if rect_fx.contains(event.position()):
            self.clip_fx_toggled.emit(clip)
            return
        if rect_px.contains(event.position()):
            self.clip_proxy_toggled.emit(clip)
            return

        if not (event.modifiers() & Qt.ShiftModifier):
            for c in self.model.clips: c.selected = False
        clip.selected = True
        
        self.potential_drag_clip = clip
        self.potential_drag_start_pos = event.position()
        self.drag_offset_x = event.x() - clip_x
        self.structure_changed.emit()

    def mouseMoveEvent(self, event):
        """Handle mouse move - drag clips, update hover, SCRUB PLAYHEAD, or DRAG FADES."""
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        self.hover_x_changed.emit(self.mouse_x)
        
        # Update cursor based on hover
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            self._update_cursor_on_hover(event)
        
        # Handle Dragging
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._handle_mouse_drag(event)
        
        self.update()

    def _update_cursor_on_hover(self, event):
        """Updates cursor icon based on what's under the mouse."""
        cursor_set = False
        track_y_positions = self._get_track_y_positions()
        
        hover_track_idx = -1
        hover_track_y = 0
        
        # Find track under mouse
        for i, ty in enumerate(track_y_positions):
            if i >= len(self.model.track_heights): break
            h = self.model.track_heights[i]
            if ty <= event.y() < ty + h:
                hover_track_idx = i
                hover_track_y = ty
                break
        
        if hover_track_idx != -1:
            for clip in self.model.clips:
                if clip.track_index == hover_track_idx:
                    clip_x = self.frameToProjectedX(clip.start_frame)
                    clip_w = self.frameToProjectedX(clip.duration_frames)
                    body_top_y = hover_track_y + 13
                    
                    # Check handles
                    if ((clip_x <= event.x() <= clip_x + 6 and body_top_y <= event.y() <= body_top_y + 6) or
                        (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and body_top_y <= event.y() <= body_top_y + 6)):
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                        cursor_set = True
                        break
        
                    # Check edges for Trim
                    edge_margin = 8
                    is_near_edge = abs(event.x() - clip_x) <= edge_margin or abs(event.x() - (clip_x + clip_w)) <= edge_margin
                    
                    track_h = self.model.track_heights[clip.track_index]
                    if is_near_edge and (hover_track_y <= event.y() <= hover_track_y + track_h):
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                        cursor_set = True
                        break

                    # Check Opacity/Gain Handle
                    opacity_level = getattr(clip, 'opacity_level', 1.0)
                    clip_h = track_h - 2
                    body_start_y = hover_track_y + 13
                    body_end_y = hover_track_y + 1 + clip_h
                    body_height = body_end_y - body_start_y
                    level_y = body_start_y + (1.0 - opacity_level) * body_height
                    
                    if (clip_x <= event.x() <= clip_x + clip_w) and (abs(event.y() - level_y) <= 5 or (abs(event.y() - body_start_y) <= 5 and opacity_level > 0.95)):
                            self.setCursor(Qt.CursorShape.PointingHandCursor)
                            cursor_set = True
                            break
        
        if not cursor_set:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _handle_mouse_drag(self, event):
        """Processes all dragging operations."""
        # 0. Handle Trim Edges
        if self.dragging_right_edge and self.dragging_clip:
            self._drag_trim_right(event)
            return

        if self.dragging_left_edge and self.dragging_clip:
            self._drag_trim_left(event)
            return

        # Check Drag Threshold
        if self.potential_drag_clip and self.potential_drag_start_pos:
            dist = (event.position() - self.potential_drag_start_pos).manhattanLength()
            if dist > 5:
                self.dragging_clip = self.potential_drag_clip
                self.potential_drag_clip = None
                self.potential_drag_start_pos = None
        
        # Handle Opacity Drag
        if self.dragging_opacity and self.dragging_clip:
            self._drag_opacity(event)
            return

        # Handle Fade Drag
        if self.dragging_fade_in and self.dragging_clip:
            self._drag_fade_in(event)
            return

        if self.dragging_fade_out and self.dragging_clip:
            self._drag_fade_out(event)
            return

        # Handle Clip Move
        if self.dragging_clip:
            self._drag_clip_move(event)
        elif not self.potential_drag_clip:
            # Scrub Playhead
            self.update_playhead_to_x(event.x())

    def _drag_trim_right(self, event):
        clip = self.dragging_clip
        target_frame = self.screenXToFrame(event.x())
        new_duration = int(target_frame - clip.start_frame)
        new_duration = max(5, new_duration)
        
        if clip.source_duration_frames > 0:
            max_d = clip.source_duration_frames - getattr(clip, 'source_offset_frames', 0)
            new_duration = min(new_duration, max_d)
        
        clip.duration_frames = new_duration
        self.structure_changed.emit()

    def _drag_trim_left(self, event):
        clip = self.dragging_clip
        orig_end = clip.start_frame + clip.duration_frames
        target_start = self.screenXToFrame(event.x())
        
        target_start = max(0, min(target_start, orig_end - 5))
        delta_frames = int(target_start - clip.start_frame)
        
        if clip.source_duration_frames > 0:
            current_offset = getattr(clip, 'source_offset_frames', 0)
            if current_offset + delta_frames < 0:
                delta_frames = -current_offset
                target_start = clip.start_frame + delta_frames
        
        clip.start_frame = int(target_start)
        clip.duration_frames -= delta_frames
        clip.source_offset_frames = getattr(clip, 'source_offset_frames', 0) + delta_frames
        self.structure_changed.emit()

    def _drag_opacity(self, event):
        clip = self.dragging_clip
        track_y = self._get_track_y_positions()[clip.track_index]
        track_h = self.model.track_heights[clip.track_index]
        clip_h = track_h - 2
        body_start_y = track_y + 13
        body_end_y = track_y + 1 + clip_h
        body_height = max(1, body_end_y - body_start_y)
        
        rel_y = event.y() - body_start_y
        new_opacity = 1.0 - (rel_y / body_height)
        clip.opacity_level = max(0.0, min(1.0, new_opacity))
        self.update() # Visual only

    def _drag_fade_in(self, event):
        clip = self.dragging_clip
        new_frames = self.screenXToFrame(event.x()) - clip.start_frame
        clip.fade_in_frames = max(0, min(clip.duration_frames, int(new_frames)))
        self.update()

    def _drag_fade_out(self, event):
        clip = self.dragging_clip
        clip_end_x = self.frameToProjectedX(clip.start_frame + clip.duration_frames)
        dist_frames = self.screenXToFrame(clip_end_x) - self.screenXToFrame(event.x())
        clip.fade_out_frames = max(0, min(clip.duration_frames, int(dist_frames)))
        self.update()

    def _drag_clip_move(self, event):
        new_x = event.x() - self.drag_offset_x
        new_frame = max(0, int(self.screenXToFrame(new_x)))
        self.dragging_clip.start_frame = new_frame
        
        # Track detection
        track_y_positions = self._get_track_y_positions()
        target_track = -1
        for i, track_y in enumerate(track_y_positions):
            if i < len(self.model.track_heights):
                track_h = self.model.track_heights[i]
                if track_y <= event.y() < track_y + track_h:
                    target_track = i
                    break
        
        if target_track != -1 and target_track != self.dragging_clip.track_index:
            self.dragging_clip.track_index = target_track
        
        self.structure_changed.emit()

    def mouseDoubleClickEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        """Handle mouse release and Auto-Crossfade logic."""
        dropped_clip = self.dragging_clip
        was_dragging_fade = self.dragging_fade_in or self.dragging_fade_out
        
        self.dragging_envelope = False
        self.dragging_fade_in = False   
        self.dragging_fade_out = False  
        self.dragging_opacity = False   
        self.dragging_left_edge = False
        self.dragging_right_edge = False
        
        self.potential_drag_clip = None
        self.potential_drag_start_pos = None
        
        if self.dragging_clip:
            self.dragging_clip = None
            self.structure_changed.emit()

        if dropped_clip and not was_dragging_fade:
            self._handle_auto_crossfade(dropped_clip)

        self.update()

    def _handle_auto_crossfade(self, dropped_clip):
        """Check for clip overlaps and apply crossfades."""
        track_clips = [c for c in self.model.clips if c.track_index == dropped_clip.track_index and c != dropped_clip]
        
        for other in track_clips:
            start_a = dropped_clip.start_frame
            end_a = dropped_clip.start_frame + dropped_clip.duration_frames
            start_b = other.start_frame
            end_b = other.start_frame + other.duration_frames
            
            if start_a < end_b and end_a > start_b:
                 intersect_start = max(start_a, start_b)
                 intersect_end = min(end_a, end_b)
                 overlap = max(0, intersect_end - intersect_start)
            
                 if overlap > 0:
                    if start_a > start_b:
                        other.fade_out_frames = overlap
                        dropped_clip.fade_in_frames = overlap
                        print(f"Auto-Crossfade: {overlap} frames")
                    elif start_a < start_b:
                        dropped_clip.fade_out_frames = overlap
                        other.fade_in_frames = overlap
                        print(f"Auto-Crossfade: {overlap} frames")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Space:
            self.play_pause_requested.emit()
        elif event.key() == Qt.Key_Left:
            new_frame = max(0, self.model.blueline.playhead_frame - 1)
            self.update_playhead_position(new_frame)
        elif event.key() == Qt.Key_Right:
            new_frame = self.model.blueline.playhead_frame + 1
            self.update_playhead_position(new_frame)
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_clip(None)
        elif event.key() == Qt.Key_Up:
            self.pixels_per_second = min(500, self.pixels_per_second * 1.2)
        elif event.key() == Qt.Key_Down:
            self.pixels_per_second = max(10, self.pixels_per_second / 1.2)
        
        self.update()
    
    def wheelEvent(self, event):
        """[VEGAS PRINCIPLE] Deterministic Zoom focused on absolute anchor time."""
        if event.modifiers() & Qt.ControlModifier:
            scroll_area = self.get_scroll_area_context()
            if not scroll_area: return
            h_scroll = scroll_area.horizontalScrollBar()
            
            mouse_abs_x = event.position().x()
            anchor_time = self.screenXToTime(mouse_abs_x)
            viewport_offset = mouse_abs_x - h_scroll.value()
            
            delta = event.angleDelta().y()
            zoom_factor = 1.15 if delta > 0 else (1.0 / 1.15)
            self.pixels_per_second = max(0.1, min(8000, self.pixels_per_second * zoom_factor))
            
            self.updateGeometry()
            self.setFixedSize(self.sizeHint())
            
            new_scroll_val = int(self.timeToProjectedX(anchor_time) - viewport_offset)
            h_scroll.setValue(max(0, new_scroll_val))
            
            self.view_updated.emit()
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-rocky-effect"):
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle file drops and EFFECT drops."""
        if event.mimeData().hasFormat("application/x-rocky-effect"):
            self._handle_effect_drop(event)
            event.accept()
            return

        urls = event.mimeData().urls()
        if not urls: return
        
        start_frame = int(self.screenXToFrame(event.pos().x()))
        track_idx = -1
        current_y = 0
        for i, height in enumerate(self.model.track_heights):
            if current_y <= event.pos().y() < current_y + height:
                track_idx = i
                break
            current_y += height
        
        app = self.window()
        if hasattr(app, "import_media"):
            for url in urls:
                path = url.toLocalFile()
                if path:
                    app.import_media(path, start_frame, track_idx)
                    start_frame += 150
        self.update()

    def _handle_effect_drop(self, event):
        data = event.mimeData().data("application/x-rocky-effect")
        data_str = data.data().decode('utf-8')
        if "|" in data_str:
            name, path = data_str.split("|", 1)
            clip = self.find_clip_at(event.pos().x(), event.pos().y())
            if clip:
                    print(f"Applying Effect '{name}' to Clip '{clip.name}'")
                    new_effect = {
                        "name": name,
                        "path": path,
                        "enabled": True
                    }
                    clip.effects.append(new_effect)
                    self.structure_changed.emit()
                    self.update()

    def get_fps(self):
        return 30.0

    def _get_track_y_positions(self):
        positions = []
        current_y = 0
        for height in self.model.track_heights:
            positions.append(current_y)
            current_y += height
        return positions
    
    def find_clip_at(self, x, y):
        """[VEGAS PRINCIPLE] Precision Hit-Testing."""
        track_y_positions = self._get_track_y_positions()
        
        track_idx = -1
        TOLERANCE_Y = 2
        for i, track_y in enumerate(track_y_positions):
            if i < len(self.model.track_heights):
                track_h = self.model.track_heights[i]
                if track_y - TOLERANCE_Y <= y < track_y + track_h + TOLERANCE_Y:
                    track_idx = i
                    break
        
        if track_idx == -1: return None
        
        TOLERANCE_X = 2
        for clip in self.model.clips:
            if clip.track_index == track_idx:
                clip_x = self.frameToProjectedX(clip.start_frame)
                clip_w = self.frameToProjectedX(clip.duration_frames)
                if clip_x - TOLERANCE_X <= x <= clip_x + clip_w + TOLERANCE_X:
                    return clip
        
        return None
    
    def timeToProjectedX(self, time_seconds):
        return time_seconds * self.pixels_per_second

    def frameToProjectedX(self, frame_index):
        return (frame_index / self.get_fps()) * self.pixels_per_second

    def screenXToTime(self, screen_x):
        return screen_x / self.pixels_per_second

    def screenXToFrame(self, screen_x):
        return (screen_x / self.pixels_per_second) * self.get_fps()

    def timeToScreen(self, time_in_seconds):
        """DEPRECATED: Use timeToProjectedX for clarity."""
        return self.timeToProjectedX(time_in_seconds)

    def frameToScreen(self, frame_index):
        """DEPRECATED: Use frameToProjectedX for clarity."""
        return self.frameToProjectedX(frame_index)

    def update_playhead_to_x(self, screen_x):
        time_seconds = max(0, self.screenXToTime(screen_x))
        frame = time_seconds * self.get_fps()
        self.update_playhead_position(frame, forced=True)
    
    def update_playhead_position(self, frame_index, forced=True):
        self.model.blueline.set_playhead_frame(frame_index)
        time_seconds = frame_index / self.get_fps()
        tc = self.model.format_timecode(frame_index, self.get_fps())
        self.time_updated.emit(time_seconds, int(frame_index), tc, forced)
        self.update()
        return self.frameToProjectedX(frame_index)
    
    def get_scroll_area_context(self):
        from PySide6.QtWidgets import QScrollArea
        current = self.parent()
        while current:
            if isinstance(current, QScrollArea):
                return current
            current = current.parent()
        return None
    
    def contextMenuEvent(self, event):
        self.show_context_menu(event.pos())
        event.accept()

    def show_context_menu(self, pos):
        """Show context menu for clips (Right Click)."""
        from ..models import FadeType, TrackType
        
        if hasattr(pos, 'toPoint'): pos = pos.toPoint()
        clip = self.find_clip_at(pos.x(), pos.y())
        
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        
        if not clip:
            menu.addAction("Añadir pista de vídeo").triggered.connect(lambda: self.track_addition_requested.emit(TrackType.VIDEO))
            menu.addAction("Añadir pista de audio").triggered.connect(lambda: self.track_addition_requested.emit(TrackType.AUDIO))
            menu.addAction("Zoom to Fit").triggered.connect(self.zoom_to_fit)
            menu.exec(self.mapToGlobal(pos))
            return

        if not clip.selected:
            for c in self.model.clips: c.selected = False
            clip.selected = True
            self.structure_changed.emit()
            self.update()
        
        # Fade Region Detection
        clip_x = self.frameToProjectedX(clip.start_frame)
        clip_w = self.frameToProjectedX(clip.duration_frames)
        rel_x = pos.x() - clip_x
        
        fade_in_w = self.frameToProjectedX(clip.fade_in_frames)
        is_fade_in = 0 <= rel_x <= fade_in_w and fade_in_w > 0
        
        fade_out_w = self.frameToProjectedX(clip.fade_out_frames)
        is_fade_out = (clip_w - fade_out_w) <= rel_x <= clip_w and fade_out_w > 0
        
        if is_fade_in or is_fade_out:
            self._add_fade_menu(menu, clip, is_fade_in)
            menu.addSeparator()

        menu.addAction("Eliminar").triggered.connect(partial(self.delete_clip, clip))
        menu.addAction("Dividir").triggered.connect(partial(self.split_clip_at_pos, clip, pos))
        menu.exec(self.mapToGlobal(pos))
        
    def _add_fade_menu(self, menu, clip, is_fade_in):
        from ..models import FadeType
        from PySide6.QtGui import QActionGroup
        
        fade_menu = menu.addMenu("Fade Type")
        fade_options = [(FadeType.LINEAR, "Linear"), (FadeType.FAST, "Fast"), (FadeType.SLOW, "Slow"), (FadeType.SMOOTH, "S-Curve")]
        group = QActionGroup(fade_menu)
        for f_type, f_name in fade_options:
            action = fade_menu.addAction(f_name)
            action.setCheckable(True)
            group.addAction(action)
            if (clip.fade_in_type if is_fade_in else clip.fade_out_type) == f_type:
                action.setChecked(True)
            def set_curve(checked, t=f_type, is_in=is_fade_in):
                if checked:
                    if is_in: clip.fade_in_type = t
                    else: clip.fade_out_type = t
                    self.structure_changed.emit()
                    self.update()
            action.triggered.connect(set_curve)

    def delete_clip(self, clip=None):
        targets = set()
        if clip:
            if clip.selected:
                for c in self.model.clips:
                    if c.selected: targets.add(c)
            targets.add(clip)
        else:
            for c in self.model.clips:
                if c.selected: targets.add(c)
        
        for c in list(targets):
            if c.linked_to and c.linked_to in self.model.clips:
                targets.add(c.linked_to)

        for c in targets:
            if c in self.model.clips:
                self.model.remove_clip(c)
                
        self.structure_changed.emit()
        self.updateGeometry()
        self.update()

    def split_clip_at_pos(self, clip, pos):
        if not clip: return
        split_frame = self.screenXToFrame(pos.x())
        self.split_clip(clip, split_frame)

    def split_clip(self, clip, split_frame):
        if not clip or split_frame <= clip.start_frame or split_frame >= (clip.start_frame + clip.duration_frames):
            return
        offset = int(split_frame - clip.start_frame)
        if offset < 2 or (clip.duration_frames - offset) < 2: return
        
        new_clip = clip.copy()
        clip.duration_frames = offset
        if clip.fade_out_frames > clip.duration_frames: clip.fade_out_frames = clip.duration_frames
        
        new_clip.start_frame = clip.start_frame + offset
        new_clip.duration_frames -= offset
        new_clip.source_offset_frames += offset
        if new_clip.fade_in_frames > new_clip.duration_frames: new_clip.fade_in_frames = new_clip.duration_frames
        
        for c in self.model.clips: c.selected = False
        new_clip.selected = True
        self.model.add_clip(new_clip)
        self.structure_changed.emit()
        self.update()

    def zoom_to_fit(self, animate=True):
        max_frame = self.model.get_max_frame()
        if max_frame <= 0: return
        
        scroll_area = self.get_scroll_area_context()
        if scroll_area:
            viewport_width = scroll_area.viewport().width()
            h_scroll = scroll_area.horizontalScrollBar()
        else:
            viewport_width = self.width()
            h_scroll = None
        
        fps = self.get_fps()
        duration_seconds = max_frame / fps
        if duration_seconds > 0:
            target_pps = (viewport_width * 0.1) / duration_seconds
            target_pps = max(10, min(500, target_pps))
            
            if animate:
                self.zoom_anim.stop()
                self.zoom_anim.setDuration(800)
                self.zoom_anim.setStartValue(self.pixels_per_second)
                self.zoom_anim.setEndValue(target_pps)
                self.zoom_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                
                if h_scroll:
                    self.scroll_anim = QPropertyAnimation(h_scroll, b"value")
                    self.scroll_anim.setDuration(800)
                    self.scroll_anim.setStartValue(h_scroll.value())
                    self.scroll_anim.setEndValue(0)
                    self.scroll_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                    
                    self.group = QParallelAnimationGroup()
                    self.group.addAnimation(self.zoom_anim)
                    self.group.addAnimation(self.scroll_anim)
                    self.group.start()
                else:
                    self.zoom_anim.start()
            else:
                self.pixels_per_second = target_pps
                if h_scroll: h_scroll.setValue(0)
                self.updateGeometry()
                self.update()
                self.view_updated.emit()
