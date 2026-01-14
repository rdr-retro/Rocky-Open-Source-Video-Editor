"""
Simple Timeline Widget - Minimal implementation that WILL render visibly.
This is a complete rewrite focusing on guaranteed visibility.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from functools import partial

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
        self.pixels_per_second = 100.0
        
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
        
        # Scroll/View state
        self.visible_start_time = 0.0  # For sync with ruler
        
        # Envelopes Interaction - REMOVED
        self.dragging_fade_in = False
        self.dragging_fade_out = False
        self.dragging_opacity = False  # NEW: For opacity/gain level handle
        
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
        
        print("SimpleTimeline: Widget created and configured", flush=True)
    
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
            print("ERROR: Painter not active!", flush=True)
            return
        
        # Enable antialiasing
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. BACKGROUND - Dark (Matches Ruler)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # 2. GRID - White dotted lines
        self._draw_grid(painter, event.rect())
        
        # 3. TRACK DIVIDERS - Horizontal lines
        self._draw_tracks(painter)
        
        # 4. CLIPS - Bright colored rectangles
        # Optimization: Pass rect to clip drawer too? For now, clipping handles it, 
        # but iterating logic is safer. Let's fix grid first.
        self._draw_clips(painter)
        
        # 5. PLAYHEAD - Bright cyan vertical line
        self._draw_playhead(painter)
        
        painter.end()
    
    
    def _draw_grid(self, painter, rect):
        """Draw vertical grid lines, efficiently clipped to visible area."""
        start_x = rect.left()
        end_x = rect.right()
        
        # Guard against zero-division (paranoid check)
        pps = max(1.0, self.pixels_per_second)
        
        start_time = start_x / pps
        end_time = end_x / pps
        
        # Step matching ruler roughly
        step = 1.0 
        if pps < 50: step = 5.0
        if pps < 10: step = 10.0
        
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DotLine)) # Dotted grid
        
        t = (int(start_time / step) * step)
        
        # Loop only through VISIBLE portion
        while t < end_time + step:
            x = int(t * pps)
            painter.drawLine(x, 0, x, self.height())
            t += step
    
    def _draw_tracks(self, painter):
        """Draw horizontal track dividers based on actual model tracks."""
        painter.setPen(QPen(QColor(40, 40, 40), 1)) # Darker dividers
        
        current_y = 0
        for i, height in enumerate(self.model.track_heights):
            current_y += height
            if current_y < self.height():
                painter.drawLine(0, current_y, self.width(), current_y)
    
    def _draw_clips(self, painter):
        """Draw clips with Vegas-style headers and icons."""
        from PySide6.QtGui import QFontMetrics, QPainterPath
        
        # Colors from screenshot
        COLOR_VIDEO_BODY = QColor("#763436") # Burgundy body
        COLOR_VIDEO_HEADER = QColor("#9E4347") # Lighter header
        COLOR_AUDIO_BODY = QColor("#347660")  # Teal/Green body for audio (guess)
        COLOR_AUDIO_HEADER = QColor("#439E80")
        COLOR_TEXT = QColor(230, 230, 230)
        # COLOR_FADE removed
        font = painter.font()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        fm = QFontMetrics(font)
        
        # Calculate track Y positions
        track_y_positions = self._get_track_y_positions()
        fps = self.get_fps()
        
        for clip in self.model.clips:
            if clip.track_index >= len(track_y_positions):
                continue
            
            # Clip geometry
            track_y = track_y_positions[clip.track_index]
            track_h = self.model.track_heights[clip.track_index]
            clip_x = int((clip.start_frame / fps) * self.pixels_per_second)
            clip_w = int((clip.duration_frames / fps) * self.pixels_per_second)
            clip_h = track_h - 2  # Small gap
            
            # Determine Track Type Color
            from ..models import TrackType
            if clip.track_index < len(self.model.track_types) and self.model.track_types[clip.track_index] == TrackType.VIDEO:
                body_col = COLOR_VIDEO_BODY
                header_col = COLOR_VIDEO_HEADER
            else:
                body_col = COLOR_AUDIO_BODY
                header_col = COLOR_AUDIO_HEADER
                
            if clip.selected:
                 # Lighten slightly for selection
                 body_col = body_col.lighter(130)
                 header_col = header_col.lighter(130)
            
            # 1. Body
            rect_body = QRectF(clip_x, track_y + 1, clip_w, clip_h)
            
            # Chamfered/Rounded corners? Screenshot shows slightly rounded or chamfered top corners.
            # Let's use simple rect for robust rendering first, mimic chamfer with fade handles
            painter.fillRect(rect_body, body_col)
            
            # 2. Header
            header_h = 12
            rect_header = QRectF(clip_x, track_y + 1, clip_w, header_h)
            painter.fillRect(rect_header, header_col)
            
            # 3. Text
            painter.setPen(COLOR_TEXT)
            font = painter.font()
            font.setPointSize(9) # Smaller font for ultra-thin header
            painter.setFont(font)
            painter.drawText(int(clip_x) + 8, int(track_y) + 11, clip.name) # Adjusted Y for 12px header
            
            # 4. OPACITY/GAIN ENVELOPE (Vegas Style)
            # Unified path: Rise -> Plateau -> Fall (/-----)
            from ..models import FadeType
            
            # Geometry
            body_start_y = track_y + 13
            body_end_y = track_y + 1 + clip_h
            body_height = body_end_y - body_start_y
            
            opacity_level = getattr(clip, 'opacity_level', 1.0)
            target_y = body_start_y + (1.0 - opacity_level) * body_height # The "Opaque" level
            
            fade_in_w = int((clip.fade_in_frames / self.get_fps()) * self.pixels_per_second)
            fade_out_w = int((clip.fade_out_frames / self.get_fps()) * self.pixels_per_second)
            
            # Construct Continuous Path
            envelope = QPainterPath()
            
            # 4a. Fade In Segment
            p_start_fi = QPointF(clip_x, body_end_y) # Bottom Left
            p_end_fi = QPointF(clip_x + fade_in_w, target_y) # Top of Fade In
            
            envelope.moveTo(p_start_fi)
            
            if fade_in_w > 0:
                c_type_in = clip.fade_in_type
                if c_type_in == FadeType.LINEAR:
                    envelope.lineTo(p_end_fi)
                elif c_type_in == FadeType.FAST: # Rise Fast
                    c1 = QPointF(clip_x, target_y) 
                    c2 = QPointF(clip_x + fade_in_w * 0.25, target_y) 
                    envelope.cubicTo(c1, c2, p_end_fi)
                elif c_type_in == FadeType.SLOW: # Rise Slow
                    c1 = QPointF(clip_x + fade_in_w * 0.75, body_end_y)
                    c2 = QPointF(clip_x + fade_in_w, body_end_y)
                    envelope.cubicTo(c1, c2, p_end_fi)
                elif c_type_in == FadeType.SMOOTH: # S-Curve
                    c1 = QPointF(clip_x + fade_in_w * 0.5, body_end_y)
                    c2 = QPointF(clip_x + fade_in_w * 0.5, target_y)
                    envelope.cubicTo(c1, c2, p_end_fi)
                elif c_type_in == FadeType.SHARP: # Step
                    envelope.lineTo(clip_x + fade_in_w, body_end_y)
                    envelope.lineTo(p_end_fi)
            else:
                 envelope.lineTo(clip_x, target_y) # Vertical rise if no fade
            
            # 4b. Plateau Segment (Top Line)
            plateau_end_x = clip_x + clip_w - fade_out_w
            envelope.lineTo(plateau_end_x, target_y)
            
            # 4c. Fade Out Segment
            p_end_fo = QPointF(clip_x + clip_w, body_end_y) # Bottom Right
            
            if fade_out_w > 0:
                c_type_out = clip.fade_out_type
                if c_type_out == FadeType.LINEAR:
                    envelope.lineTo(p_end_fo)
                elif c_type_out == FadeType.FAST: # Drop Fast
                    # Start Top-Left -> Go Bottom-Left quickly
                    c1 = QPointF(plateau_end_x, body_end_y) 
                    c2 = QPointF(plateau_end_x + fade_out_w * 0.25, body_end_y)
                    envelope.cubicTo(c1, c2, p_end_fo)
                elif c_type_out == FadeType.SLOW: # Drop Slow
                    # Start Top-Left -> Go Top-Right
                    c1 = QPointF(p_end_fo.x(), target_y) 
                    c2 = QPointF(p_end_fo.x(), target_y + (body_end_y - target_y) * 0.25)
                    envelope.cubicTo(c1, c2, p_end_fo)
                elif c_type_out == FadeType.SMOOTH: # S-Curve Drop
                    c1 = QPointF(plateau_end_x + fade_out_w * 0.5, target_y)
                    c2 = QPointF(plateau_end_x + fade_out_w * 0.5, body_end_y)
                    envelope.cubicTo(c1, c2, p_end_fo)
                elif c_type_out == FadeType.SHARP: # Step Drop
                    envelope.lineTo(clip_x + clip_w, target_y)
                    envelope.lineTo(p_end_fo)
            else:
                envelope.lineTo(clip_x + clip_w, target_y) # Horizontal if no fade out
                envelope.lineTo(clip_x + clip_w, body_end_y) # Vertical drop (handled by fill logic? or explicitly)
            
            # Draw the Envelope
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.PenStyle.SolidLine))
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
            painter.drawRect(int(center_x - 3), int(target_y - 2), 6, 4)

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
            
            # Determine Color for PX
            # Status: 0=Inactive(Gray), 1=Generating(Orange), 2=Active(Green), 3=Error(Red)
            p_status = getattr(clip, 'proxy_status', 0) 
            if p_status == 1:
                px_col = QColor("#ff8800") # Orange
            elif p_status == 2:
                px_col = QColor("#00ff00") # Green
            elif p_status == 3:
                px_col = QColor("#ff0000") # Red
            else:
                px_col = QColor("#505050") # Dark Gray (visible on dark background)
                
            rect_px = QRectF(px_x, px_y, button_w, button_h)
            painter.setBrush(px_col)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect_px, 2, 2)
            
            # Text "PX"
            painter.setPen(QColor("#ffffff") if p_status == 0 or p_status == 3 else QColor("#000000"))
            font_btn = painter.font()
            font_btn.setPointSize(7)
            font_btn.setBold(True)
            painter.setFont(font_btn)
            painter.drawText(rect_px, Qt.AlignmentFlag.AlignCenter, "PX")
            
            # Button 1: FX (Effects) - Left of PX
            fx_x = px_x - button_w - spacing
            fx_y = px_y
            
            # FX always black for now unless we track active effects? 
            # User said "dos botones negros", implying default state.
            fx_col = QColor("#000000")
            
            rect_fx = QRectF(fx_x, fx_y, button_w, button_h)
            painter.setBrush(fx_col)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect_fx, 2, 2)
            
            # Text "FX"
            painter.setPen(QColor("#ffffff"))
            painter.drawText(rect_fx, Qt.AlignmentFlag.AlignCenter, "FX")

            # 7. Clip Selection Border
            if clip.selected:
                painter.setPen(QPen(QColor("#FFFF00"), 1)) # Bright yellow border
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(clip_x, track_y + 1, clip_w, clip_h)

    def _draw_playhead(self, painter):
        """Draw playhead as thin vertical line with sub-pixel precision."""
        from PySide6.QtCore import QLineF
        
        fps = self.get_fps()
        # Use float for sub-pixel precision
        ph_x = (self.model.blueline.playhead_frame / fps) * self.pixels_per_second
        
        # Black line with white edges for contrast
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawLine(QLineF(ph_x, 0, ph_x, self.height()))
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawLine(QLineF(ph_x, 0, ph_x, self.height()))

    def mousePressEvent(self, event):
        """Handle mouse press - select clips, move playhead, or EDIT ENVELOPES."""
        self.setFocus() # Ensure we catch keyboard events
        
        if event.button() == Qt.MouseButton.LeftButton:
            
            # 1. Check FADE HANDLE Hits first (Priority interaction, allowing sloppy hits)
            # Find Track from Y
            track_y_positions = []
            curr_y = 0
            click_track_idx = -1
            click_track_y = 0
            
            for h in self.model.track_heights:
                if curr_y <= event.y() < curr_y + h:
                    click_track_idx = len(track_y_positions)
                    click_track_y = curr_y
                    break
                track_y_positions.append(curr_y)
                curr_y += h
                
            # 1. Check FADE HANDLE Hits (Blue Triangles)
            # Calculate track positions
            track_y_positions = []
            curr_y = 0
            click_track_idx = -1
            click_track_y = 0
            
            for h in self.model.track_heights:
                if curr_y <= event.y() < curr_y + h:
                    click_track_idx = len(track_y_positions)
                    click_track_y = curr_y
                    break
                track_y_positions.append(curr_y)
                curr_y += h
            
            if click_track_idx != -1:
                # Check clips in this track for Fade Handle hits
                for clip in self.model.clips:
                    if clip.track_index == click_track_idx:
                        clip_x = int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                        clip_w = int((clip.duration_frames / self.get_fps()) * self.pixels_per_second)
                        body_top_y = click_track_y + 13  # Below header
                        
                        # Fade In Triangle (Top-Left): 6x6 triangle
                        # Triangle points: (clip_x, body_top_y), (clip_x+6, body_top_y), (clip_x, body_top_y+6)
                        if (clip_x <= event.x() <= clip_x + 6 and 
                            body_top_y <= event.y() <= body_top_y + 6):
                            # Check if click is inside triangle (simple bounding box for now)
                            self.dragging_clip = clip
                            self.dragging_fade_in = True
                            self.structure_changed.emit()
                            return
                        
                        # Fade Out Triangle (Top-Right): 6x6 triangle
                        # Triangle points: (clip_x+clip_w, body_top_y), (clip_x+clip_w-6, body_top_y), (clip_x+clip_w, body_top_y+6)
                        if (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and 
                            body_top_y <= event.y() <= body_top_y + 6):
                            self.dragging_clip = clip
                            self.dragging_fade_out = True
                            self.structure_changed.emit()
                            return
                        
                        # Opacity/Gain Level Line (Center Handle)
                        # We also allow grabbing the top edge area if the line is 1.0
                        
                        # Body Top/Bottom properties
                        track_h = self.model.track_heights[clip.track_index]
                        clip_h = track_h - 2
                        body_start_y = click_track_y + 13
                        body_end_y = click_track_y + 1 + clip_h
                        body_height = body_end_y - body_start_y
                        
                        # Current Level Line Y
                        opacity_level = getattr(clip, 'opacity_level', 1.0)
                        level_y = body_start_y + (1.0 - opacity_level) * body_height
                        
                        # Hit Check:
                        # 1. Near the current Level Line (precise adjustment)
                        # 2. Near the Top Edge (easy grab for 100% -> lower)
                        hit_line = abs(event.y() - level_y) <= 5
                        hit_top = abs(event.y() - body_start_y) <= 5 and opacity_level > 0.95
                        
                        if (clip_x <= event.x() <= clip_x + clip_w) and (hit_line or hit_top):
                            self.dragging_clip = clip
                            self.dragging_opacity = True
                            self.structure_changed.emit()
                            return

            # [Existing Clip Logic]
            # Check if clicking on a clip
            clip = self.find_clip_at(event.x(), event.y()) # Strict bounds for selection
            
            if clip:
                # Calculate local click coords relative to clip
                # Need to reconstruct clip geometry to find button rect
                clip_x = int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                clip_w = int((clip.duration_frames / self.get_fps()) * self.pixels_per_second)
                
                # Re-calculate button geometry (Same as paintEvent)
                # Ensure we handle tracks correctly to get Y
                track_y = 0
                for i in range(clip.track_index):
                    track_y += self.model.track_heights[i] if i < len(self.model.track_heights) else 60
                
                button_w = 14
                button_h = 8
                spacing = 2
                
                px_x = clip_x + clip_w - button_w - 4
                px_y = track_y + 2
                rect_px = QRectF(px_x, px_y, button_w, button_h)

                fx_x = px_x - button_w - spacing
                fx_y = px_y
                rect_fx = QRectF(fx_x, fx_y, button_w, button_h)
                
                # CHECK CLICK ON FX BUTTON
                if rect_fx.contains(event.position()):
                    self.clip_fx_toggled.emit(clip)
                    return

                # CHECK CLICK ON PX BUTTON
                if rect_px.contains(event.position()):
                    # Emit signal to Controller (rocky_ui handles logic)
                    self.clip_proxy_toggled.emit(clip)
                    return # Stop propagation (don't select/drag)

                # Select clip
                if not (event.modifiers() & Qt.ShiftModifier):
                    # Clear other selections
                    for c in self.model.clips:
                        c.selected = False
                
                clip.selected = True
                
                # DRAG THRESHOLD LOGIC:
                # Don't set self.dragging_clip yet. Wait for move > threshold.
                self.potential_drag_clip = clip
                self.potential_drag_start_pos = event.position()
                
                self.drag_start_x = event.x()
                self.drag_start_y = event.y()
                self.drag_offset_x = event.x() - int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                self.drag_start_track = clip.track_index
                
                self.structure_changed.emit()
            else:
                # Move playhead
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
                        clip_x = int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                        clip_w = int((clip.duration_frames / self.get_fps()) * self.pixels_per_second)
                        body_top_y = hover_track_y + 13
                        
                        # Check fade handles
                        if ((clip_x <= event.x() <= clip_x + 6 and body_top_y <= event.y() <= body_top_y + 6) or
                            (clip_x + clip_w - 6 <= event.x() <= clip_x + clip_w and body_top_y <= event.y() <= body_top_y + 6)):
                            self.setCursor(Qt.CursorShape.SizeHorCursor)
                            cursor_set = True
                            break
            
                        # Check Opacity/Gain Handle (Top Edge or Line)
                        opacity_level = getattr(clip, 'opacity_level', 1.0)
                        track_h = self.model.track_heights[clip.track_index]
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
                clip_x = int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                
                # New Fade In Width
                new_w = max(0, event.x() - clip_x)
                # Convert to frames
                new_frames = int((new_w / self.pixels_per_second) * self.get_fps())
                # Clamp: 0 to duration
                clip.fade_in_frames = max(0, min(clip.duration_frames, new_frames))
                
                self.update()
                return

            if self.dragging_fade_out and self.dragging_clip:
                clip = self.dragging_clip
                clip_x = int((clip.start_frame / self.get_fps()) * self.pixels_per_second)
                clip_w = int((clip.duration_frames / self.get_fps()) * self.pixels_per_second)
                
                # New Fade Out Width (from right)
                # Mouse X is at (clip_x + clip_w - fade_out_w)
                dist_from_right = (clip_x + clip_w) - event.x()
                new_frames = int((dist_from_right / self.pixels_per_second) * self.get_fps())
                clip.fade_out_frames = max(0, min(clip.duration_frames, new_frames))
                
                self.update()
                return

            if self.dragging_clip:
                # Drag Clip (Horizontal + Vertical)
                new_x = event.x() - self.drag_offset_x
                new_time = new_x / self.pixels_per_second
                new_frame = max(0, int(new_time * self.get_fps()))
                
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
        """Handle mouse wheel - zoom."""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.pixels_per_second = min(500, self.pixels_per_second * 1.1)
            else:
                self.pixels_per_second = max(10, self.pixels_per_second / 1.1)
            self.view_updated.emit()
            self.updateGeometry()
            self.update()
            event.accept()
        else:
            event.ignore()
    
    def dragEnterEvent(self, event):
        """Accept drag events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle file drops."""
        urls = event.mimeData().urls()
        if not urls:
            return
        
        drop_time = event.pos().x() / self.pixels_per_second
        start_frame = max(0, int(drop_time * self.get_fps()))
        
        # Calculate track index from Y position
        track_idx = -1
        current_y = 0
        for i, height in enumerate(self.model.track_heights):
            if current_y <= event.pos().y() < current_y + height:
                track_idx = i
                break
            current_y += height
        
        # Import via main app
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
        """Find clip at position with tolerance (Fuzzy Search)."""
        track_y_positions = self._get_track_y_positions()
        
        # Find which track we're in
        track_idx = -1
        TOLERANCE_Y = 2 # Pixels
        for i, track_y in enumerate(track_y_positions):
            if i < len(self.model.track_heights):
                track_h = self.model.track_heights[i]
                # Fuzzy Y check
                if track_y - TOLERANCE_Y <= y < track_y + track_h + TOLERANCE_Y:
                    track_idx = i
                    break
        
        if track_idx == -1:
            return None
        
        # Find clip in that track
        fps = self.get_fps()
        TOLERANCE_X = 2 # Pixels
        for clip in self.model.clips:
            if clip.track_index == track_idx:
                clip_x = int((clip.start_frame / fps) * self.pixels_per_second)
                clip_w = int((clip.duration_frames / fps) * self.pixels_per_second)
                
                # Fuzzy X check
                if clip_x - TOLERANCE_X <= x <= clip_x + clip_w + TOLERANCE_X:
                    return clip
        
        return None
    
    def update_playhead_to_x(self, screen_x):
        """Update playhead position from screen x coordinate."""
        time_seconds = max(0, screen_x / self.pixels_per_second)
        frame = time_seconds * self.get_fps()  # Keep as float!
        self.model.blueline.set_playhead_frame(frame)
        
        # Calculate proper timecode string including frames
        tc = self.model.format_timecode(frame, self.get_fps())
        self.time_updated.emit(time_seconds, int(frame), tc, True)
        self.update()
    
    def _finish_proxy_sim(self, clip):
        """Simulate proxy generation completion provided clip still exists."""
        if clip in self.model.clips:
            clip.proxy_status = 2 # Ready
            self.update()
    
    def update_playhead_position(self, frame_index):
        """Update playhead to specific frame (can be float)."""
        self.model.blueline.set_playhead_frame(frame_index) # No casting to int
        time_seconds = frame_index / self.get_fps()
        self.time_updated.emit(time_seconds, int(frame_index), "00:00:00", True)
        self.update()
        return frame_index * self.pixels_per_second / self.get_fps() # Return float screen x
    
    def frameToScreen(self, frame_index):
        """Convert frame index to screen x coordinate."""
        fps = self.get_fps()
        return frame_index * self.pixels_per_second / fps # Return float screen x
    
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
        """Handle native context menu event (Right Click or Keyboard)."""
        self.show_context_menu(event.pos())
        event.accept()

    def show_context_menu(self, pos):
        """Show context menu for clips (Right Click)."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QActionGroup
        from ..models import FadeType
        
        # Ensure pos is a QPoint (handling both Point and event types if mixed)
        if hasattr(pos, 'toPoint'): pos = pos.toPoint()
            
        clip = self.find_clip_at(pos.x(), pos.y())
        
        menu = QMenu(self)
        
        if not clip:
            # Show Generic Timeline Menu if no clip clicked (Feedback for user)
            action_zoom = menu.addAction("Zoom to Fit")
            action_zoom.triggered.connect(self.zoom_to_fit)
            menu.exec(self.mapToGlobal(pos))
            return

        # Auto-select on right click if not already selected (Standard UX)
        if not clip.selected:
            for c in self.model.clips:
                c.selected = False
            clip.selected = True
            self.structure_changed.emit()
            self.update()
        
        # Check if we clicked on a Fade Region
        fps = self.get_fps()
        clip_x = int((clip.start_frame / fps) * self.pixels_per_second)
        clip_w = int((clip.duration_frames / fps) * self.pixels_per_second)
        
        rel_x = pos.x() - clip_x
        
        # Fade In Region?
        fade_in_w = int((clip.fade_in_frames / fps) * self.pixels_per_second)
        is_fade_in = 0 <= rel_x <= fade_in_w and fade_in_w > 0
        
        # Fade Out Region?
        fade_out_w = int((clip.fade_out_frames / fps) * self.pixels_per_second)
        is_fade_out = (clip_w - fade_out_w) <= rel_x <= clip_w and fade_out_w > 0
        
        if is_fade_in or is_fade_out:
            fade_menu = menu.addMenu("Fade Type")
            
            # Map FadeType to Names
            fade_options = [
                (FadeType.LINEAR, "Lineal (Linear)"),
                (FadeType.FAST, "Rápida (Fast)"),
                (FadeType.SLOW, "Lenta (Slow)"),
                (FadeType.SMOOTH, "Suave (S-Curve)")
            ]
            
            group = QActionGroup(fade_menu)
            
            for f_type, f_name in fade_options:
                action = fade_menu.addAction(f_name)
                action.setCheckable(True)
                group.addAction(action)
                
                # Check current
                current = clip.fade_in_type if is_fade_in else clip.fade_out_type
                if current == f_type:
                    action.setChecked(True)
                
                # Callback closure
                def set_curve(checked, t=f_type, is_in=is_fade_in):
                    if checked:
                        if is_in:
                            clip.fade_in_type = t
                        else:
                            clip.fade_out_type = t
                        self.structure_changed.emit()
                        self.update()
                    
                action.triggered.connect(set_curve)
                
            menu.addSeparator()

        # Standard Clip Actions
        action_delete = menu.addAction("Eliminar (Delete)")
        # Fix: Use partial to robustly bind the clip to the slot (avoids lambda garbage collection issues)
        action_delete.triggered.connect(partial(self.delete_clip, clip))

        menu.exec(self.mapToGlobal(pos))
        
    def delete_clip(self, clip=None):
        """Delete a clip (or multiple selected clips). If clip is None, delete all selected."""
        clips_to_remove = set() # Use set to avoid duplicates
        
        # 1. Identify primary targets
        if clip:
            if clip.selected:
                 for c in self.model.clips:
                     if c.selected: clips_to_remove.add(c)
                 # Ensure clicked one is included
                 clips_to_remove.add(clip)
            else:
                 clips_to_remove.add(clip)
        else:
             # Keyboard delete
             for c in self.model.clips:
                 if c.selected: clips_to_remove.add(c)
        
        # 2. Identify LINKED targets (Vegas Style)
        # We must iterate a copy or new list because we are adding to the set
        initial_targets = list(clips_to_remove)
        for c in initial_targets:
            if c.linked_to and c.linked_to in self.model.clips:
                clips_to_remove.add(c.linked_to)

        if not clips_to_remove:
            return

        count = 0
        for c in clips_to_remove:
            # 1. Try Direct Removal (Identity)
            if c in self.model.clips:
                self.model.remove_clip(c)
                count += 1
            else:
                # 2. Soft Match Fallback (If object identity was lost)
                target = None
                for real_c in self.model.clips:
                    if (real_c.track_index == c.track_index and 
                        abs(real_c.start_frame - c.start_frame) < 1 and 
                        real_c.name == c.name):
                        target = real_c
                        break
                
                if target:
                    self.model.remove_clip(target)
                    count += 1
                
        if count > 0:
            self.structure_changed.emit()
            self.updateGeometry()
            self.repaint() # FORCE immediate repaint

    def timeToScreen(self, time_in_seconds):
        """Convert time to screen x coordinate (float)."""
        return time_in_seconds * self.pixels_per_second

    def zoom_to_fit(self):
        """Auto-zoom timeline to fit all content in visible area."""
        max_frame = self.model.get_max_frame()
        if max_frame <= 0:
            return
        
        # Get scroll area width
        scroll_area = self.get_scroll_area_context()
        if scroll_area:
            viewport_width = scroll_area.viewport().width()
        else:
            viewport_width = self.width()
        
        # Calculate pixels per second to fit content
        duration_seconds = max_frame / self.get_fps()
        if duration_seconds > 0:
            # Leave some padding (80% of viewport)
            self.pixels_per_second = (viewport_width * 0.8) / duration_seconds
            self.pixels_per_second = max(10, min(500, self.pixels_per_second))  # Clamp
            
            self.view_updated.emit()
            self.updateGeometry()
            self.update()
