"""
Timeline Painter - Handles all visual rendering for the SimpleTimeline widget.
Extracted for optimization and separation of concerns.
"""

from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QPainterPath
import math
from ..core.models import FadeType, TrackType, ProxyStatus, TICKS_PER_SECOND
from ..core import design_tokens as dt

class TimelinePainter:
    """
    Handles drawing logic for the SimpleTimeline.
    """
    
    # --- CONFIGURATION (CONSTANTS) ---
    class Palette:
        """Centralized Color Scheme for Timeline Elements."""
        BG = QColor(30, 30, 30)
        GRID_MAJOR = QColor(80, 80, 80, 150)
        GRID_MINOR = QColor(60, 60, 60, 80)
        TRACK_DIVIDER = QColor(40, 40, 40)
        
        VIDEO_BODY = QColor("#763436")
        VIDEO_HEADER = QColor("#9E4347")
        AUDIO_BODY = QColor("#1c2224")
        AUDIO_HEADER = QColor("#2a3539")
        
        TEXT_PRIMARY = QColor(230, 230, 230)
        SELECTION_BORDER = QColor("#FFFF00")
        PLAYHEAD_BODY = QColor(0, 0, 0)
        PLAYHEAD_LINE = QColor(255, 255, 255)
        
        # UI Elements
        BTN_TEXT_ACTIVE = QColor("#00FF00")
        BTN_TEXT_INACTIVE = QColor("#FFFFFF")
        FADE_HANDLE = QColor(255, 255, 255)

    class Dimensions:
        """Layout Measurements (Pixels)."""
        HEADER_HEIGHT = 28
        BUTTON_SIZE = 24
        BUTTON_SPACING = 8
        CHAMFER_SIZE = 10.0   # Corner cut size
        FADE_TRIANGLE = 5.0   # Size of fade handles
        FADE_GAP = 1.5        # Padding from edge
    
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
        
        # Performance Cache
        self._waveform_cache = {} # Key: (clip_id, width, height), Value: QImage
        self._last_pps = timeline.pixels_per_second

    def paint(self, event):
        """Main paint method called from SimpleTimeline.paintEvent."""
        painter = QPainter(self.timeline)
        
        if not painter.isActive():
            return
        
        # Visible region for culling
        visible_rect = event.rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        try:
            # 1. BACKGROUND
            painter.fillRect(visible_rect, self.Palette.BG)
            
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
        
        pen_major = QPen(self.Palette.GRID_MAJOR, 1, Qt.PenStyle.DotLine)
        pen_minor = QPen(self.Palette.GRID_MINOR, 1, Qt.PenStyle.DotLine)
        
        height = self.timeline.height()
        
        while t_major < end_time + major_step:
            # 1. Draw Minor Subdivisions first
            painter.setPen(pen_minor)
            for i in range(1, divs):
                t_minor = t_major + (i * minor_step)
                x_minor = self.timeline.tickToProjectedX(int(t_minor * TICKS_PER_SECOND))
                if rect.left() <= x_minor <= rect.right():
                    painter.drawLine(QLineF(x_minor, 0, x_minor, height))
            
            # 2. Draw Major Line
            painter.setPen(pen_major)
            x_major = self.timeline.tickToProjectedX(int(t_major * TICKS_PER_SECOND))
            if rect.left() <= x_major <= rect.right():
                painter.drawLine(QLineF(x_major, 0, x_major, height))
            
            t_major += major_step

    def _draw_tracks(self, painter):
        """Draw horizontal track dividers based on actual model tracks."""
        painter.setPen(QPen(self.Palette.TRACK_DIVIDER, 1))
        
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
            
            # [VEGAS PRINCIPLE] Precision Projection (Tick-Engine)
            clip_x = self.timeline.tickToProjectedX(clip.start_tick)
            clip_w = self.timeline.tickToProjectedX(clip.duration_ticks)
            
            # CULLING (Precision Check)
            if clip_x + clip_w < visible_rect.left() or clip_x > visible_rect.right():
                continue
            
            track_y = track_y_positions[clip.track_index]
            track_h = self.model.track_heights[clip.track_index]
            clip_h = track_h - 2
            
            # Track Type Colors
            is_video = (clip.track_index < len(self.model.track_types) and self.model.track_types[clip.track_index] == TrackType.VIDEO)
            
            if is_video:
                body_col = self.Palette.VIDEO_BODY
                header_col = self.Palette.VIDEO_HEADER
            else:
                body_col = self.Palette.AUDIO_BODY
                header_col = self.Palette.AUDIO_HEADER
                
            if clip.selected:
                 body_col = body_col.lighter(130)
                 header_col = header_col.lighter(130)
            
            # 1. Body & Header Path (Proprietary Chamfer Shape)
            # ADAPTIVE: Cap chamfer size to avoid path inversion on tiny clips
            cut_size = min(self.Dimensions.CHAMFER_SIZE, clip_w / 2.0)
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
            header_h = self.Dimensions.HEADER_HEIGHT 
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
                # 2. DRAW WAVEFORM (Zoom Synced)
                if clip_w > 10:
                    painter.save()
                    painter.setClipPath(clip_path)
                    self._draw_waveform(painter, clip, clip_x, content_y, clip_w, content_h, visible_rect)
                    painter.restore()
            
            # 3. Text & Buttons
            if clip_w > 40:
                painter.setPen(self.Palette.TEXT_PRIMARY)
                font = painter.font()
                font.setPointSize(9) 
                font.setBold(False)
                painter.setFont(font)
                
                # Estimate large button area to avoid overlap
                btn_w = 28 
                
                # Offset text to avoid chamfer and large buttons
                text_rect = rect_header.adjusted(cut_size + 4, 0, - (btn_w * 2 + 20), 0)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, clip.name)
                
                # 4. Envelopes (Opacity/Fades) - Only show if useful
                self._draw_clip_envelopes(painter, clip, clip_x, clip_w, track_y, clip_h)
                
                # 5. Buttons (FX, PX)
                self._draw_clip_buttons(painter, clip, clip_x, clip_w, track_y, cut_size)
            else:
                # For tiny clips, just a solid vertical line/block
                pass
            
            # 6. Selection Border
            if clip.selected:
                painter.setPen(QPen(self.Palette.SELECTION_BORDER, 1.5))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(clip_path)

    def _draw_clip_envelopes(self, painter, clip, clip_x, clip_w, track_y, clip_h):
        """Draws the opacity/fade envelope and handles for a clip."""
        body_start_y = track_y + 1
        body_end_y = track_y + 1 + clip_h
        body_height = body_end_y - body_start_y
        
        opacity_level = getattr(clip, 'opacity_level', 1.0)
        target_y = body_start_y + (1.0 - opacity_level) * body_height
        
        fade_in_w = self.timeline.tickToProjectedX(clip.fade_in_ticks)
        fade_out_w = self.timeline.tickToProjectedX(clip.fade_out_ticks)
        
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
        COLOR_FADE_HANDLE = self.Palette.FADE_HANDLE
        cut_size = self.Dimensions.CHAMFER_SIZE
        
        # Triangle positioned inside the chamfer area
        triangle_size = self.Dimensions.FADE_TRIANGLE
        gap = self.Dimensions.FADE_GAP  # Gap between triangle and the clip body edge
        
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
        button_w = self.Dimensions.BUTTON_SIZE
        button_h = self.Dimensions.BUTTON_SIZE
        spacing = self.Dimensions.BUTTON_SPACING
        
        # 1. Determine State for PX
        p_status = getattr(clip, 'proxy_status', ProxyStatus.NONE)
        global_proxy_on = False
        try:
            main_window = self.timeline.window()
            if hasattr(main_window, 'toolbar'):
                global_proxy_on = main_window.toolbar.btn_proxy.isChecked()
        except: pass

        # Logic: 
        # - Orange: Generating
        # - Green: Ready and Global Proxy is ON
        # - White: Else
        px_tint = None
        if p_status == ProxyStatus.GENERATING:
            px_tint = QColor(dt.ACCENT_WARNING)
        elif p_status == ProxyStatus.READY and global_proxy_on:
            px_tint = QColor(dt.ACCENT_SUCCESS)
            
        # 2. Draw PX Button (Rightmost)
        px_x = clip_x + clip_w - button_w - cut_size - 4
        px_y = track_y + 1 + (self.Dimensions.HEADER_HEIGHT - button_h) / 2
        rect_px = QRectF(px_x, px_y, button_w, button_h)
        
        if not self.img_px.isNull():
            if px_tint:
                # Proper Tinting: Create a copy and tint it
                tinted = self.img_px.copy()
                tp = QPainter(tinted)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tp.fillRect(tinted.rect(), px_tint)
                tp.end()
                painter.drawImage(rect_px, tinted)
            else:
                # Normal state: White image as is
                painter.drawImage(rect_px, self.img_px)
        else:
            painter.setPen(px_tint if px_tint else self.Palette.BTN_TEXT_INACTIVE)
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
            painter.setPen(QColor(0, 180, 255) if is_fx_target else self.Palette.BTN_TEXT_INACTIVE)
            painter.drawText(rect_fx, Qt.AlignmentFlag.AlignCenter, "...")
        
        # SUB Button removed as per simplified design


    def _draw_thumbnail(self, painter, clip, x, y, w, h, visible_rect):
        """Draws thumbnails with viewport culling."""
        if not clip.thumbnails: return
        
        thumb_h = h
        thumb_w = int(thumb_h * 1.77)
        
        # Determine thumbnail positions (start, middle, end)
        start_x = x
        mid_x = x + (w - thumb_w) / 2
        end_x = x + w - thumb_w
        
        # Only draw when there is enough space to avoid heavy overlap
        draw_start = True
        draw_end = w >= thumb_w * 2
        draw_mid = w >= thumb_w * 3 and len(clip.thumbnails) > 1
        
        # Only draw if the thumbnail position overlaps with viewport
        if draw_start and start_x + thumb_w > visible_rect.left() and start_x < visible_rect.right():
             self._paint_thumb(painter, clip.thumbnails[0], start_x, y, thumb_w, thumb_h)
        
        if draw_mid and mid_x + thumb_w > visible_rect.left() and mid_x < visible_rect.right():
             mid_idx = 1 if len(clip.thumbnails) > 1 else 0
             self._paint_thumb(painter, clip.thumbnails[mid_idx], mid_x, y, thumb_w, thumb_h)
        
        if draw_end and end_x + thumb_w > visible_rect.left() and end_x < visible_rect.right() and len(clip.thumbnails) > 2:
             self._paint_thumb(painter, clip.thumbnails[2], end_x, y, thumb_w, thumb_h)

    def _paint_thumb(self, painter, thumb_data, x, y, w, h):
        """Internal helper for pixel data painting."""
        try:
            if isinstance(thumb_data, QImage):
                painter.drawImage(QRectF(x, y, w, h), thumb_data)
                return
            
            height, width, channel = thumb_data.shape
            bytes_per_line = 3 * width
            q_img = QImage(thumb_data.data, width, height, bytes_per_line, QImage.Format_RGB888)
            painter.drawImage(QRectF(x, y, w, h), q_img)
        except: pass

    def _draw_waveform(self, painter, clip, x, y, w, h, visible_rect):
        """Draws audio waveforms using C++ extracted peaks with viewport culling."""
        # 1. Calculate VISIBLE sub-region of the clip on screen
        draw_x_start = max(x, visible_rect.left())
        draw_x_end = min(x + w, visible_rect.right())
        
        if draw_x_start >= draw_x_end: return
        
        visible_pixel_w = int(draw_x_end - draw_x_start)
        if visible_pixel_w <= 0: return

        # 2. Map screen region to clip-local time for C++ peak extraction
        clip_duration_sec = clip.duration_ticks / float(TICKS_PER_SECOND)
        source_clip_start_sec = clip.source_offset_ticks / float(TICKS_PER_SECOND)
        
        start_ratio = (draw_x_start - x) / float(w)
        width_ratio = (draw_x_end - draw_x_start) / float(w)
        
        req_start_time = source_clip_start_sec + (start_ratio * clip_duration_sec)
        req_duration = width_ratio * clip_duration_sec
        
        # Number of buckets = Exactly the number of pixels we will draw
        num_buckets = visible_pixel_w
        
        try:
            # Find the editor instance to access the media cache
            editor = None
            curr = self.timeline
            while curr:
                if hasattr(curr, 'media_source_cache'):
                    editor = curr
                    break
                curr = curr.parent()
            
            if not editor: return
            
            use_proxies = False
            if hasattr(editor, 'toolbar'):
                use_proxies = editor.toolbar.btn_proxy.isChecked()
            
            path_to_use = clip.file_path
            if use_proxies and clip.proxy_status == ProxyStatus.READY and clip.proxy_path:
                path_to_use = clip.proxy_path
            
            if path_to_use not in editor.media_source_cache: return
            source = editor.media_source_cache[path_to_use]
            
            # OPTIMIZED CALL: Request only visible peaks
            peaks = source.get_peaks(req_start_time, req_duration, num_buckets)
            if not peaks: return
            
            # Colors from hondaaudio.py
            color_l = QColor("#00d4ff") # Cyan
            color_r = QColor("#ff2e97") # Hot Pink
            
            channel_h = h / 2
            scale = (channel_h / 2) * 0.8 # Waveform amplitude scale
            
            # Draw L (Top half of content area)
            painter.setPen(QPen(color_l, 1))
            y_center_l = y + channel_h / 2
            for i in range(num_buckets):
                px = draw_x_start + i
                p_min = peaks[i*2]
                p_max = peaks[i*2+1]
                
                y0 = y_center_l - (p_max * scale)
                y1 = y_center_l - (p_min * scale)
                painter.drawLine(px, int(y0), px, int(y1))

            # Draw R (Bottom half)
            painter.setPen(QPen(color_r, 1))
            y_center_r = y + channel_h + channel_h / 2
            for i in range(num_buckets):
                px = draw_x_start + i
                p_min = peaks[i*2]
                p_max = peaks[i*2+1]
                
                y0 = y_center_r - (p_max * scale)
                y1 = y_center_r - (p_min * scale)
                painter.drawLine(px, int(y0), px, int(y1))
                
        except Exception as e:
            pass

    def _render_waveform_to_painter(self, painter, clip, x, y, w, h):
        """Unified rendering logic for waveforms into any painter."""
        clip_duration_sec = clip.duration_ticks / float(TICKS_PER_SECOND)
        source_clip_start_sec = clip.source_offset_ticks / float(TICKS_PER_SECOND)
        
        num_buckets = int(w)
        if num_buckets <= 0: return

        try:
            editor = self._find_editor()
            if not editor: return
            
            use_proxies = False
            if hasattr(editor, 'toolbar'):
                use_proxies = editor.toolbar.btn_proxy.isChecked()
            
            path_to_use = clip.file_path
            if use_proxies and clip.proxy_status == ProxyStatus.READY and clip.proxy_path:
                path_to_use = clip.proxy_path
            
            if path_to_use not in editor.media_source_cache: return
            source = editor.media_source_cache[path_to_use]
            
            peaks = source.get_peaks(source_clip_start_sec, clip_duration_sec, num_buckets)
            if not peaks: return
            
            color_l, color_r = QColor("#00d4ff"), QColor("#ff2e97")
            channel_h = h / 2
            scale = (channel_h / 2) * 0.8 
            
            # L
            painter.setPen(QPen(color_l, 1))
            y_center_l = y + channel_h / 2
            for i in range(num_buckets):
                p_min, p_max = peaks[i*2], peaks[i*2+1]
                painter.drawLine(int(x + i), int(y_center_l - p_max * scale), int(x + i), int(y_center_l - p_min * scale))

            # R
            painter.setPen(QPen(color_r, 1))
            y_center_r = y + channel_h + channel_h / 2
            for i in range(num_buckets):
                p_min, p_max = peaks[i*2], peaks[i*2+1]
                painter.drawLine(int(x + i), int(y_center_r - p_max * scale), int(x + i), int(y_center_r - p_min * scale))
                
        except Exception: pass

    def _render_waveform_direct(self, painter, clip, x, y, w, h, visible_rect):
        """Fallback direct rendering for extremely long segments."""
        draw_x_start = max(x, visible_rect.left())
        draw_x_end = min(x + w, visible_rect.right())
        visible_pixel_w = int(draw_x_end - draw_x_start)
        if visible_pixel_w <= 0: return

        clip_duration_sec = clip.duration_ticks / float(TICKS_PER_SECOND)
        source_clip_start_sec = clip.source_offset_ticks / float(TICKS_PER_SECOND)
        start_ratio = (draw_x_start - x) / float(w)
        width_ratio = (draw_x_end - draw_x_start) / float(w)
        
        req_start_time = source_clip_start_sec + (start_ratio * clip_duration_sec)
        req_duration = width_ratio * clip_duration_sec
        
        try:
            editor = self._find_editor()
            if not editor or clip.file_path not in editor.media_source_cache: return
            source = editor.media_source_cache[clip.file_path]
            peaks = source.get_peaks(req_start_time, req_duration, visible_pixel_w)
            if not peaks: return
            
            color_l, color_r = QColor("#00d4ff"), QColor("#ff2e97")
            channel_h = h / 2
            scale = (channel_h / 2) * 0.8
            
            for i in range(visible_pixel_w):
                px = draw_x_start + i
                y_l = y + channel_h / 2
                y_r = y + channel_h + channel_h / 2
                painter.setPen(QPen(color_l, 1))
                painter.drawLine(int(px), int(y_l - peaks[i*2+1]*scale), int(px), int(y_l - peaks[i*2]*scale))
                painter.setPen(QPen(color_r, 1))
                painter.drawLine(int(px), int(y_r - peaks[i*2+1]*scale), int(px), int(y_r - peaks[i*2]*scale))
        except: pass

    def _find_editor(self):
        """Finds the editor instance to access the media cache."""
        curr = self.timeline
        while curr:
            if hasattr(curr, 'media_source_cache'):
                return curr
            curr = curr.parent()
        return None

    def invalidate_cache(self, clip_id=None):
        """Clears the waveform cache."""
        if clip_id:
            keys_to_del = [k for k in self._waveform_cache.keys() if k[0] == clip_id]
            for k in keys_to_del: del self._waveform_cache[k]
        else:
            self._waveform_cache.clear()

    def _draw_playhead(self, painter):
        """Draw playhead using absolute Tick projection."""
        ph_x = int(self.timeline.tickToProjectedX(self.timeline.model.blueline.playhead_tick))
        line = QLineF(ph_x, 0, ph_x, self.timeline.height())
        painter.setPen(QPen(self.Palette.PLAYHEAD_BODY, 3))
        painter.drawLine(line)
        painter.setPen(QPen(self.Palette.PLAYHEAD_LINE, 1))
        painter.drawLine(line)
