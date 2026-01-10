import math
from PyQt5.QtWidgets import QWidget, QScrollArea
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QBrush, QImage

from ..models import TimelineClip, TrackType, FadeType
from .constants import *
from .renderer import TimelineRenderer
from .interactions import TimelineInteractions

class TimelinePanel(QWidget, TimelineRenderer, TimelineInteractions):
    """
    Core interactive timeline component. 
    Handles clip manipulation, visual rendering of tracks, and temporal navigation.
    """
    time_updated = pyqtSignal(float, int, str, bool)
    structure_changed = pyqtSignal()
    view_updated = pyqtSignal()
    track_addition_requested = pyqtSignal(object)
    hover_x_changed = pyqtSignal(int)
    play_pause_requested = pyqtSignal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._initialize_view_state()
        self._initialize_design_system()
        self._configure_widget_behavior()
        
    def _initialize_view_state(self):
        self.pixels_per_second = 100.0
        self.visible_start_time = 0.0
        self.mouse_x = -1
        self.mouse_y = -1
        self.active_clip = None
        self.active_rolling_clip = None
        self.interaction_mode = MODE_IDLE
        self.ripple_enabled = True
        self.snapping_enabled = True
        self.drag_start_x = 0
        self.original_start = 0
        self.original_duration = 0
        self.original_fade_in = 0
        self.original_fade_out = 0
        self.original_start_opacity = 1.0
        self.original_end_opacity = 1.0
        self.interaction_start_y = 0
        self.active_node_idx = -1
        self.press_track_y = 0
        self.press_track_h = 0
        
    def _initialize_design_system(self):
        self._stipple_brush = self._create_stipple_brush()

    def _configure_widget_behavior(self):
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.repaint_timer = QTimer(self)
        self.repaint_timer.timeout.connect(self.update)
        self.repaint_timer.start(16)
        self.zoom_animation = None
        
    def zoom_to_fit(self):
        max_frame = self.model.get_max_frame()
        
        # Get actual visible width (viewport), not the potentially huge canvas width
        viewport_width = self.parent().width() if self.parent() else self.width()
        
        if max_frame <= 0 or viewport_width <= 0: return
        
        project_duration = max_frame / self.get_fps()
        
        # Calculate PPS to fit duration into 50% of the visible area
        target_pps = (viewport_width * 0.50) / max(1.0, project_duration)
        target_pps = max(0.5, min(5000.0, target_pps))
        
        # Determine start PPS (current)
        start_pps = self.pixels_per_second
        
        from PyQt5.QtCore import QVariantAnimation, QEasingCurve
        self.zoom_animation = QVariantAnimation()
        self.zoom_animation.setDuration(800) # Slightly slower for cinematic feel
        self.zoom_animation.setStartValue(0.0)
        self.zoom_animation.setEndValue(1.0)
        self.zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        def anim_step(progress):
            # Lerp PPS
            self.pixels_per_second = start_pps + (target_pps - start_pps) * progress
            self.updateGeometry()
            
            # Identify scroll context
            scroll_area = self.get_scroll_area_context()
            if scroll_area:
                # Interpolate scrollbar value -> 0
                current_scroll = scroll_area.horizontalScrollBar().value()
                if current_scroll > 0:
                     scroll_area.horizontalScrollBar().setValue(int(current_scroll * (1.0 - progress)))
                     
            self.view_updated.emit()
            self.update()
            
        self.zoom_animation.valueChanged.connect(anim_step)
        self.zoom_animation.start()

    def _on_zoom_anim_update(self, value):
        # Legacy/Unused now since we defined inline, but could be kept if needed or removed.
        # Replacing the whole block so we can implement the inline step 
        pass

    def mouseDoubleClickEvent(self, event):
        target_clip = self.find_clip_at(event.x(), event.y())
        if target_clip:
            self._add_gain_node_at_screen_pos(target_clip, event.x())
        else:
            self.zoom_to_fit()

    def _add_gain_node_at_screen_pos(self, clip, screen_x):
        clip_x = self.timeToScreen(clip.start_frame / self.get_fps())
        frame_offset = int((screen_x - clip_x) / self.pixels_per_second * self.get_fps())
        clip.opacity_nodes.append([frame_offset, 1.0, 1])
        self.update()

    def sizeHint(self):
        h = sum(self.model.track_heights) + 2000
        w = int((self.model.get_max_frame() / self.get_fps() + 20) * self.pixels_per_second)
        return QSize(max(1000, w), h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def _create_stipple_brush(self):
        img = QImage(3, 3, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        painter = self.create_painter_on_image(img)
        painter.setPen(QColor(0, 0, 0, 80))
        painter.drawPoint(1, 1)
        painter.end()
        return QBrush(img)
    
    def create_painter_on_image(self, img):
        from PyQt5.QtGui import QPainter
        return QPainter(img)

    def get_fps(self) -> float:
        return 30.0

    def timeToScreen(self, time_in_seconds: float) -> int:
        return int(round(time_in_seconds * self.pixels_per_second))

    def screenToTime(self, pixel_x: int) -> float:
        scale_factor = float(self.pixels_per_second if self.pixels_per_second > 0 else 1)
        return pixel_x / scale_factor

    def find_snap_frame(self, target_frame: int, exclude_clip=None) -> int:
        if not self.snapping_enabled: return -1
        threshold_pixels = 12
        threshold_seconds = threshold_pixels / self.pixels_per_second
        threshold_frames = threshold_seconds * self.get_fps()
        closest_snap = -1
        min_delta = threshold_frames + 0.1
        candidates = [0, self.model.blueline.playhead_frame]
        for clip in self.model.clips:
            if clip == exclude_clip: continue
            candidates.append(clip.start_frame)
            candidates.append(clip.start_frame + clip.duration_frames)
        for cand in candidates:
            delta = abs(target_frame - cand)
            if delta < min_delta:
                min_delta = delta
                closest_snap = cand
        return closest_snap if min_delta <= threshold_frames else -1

    def _get_track_vertical_offsets(self):
        offsets = []
        current_y = 0
        for height in self.model.track_heights:
            offsets.append(current_y)
            current_y += height
        return offsets

    def get_scroll_area_context(self):
        current_node = self.parent()
        while current_node:
            if isinstance(current_node, QScrollArea): return current_node
            current_node = current_node.parent()
        return None

    def interpolate_fade(self, progression: float, fade_type: FadeType) -> float:
        t = max(0.0, min(1.0, progression))
        if fade_type == FadeType.FAST:   return t * t
        if fade_type == FadeType.SLOW:   return 1.0 - (1.0 - t)**2
        if fade_type == FadeType.SMOOTH: return t * t * (3.0 - 2.0 * t)
        if fade_type == FadeType.SHARP:  return t**3
        return t

    def update_cursor_state(self, event):
        interaction_type, _ = self.query_interaction_at(event.x(), event.y())
        if interaction_type == MODE_MOVE: self.setCursor(Qt.SizeAllCursor)
        elif interaction_type in [MODE_TRIM_LEFT, MODE_TRIM_RIGHT]: self.setCursor(Qt.SizeHorCursor)
        elif interaction_type == MODE_GAIN: self.setCursor(Qt.PointingHandCursor)
        elif interaction_type in [MODE_FADE_IN, MODE_FADE_OUT]: self.setCursor(Qt.SizeBDiagCursor)
        elif interaction_type == MODE_ROLL_EDIT: self.setCursor(Qt.SplitHCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _find_clip_ending_at(self, frame, track_idx):
        for clip in self.model.clips:
            if clip.track_index == track_idx and abs(clip.start_frame + clip.duration_frames - frame) <= 2:
                return clip
        return None

    def _find_clip_starting_at(self, frame, track_idx):
        for clip in self.model.clips:
            if clip.track_index == track_idx and abs(clip.start_frame - frame) <= 2:
                return clip
        return None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls: return
        drop_time = self.screenToTime(event.pos().x())
        start_frame = max(0, int(drop_time * self.get_fps()))
        
        # Búsqueda de pista destino por posición Y
        track_idx = -1
        curr_y = 0
        for i, h in enumerate(self.model.track_heights):
            if curr_y <= event.pos().y() < curr_y + h:
                track_idx = i
                break
            curr_y += h
            
        # Delegar la importación al CORE de la aplicación para consistencia
        app = self.window()
        if not hasattr(app, "import_media"):
            return # Fallback de seguridad
            
        for url in urls:
            path = url.toLocalFile()
            if not path: continue
            
            # Snap support
            snapped = self.find_snap_frame(start_frame)
            if snapped != -1: start_frame = snapped
            
            # Importación centralizada - ahora devuelve la duración usada
            duration = app.import_media(path, start_frame, track_idx)
            start_frame += duration
            
        self.update()

    def contextMenuEvent(self, event):
        clip = self.find_clip_at(event.x(), event.y())
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        if clip:
            mode, _ = self.query_interaction_at(event.x(), event.y())
            if mode in [MODE_FADE_IN, MODE_FADE_OUT]:
                fade_menu = menu.addMenu("Tipo de curva de desvanecimiento")
                types = [("Lineal", FadeType.LINEAR), ("Rápida", FadeType.FAST), ("Lenta", FadeType.SLOW), ("Suave", FadeType.SMOOTH), ("Brusca", FadeType.SHARP)]
                for name, ftype in types:
                    act = fade_menu.addAction(name)
                    def set_f(ft=ftype, m=mode, c=clip):
                        if m == 7: c.fade_in_type = ft
                        else: c.fade_out_type = ft
                        self.update()
                    act.triggered.connect(set_f)
                menu.exec_(event.globalPos())
                return
            menu.addAction("Eliminar").triggered.connect(lambda: self._remove_clip(clip))
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        mods = event.modifiers()
        if (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier):
            if event.key() == Qt.Key_Up: self._change_all_track_heights(10); return
            elif event.key() == Qt.Key_Down: self._change_all_track_heights(-10); return
        if event.key() == Qt.Key_Up: self._zoom_horizontal(1.2); return
        elif event.key() == Qt.Key_Down: self._zoom_horizontal(0.8); return
        if event.key() == Qt.Key_Left:
            new_f = max(0, self.model.blueline.playhead_frame - 1)
            self.model.blueline.set_playhead_frame(new_f)
            self.time_updated.emit(new_f/self.get_fps(), new_f, self.model.format_timecode(new_f, self.get_fps()), True)
            self.update(); return
        elif event.key() == Qt.Key_Right:
            new_f = self.model.blueline.playhead_frame + 1
            self.model.blueline.set_playhead_frame(new_f)
            self.time_updated.emit(new_f/self.get_fps(), new_f, self.model.format_timecode(new_f, self.get_fps()), True)
            self.update(); return
        elif event.key() == Qt.Key_Space: self.play_pause_requested.emit(); return
        elif event.key() == Qt.Key_Escape: self.update_playhead_to_x(0); return
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            to_remove = [c for c in self.model.clips if c.selected]
            for c in to_remove: self.model.remove_clip(c)
            if to_remove: self.structure_changed.emit(); self.update()

    def _change_all_track_heights(self, delta):
        for i in range(len(self.model.track_heights)):
            self.model.track_heights[i] = max(20, self.model.track_heights[i] + delta)
        self.structure_changed.emit()
        self.updateGeometry()
        self.update()

    def _zoom_horizontal(self, factor, center_on_mouse=False):
        scroll_area = self.get_scroll_area_context()
        if center_on_mouse and self.mouse_x >= 0:
            anchor_time = self.screenToTime(self.mouse_x)
            view_anchor_px = self.mouse_x - (scroll_area.horizontalScrollBar().value() if scroll_area else 0)
        else:
            anchor_time = self.model.blueline.playhead_frame / self.get_fps()
            view_anchor_px = self.timeToScreen(anchor_time) - (scroll_area.horizontalScrollBar().value() if scroll_area else 0)
        self.pixels_per_second = max(0.5, min(5000, self.pixels_per_second * factor))
        self.updateGeometry()
        new_abs_x = self.timeToScreen(anchor_time)
        new_scroll_value = new_abs_x - view_anchor_px
        if scroll_area: scroll_area.horizontalScrollBar().setValue(int(new_scroll_value))
        self.view_updated.emit()
        self.update()

    def _remove_clip(self, clip):
        track_idx, start_f, dur_f = clip.track_index, clip.start_frame, clip.duration_frames
        self.model.remove_clip(clip)
        if self.ripple_enabled:
            for c in self.model.clips:
                if c.track_index == track_idx and c.start_frame > start_f: c.start_frame -= dur_f
        self.update()
        self.structure_changed.emit()

    def _split_clip(self, clip, frame):
        offset = frame - clip.start_frame
        right = clip.copy()
        right.start_frame = frame
        right.duration_frames = clip.duration_frames - offset
        clip.duration_frames = offset
        self.model.add_clip(right)
        self.update()
        self.structure_changed.emit()

    def find_clip_at(self, x: int, y: int) -> TimelineClip:
        current_y = 0
        for track_idx, track_h in enumerate(self.model.track_heights):
            if current_y <= y < current_y + track_h:
                for clip in self.model.clips:
                    if clip.track_index == track_idx:
                        clip_x = self.timeToScreen(clip.start_frame / self.get_fps())
                        clip_w = int(clip.duration_frames / self.get_fps() * self.pixels_per_second)
                        if clip_x <= x <= clip_x + clip_w: return clip
            current_y += track_h
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton: self._initiate_panning(event); return
        if event.button() == Qt.LeftButton:
            interaction_type, target_clip = self.query_interaction_at(event.x(), event.y(), event.modifiers())
            if interaction_type != MODE_IDLE and target_clip:
                self._record_interaction_start(event, target_clip, interaction_type)
                self._update_selection_state(event, target_clip)
            else: self.update_playhead_to_x(event.x())
        self.update()

    def _initiate_panning(self, event):
        self.interaction_mode = MODE_PANNING
        self.drag_start_x = event.x()
        self.interaction_start_y = event.y()
        self.setCursor(Qt.ClosedHandCursor)

    def _record_interaction_start(self, event, clip, mode):
        self.active_clip = clip
        self.interaction_mode = mode
        self.drag_start_x = event.x()
        self.interaction_start_y = event.y()
        self.original_start = clip.start_frame
        self.original_duration = clip.duration_frames
        self.original_fade_in = clip.fade_in_frames
        self.original_fade_out = clip.fade_out_frames
        self.original_start_opacity = clip.start_opacity
        self.original_end_opacity = clip.end_opacity
        track_y = 0
        for height in self.model.track_heights:
            if track_y <= event.y() < track_y + height:
                self.press_track_y, self.press_track_h = track_y, height; break
            track_y += height
        if mode == MODE_ROLL_EDIT:
            self.active_rolling_clip = self._find_clip_starting_at(clip.start_frame + clip.duration_frames, clip.track_index)

    def _update_selection_state(self, event, target_clip):
        is_shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)
        if not is_shift_pressed:
            for clip in self.model.clips: clip.selected = False
        target_clip.selected = True

    def update_playhead_to_x(self, screen_x):
        fps = self.get_fps()
        timestamp = self.screenToTime(screen_x)
        frame_idx = max(0, int(timestamp * fps))
        self.model.blueline.set_playhead_frame(frame_idx)
        timecode_str = self.model.format_timecode(frame_idx, fps)
        self.time_updated.emit(timestamp, frame_idx, timecode_str, True)

    def mouseMoveEvent(self, event):
        self.mouse_x, self.mouse_y = event.x(), event.y()
        self.hover_x_changed.emit(self.mouse_x)
        if self.interaction_mode != MODE_IDLE: self.handle_drag(event)
        elif event.buttons() & Qt.LeftButton: self.update_playhead_to_x(event.x())
        else: self.update_cursor_state(event)
        self.update()

    def leaveEvent(self, event):
        self.mouse_x = -1
        self.hover_x_changed.emit(-1)
        self.update()

    def mouseReleaseEvent(self, event):
        self.active_clip = None
        self.interaction_mode = MODE_IDLE
        self.setCursor(Qt.ArrowCursor)
        self.structure_changed.emit()

    def update_playhead_position(self, frame_index: float) -> int:
        self.model.blueline.set_playhead_frame(frame_index)
        fps = self.get_fps()
        timestamp = frame_index / fps
        self.time_updated.emit(timestamp, int(frame_index), self.model.format_timecode(int(frame_index), fps), True)
        return self.timeToScreen(timestamp)

    def wheelEvent(self, event):
        modifiers = event.modifiers()
        normalized_delta = event.angleDelta().y() / 120.0
        scroll_area = self.get_scroll_area_context()
        if (modifiers & Qt.ControlModifier) and (modifiers & Qt.ShiftModifier):
            self._change_all_track_heights(int(normalized_delta * 10))
            event.accept()
        elif (modifiers & Qt.ControlModifier) or (modifiers & Qt.MetaModifier):
            zoom_factor = 1.2 if normalized_delta > 0 else 0.8
            self._zoom_horizontal(zoom_factor)
            event.accept()
        elif modifiers & Qt.ShiftModifier:
            if scroll_area:
                v_sb = scroll_area.verticalScrollBar()
                v_sb.setValue(v_sb.value() - event.angleDelta().y())
            event.accept()
        else:
            if scroll_area:
                h_sb = scroll_area.horizontalScrollBar()
                h_sb.setValue(int(h_sb.value() - event.angleDelta().y() * 0.8))
            event.accept()
