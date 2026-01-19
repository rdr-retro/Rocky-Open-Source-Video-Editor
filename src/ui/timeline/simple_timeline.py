"""
Simple Timeline Widget - Minimal implementation that WILL render visibly.
This is a complete rewrite focusing on guaranteed visibility.
"""

from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRectF, QPointF, QLineF, Property, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QImage
from functools import partial
import numpy as np
import math
from ..styles import MENU_STYLE

class SimpleTimeline(QWidget):
    """Ultra-simple timeline that is guaranteed to be visible."""
    
    # Signals expected by rocky_ui.py
    time_updated = Signal(float, int, str, bool)
    structure_changed = Signal()
    view_updated = Signal()
    track_addition_requested = Signal(object)
    hover_x_changed = Signal(int)
    play_pause_requested = Signal()
    clip_proxy_toggled = Signal(object) # New Signal for Proxy Click
    clip_fx_toggled = Signal(object)    # New Signal for FX Click
    
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._pixels_per_second = 100.0
        
        # Interaction state
        self.mouse_x = -1
        self.mouse_y = -1
        self.dragging_clip = None
        self.potential_drag_clip = None # NEW: For drag threshold
        self.potential_drag_start_pos = None # NEW: For drag threshold
        self.drag_start_x = 0
        self.drag_start_y = 0  # NEW: Track vertical drag
        self.drag_offset_x = 0
        self.drag_start_track = -1  # NEW: Original track index
        self.selected_clips = []
        
        # [VEGAS MAPPING]
        # visible_start_time is now a derived property, not an instance variable.
        
        # Envelopes Interaction - REMOVED
        self.dragging_fade_in = False
        self.dragging_fade_out = False
        self.dragging_opacity = False  # NEW: For opacity/gain level handle
        self.dragging_left_edge = False
        self.dragging_right_edge = False
        
        # Configure widget for visibility
        self.setMinimumSize(800, 400)
        self.setVisible(True)
        self.setEnabled(True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        # Standard context menu policy (default is PreventContextMenu, we want DefaultContextMenu)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        
        # Force opaque painting
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAutoFillBackground(False)
        
        # Repaint timer
        self.repaint_timer = QTimer(self)
        self.repaint_timer.timeout.connect(self.update)
        self.repaint_timer.start(16)  # 60 FPS
        
        
        # Animations
        self.zoom_anim = QPropertyAnimation(self, b"pixels_per_second")
        self.scroll_anim = None # Will be created on demand
        
        print("SimpleTimeline: Widget created and configured", flush=True)

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
    
    def sizeHint(self):
        """Provide size based on timeline content."""
        # Calculate width based on timeline duration
        max_frame = self.model.get_max_frame()
        if max_frame > 0:
            width = int((max_frame / self.get_fps()) * self.pixels_per_second) + 500  # Add padding
        else:
            width = 3000  # Default width
        
        # Calculate height based on tracks
        height = sum(self.model.track_heights) if self.model.track_heights else 600
        
        return QSize(max(width, 1200), max(height, 600))
    
    def minimumSizeHint(self):
        """Minimum size to ensure visibility."""
        # Height based on tracks
        height = sum(self.model.track_heights) if self.model.track_heights else 400
        return QSize(800, max(height, 400))
    
    def paintEvent(self, event):
        """Paint the timeline - GUARANTEED TO BE VISIBLE."""
        painter = QPainter(self)
        
        if not painter.isActive():
            return
        
        # Visible region for culling
        visible_rect = event.rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        try:
            # 1. BACKGROUND
            painter.fillRect(visible_rect, QColor(30, 30, 30))
            
            # 2. GRID
            self._draw_grid(painter, visible_rect)
            
            # 3. TRACK DIVIDERS
            self._draw_tracks(painter)
            
            # 4. CLIPS (Culling enabled)
            self._draw_clips(painter, visible_rect)
            
            # 5. PLAYHEAD
            self._draw_playhead(painter)
        except Exception as e:
            print(f"Paint Error: {e}")
        finally:
            painter.end()
    
    
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

    def _draw_grid(self, painter, rect):
        """[VEGAS REDESIGN] Draw vertical grid lines based on adaptive subdivisions."""
        pps = self.pixels_per_second
        fps = self.get_fps()
        
        major_step, divs = self.calculate_adaptive_step(pps, fps)
        minor_step = major_step / float(divs)
        
        start_time = self.screenXToTime(rect.left())
        end_time = self.screenXToTime(rect.right())
        
        # Align to major step
        t_major = math.floor(start_time / major_step) * major_step
        
        pen_major = QPen(QColor(80, 80, 80, 150), 1, Qt.PenStyle.DotLine)
        pen_minor = QPen(QColor(60, 60, 60, 80), 1, Qt.PenStyle.DotLine)
        
        while t_major < end_time + major_step:
            # 1. Draw Minor Subdivisions first
            painter.setPen(pen_minor)
            for i in range(1, divs):
                t_minor = t_major + (i * minor_step)
                x_minor = self.timeToProjectedX(t_minor)
                if rect.left() <= x_minor <= rect.right():
                    painter.drawLine(QLineF(x_minor, 0, x_minor, self.height()))
            
            # 2. Draw Major Line
            painter.setPen(pen_major)
            x_major = self.timeToProjectedX(t_major)
            if rect.left() <= x_major <= rect.right():
                painter.drawLine(QLineF(x_major, 0, x_major, self.height()))
            
            t_major += major_step
    
    def _draw_tracks(self, painter):
        """Draw horizontal track dividers based on actual model tracks."""
        painter.setPen(QPen(QColor(40, 40, 40), 1)) # Darker dividers
        
        current_y = 0
        for i, height in enumerate(self.model.track_heights):
            current_y += height
            if current_y < self.height():
                painter.drawLine(0, current_y, self.width(), current_y)
    
    def _draw_clips(self, painter, visible_rect):
        """[VEGAS REDESIGN] Deterministic clip drawing with floating point precision."""
        from PySide6.QtGui import QFontMetrics
        
        COLOR_VIDEO_BODY = QColor("#763436")
        COLOR_VIDEO_HEADER = QColor("#9E4347")
        COLOR_AUDIO_BODY = QColor("#347660")
        COLOR_AUDIO_HEADER = QColor("#439E80")
        COLOR_TEXT = QColor(230, 230, 230)
        
        font = painter.font()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        
        track_y_positions = self._get_track_y_positions()
        
        for clip in self.model.clips:
            if clip.track_index >= len(track_y_positions):
                continue
            
            # [VEGAS PRINCIPLE] Precision Projection
            clip_x = self.frameToProjectedX(clip.start_frame)
            clip_w = self.frameToProjectedX(clip.duration_frames)
            
            # CULLING (Precision Check)
            if clip_x + clip_w < visible_rect.left() or clip_x > visible_rect.right():
                continue
            
            track_y = track_y_positions[clip.track_index]
            track_h = self.model.track_heights[clip.track_index]
            clip_h = track_h - 2
            
            # Track Type Colors
            from ..models import TrackType
            if clip.track_index < len(self.model.track_types) and self.model.track_types[clip.track_index] == TrackType.VIDEO:
                body_col = COLOR_VIDEO_BODY
                header_col = COLOR_VIDEO_HEADER
            else:
                body_col = COLOR_AUDIO_BODY
                header_col = COLOR_AUDIO_HEADER
                
            if clip.selected:
                 body_col = body_col.lighter(130)
                 header_col = header_col.lighter(130)
            
            # 1. Body (QRectF for sub-pixel)
            rect_body = QRectF(clip_x, track_y + 1, clip_w, clip_h)
            painter.fillRect(rect_body, body_col)
            
            # 2. Header
            header_h = 12
            rect_header = QRectF(clip_x, track_y + 1, clip_w, header_h)
            painter.fillRect(rect_header, header_col)
            
            # --- WAVEFORM / THUMBNAILS ---
            is_video = (clip.track_index < len(self.model.track_types) and self.model.track_types[clip.track_index] == TrackType.VIDEO)
            if is_video:
                if hasattr(clip, 'thumbnails') and clip.thumbnails:
                    self._draw_thumbnail(painter, clip, clip_x, track_y + 13, clip_w, clip_h - 12, visible_rect)
            else:
                if hasattr(clip, 'waveform') and clip.waveform:
                    self._draw_waveform(painter, clip.waveform, clip_x, track_y + 13, clip_w, clip_h - 12, visible_rect)
                elif getattr(clip, 'waveform_computing', False):
                    painter.setPen(QColor(255, 255, 255, 100))
                    painter.drawText(int(clip_x) + 5, int(track_y) + 30, "Computing peaks...")
            
            # 3. Text
            painter.setPen(COLOR_TEXT)
            font = painter.font()
            font.setPointSize(9) # Smaller font for ultra-thin header
            painter.setFont(font)
            painter.drawText(rect_header.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, clip.name)
            
            # 4. OPACITY/GAIN ENVELOPE (Precision Rendering)
            from ..models import FadeType
            body_start_y = track_y + 13
            body_end_y = track_y + 1 + clip_h
            body_height = body_end_y - body_start_y
            
            opacity_level = getattr(clip, 'opacity_level', 1.0)
            target_y = body_start_y + (1.0 - opacity_level) * body_height
            
            fade_in_w = self.frameToProjectedX(clip.fade_in_frames)
            fade_out_w = self.frameToProjectedX(clip.fade_out_frames)
            
            envelope = QPainterPath()
            p_start_fi = QPointF(clip_x, body_end_y)
            envelope.moveTo(p_start_fi)
            
            if fade_in_w > 0:
                p_end_fi = QPointF(clip_x + fade_in_w, target_y)
                c_type_in = clip.fade_in_type
                if c_type_in == FadeType.LINEAR:
                    envelope.lineTo(p_end_fi)
                elif c_type_in == FadeType.FAST:
                    envelope.cubicTo(QPointF(clip_x, target_y), QPointF(clip_x + fade_in_w * 0.25, target_y), p_end_fi)
                elif c_type_in == FadeType.SLOW:
                    envelope.cubicTo(QPointF(clip_x + fade_in_w * 0.75, body_end_y), QPointF(clip_x + fade_in_w, body_end_y), p_end_fi)
                elif c_type_in == FadeType.SMOOTH:
                    envelope.cubicTo(QPointF(clip_x + fade_in_w * 0.5, body_end_y), QPointF(clip_x + fade_in_w * 0.5, target_y), p_end_fi)
                elif c_type_in == FadeType.SHARP:
                    envelope.lineTo(clip_x + fade_in_w, body_end_y)
                    envelope.lineTo(p_end_fi)
            else:
                envelope.lineTo(clip_x, target_y)
            
            plateau_end_x = clip_x + clip_w - fade_out_w
            envelope.lineTo(plateau_end_x, target_y)
            
            if fade_out_w > 0:
                p_end_fo = QPointF(clip_x + clip_w, body_end_y)
                c_type_out = clip.fade_out_type
                if c_type_out == FadeType.LINEAR:
                    envelope.lineTo(p_end_fo)
                elif c_type_out == FadeType.FAST:
                    envelope.cubicTo(QPointF(plateau_end_x, body_end_y), QPointF(plateau_end_x + fade_out_w * 0.25, body_end_y), p_end_fo)
                elif c_type_out == FadeType.SLOW:
                    envelope.cubicTo(QPointF(p_end_fo.x(), target_y), QPointF(p_end_fo.x(), target_y + (body_end_y - target_y) * 0.25), p_end_fo)
                elif c_type_out == FadeType.SMOOTH:
                    envelope.cubicTo(QPointF(plateau_end_x + fade_out_w * 0.5, target_y), QPointF(plateau_end_x + fade_out_w * 0.5, body_end_y), p_end_fo)
                elif c_type_out == FadeType.SHARP:
                    envelope.lineTo(clip_x + clip_w, target_y)
                    envelope.lineTo(p_end_fo)
            else:
                envelope.lineTo(clip_x + clip_w, target_y)
                envelope.lineTo(clip_x + clip_w, body_end_y)
            
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(envelope)
            
            # Draw small handle in the center of the clip (on the computed line)
            # Find center X of the clip body
            center_x = clip_x + clip_w / 2
            # Is center on plateau or curve? Usually plateau.
            # Ideally we clamp to plateau, but user wants dragging.
            # Handle Y is 'target_y'
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(center_x - 3, target_y - 2, 6, 4))

            # Fade Out Handle REMOVED as per user request


            # Corner Triangles (Blue) - Top corners of body area
            body_top_y = track_y + 13  # Just below 12px header
            COLOR_CORNER = QColor(0, 170, 255)  # Blue
            
            # Top-Left Corner Triangle
            path_tl = QPainterPath()
            path_tl.moveTo(clip_x, body_top_y)
            path_tl.lineTo(clip_x + 6, body_top_y)
            path_tl.lineTo(clip_x, body_top_y + 6)
            path_tl.closeSubpath()
            painter.fillPath(path_tl, COLOR_CORNER)
            
            # Top-Right Corner Triangle
            path_tr = QPainterPath()
            path_tr.moveTo(clip_x + clip_w, body_top_y)
            path_tr.lineTo(clip_x + clip_w - 6, body_top_y)
            path_tr.lineTo(clip_x + clip_w, body_top_y + 6)
            path_tr.closeSubpath()
            painter.fillPath(path_tr, COLOR_CORNER)

            # 5.5. Bottom Handles (White Triangles)
            bottom_y = track_y + 1 + clip_h
            COLOR_BOTTOM_HANDLE = QColor(255, 255, 255)

            # Bottom-Left
            path_bottom_l = QPainterPath()
            path_bottom_l.moveTo(clip_x, bottom_y)
            path_bottom_l.lineTo(clip_x + 6, bottom_y)
            path_bottom_l.lineTo(clip_x, bottom_y - 6)
            path_bottom_l.closeSubpath()
            painter.fillPath(path_bottom_l, COLOR_BOTTOM_HANDLE)

            # Bottom-Right
            path_bottom_r = QPainterPath()
            path_bottom_r.moveTo(clip_x + clip_w, bottom_y)
            path_bottom_r.lineTo(clip_x + clip_w - 6, bottom_y)
            path_bottom_r.lineTo(clip_x + clip_w, bottom_y - 6)
            path_bottom_r.closeSubpath()
            painter.fillPath(path_bottom_r, COLOR_BOTTOM_HANDLE)
            
            # 5. Buttons (FX, PX) - Right aligned in header
            # Remove old icons
            
            button_w = 14
            button_h = 8
            spacing = 2
            
            # Button 2: PX (Proxy) - Rightmost
            px_x = clip_x + clip_w - button_w - 4
            px_y = track_y + 2
            
            # Determine Color for PX (Vegas Style)
            # ProxyStatus: NONE=0, GENERATING=1, READY=2, ERROR=3
            from ..models import ProxyStatus
            p_status = getattr(clip, 'proxy_status', ProxyStatus.NONE)
            # Check global proxy toggle state
            global_proxy_on = False
            try:
                main_window = self.window()
                if hasattr(main_window, 'toolbar'):
                    global_proxy_on = main_window.toolbar.btn_proxy.isChecked()
            except: pass

            if p_status == ProxyStatus.GENERATING:
                px_col = QColor("#FF8800") # Orange (Generating)
            elif p_status == ProxyStatus.READY and getattr(clip, 'use_proxy', False) and global_proxy_on:
                px_col = QColor("#00FF00") # Green (Active)
            else:
                px_col = QColor("#000000") # Black (Deactivated / Not Ready)
                
            rect_px = QRectF(px_x, px_y, button_w, button_h)
            painter.setBrush(px_col)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 0.5)) # Subtle border
            painter.drawRoundedRect(rect_px, 1.5, 1.5)
            
            # Text "PX"
            painter.setPen(QColor("#000000") if px_col == QColor("#00FF00") else QColor("#FFFFFF"))
            font_btn = painter.font()
            font_btn.setPointSize(6.5)
            font_btn.setBold(True)
            painter.setFont(font_btn)
            painter.drawText(rect_px, Qt.AlignmentFlag.AlignCenter, "PX")
            
            # Button 1: FX (Effects) - Left of PX
            fx_x = px_x - button_w - spacing
            fx_y = px_y
            
            # FX always black
            fx_col = QColor("#000000")
            
            rect_fx = QRectF(fx_x, fx_y, button_w, button_h)
            painter.setBrush(fx_col)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 0.5))
            painter.drawRoundedRect(rect_fx, 1.5, 1.5)
            
            # Text "FX"
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(rect_fx, Qt.AlignmentFlag.AlignCenter, "FX")
            
            # 7. Clip Selection Border
            if clip.selected:
                painter.setPen(QPen(QColor("#FFFF00"), 1)) # Bright yellow border
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(clip_x, track_y + 1, clip_w, clip_h)

    def _draw_waveform(self, painter, peaks, x, y, w, h, visible_rect):
        """[VEGAS REDESIGN] Stereo Waveform Drawing (L/R Channels)."""
        if not peaks or w < 1:
            return
            
        # Split height for stereo display
        h_per_ch = h / 2.0
        mid_y_l = y + (h_per_ch / 2.0)
        mid_y_r = y + h_per_ch + (h_per_ch / 2.0)
        
        # Interleaved peaks: L, R, L, R...
        # So we have len(peaks)//2 logical points
        num_logical_points = len(peaks) // 2
        
        # Determine strict drawing boundary: Intersect clip with viewport
        draw_start_x = max(int(x), visible_rect.left())
        draw_end_x = min(int(x + w), visible_rect.right())
        
        if draw_start_x >= draw_end_x:
            return

        painter.setPen(QPen(QColor(255, 255, 255, 140), 1))
        ppp = num_logical_points / float(w)
        
        # Loop only over the visible pixels
        for px in range(draw_start_x, draw_end_x):
            # Relative pixel index inside clip
            i = px - x
            p_idx = int(i * ppp)
            if p_idx >= num_logical_points: break
            
            # --- CHANNEL L (TOP) ---
            val_l = peaks[p_idx * 2]
            if val_l > 0.005:
                # Vertical mirror effect per channel
                line_h_l = val_l * (h_per_ch / 2.0) * 0.95
                painter.drawLine(QLineF(px, mid_y_l - line_h_l, px, mid_y_l + line_h_l))

            # --- CHANNEL R (BOTTOM) ---
            val_r = peaks[p_idx * 2 + 1]
            if val_r > 0.005:
                line_h_r = val_r * (h_per_ch / 2.0) * 0.95
                painter.drawLine(QLineF(px, mid_y_r - line_h_r, px, mid_y_r + line_h_r))

    def _draw_thumbnail(self, painter, clip, x, y, w, h, visible_rect):
        """Draws thumbnails with viewport culling."""
        if not clip.thumbnails: return
        
        thumb_h = h
        thumb_w = int(thumb_h * 1.77)
        
        # Only draw if the thumbnail position overlaps with viewport
        # Start thumb
        if x + thumb_w > visible_rect.left() and x < visible_rect.right():
             self._paint_thumb(painter, clip.thumbnails[0], x, y, thumb_w, thumb_h)
        
        # End thumb
        end_x = x + w - thumb_w
        if end_x + thumb_w > visible_rect.left() and end_x < visible_rect.right() and w > thumb_w * 2:
             self._paint_thumb(painter, clip.thumbnails[2], end_x, y, thumb_w, thumb_h)

    def _paint_thumb(self, painter, thumb_data, x, y, w, h):
        """Internal helper for pixel data painting."""
        try:
            height, width, channel = thumb_data.shape
            bytes_per_line = 3 * width
            q_img = QImage(thumb_data.data, width, height, bytes_per_line, QImage.Format_RGB888)
            painter.drawImage(QRectF(x, y, w, h), q_img)
        except: pass

    def _draw_playhead(self, painter):
        """[VEGAS REDESIGN] Draw playhead using absolute time projection."""
        # [VEGAS PRINCIPLE] Playhead doesn't depend on GUI state, it's projected.
        ph_x = self.frameToProjectedX(self.model.blueline.playhead_frame)
        
        # Consistent Precision Drawing
        line = QLineF(ph_x, 0, ph_x, self.height())
        
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawLine(line)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawLine(line)

    def mousePressEvent(self, event):
        """Handle mouse press - select clips, move playhead, or EDIT ENVELOPES."""
        self.setFocus() # Ensure we catch keyboard events
        
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Check FADE/TRIM/OPACITY Hits
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
                        clip_x = self.frameToProjectedX(clip.start_frame)
                        clip_w = self.frameToProjectedX(clip.duration_frames)
                        body_top_y = click_track_y + 13
                        
                        # Fade Handles
                        if (clip_x <= event.x() <= clip_x + 6 and body_top_y <= event.y() <= body_top_y + 6):
                            self.dragging_clip, self.dragging_fade_in = clip, True
                            self.structure_changed.emit()
                            return
                        if (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and body_top_y <= event.y() <= body_top_y + 6):
                            self.dragging_clip, self.dragging_fade_out = clip, True
                            self.structure_changed.emit()
                            return

                        # Trim Edges
                        edge_margin = 8
                        if (abs(event.x() - clip_x) <= edge_margin and click_track_y <= event.y() <= click_track_y + track_h):
                            self.dragging_clip, self.dragging_left_edge = clip, True
                            return
                        if (abs(event.x() - (clip_x + clip_w)) <= edge_margin and click_track_y <= event.y() <= click_track_y + track_h):
                            self.dragging_clip, self.dragging_right_edge = clip, True
                            return
                            
                        # Opacity Handle
                        opacity_level = getattr(clip, 'opacity_level', 1.0)
                        level_y = body_top_y + (1.0 - opacity_level) * (click_track_y + track_h - 1 - body_top_y)
                        if (clip_x <= event.x() <= clip_x + clip_w) and (abs(event.y() - level_y) <= 5 or (abs(event.y() - body_top_y) <= 5 and opacity_level > 0.95)):
                            self.dragging_clip, self.dragging_opacity = clip, True
                            self.structure_changed.emit()
                            return

            # Selection/Playhead
            clip = self.find_clip_at(event.x(), event.y())
            if clip:
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
            else:
                self.update_playhead_to_x(event.x())
            self.update()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - drag clips, update hover, SCRUB PLAYHEAD, or DRAG FADES."""
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        self.hover_x_changed.emit(self.mouse_x)
        
        # Update cursor based on hover (when not dragging)
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            # Check if hovering over fade handles
            cursor_set = False
            track_y_positions = []
            curr_y = 0
            hover_track_idx = -1
            hover_track_y = 0
            
            for h in self.model.track_heights:
                if curr_y <= event.y() < curr_y + h:
                    hover_track_idx = len(track_y_positions)
                    hover_track_y = curr_y
                    break
                track_y_positions.append(curr_y)
                curr_y += h
            
            if hover_track_idx != -1:
                for clip in self.model.clips:
                    if clip.track_index == hover_track_idx:
                        clip_x = self.frameToProjectedX(clip.start_frame)
                        clip_w = self.frameToProjectedX(clip.duration_frames)
                        body_top_y = hover_track_y + 13
                        
                        # Check handles and edges using projected math
                        if ((clip_x <= event.x() <= clip_x + 6 and body_top_y <= event.y() <= body_top_y + 6) or
                            (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and body_top_y <= event.y() <= body_top_y + 6)):
                            self.setCursor(Qt.CursorShape.SizeHorCursor)
                            cursor_set = True
                            break
            
                        # Check edges for Trim (SizeHorCursor)
                        edge_margin = 8
                        is_near_left = abs(event.x() - clip_x) <= edge_margin
                        is_near_right = abs(event.x() - (clip_x + clip_w)) <= edge_margin
                        
                        track_h = self.model.track_heights[clip.track_index]
                        if (is_near_left or is_near_right) and (hover_track_y <= event.y() <= hover_track_y + track_h):
                            self.setCursor(Qt.CursorShape.SizeHorCursor)
                            cursor_set = True
                            break

                        # Check Opacity/Gain Handle (Top Edge or Line)
                        opacity_level = getattr(clip, 'opacity_level', 1.0)
                        clip_h = track_h - 2
                        body_start_y = hover_track_y + 13
                        body_end_y = hover_track_y + 1 + clip_h
                        body_height = body_end_y - body_start_y
                        
                        level_y = body_start_y + (1.0 - opacity_level) * body_height
                        
                        hit_line = abs(event.y() - level_y) <= 5
                        # Allow top grab if near full opac
                        hit_top = abs(event.y() - body_start_y) <= 5 and opacity_level > 0.95 
                        
                        if (clip_x <= event.x() <= clip_x + clip_w) and (hit_line or hit_top):
                             self.setCursor(Qt.CursorShape.PointingHandCursor) # Hand icon
                             cursor_set = True
                             break
            
            if not cursor_set:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            
            # --- 0. Handle Trim Edges ---
            if self.dragging_right_edge and self.dragging_clip:
                clip = self.dragging_clip
                target_frame = self.screenXToFrame(event.x())
                new_duration = int(target_frame - clip.start_frame)
                new_duration = max(5, new_duration)
                
                if clip.source_duration_frames > 0:
                    max_d = clip.source_duration_frames - getattr(clip, 'source_offset_frames', 0)
                    new_duration = min(new_duration, max_d)
                
                clip.duration_frames = new_duration
                self.update()
                self.structure_changed.emit()
                return

            if self.dragging_left_edge and self.dragging_clip:
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
                
                self.update()
                self.structure_changed.emit()
                return

            # --- CHECK DRAG THRESHOLD (New Logic) ---
            if self.potential_drag_clip and self.potential_drag_start_pos:
                dist = (event.position() - self.potential_drag_start_pos).manhattanLength()
                if dist > 5: # Threshold of 5 pixels
                    self.dragging_clip = self.potential_drag_clip
                    self.potential_drag_clip = None
                    self.potential_drag_start_pos = None
            
            # --- 0. Handle Opacity/Gain Drag ---
            if self.dragging_opacity and self.dragging_clip:
                clip = self.dragging_clip
                
                # Re-calculate track geometry to get bounds
                track_y = 0
                for i in range(clip.track_index):
                    track_y += self.model.track_heights[i] if i < len(self.model.track_heights) else 60
                
                track_h = self.model.track_heights[clip.track_index]
                clip_h = track_h - 2
                body_start_y = track_y + 13
                body_end_y = track_y + 1 + clip_h
                body_height = max(1, body_end_y - body_start_y)
                
                # Mouse Y relative to body start
                rel_y = event.y() - body_start_y
                
                # Calculate new Opacity (0.0 to 1.0)
                # rel_y = 0 -> Opacity 1.0
                # rel_y = height -> Opacity 0.0
                new_opacity = 1.0 - (rel_y / body_height)
                
                # Clamp
                clip.opacity_level = max(0.0, min(1.0, new_opacity))
                
                self.update() # Repaint only (visual change)
                return

            # 0b. Handle Fade Drag
            if self.dragging_fade_in and self.dragging_clip:
                clip = self.dragging_clip
                clip_x = self.frameToProjectedX(clip.start_frame)
                new_frames = self.screenXToFrame(event.x()) - clip.start_frame
                clip.fade_in_frames = max(0, min(clip.duration_frames, int(new_frames)))
                
                self.update()
                return

            if self.dragging_fade_out and self.dragging_clip:
                clip = self.dragging_clip
                clip_end_x = self.frameToProjectedX(clip.start_frame + clip.duration_frames)
                dist_frames = self.screenXToFrame(clip_end_x) - self.screenXToFrame(event.x())
                clip.fade_out_frames = max(0, min(clip.duration_frames, int(dist_frames)))
                
                self.update()
                return

            if self.dragging_clip:
                new_x = event.x() - self.drag_offset_x
                new_frame = max(0, int(self.screenXToFrame(new_x)))
                self.dragging_clip.start_frame = new_frame
                
                # NEW: Vertical track detection
                # Calculate which track the mouse is currently over
                track_y_positions = []
                current_y = 0
                for height in self.model.track_heights:
                    track_y_positions.append(current_y)
                    current_y += height
                
                # Find target track based on mouse Y
                target_track = -1
                for i, track_y in enumerate(track_y_positions):
                    if i < len(self.model.track_heights):
                        track_h = self.model.track_heights[i]
                        if track_y <= event.y() < track_y + track_h:
                            target_track = i
                            break
                
                # Update track if valid and different from current
                if target_track != -1 and target_track != self.dragging_clip.track_index:
                    # Check if track type is compatible (optional validation)
                    # For now, allow any track change
                    self.dragging_clip.track_index = target_track
                
                self.structure_changed.emit()
            elif not self.potential_drag_clip: # Scrub if NOT in potential drag wait state
                # Scrub Playhead (Fluid) only if we aren't waiting for a potential drag
                self.update_playhead_to_x(event.x())
        
        self.update()
    
    def mouseDoubleClickEvent(self, event):
        """Handle Double Click."""
        # Previous Keyframe Logic Removed.
        pass

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        
        # Capture context before clearing
        dropped_clip = self.dragging_clip
        was_dragging_fade = self.dragging_fade_in or self.dragging_fade_out
        
        self.dragging_envelope = False
        self.dragging_fade_in = False   # NEW
        self.dragging_fade_out = False  # NEW
        self.dragging_opacity = False   # NEW
        self.dragging_left_edge = False
        self.dragging_right_edge = False
        
        # CLEAR potential drag state
        self.potential_drag_clip = None
        self.potential_drag_start_pos = None
        
        if self.dragging_clip:
            self.dragging_clip = None
            self.structure_changed.emit()

        # --- AUTOMATIC CROSSFADE LOGIC ---
        # "Si arrastras un clip sobre el final de otro... crea automáticamente un área de intersección."
        # Trigger only on Clip Move (not Fade drag, not Keyframe drag)
        if dropped_clip and not was_dragging_fade:
            # Find overlaps on the same track
            track_clips = [c for c in self.model.clips if c.track_index == dropped_clip.track_index and c != dropped_clip]
            
            for other in track_clips:
                # Check for Overlap
                # A: dropped, B: other
                # Overlap: A.start < B.end AND A.end > B.start
                
                # We specifically look for "Crossfade" scenario:
                # 1. Dropped is Right of Other (Standard drag to append/overlap)
                #    Other.start < Dropped.start < Other.end
                
                start_a = dropped_clip.start_frame
                end_a = dropped_clip.start_frame + dropped_clip.duration_frames
                
                start_b = other.start_frame
                end_b = other.start_frame + other.duration_frames
                
                overlap = 0
                
                # Check intersection
                if start_a < end_b and end_a > start_b:
                     # Calculate intersection width
                     intersect_start = max(start_a, start_b)
                     intersect_end = min(end_a, end_b)
                     overlap = max(0, intersect_end - intersect_start)
                
                if overlap > 0:
                    # Apply Crossfade
                    # "Los tiradores de opacidad de ambos clips se cruzan"
                    
                    # If Dropped is the "Incoming" (Right) clip
                    if start_a > start_b:
                        # Other is Left, Dropped is Right.
                        # Overlap is at the end of Other and start of Dropped.
                        other.fade_out_frames = overlap
                        dropped_clip.fade_in_frames = overlap
                        print(f"Auto-Crossfade: {overlap} frames between '{other.name}' and '{dropped_clip.name}'")
                        
                    # If Dropped is the "Outgoing" (Left) clip
                    elif start_a < start_b:
                        # Dropped is Left, Other is Right.
                        dropped_clip.fade_out_frames = overlap
                        other.fade_in_frames = overlap
                        print(f"Auto-Crossfade: {overlap} frames between '{dropped_clip.name}' and '{other.name}'")

        self.update()

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
            self.delete_clip(None) # Use centralized delete logic
        elif event.key() == Qt.Key_Up:
            self.pixels_per_second = min(500, self.pixels_per_second * 1.2)
            self.view_updated.emit()
            self.updateGeometry()
        elif event.key() == Qt.Key_Down:
            self.pixels_per_second = max(10, self.pixels_per_second / 1.2)
            self.view_updated.emit()
            self.updateGeometry()
        
        self.update()
    
    def wheelEvent(self, event):
        """[VEGAS PRINCIPLE] Deterministic Zoom focused on absolute anchor time."""
        if event.modifiers() & Qt.ControlModifier:
            scroll_area = self.get_scroll_area_context()
            if not scroll_area: return
            h_scroll = scroll_area.horizontalScrollBar()
            
            # 1. Capture Anchor Point (Absolute time under mouse)
            mouse_abs_x = event.position().x()
            anchor_time = self.screenXToTime(mouse_abs_x)
            viewport_offset = mouse_abs_x - h_scroll.value()
            
            # 2. Update Scale (Multiplicative)
            delta = event.angleDelta().y()
            zoom_factor = 1.15 if delta > 0 else (1.0 / 1.15)
            # [VEGAS REDESIGN] Lower minimum zoom (0.1) for extreme project overview
            self.pixels_per_second = max(0.1, min(8000, self.pixels_per_second * zoom_factor))
            
            # 3. Synchronous Redraw & Refit
            self.updateGeometry()
            self.setFixedSize(self.sizeHint())
            
            # 4. Project new scroll to maintain anchor_time position
            new_scroll_val = int(self.timeToProjectedX(anchor_time) - viewport_offset)
            h_scroll.setValue(max(0, new_scroll_val))
            
            self.view_updated.emit()
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def dragEnterEvent(self, event):
        """Accept drag events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-rocky-effect"):
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle file drops and EFFECT drops."""
        # 1. Handle Effect Drops
        if event.mimeData().hasFormat("application/x-rocky-effect"):
            data = event.mimeData().data("application/x-rocky-effect")
            data_str = data.data().decode('utf-8')
            if "|" in data_str:
                name, path = data_str.split("|", 1)
                
                # Find clip under mouse
                clip = self.find_clip_at(event.pos().x(), event.pos().y())
                if clip:
                     print(f"Applying Effect '{name}' to Clip '{clip.name}'")
                     
                     # Add to clip model
                     new_effect = {
                         "name": name,
                         "path": path,
                         "enabled": True
                     }
                     clip.effects.append(new_effect)
                     print(f"Current Effects on {clip.name}: {len(clip.effects)}")
                     
                     self.structure_changed.emit() # Trigger update/save
                     self.update()
                else:
                    print("Drop ignored: No clip under mouse.")
            
            event.accept()
            return

        # 2. Handle File Drops (Media Import) using Precision Time
        urls = event.mimeData().urls()
        if not urls: return
        
        start_frame = int(self.screenXToFrame(event.pos().x()))
        
        # Calculate track index
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
    
    def get_fps(self):
        """Return FPS (should be dynamic from model/engine)."""
        return 30.0

    def _get_track_y_positions(self):
        """Calculate Y position for each track. Cached calculation could be added here."""
        positions = []
        current_y = 0
        for height in self.model.track_heights:
            positions.append(current_y)
            current_y += height
        return positions
    
    def find_clip_at(self, x, y):
        """[VEGAS PRINCIPLE] Precision Hit-Testing."""
        track_y_positions = self._get_track_y_positions()
        
        # 1. Find Track from Y
        track_idx = -1
        TOLERANCE_Y = 2
        for i, track_y in enumerate(track_y_positions):
            if i < len(self.model.track_heights):
                track_h = self.model.track_heights[i]
                if track_y - TOLERANCE_Y <= y < track_y + track_h + TOLERANCE_Y:
                    track_idx = i
                    break
        
        if track_idx == -1: return None
        
        # 2. Find Clip in Track from X (Precision Math)
        TOLERANCE_X = 2
        for clip in self.model.clips:
            if clip.track_index == track_idx:
                clip_x = self.frameToProjectedX(clip.start_frame)
                clip_w = self.frameToProjectedX(clip.duration_frames)
                if clip_x - TOLERANCE_X <= x <= clip_x + clip_w + TOLERANCE_X:
                    return clip
        
        return None
    
    def timeToProjectedX(self, time_seconds):
        """
        [VEGAS PRINCIPLE] Centralized Projection.
        Returns the absolute screen X coordinate for a given time in seconds.
        This is a continuous mathematical mapping.
        """
        return time_seconds * self.pixels_per_second

    def frameToProjectedX(self, frame_index):
        """Converts absolute frame index to continuous screen X."""
        return (frame_index / self.get_fps()) * self.pixels_per_second

    def screenXToTime(self, screen_x):
        """[VEGAS PRINCIPLE] Centralized Inverse Projection."""
        return screen_x / self.pixels_per_second

    def screenXToFrame(self, screen_x):
        """Converts screen X back to absolute frame index."""
        return (screen_x / self.pixels_per_second) * self.get_fps()

    def timeToScreen(self, time_in_seconds):
        """DEPRECATED: Use timeToProjectedX for clarity."""
        return self.timeToProjectedX(time_in_seconds)

    def frameToScreen(self, frame_index):
        """DEPRECATED: Use frameToProjectedX for clarity."""
        return self.frameToProjectedX(frame_index)

    def update_playhead_to_x(self, screen_x):
        """Update playhead position from screen x coordinate."""
        time_seconds = max(0, self.screenXToTime(screen_x))
        frame = time_seconds * self.get_fps()
        self.update_playhead_position(frame, forced=True)
    
    def update_playhead_position(self, frame_index, forced=True):
        """Update playhead to specific frame using absolute math."""
        self.model.blueline.set_playhead_frame(frame_index)
        time_seconds = frame_index / self.get_fps()
        tc = self.model.format_timecode(frame_index, self.get_fps())
        self.time_updated.emit(time_seconds, int(frame_index), tc, forced)
        self.update()
        return self.frameToProjectedX(frame_index)
    
    def get_scroll_area_context(self):
        """Get parent scroll area."""
        from PySide6.QtWidgets import QScrollArea
        current = self.parent()
        while current:
            if isinstance(current, QScrollArea):
                return current
            current = current.parent()
        return None
    
    def contextMenuEvent(self, event):
        """Handle native context menu event."""
        self.show_context_menu(event.pos())
        event.accept()

    def show_context_menu(self, pos):
        """Show context menu for clips (Right Click)."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QActionGroup
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
        
        # Fade Region Detection using Precision Projection
        fps = self.get_fps()
        clip_x = self.frameToProjectedX(clip.start_frame)
        clip_w = self.frameToProjectedX(clip.duration_frames)
        rel_x = pos.x() - clip_x
        
        fade_in_w = self.frameToProjectedX(clip.fade_in_frames)
        is_fade_in = 0 <= rel_x <= fade_in_w and fade_in_w > 0
        
        fade_out_w = self.frameToProjectedX(clip.fade_out_frames)
        is_fade_out = (clip_w - fade_out_w) <= rel_x <= clip_w and fade_out_w > 0
        
        if is_fade_in or is_fade_out:
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
            menu.addSeparator()

        menu.addAction("Eliminar").triggered.connect(partial(self.delete_clip, clip))
        menu.addAction("Dividir").triggered.connect(partial(self.split_clip_at_pos, clip, pos))
        menu.exec(self.mapToGlobal(pos))
        
    def delete_clip(self, clip=None):
        """Delete clips following Linked philosophy."""
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
        """Split based on screen click position."""
        if not clip: return
        split_frame = self.screenXToFrame(pos.x())
        self.split_clip(clip, split_frame)

    def split_clip(self, clip, split_frame):
        """Mathematical split logic."""
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
        """Auto-zoom timeline to fit all content in visible area."""
        max_frame = self.model.get_max_frame()
        if max_frame <= 0:
            return
        
        # Get scroll area width
        scroll_area = self.get_scroll_area_context()
        if scroll_area:
            viewport_width = scroll_area.viewport().width()
            h_scroll = scroll_area.horizontalScrollBar()
        else:
            viewport_width = self.width()
            h_scroll = None
        
        # Calculate pixels per second to fit content
        fps = self.get_fps()
        duration_seconds = max_frame / fps
        if duration_seconds > 0:
            # Leave extreme padding (10% of viewport) to ensure it's ultra zoomed out
            target_pps = (viewport_width * 0.1) / duration_seconds
            target_pps = max(10, min(500, target_pps))  # Clamp
            
            if animate:
                self.zoom_anim.stop()
                self.zoom_anim.setDuration(800)
                self.zoom_anim.setStartValue(self.pixels_per_second)
                self.zoom_anim.setEndValue(target_pps)
                self.zoom_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                
                # If we have a scroll area, also animate the scroll to center/reveal the whole thing
                if h_scroll:
                    # We might need a separate QPropertyAnimation for the scroll bar
                    # Since we can't easily add a property to QScrollBar from here, 
                    # we can animate a dummy property or just use a Timer-based approach, 
                    # but QPropertyAnimation on the scrollbar's value is also possible if we wrap it.
                    # Standard way in PySide6 is to animate the scrollbar value directly.
                    # Note: viewport_width is used to calculate target_pps such that duration_seconds fits.
                    # We usually want to scroll so the content starts with some padding.
                    target_scroll = 0 # Reveal from the start
                    
                    self.scroll_anim = QPropertyAnimation(h_scroll, b"value")
                    self.scroll_anim.setDuration(800)
                    self.scroll_anim.setStartValue(h_scroll.value())
                    self.scroll_anim.setEndValue(target_scroll)
                    self.scroll_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                    
                    # Run them together
                    self.group = QParallelAnimationGroup()
                    self.group.addAnimation(self.zoom_anim)
                    self.group.addAnimation(self.scroll_anim)
                    self.group.start()
                else:
                    self.zoom_anim.start()
            else:
                self.pixels_per_second = target_pps
                if h_scroll:
                    h_scroll.setValue(0)
                self.updateGeometry()
                self.update()
                self.view_updated.emit()
