from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QPoint, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath
import math

class RadialMenu(QWidget):
    """
    Blender-style Pie Menu.
    Appears at mouse position, options are arranged in a circle.
    """
    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Items: [(Label, Icon, Callback), ...]
        self.items = items or []
        self.radius = 120
        self.inner_radius = 40
        self.hovered_idx = -1
        
        self.setMouseTracking(True)
        self.setFixedSize(self.radius * 2 + 50, self.radius * 2 + 50)
        
    def show_at(self, pos):
        """Show the menu centered at pos (global)."""
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        self.show()
        self.grabMouse() # Capture mouse to handle selection

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2, self.height() / 2
        num_items = len(self.items)
        if num_items == 0: return

        angle_step = 360 / num_items
        
        for i, (label, icon, callback) in enumerate(self.items):
            start_angle = i * angle_step - 90 - (angle_step / 2)
            
            # Draw Sector
            path = QPainterPath()
            path.arcMoveTo(cx - self.radius, cy - self.radius, self.radius * 2, self.radius * 2, -start_angle)
            path.arcTo(cx - self.radius, cy - self.radius, self.radius * 2, self.radius * 2, -start_angle, -angle_step)
            path.arcTo(cx - self.inner_radius, cy - self.inner_radius, self.inner_radius * 2, self.inner_radius * 2, -start_angle - angle_step, angle_step)
            path.closeSubpath()
            
            color = QColor(255, 153, 0, 200) if i == self.hovered_idx else QColor(30, 30, 30, 230)
            painter.fillPath(path, QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
            painter.drawPath(path)
            
            # Draw Label & Icon
            mid_angle = math.radians(i * angle_step - 90)
            tx = cx + (self.radius * 0.75) * math.cos(mid_angle)
            ty = cy + (self.radius * 0.75) * math.sin(mid_angle)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            
            rect = QRectF(tx - 45, ty - 25, 90, 50)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{icon}\n{label}")

    def mouseMoveEvent(self, event):
        cx, cy = self.width() / 2, self.height() / 2
        dx = event.position().x() - cx
        dy = event.position().y() - cy
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < self.inner_radius:
            self.hovered_idx = -1
        else:
            angle = math.degrees(math.atan2(dy, dx)) + 90
            if angle < 0: angle += 360
            
            num_items = len(self.items)
            angle_step = 360 / num_items
            idx = int((angle + (angle_step / 2)) % 360 // angle_step)
            self.hovered_idx = idx if idx < num_items else -1
            
        self.update()

    def mouseReleaseEvent(self, event):
        if self.hovered_idx != -1:
            label, icon, callback = self.items[self.hovered_idx]
            callback()
        
        self.releaseMouse()
        self.hide()
        self.deleteLater()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.deleteLater()
