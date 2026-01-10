from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QImage, QPolygon
import math
from ..models import TrackType, FadeType
from .constants import *

class TimelineRenderer:
    def paintEvent(self, event):
        """Main rendering pipeline for the timeline surface."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Background
        painter.fillRect(self.rect(), BG_COLOR)
        
        # 2. Structural Elements
        self.draw_track_selection_highlights(painter)
        self.draw_grid(painter)
        self._draw_track_dividers(painter)
        
        # 3. Dynamic Elements (Clips, Cursors)
        track_y_positions = self._get_track_vertical_offsets()
        for clip in self.model.clips:
            self.draw_clip(painter, clip, track_y_positions)
            
        self._draw_interaction_overlays(painter)
        self._draw_playhead(painter)

    def _draw_track_dividers(self, painter):
        current_y = 0
        painter.setPen(QPen(Qt.black, 1))
        for height in self.model.track_heights:
            painter.drawLine(0, current_y + height - 1, self.width(), current_y + height - 1)
            current_y += height

    def draw_track_selection_highlights(self, painter):
        """Draws a subtle horizontal highlight for selected tracks."""
        track_y_positions = self._get_track_vertical_offsets()
        highlight_color = QColor(116, 138, 145, 40)
        
        for idx in self.model.selected_tracks:
            if idx < len(track_y_positions) and idx < len(self.model.track_heights):
                y = track_y_positions[idx]
                h = self.model.track_heights[idx]
                painter.fillRect(0, y, self.width(), h, highlight_color)

    def _draw_interaction_overlays(self, painter):
        """Draws temporary UI elements during user interactions."""
        if self.active_clip and self.interaction_mode == MODE_GAIN:
            self._draw_value_tooltip(painter, f"Opacidad: {int(self.active_clip.start_opacity * 100)}%")

    def _draw_value_tooltip(self, painter, text):
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.setPen(Qt.white)
        painter.drawRoundedRect(self.mouse_x + 10, self.mouse_y - 25, 100, 20, 5, 5)
        painter.drawText(self.mouse_x + 15, self.mouse_y - 10, text)

    def _draw_playhead(self, painter):
        fps = self.get_fps()
        ph_x = self.timeToScreen(self.model.blueline.playhead_frame / fps)
        painter.setPen(QPen(QColor("#00aaff"), 2))
        painter.drawLine(ph_x, 0, ph_x, self.height())

    def draw_grid(self, painter):
        scroll_area = self.get_scroll_area_context()
        if not scroll_area: return
        
        view_start_px = scroll_area.horizontalScrollBar().value()
        view_end_time = (view_start_px + scroll_area.width()) / float(self.pixels_per_second)
        step = self._calculate_adaptive_grid_step()
        time_cursor = math.floor((view_start_px / float(self.pixels_per_second)) / step) * step
        
        pen = QPen(GRID_COLOR, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setDashPattern([0.1, 4]) # Maximum density (4px gap)
        painter.setPen(pen)
        
        while time_cursor < view_end_time + step:
            x_pos = self.timeToScreen(time_cursor)
            painter.drawLine(x_pos, 0, x_pos, self.height())
            time_cursor += step

    def _calculate_adaptive_grid_step(self) -> float:
        if self.pixels_per_second > 800: return 0.05
        if self.pixels_per_second > 200: return 0.1
        if self.pixels_per_second < 10:  return 30.0
        if self.pixels_per_second < 50:  return 5.0
        return 1.0

    def draw_clip(self, painter, clip, track_y_positions):
        if clip.track_index >= len(track_y_positions): return
        
        track_y = track_y_positions[clip.track_index]
        track_h = self.model.track_heights[clip.track_index]
        clip_x = self.timeToScreen(clip.start_frame / self.get_fps())
        clip_w = int(clip.duration_frames / self.get_fps() * self.pixels_per_second)
        
        if clip_x + clip_w < 0 or clip_x > self.width(): return
            
        is_video_track = self.model.track_types[clip.track_index] == TrackType.VIDEO
        theme = THEME_VIDEO if is_video_track else THEME_AUDIO
        
        self._draw_clip_infrastructure(painter, clip_x, track_y, clip_w, track_h, theme)
        
        if is_video_track:
            self._draw_video_thumbnails(painter, clip, clip_x, track_y, clip_w, track_h)
        else:
            self._draw_audio_waveform(painter, clip, clip_x, track_y, clip_w, track_h)
            
        self._draw_clip_header_content(painter, clip, clip_x, track_y, clip_w)
        self._draw_corner_indicators(painter, clip_x, track_y, clip_w)

        if clip.selected:
            self._draw_selection_highlight(painter, clip_x, track_y, clip_w, track_h)

        content_rect_y = track_y + CLIP_HEADER_HEIGHT
        content_rect_h = track_h - CLIP_HEADER_HEIGHT - 1
        self.draw_opacity_and_fades(painter, clip, clip_x, clip_w, content_rect_y, content_rect_h)

    def _draw_selection_highlight(self, painter, x, y, w, h):
        # Borde amarillo chillón (Neón)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ffff00"), 2))
        painter.drawRect(x, y, w, h - 1)

    def _draw_clip_infrastructure(self, painter, x, y, w, h, theme):
        painter.setBrush(theme["header"])
        painter.setPen(Qt.NoPen)
        painter.drawRect(x, y, w, CLIP_HEADER_HEIGHT)
        painter.setBrush(theme["body"])
        painter.drawRect(x, y + CLIP_HEADER_HEIGHT, w, h - CLIP_HEADER_HEIGHT - 1)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawLine(x, y + CLIP_HEADER_HEIGHT, x + w, y + CLIP_HEADER_HEIGHT)

    def _draw_video_thumbnails(self, painter, clip, x, y, w, h):
        if w < 20: return
        painter.save()
        content_y = y + CLIP_HEADER_HEIGHT + 1
        content_h = h - CLIP_HEADER_HEIGHT - 2
        painter.setClipRect(QRect(max(0, x), content_y, w, content_h))
        
        # Calculate thumbnail width maintaining aspect ratio (approx 16:9)
        thumb_w = int(content_h * 1.77)
        if thumb_w <= 0: thumb_w = 40

        if clip.thumbnails:
            # Draw START thumbnail
            painter.drawImage(QRect(x, content_y, thumb_w, content_h), clip.thumbnails[0])
            
            # Draw MIDDLE thumbnail if clip is long enough
            if w > thumb_w * 2.5 and len(clip.thumbnails) > 1:
                mid_x = x + (w - thumb_w) // 2
                painter.drawImage(QRect(mid_x, content_y, thumb_w, content_h), clip.thumbnails[1])
                
            # Draw END thumbnail if clip is long enough
            if w > thumb_w * 1.2 and len(clip.thumbnails) > 2:
                end_x = x + w - thumb_w
                painter.drawImage(QRect(end_x, content_y, thumb_w, content_h), clip.thumbnails[2])
            
            # Draw thin separators between thumbs for professional look
            painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
            painter.drawLine(x + thumb_w, content_y, x + thumb_w, content_y + content_h)
            if w > thumb_w * 2.5:
                mid_x = x + (w - thumb_w) // 2
                painter.drawLine(mid_x, content_y, mid_x, content_y + content_h)
                painter.drawLine(mid_x + thumb_w, content_y, mid_x + thumb_w, content_y + content_h)
            if w > thumb_w:
                painter.drawLine(x + w - thumb_w, content_y, x + w - thumb_w, content_y + content_h)
                
        elif clip.thumbnails_computing:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.setFont(QFont(".AppleSystemUIFont", 8, QFont.Bold))
            painter.drawText(x + 5, content_y + 15, "PROCESANDO MINIATURAS...")
        else:
            # Fallback placeholder
            painter.setBrush(QColor(0, 0, 0, 50))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x, content_y, thumb_w, content_h)
            if w > thumb_w * 2.5:
                painter.drawRect(x + (w - thumb_w) // 2, content_y, thumb_w, content_h)
            if w > thumb_w:
                painter.drawRect(x + w - thumb_w, content_y, thumb_w, content_h)
                
        painter.restore()

    def _draw_audio_waveform(self, painter, clip, x, y, w, h):
        if w < 10: return
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        content_y = y + CLIP_HEADER_HEIGHT
        content_h = h - CLIP_HEADER_HEIGHT
        mid_y = content_y + content_h // 2
        
        if clip.waveform:
            # Render REAL peaks analyzed in background (Sony Vegas Style)
            num_points = len(clip.waveform)
            # Simple decimation for performance: 1 pixel = 1 sample point (or more)
            for dx in range(0, w, 2):
                # Map screen relative pixel to waveform index
                idx = int((dx / w) * num_points)
                if idx < num_points:
                    mag = clip.waveform[idx] * content_h * 0.8
                    painter.drawLine(x + dx, int(mid_y - mag/2), x + dx, int(mid_y + mag/2))
        elif clip.waveform_computing:
            # Subtle feedback that analysis is in progress
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.setFont(QFont(".AppleSystemUIFont", 8, QFont.Bold))
            painter.drawText(x + 5, mid_y + 4, "ANÁLISIS DE AUDIO...")
        else:
            # Smooth sine fallback if source has no audio or analysis failed
            for dx in range(0, w, 2):
                magnification = (math.sin(dx * 0.1) + 1) * content_h * 0.4
                painter.drawLine(x + dx, int(mid_y - magnification/2), x + dx, int(mid_y + magnification/2))

    def _draw_clip_header_content(self, painter, clip, x, y, w):
        if w < 30: return
        painter.save()
        painter.setClipRect(x + 1, y + 1, w - 2, CLIP_HEADER_HEIGHT - 1)
        painter.setPen(Qt.white)
        painter.setFont(QFont(".AppleSystemUIFont", 9, QFont.Bold))
        label_x = max(x, 0) + 5
        button_area_w = 65 if w > 80 else 5
        if label_x < x + w - button_area_w:
            painter.drawText(label_x, y + 15, clip.name)
        if w > 80:
            # Determine PX button color based on clip status
            px_color = None
            try:
                # Assuming values: 0=NONE, 1=GENERATING, 2=READY, 3=ERROR
                if hasattr(clip, 'proxy_status') and clip.proxy_status is not None:
                    st = clip.proxy_status.value
                    if st == 1: # GENERATING
                        px_color = "#ff9900"
                    elif st == 2: # READY
                        px_color = "#00cc66" 
                    elif st == 3: # ERROR
                        px_color = "#ff3333"
            except Exception:
                pass # Fallback to default styling
                
            self._draw_clip_button(painter, x + w - 60, y + 3, "px", bg_override=px_color)
            self._draw_clip_button(painter, x + w - 30, y + 3, "fx")
        painter.restore()

    def _draw_clip_button(self, painter, x, y, text, bg_override=None):
        brush_color = QColor(bg_override) if bg_override else QColor("#1a0b2e")
        painter.setBrush(brush_color)
        
        # If color is bright, use black text, else white
        text_color = Qt.white
        if bg_override and (text == "px"):
             # Simple heuristic: Orange/Green are bright
             if bg_override in ["#ff9900", "#00cc66"]:
                 text_color = Qt.black
        
        painter.setPen(QPen(text_color if bg_override else Qt.white, 1))
        painter.drawRoundedRect(x + 2, y, 24, 14, 4, 4)
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(x + 6 if text == "px" else x + 8, y + 11, text)

    def _draw_corner_indicators(self, painter, x, y, w):
        painter.setBrush(QColor(0, 255, 255, 220)) 
        painter.setPen(Qt.NoPen)
        base_y = y + CLIP_HEADER_HEIGHT
        tri_size = 7
        left_tri = QPolygon([QPoint(x, base_y), QPoint(x + tri_size, base_y), QPoint(x, base_y + tri_size)])
        right_tri = QPolygon([QPoint(x + w, base_y), QPoint(x + w - tri_size, base_y), QPoint(x + w, base_y + tri_size)])
        painter.drawPolygon(left_tri)
        painter.drawPolygon(right_tri)

    def draw_opacity_and_fades(self, painter, clip, x, w, y, h):
        if not self.model: return
        if w <= 0: return
        all_pts = []
        fi_frames = clip.fade_in_frames
        if fi_frames > 0:
            segments = 15
            for i in range(segments + 1):
                t_norm = i / float(segments)
                val = self.interpolate_fade(t_norm, clip.fade_in_type)
                all_pts.append((i * fi_frames / float(segments), val * clip.start_opacity))
        else:
            all_pts.append((0, clip.start_opacity))
            
        fi_end_f = fi_frames
        fo_start_f = clip.duration_frames - clip.fade_out_frames
        for fn, op, _ in sorted(clip.opacity_nodes):
            if fi_end_f < fn < fo_start_f:
                all_pts.append((fn, op))
                
        fo_frames = clip.fade_out_frames
        if fo_frames > 0:
            segments = 15
            for i in range(segments + 1):
                t_norm = 1.0 - (i / float(segments))
                val = self.interpolate_fade(t_norm, clip.fade_out_type)
                all_pts.append((fo_start_f + i * fo_frames / float(segments), val * clip.end_opacity))
        else:
            all_pts.append((clip.duration_frames, clip.end_opacity))
        
        all_pts.sort(key=lambda p: p[0])
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
        prev_px = None
        prev_py = None
        for fn, op in all_pts:
            px = x + int(fn / self.get_fps() * self.pixels_per_second)
            py = y + int((1.0 - op) * h)
            if prev_px is not None:
                painter.drawLine(prev_px, prev_py, px, py)
            prev_px, prev_py = px, py

        poly = QPolygon()
        poly << QPoint(x, y + h)
        for fn, op in all_pts:
            px = x + int(fn / self.get_fps() * self.pixels_per_second)
            py = y + int((1.0 - op) * h)
            poly << QPoint(px, py)
        poly << QPoint(x + w, y + h)
        
        painter.setBrush(QColor(255, 255, 255, 40))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)
        
        if w > 40:
            mid_x = x + (w // 2)
            target_y = y + int((1.0 - clip.start_opacity) * h)
            painter.setBrush(QColor(0, 0, 255))
            painter.setPen(QPen(Qt.white, 1))
            trap = QPolygon([
                QPoint(mid_x - 7, target_y - 3), QPoint(mid_x + 7, target_y - 3), 
                QPoint(mid_x + 4, target_y + 3),  QPoint(mid_x - 4, target_y + 3)   
            ])
            painter.drawPolygon(trap)
