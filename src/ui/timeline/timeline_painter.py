"""
Timeline Painter - Handles all visual rendering for the SimpleTimeline widget.
Extracted for optimization and separation of concerns.
"""

from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QPainterPath
import math
from ..models import FadeType, TrackType, ProxyStatus
from .. import design_tokens as dt

class TimelinePainter:
    """
    Handles drawing logic for the SimpleTimeline.
    """
    
    # Class-level Constants for Optimization
    COLOR_BG = QColor(30, 30, 30)
    COLOR_GRID_MAJOR = QColor(80, 80, 80, 150)
    COLOR_GRID_MINOR = QColor(60, 60, 60, 80)
    COLOR_TRACK_DIVIDER = QColor(40, 40, 40)
    
    COLOR_VIDEO_BODY = QColor("#763436")
    COLOR_VIDEO_HEADER = QColor("#9E4347")
    COLOR_AUDIO_BODY = QColor("#3a9b8f")
    COLOR_AUDIO_HEADER = QColor("#49c2b3")
    COLOR_TEXT = QColor(230, 230, 230)
    COLOR_SELECTION = QColor("#FFFF00")
    COLOR_PLAYHEAD = QColor(0, 0, 0)
    COLOR_PLAYHEAD_LINE = QColor(255, 255, 255)
    
    # Button Colors
    COLOR_BTN_FX = QColor("#000000")
    COLOR_BTN_PROXY_GEN = QColor("#FF8800")
    COLOR_BTN_PROXY_READY = QColor("#00FF00")
    COLOR_BTN_PROXY_OFF = QColor("#000000")
    COLOR_BTN_SUB = QColor("#673AB7") # Purple for Subs
    COLOR_BTN_TEXT = QColor("#FFFFFF")
    COLOR_BTN_TEXT_BLACK = QColor("#000000")
    
    def __init__(self, timeline):
        """
        Initialize with reference to the timeline widget.
        :param timeline: The SimpleTimeline instance.
        """
        self.timeline = timeline
        self.model = timeline.model
        
        # Pre-load Button Images
        import os
        base_img_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "img")
        self.img_px = QImage(os.path.join(base_img_path, "px.png"))
        self.img_inf = QImage(os.path.join(base_img_path, "inf.png"))

    def paint(self, event):
        """Main paint method called from SimpleTimeline.paintEvent."""
        painter = QPainter(self.timeline)
        
        if not painter.isActive():
            return
        
        # Visible region for culling
        visible_rect = event.rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        try:
            # 1. BACKGROUND
            painter.fillRect(visible_rect, self.COLOR_BG)
            
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

    def _draw_grid(self, painter, rect):
        """[VEGAS REDESIGN] Draw vertical grid lines based on adaptive subdivisions."""
        pps = self.timeline.pixels_per_second
        fps = self.timeline.get_fps()
        
        major_step, divs = self.timeline.calculate_adaptive_step(pps, fps)
        minor_step = major_step / float(divs)
        
        start_time = self.timeline.screenXToTime(rect.left())
        end_time = self.timeline.screenXToTime(rect.right())
        
        # Align to major step
        t_major = math.floor(start_time / major_step) * major_step
        
        pen_major = QPen(self.COLOR_GRID_MAJOR, 1, Qt.PenStyle.DotLine)
        pen_minor = QPen(self.COLOR_GRID_MINOR, 1, Qt.PenStyle.DotLine)
        
        height = self.timeline.height()
        
        while t_major < end_time + major_step:
            # 1. Draw Minor Subdivisions first
            painter.setPen(pen_minor)
            for i in range(1, divs):
                t_minor = t_major + (i * minor_step)
                x_minor = self.timeline.timeToProjectedX(t_minor)
                if rect.left() <= x_minor <= rect.right():
                    painter.drawLine(QLineF(x_minor, 0, x_minor, height))
            
            # 2. Draw Major Line
            painter.setPen(pen_major)
            x_major = self.timeline.timeToProjectedX(t_major)
            if rect.left() <= x_major <= rect.right():
                painter.drawLine(QLineF(x_major, 0, x_major, height))
            
            t_major += major_step

    def _draw_tracks(self, painter):
        """Draw horizontal track dividers based on actual model tracks."""
        painter.setPen(QPen(self.COLOR_TRACK_DIVIDER, 1))
        
        current_y = 0
        width = self.timeline.width()
        total_height = self.timeline.height()
        
        for i, height in enumerate(self.model.track_heights):
            current_y += height
            if current_y < total_height:
                painter.drawLine(0, current_y, width, current_y)

    def _draw_clips(self, painter, visible_rect):
        """[VEGAS REDESIGN] Deterministic clip drawing with floating point precision."""
        
        font = painter.font()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        
        track_y_positions = self.timeline._get_track_y_positions()
        
        for clip in self.model.clips:
            if clip.track_index >= len(track_y_positions):
                continue
            
            # [VEGAS PRINCIPLE] Precision Projection
            clip_x = self.timeline.frameToProjectedX(clip.start_frame)
            clip_w = self.timeline.frameToProjectedX(clip.duration_frames)
            
            # CULLING (Precision Check)
            if clip_x + clip_w < visible_rect.left() or clip_x > visible_rect.right():
                continue
            
            track_y = track_y_positions[clip.track_index]
            track_h = self.model.track_heights[clip.track_index]
            clip_h = track_h - 2
            
            # Track Type Colors
            is_video = (clip.track_index < len(self.model.track_types) and self.model.track_types[clip.track_index] == TrackType.VIDEO)
            
            if is_video:
                body_col = self.COLOR_VIDEO_BODY
                header_col = self.COLOR_VIDEO_HEADER
            else:
                body_col = self.COLOR_AUDIO_BODY
                header_col = self.COLOR_AUDIO_HEADER
                
            if clip.selected:
                 body_col = body_col.lighter(130)
                 header_col = header_col.lighter(130)
            
            # 1. Body & Header Path (Chamfered Top Corners)
            cut_size = 10.0
            clip_path = QPainterPath()
            clip_path.moveTo(clip_x, track_y + 1 + clip_h) # Bottom-left
            clip_path.lineTo(clip_x + clip_w, track_y + 1 + clip_h) # Bottom-right
            clip_path.lineTo(clip_x + clip_w, track_y + 1 + cut_size) # Below top-right chamfer
            clip_path.lineTo(clip_x + clip_w - cut_size, track_y + 1) # Top-right chamfer end
            clip_path.lineTo(clip_x + cut_size, track_y + 1) # Top-left chamfer start
            clip_path.lineTo(clip_x, track_y + 1 + cut_size) # Top-left chamfer end
            clip_path.closeSubpath()
            
            # Draw Unified Body (Header + Content area as one piece)
            painter.setPen(Qt.NoPen)
            # Use header_col as the primary color for the unified piece 
            # as it represents the "identity" color of the track (Red for Video / Teal for Audio)
            painter.setBrush(header_col)
            painter.drawPath(clip_path)
            
            # --- WAVEFORM / THUMBNAILS ---
            header_h = 22 # Increased from 14 for larger buttons
            content_y = track_y + header_h + 1
            content_h = clip_h - header_h
            
            rect_header = QRectF(clip_x, track_y + 1, clip_w, header_h)
            
            if is_video:
                if hasattr(clip, 'thumbnails') and clip.thumbnails:
                    painter.save()
                    painter.setClipPath(clip_path)
                    self._draw_thumbnail(painter, clip, clip_x, content_y, clip_w, content_h, visible_rect)
                    painter.restore()
            else:
                if hasattr(clip, 'waveform') and clip.waveform:
                    self._draw_waveform(painter, clip.waveform, clip_x, content_y, clip_w, content_h, visible_rect)
                elif getattr(clip, 'waveform_computing', False):
                    painter.setPen(QColor(255, 255, 255, 100))
                    painter.drawText(int(clip_x) + 5, int(track_y) + 30, "Computing peaks...")
            
            # 3. Text
            painter.setPen(self.COLOR_TEXT)
            font = painter.font()
            font.setPointSize(9) 
            font.setBold(False)
            painter.setFont(font)
            
            # Estimate large button area to avoid overlap
            btn_w = 28 
            
            # Offset text to avoid chamfer and large buttons
            text_rect = rect_header.adjusted(cut_size + 4, 0, - (btn_w * 2 + 20), 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, clip.name)
            
            # 4. Envelopes (Opacity/Fades)
            self._draw_clip_envelopes(painter, clip, clip_x, clip_w, track_y, clip_h)
            
            # 5. Buttons (FX, PX)
            self._draw_clip_buttons(painter, clip, clip_x, clip_w, track_y, cut_size)
            
            # 6. Selection Border
            if clip.selected:
                painter.setPen(QPen(self.COLOR_SELECTION, 1.5))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(clip_path)

    def _draw_clip_envelopes(self, painter, clip, clip_x, clip_w, track_y, clip_h):
        """Draws the opacity/fade envelope and handles for a clip."""
        body_start_y = track_y + 1
        body_end_y = track_y + 1 + clip_h
        body_height = body_end_y - body_start_y
        
        opacity_level = getattr(clip, 'opacity_level', 1.0)
        target_y = body_start_y + (1.0 - opacity_level) * body_height
        
        fade_in_w = self.timeline.frameToProjectedX(clip.fade_in_frames)
        fade_out_w = self.timeline.frameToProjectedX(clip.fade_out_frames)
        
        envelope = QPainterPath()
        p_start_fi = QPointF(clip_x, body_end_y)
        envelope.moveTo(p_start_fi)
        
        # Fade In
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
        
        # Fade Out
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
        
        # Opacity Handle (Center Blue Bar - Moves vertically with opacity)
        bar_w = min(clip_w * 0.4, 40)
        center_x = clip_x + clip_w / 2
        painter.setBrush(QColor(0, 0, 255)) # Pure Blue
        painter.setPen(Qt.NoPen)
        # Position it at target_y instead of static top
        painter.drawRect(QRectF(center_x - bar_w/2, target_y - 1.5, bar_w, 3))
        
        # Fade Handles (Top Triangles - positioned inside chamfer with gap)
        COLOR_FADE_HANDLE = QColor(255, 255, 255)
        cut_size = 10.0
        
        # Triangle positioned inside the chamfer area
        triangle_size = 5.0
        gap = 1.5  # Gap between triangle and the clip body edge
        
        # Top-Left Fade Handle (inside the chamfer, separated from body)
        path_tl = QPainterPath()
        # Start at the chamfer diagonal, offset inward
        path_tl.moveTo(clip_x + gap, track_y + 1 + gap)
        path_tl.lineTo(clip_x + gap + triangle_size, track_y + 1 + gap)
        path_tl.lineTo(clip_x + gap, track_y + 1 + gap + triangle_size)
        path_tl.closeSubpath()
        painter.fillPath(path_tl, COLOR_FADE_HANDLE)
        
        # Top-Right Fade Handle (inside the chamfer, separated from body)
        path_tr = QPainterPath()
        path_tr.moveTo(clip_x + clip_w - gap, track_y + 1 + gap)
        path_tr.lineTo(clip_x + clip_w - gap - triangle_size, track_y + 1 + gap)
        path_tr.lineTo(clip_x + clip_w - gap, track_y + 1 + gap + triangle_size)
        path_tr.closeSubpath()
        painter.fillPath(path_tr, COLOR_FADE_HANDLE)



    def _draw_clip_buttons(self, painter, clip, clip_x, clip_w, track_y, cut_size):
        """Draws FX and PX buttons using images on the clip header."""
        button_w = 18
        button_h = 18
        spacing = 8
        
        # 1. Determine State for PX
        p_status = getattr(clip, 'proxy_status', ProxyStatus.NONE)
        global_proxy_on = False
        try:
            main_window = self.timeline.window()
            if hasattr(main_window, 'toolbar'):
                global_proxy_on = main_window.toolbar.btn_proxy.isChecked()
        except: pass

        px_active = (p_status == ProxyStatus.READY and getattr(clip, 'use_proxy', False) and global_proxy_on)
        
        # 2. Draw PX Button (Rightmost)
        px_x = clip_x + clip_w - button_w - cut_size - 4
        px_y = track_y + 1 + (22 - button_h) / 2
        rect_px = QRectF(px_x, px_y, button_w, button_h)
        
        if not self.img_px.isNull():
            if px_active:
                # Proper Tinting: Create a copy and tint it green
                # This avoids messing with the clip's background
                tinted = self.img_px.copy()
                tp = QPainter(tinted)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tp.fillRect(tinted.rect(), QColor(0, 255, 0)) # Clean Green
                tp.end()
                painter.drawImage(rect_px, tinted)
            else:
                # Normal state: White image as is
                painter.drawImage(rect_px, self.img_px)
        else:
            painter.setPen(QColor(0, 255, 0) if px_active else self.COLOR_BTN_TEXT)
            painter.drawText(rect_px, Qt.AlignmentFlag.AlignCenter, "PX")

        # 3. Draw FX Button (Left of PX)
        fx_x = px_x - button_w - spacing
        fx_y = px_y
        rect_fx = QRectF(fx_x, fx_y, button_w, button_h)
        
        is_fx_target = getattr(clip, 'is_fx_active', False)
        
        if not self.img_inf.isNull():
            if is_fx_target:
                # Proper Tinting: Blue focus
                tinted_inf = self.img_inf.copy()
                tp = QPainter(tinted_inf)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tp.fillRect(tinted_inf.rect(), QColor(0, 180, 255))
                tp.end()
                painter.drawImage(rect_fx, tinted_inf)
            else:
                painter.drawImage(rect_fx, self.img_inf)
        else:
            painter.setPen(QColor(0, 180, 255) if is_fx_target else self.COLOR_BTN_TEXT)
            painter.drawText(rect_fx, Qt.AlignmentFlag.AlignCenter, "...")
        
        # SUB Button removed as per simplified design



    def _draw_waveform(self, painter, peaks, x, y, w, h, visible_rect):
        """[VEGAS REDESIGN] Stereo Waveform Drawing (L/R Channels)."""
        if not peaks or w < 1:
            return
            
        # Split height for stereo display
        h_per_ch = h / 2.0
        mid_y_l = y + (h_per_ch / 2.0)
        mid_y_r = y + h_per_ch + (h_per_ch / 2.0)
        
        # Interleaved peaks: L, R, L, R...
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
        """Draw playhead using absolute time projection."""
        ph_x = self.timeline.frameToProjectedX(self.timeline.model.blueline.playhead_frame)
        
        # Consistent Precision Drawing
        line = QLineF(ph_x, 0, ph_x, self.timeline.height())
        
        painter.setPen(QPen(self.COLOR_PLAYHEAD, 3))
        painter.drawLine(line)
        
        painter.setPen(QPen(self.COLOR_PLAYHEAD_LINE, 1))
        painter.drawLine(line)
