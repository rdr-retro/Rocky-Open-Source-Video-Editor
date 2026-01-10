import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygon

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
        self.COLOR_BG = QColor("#252525")
        self.COLOR_TICK = QColor("#555555")
        self.COLOR_PLAYHEAD = QColor("#00a3ff")
        self.COLOR_HOVER = QColor("#44475a")
        self.FONT_MAIN = QFont("Roboto Mono", 9)
        self.FONT_MAIN.setPixelSize(11)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Vegas Pro Industrial Ruler
        painter.fillRect(self.rect(), self.COLOR_BG)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(0, self.height()-1, self.width(), self.height()-1)
        
        # 1. Coordinate Synthesis
        pixels_per_second = self.timeline.pixels_per_second
        scroll_area = self.timeline.get_scroll_area_context()
        scroll_x = scroll_area.horizontalScrollBar().value() if scroll_area else 0
        
        visible_start_time = scroll_x / float(pixels_per_second if pixels_per_second > 0 else 1)
        fps = self.timeline.get_fps()
        
        # 2. Adaptive Step Calculation
        step = self._calculate_adaptive_step(pixels_per_second, fps)
        
        # 3. Tick Rendering
        painter.setPen(QPen(self.COLOR_TICK, 1))
        painter.setFont(self.FONT_MAIN)
        
        time_cursor = math.floor(visible_start_time / step) * step
        while time_cursor < (scroll_x + self.width()) / float(pixels_per_second) + step:
            screen_x = self.timeline.timeToScreen(time_cursor) - scroll_x
            
            if -100 <= screen_x <= self.width() + 100:
                self._draw_tick_label(painter, screen_x, time_cursor, fps)
                self._draw_sub_ticks(painter, screen_x, pixels_per_second, time_cursor, step)
            
            time_cursor += step
            
        # 4. Interactive Elements (Hover, Playhead)
        self._draw_hover_indicator(painter)
        self._draw_playhead_handle(painter, scroll_x, fps)

    def _calculate_adaptive_step(self, px_per_sec, fps):
        candidates = [
            1.0/fps, 2.0/fps, 5.0/fps, 10.0/fps, 
            1.0, 2.0, 5.0, 10.0, 30.0,           
            60.0, 120.0, 300.0, 600.0, 1800.0,     
            3600.0                               
        ]
        chosen_step = candidates[-1]
        for s in candidates:
            if s * px_per_sec >= 100:
                chosen_step = s
                break
        return chosen_step

    def _draw_tick_label(self, painter, x, time, fps):
        painter.drawLine(x, 5, x, 30)
        frame_idx = int(round(time * fps))
        timecode = self.timeline.model.format_timecode(frame_idx, fps)
        painter.drawText(x + 5, 18, timecode)

    def _draw_sub_ticks(self, painter, x, px_per_sec, time, step):
        # Middle Tick
        mid_x = self.timeline.timeToScreen(time + step/2.0) - (x + self.timeline.get_scroll_area_context().horizontalScrollBar().value() if self.timeline.get_scroll_area_context() else 0)
        # Fix: the previous logic for sub-ticks was a bit messy. 
        # For simplicity, let's just use the absolute coordinate from timeToScreen relative to viewport.
        scroll_x = self.timeline.get_scroll_area_context().horizontalScrollBar().value() if self.timeline.get_scroll_area_context() else 0
        
        mid_screen_x = self.timeline.timeToScreen(time + step/2.0) - scroll_x
        painter.drawLine(mid_screen_x, 18, mid_screen_x, 30)
        
        sub_step = step / 10.0
        if sub_step * px_per_sec > 6:
            for i in range(1, 10):
                if i == 5: continue
                stx = self.timeline.timeToScreen(time + sub_step * i) - scroll_x
                painter.drawLine(stx, 24, stx, 30)

    def _draw_hover_indicator(self, painter):
        # Hover indicator removed to fulfill user request for a cleaner interface.
        pass

    def _draw_playhead_handle(self, painter, scroll_x, fps):
        ph_x = self.timeline.timeToScreen(self.timeline.model.blueline.playhead_frame / fps) - scroll_x
        painter.setBrush(self.COLOR_PLAYHEAD)
        painter.setPen(QPen(Qt.white, 1))
        # Iconic Vegas playhead diamond shape
        handle = QPolygon([
            QPoint(ph_x - 6, 0), 
            QPoint(ph_x + 6, 0), 
            QPoint(ph_x + 6, 10), 
            QPoint(ph_x, 16), 
            QPoint(ph_x - 6, 10)
        ])
        painter.drawPolygon(handle)

    def mouseMoveEvent(self, event):
        self.mouse_x = event.x()
        self.timeline.mouse_x = self.mouse_x 
        
        if event.buttons() & Qt.LeftButton: 
            self.timeline.update_playhead_to_x(event.x())
            
        self.update()

    def leaveEvent(self, event):
        self.mouse_x = -1
        self.timeline.mouse_x = -1
        self.update()

    def mousePressEvent(self, event): 
        if event.button() == Qt.LeftButton:
            self.timeline.update_playhead_to_x(event.x())
            self.update()
