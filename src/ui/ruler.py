import numpy as np
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRect, QPointF, QLineF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from .styles import MENU_STYLE
from .models import TICKS_PER_FRAME, TICKS_PER_SECOND, TimeFormat

class TimelineRuler(QWidget):
    """
    Renders the temporal ruler and playhead handle at the top of the timeline.
    Handles temporal seeking through mouse interactions.
    """
    def __init__(self, timeline_panel):
        super().__init__()
        self.timeline = timeline_panel
        self._initialize_ui()
        self._initialize_design_system()
        
    def _initialize_ui(self):
        self.setFixedHeight(38) 
        self.setMouseTracking(True)
        self.mouse_x = -1
        self.setContentsMargins(0, 0, 0, 0)
        # Sync updates with timeline repaint toggle
        self.timeline.repaint_timer.timeout.connect(self.update)

    def _initialize_design_system(self):
        self.COLOR_BG = QColor("#1e1e1e") # Darker, matching screenshot sidebar
        self.COLOR_TICK = QColor("#888888") # Lighter ticks
        self.COLOR_PLAYHEAD = QColor("#d4d4d4") # Silver/White handle
        self.COLOR_HOVER = QColor("#44475a")
        self.FONT_MAIN = QFont("Roboto Mono", 9)
        self.FONT_MAIN.setPixelSize(10)

    def _draw_tick_label(self, painter, x, time, fps):
        # Major Tick
        painter.setPen(QPen(self.COLOR_TICK, 1))
        painter.drawLine(int(x), 15, int(x), 38) # Bottom aligned
        
        # Text based on format
        fmt = self.timeline.model.time_format
        
        label = ""
        if fmt == TimeFormat.TIMECODE:
            frame_idx = int(round(time * fps))
            label = self.timeline.model.format_timecode(frame_idx, fps)
        elif fmt == TimeFormat.SECONDS:
            label = f"{time:.1f}s"
        elif fmt == TimeFormat.FRAMES:
            label = str(int(round(time * fps)))
            
        painter.setPen(QPen(QColor("#bbbbbb")))
        # Center the text on the tick for perfect balance
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(label)
        painter.drawText(int(x - w/2), 34, label)

    def _draw_markers_and_regions(self, painter, scroll_x, fps):
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        
        # 1. Regions (ranges)
        for region in self.timeline.model.regions:
            start_x = self.timeline.tickToProjectedX(region.start_tick) - scroll_x
            width = self.timeline.tickToProjectedX(region.duration_ticks)
            
            # Draw semi-transparent background
            col = QColor(region.color)
            col.setAlpha(40)
            painter.fillRect(int(start_x), 0, int(width), 15, col)
            
            # Draw bracket lines
            col.setAlpha(255)
            painter.setPen(QPen(col, 1))
            painter.drawLine(int(start_x), 0, int(start_x), 15)
            painter.drawLine(int(start_x + width), 0, int(start_x + width), 15)
            painter.drawLine(int(start_x), 0, int(start_x + width), 0)
            
            # Label
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(int(start_x) + 4, 10, region.name)
            
        # 2. Markers (points)
        for marker in self.timeline.model.markers:
            mx = self.timeline.tickToProjectedX(marker.tick) - scroll_x
            
            col = QColor(marker.color)
            painter.setPen(QPen(col, 1))
            painter.drawLine(int(mx), 0, int(mx), 38)
            
            # Tag
            painter.setBrush(col)
            points = [QPoint(int(mx), 0), QPoint(int(mx) + 5, 0), QPoint(int(mx) + 5, 8), QPoint(int(mx), 12), QPoint(int(mx) - 5, 8), QPoint(int(mx) - 5, 0)]
            painter.drawPolygon(QPolygon(points))
            
            # Number/Name
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(int(mx) - 3, 8, marker.name[:1]) # Just first char/number


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Vegas Pro Industrial Ruler
        painter.fillRect(self.rect(), self.COLOR_BG)
        
        # Bottom border
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(0, self.height()-1, self.width(), self.height()-1)
        
        # 1. Coordinate Synthesis
        pixels_per_second = self.timeline.pixels_per_second
        scroll_area = self.timeline.get_scroll_area_context()
        scroll_x = scroll_area.horizontalScrollBar().value() if scroll_area else 0
        
        visible_start_time = scroll_x / float(pixels_per_second if pixels_per_second > 0 else 1)
        fps = self.timeline.get_fps()
        
        # 2. Adaptive Step Calculation (Shared with Timeline)
        step, divs = self.timeline.calculate_adaptive_step(pixels_per_second, fps)
        
        # 3. Tick Rendering
        painter.setPen(QPen(self.COLOR_TICK, 1))
        painter.setFont(self.FONT_MAIN)
        
        time_limit = (scroll_x + self.width()) / float(pixels_per_second)
        
        # SAFETY CAP: Never try to render more than 1 hour past the end of the project.
        # This prevents UI hangs when PPS is ultra-small (0.0001) but scroll_x is still large.
        max_project_time = (self.timeline.model.get_max_tick() / TICKS_PER_SECOND) + 3600
        time_limit = min(time_limit, max_project_time)
        
        time_cursor = math.floor(visible_start_time / step) * step
        while time_cursor < time_limit + step:
            tick_cursor = int(time_cursor * TICKS_PER_SECOND)
            screen_x = self.timeline.tickToProjectedX(tick_cursor) - scroll_x
            
            if -100 <= screen_x <= self.width() + 100:
                self._draw_tick_label(painter, screen_x, time_cursor, fps)
                self._draw_sub_ticks(painter, screen_x, pixels_per_second, time_cursor, step, divs)
            
            time_cursor += step
            
        # 4. Interactive Elements
        self._draw_markers_and_regions(painter, scroll_x, fps)
        self._draw_playhead_handle(painter, scroll_x, fps)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(MENU_STYLE)
        
        act_tc = menu.addAction("Timecode (HH:MM:SS:FF)")
        act_tc.setCheckable(True)
        act_tc.setChecked(self.timeline.model.time_format == TimeFormat.TIMECODE)
        act_tc.triggered.connect(lambda: self._set_format(TimeFormat.TIMECODE))
        
        act_sec = menu.addAction("Seconds (1.5s)")
        act_sec.setCheckable(True)
        act_sec.setChecked(self.timeline.model.time_format == TimeFormat.SECONDS)
        act_sec.triggered.connect(lambda: self._set_format(TimeFormat.SECONDS))
        
        act_frm = menu.addAction("Frames (1234)")
        act_frm.setCheckable(True)
        act_frm.setChecked(self.timeline.model.time_format == TimeFormat.FRAMES)
        act_frm.triggered.connect(lambda: self._set_format(TimeFormat.FRAMES))
        
        menu.addSeparator()
        menu.addAction("Set Marker (M)").triggered.connect(self._add_marker_at_cursor)
        
        menu.exec(event.globalPos())
        
    def _set_format(self, fmt):
        self.timeline.model.time_format = fmt
        self.update()
        
    def _add_marker_at_cursor(self):
        from .models import TimelineMarker
        tick = int(self.timeline.model.blueline.playhead_tick)
        self.timeline.model.markers.append(TimelineMarker(tick, str(len(self.timeline.model.markers)+1)))
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_M:
            self._add_marker_at_cursor()
        else:
            super().keyPressEvent(event)


    def _draw_sub_ticks(self, painter, x, px_per_sec, time, step, divisions):
        scroll_area = self.timeline.get_scroll_area_context()
        scroll_x = scroll_area.horizontalScrollBar().value() if scroll_area else 0
        
        painter.setPen(QPen(QColor(85, 85, 85, 180), 2)) # Slightly thicker dots
        
        sub_step = step / float(divisions)
        
        for i in range(1, divisions):
            st_time = time + (sub_step * i)
            st_tick = int(st_time * TICKS_PER_SECOND)
            st_x = self.timeline.tickToProjectedX(st_tick) - scroll_x
            
            # Draw a dot at the middle of the lower half of the ruler
            painter.drawPoint(QPointF(st_x, 35))

    def _draw_hover_indicator(self, painter):
        pass

    def _draw_playhead_handle(self, painter, scroll_x, fps):
        from PySide6.QtCore import QPointF, QRectF
        from PySide6.QtGui import QPolygonF, QLinearGradient, QColor, QBrush
        
        # 1. Playhead Tick Projection
        ph_x = self.timeline.tickToProjectedX(self.timeline.model.blueline.playhead_tick) - scroll_x
        
        # 1. Shadow/Glow (Subtle elevation)
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.setPen(Qt.NoPen)
        shadow_off = 1.5
        shadow_handle = QPolygonF([
            QPointF(ph_x - 6 + shadow_off, 2 + shadow_off), 
            QPointF(ph_x + 6 + shadow_off, 2 + shadow_off), 
            QPointF(ph_x + 6 + shadow_off, 11 + shadow_off), 
            QPointF(ph_x + shadow_off, 18 + shadow_off), 
            QPointF(ph_x - 6 + shadow_off, 11 + shadow_off)
        ])
        painter.drawPolygon(shadow_handle)

        # 2. Main Diamond Handle Geometry
        # A more stylized, taller and sharper hexagonal diamond
        handle_poly = QPolygonF([
            QPointF(ph_x - 6, 2),   # Top Left
            QPointF(ph_x + 6, 2),   # Top Right
            QPointF(ph_x + 6, 11),  # Mid Right
            QPointF(ph_x, 18),      # Tip Bottom
            QPointF(ph_x - 6, 11)   # Mid Left
        ])
        
        # 3. Base Fill (Deep Dark Gray)
        painter.setBrush(QColor("#1a1a1a"))
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawPolygon(handle_poly)
        
        # 4. Glowing Core (Diamond facet look)
        core_poly = QPolygonF([
            QPointF(ph_x - 3, 4), 
            QPointF(ph_x + 3, 4), 
            QPointF(ph_x + 3, 9), 
            QPointF(ph_x, 14), 
            QPointF(ph_x - 3, 9)
        ])
        
        grad = QLinearGradient(ph_x, 4, ph_x, 14)
        grad.setColorAt(0, QColor("#00c3ff")) # Bright Cyan
        grad.setColorAt(1, QColor("#005577")) # Deep Navy
        
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(core_poly)
        
        # 5. Highlight on the tip
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawPoint(QPointF(ph_x, 18))

        # 6. Playhead Line (Exact Center)
        line_ruler = QLineF(int(ph_x), 18, int(ph_x), self.height())
        
        # Glow / Soft Border
        painter.setPen(QPen(QColor(0, 0, 0, 150), 3))
        painter.drawLine(line_ruler)
        
        # High-precision white center
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawLine(line_ruler)



    def mouseMoveEvent(self, event):
        self.mouse_x = event.x()
        self.timeline.mouse_x = self.mouse_x 
        
        if event.buttons() & Qt.MouseButton.LeftButton: 
            scroll_area = self.timeline.get_scroll_area_context()
            scroll_x = scroll_area.horizontalScrollBar().value() if scroll_area else 0
            self.timeline.update_playhead_to_x(event.x() + scroll_x)
            
        self.update()

    def leaveEvent(self, event):
        self.mouse_x = -1
        self.timeline.mouse_x = -1
        self.update()

    def mousePressEvent(self, event): 
        if event.button() == Qt.MouseButton.LeftButton:
            scroll_area = self.timeline.get_scroll_area_context()
            scroll_x = scroll_area.horizontalScrollBar().value() if scroll_area else 0
            self.timeline.update_playhead_to_x(event.x() + scroll_x)
            self.update()
