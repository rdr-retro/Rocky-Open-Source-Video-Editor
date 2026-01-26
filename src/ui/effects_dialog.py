from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame, QSizePolicy, QPushButton
from PySide6.QtCore import Qt, QRectF, QLineF, QPointF, QTimer, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QImage, QPixmap, QPainterPath
import math

class OverlayViewer(QLabel):
    """
    Subclass of QLabel that draws interactive Pan/Crop handles over the video.
    """
    transform_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.video_rect = QRect() # Actual screen rect of the video content
        self.clip = None # Reference to the clip being edited
        self.project_res = (1920, 1080) # Default guidance aspect
        self.dragging_handle = None # 'tl', 'tr', 'bl', 'br' or 'body'
        self.app = None
        
        # Workspace Zoom & Pan
        self.view_zoom = 1.0
        self.view_offset = QPointF(0, 0)
        self.panning = False

    def set_clip(self, clip):
        self.clip = clip

    def _get_thumbnail(self):
        """Helper to get a cached thumbnail from the clip model."""
        if hasattr(self.clip, 'thumbnails') and self.clip.thumbnails:
            # Prefer the middle thumbnail (index 1) if available
            if len(self.clip.thumbnails) > 1:
                return self.clip.thumbnails[1]
            return self.clip.thumbnails[0]
        else:
            pass
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 0. Draw Dark Workspace Background (Static, fills the whole widget)
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        
        # --- Apply World Transformations ---
        # We save the painter state and apply transformations for the "world" (stage, video, handles)
        painter.save()
        # Origin is center of widget + manual pan offset
        painter.translate(self.width()/2 + self.view_offset.x(), self.height()/2 + self.view_offset.y())
        painter.scale(self.view_zoom, self.view_zoom)
        # Move back so that logic based on widget center (lw/2, lh/2) works correctly
        painter.translate(-self.width()/2, -self.height()/2)
        
        # 1. Draw Stage (Project Boundary)
        label_size = self.size()
        lw, lh = label_size.width(), label_size.height()
        
        if lw < 10 or lh < 10:
            painter.restore()
            return # Dialog not fully laid out yet
        
        # Calculate Project Frame at 80% of label size
        try:
            # Safety Check: Ensure we have valid numeric values
            res_w = self.project_res[0]() if callable(self.project_res[0]) else self.project_res[0]
            res_h = self.project_res[1]() if callable(self.project_res[1]) else self.project_res[1]
            p_aspect = float(res_w) / float(res_h)
        except (TypeError, ValueError, ZeroDivisionError, IndexError):
            p_aspect = 16.0 / 9.0 # Fallback standard
            
        l_aspect = lw / lh
        
        if p_aspect > l_aspect:
            p_w = lw * 0.8
            p_h = p_w / p_aspect
        else:
            p_h = lh * 0.8
            p_w = p_h * p_aspect
            
        px = (lw - p_w) // 2
        py = (lh - p_h) // 2
        stage_rect = QRectF(px, py, p_w, p_h)
        
        # Draw Stage Area
        painter.setBrush(QColor(10, 10, 10))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(stage_rect)
        
        # Draw Project Boundary (Dashed Line)
        painter.setPen(QPen(QColor(100, 100, 100), 1, Qt.PenStyle.DashLine))
        painter.drawRect(stage_rect)
        
        # Draw Center Crosshair for alignment
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        painter.drawLine(int(lw/2), int(py), int(lw/2), int(py+p_h))
        painter.drawLine(int(px), int(lh/2), int(px+p_w), int(lh/2))

        # 2. Draw Video Layout (Thumbnail base + Live frame)
        if self.clip and hasattr(self.clip, 'transform'):
            t = self.clip.transform
            vw = p_w * t.scale_x
            vh = p_h * t.scale_y
            vx = lw/2 - vw/2 + (t.x * p_w)
            vy = lh/2 - vh/2 - (t.y * p_h) 
            
            self.video_rect = QRectF(vx, vy, vw, vh).toRect()
            
            # A. Draw Thumbnail Background (Always as basis for guidance)
            thumb = self._get_thumbnail()
            if thumb:
                painter.drawImage(self.video_rect, thumb)
            
            # B. Draw Live High-Res Frame (On top)
            if self.pixmap() and not self.pixmap().isNull():
                if self.dragging_handle:
                    painter.setOpacity(0.6)
                painter.drawPixmap(self.video_rect, self.pixmap())
                painter.setOpacity(1.0)
            
            if not thumb and (not self.pixmap() or self.pixmap().isNull()):
                painter.fillRect(self.video_rect, QColor(30, 30, 30))
                painter.setPen(QPen(QColor(60, 60, 60), 1))
                painter.drawRect(self.video_rect)
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(self.video_rect, Qt.AlignmentFlag.AlignCenter, f"Cargando {self.clip.name if self.clip else 'Media'}...")

            # Draw Video Border
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.drawRect(self.video_rect)
            
            # Draw Handles (Triangular)
            COLOR_HANDLE = QColor(0, 150, 255)
            h_size = 18 
            painter.setBrush(COLOR_HANDLE)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # TL Triangle
            path_tl = QPainterPath()
            path_tl.moveTo(vx, vy)
            path_tl.lineTo(vx + h_size, vy)
            path_tl.lineTo(vx, vy + h_size)
            path_tl.closeSubpath()
            painter.drawPath(path_tl)
            
            # TR Triangle
            path_tr = QPainterPath()
            path_tr.moveTo(vx + vw, vy)
            path_tr.lineTo(vx + vw - h_size, vy)
            path_tr.lineTo(vx + vw, vy + h_size)
            path_tr.closeSubpath()
            painter.drawPath(path_tr)
            
            # BL Triangle
            path_bl = QPainterPath()
            path_bl.moveTo(vx, vy + vh)
            path_bl.lineTo(vx + h_size, vy + vh)
            path_bl.lineTo(vx, vy + vh - h_size)
            path_bl.closeSubpath()
            painter.drawPath(path_bl)
            
            # BR Triangle
            path_br = QPainterPath()
            path_br.moveTo(vx + vw, vy + vh)
            path_br.lineTo(vx + vw - h_size, vy + vh)
            path_br.lineTo(vx + vw, vy + vh - h_size)
            path_br.closeSubpath()
            painter.drawPath(path_br)
            
            # Center Cross Hair (Always Logical)
            painter.setPen(QPen(COLOR_HANDLE, 1, Qt.PenStyle.DashLine))
            cx, cy = int(vx + vw/2), int(vy + vh/2)
            painter.drawLine(cx - 10, cy, cx + 10, cy)
            painter.drawLine(cx, cy - 10, cx, cy + 10)

        painter.restore()
        
        # 3. Draw Overlay UI (Screen space - untransformed)
        painter.setPen(QColor(200, 200, 200, 200))
        painter.setFont(QFont("Inter", 10))
        zoom_text = f"ZOOM: {int(self.view_zoom * 100)}%"
        painter.drawText(self.rect().adjusted(15, 0, -15, -15), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, zoom_text)
        
        if self.view_zoom > 1.0 or self.panning:
             painter.drawText(self.rect().adjusted(15, 0, -15, -15), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "Click Central para PAN")
    def _screen_to_logical(self, pos):
        """Map screen pixel coordinates to logical workspace coordinates (affected by zoom/pan)."""
        # Invert the transformations applied in paintEvent:
        # 1. Offset by widget center
        # 2. Invert pan/offset
        # 3. Invert zoom/scale
        # 4. Re-center relative to center
        
        lx = (pos.x() - self.width()/2 - self.view_offset.x()) / self.view_zoom + self.width()/2
        ly = (pos.y() - self.height()/2 - self.view_offset.y()) / self.view_zoom + self.height()/2
        return QPointF(lx, ly)

    def wheelEvent(self, event):
        """Handle workspace zoom."""
        delta = event.angleDelta().y()
        zoom_factor = 1.15 if delta > 0 else 1.0 / 1.15
        
        # Zoom around mouse cursor or center? 
        # For simplicity, zoom around center for now, but Vegas usually zooms to cursor.
        old_zoom = self.view_zoom
        self.view_zoom = max(0.1, min(10.0, self.view_zoom * zoom_factor))
        
        # Optional: Adjust view_offset to keep cursor stable (Vegas feature)
        # For now, just basic zoom
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        self.last_mouse_pos = pos
        
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self.app and getattr(self.app, 'space_pressed', False)):
            self.panning = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Map click to logical space
            l_pos = self._screen_to_logical(pos)
            
            x, y = self.video_rect.x(), self.video_rect.y()
            rw, rh = self.video_rect.width(), self.video_rect.height()
            h_size = 15 
            
            # Hit testing for corners using logical pos
            if QRect(x, y, h_size, h_size).contains(l_pos.toPoint()):
                self.dragging_handle = "tl"
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif QRect(x + rw - h_size, y, h_size, h_size).contains(l_pos.toPoint()):
                self.dragging_handle = "tr"
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif QRect(x, y + rh - h_size, h_size, h_size).contains(l_pos.toPoint()):
                self.dragging_handle = "bl"
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif QRect(x + rw - h_size, y + rh - h_size, h_size, h_size).contains(l_pos.toPoint()):
                self.dragging_handle = "br"
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self.video_rect.contains(l_pos.toPoint()):
                self.dragging_handle = "body"
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.dragging_handle = None

    def mouseMoveEvent(self, event):
        pos = event.position()
        if not self.last_mouse_pos:
            self.last_mouse_pos = pos
            return

        dx_pix = pos.x() - self.last_mouse_pos.x()
        dy_pix = pos.y() - self.last_mouse_pos.y()
        self.last_mouse_pos = pos
        
        if self.panning:
            self.view_offset += QPointF(dx_pix, dy_pix)
            self.update()
            return
            
        if not self.dragging_handle:
            # Update cursor on hover (using logical space)
            l_pos = self._screen_to_logical(pos)
            x, y = self.video_rect.x(), self.video_rect.y()
            rw, rh = self.video_rect.width(), self.video_rect.height()
            h_size = 15
            if QRect(x, y, h_size, h_size).contains(l_pos.toPoint()) or QRect(x + rw - h_size, y + rh - h_size, h_size, h_size).contains(l_pos.toPoint()):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif QRect(x + rw - h_size, y, h_size, h_size).contains(l_pos.toPoint()) or QRect(x, y + rh - h_size, h_size, h_size).contains(l_pos.toPoint()):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif self.video_rect.contains(l_pos.toPoint()):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        # Sensitivity should be adjusted by zoom so dragging feels natural
        logical_dx = dx_pix / self.view_zoom
        logical_dy = dy_pix / self.view_zoom

        if self.dragging_handle == "body":
            p_w = self.width() * 0.8
            p_h = self.height() * 0.8
            dx = logical_dx / p_w
            dy = -logical_dy / p_h
            if hasattr(self.clip, 'transform'):
                self.clip.transform.x += dx
                self.clip.transform.y += dy
                
        elif self.dragging_handle in ["tl", "br", "tr", "bl"]:
            sensitivity = 0.005
            change_x = logical_dx * sensitivity
            change_y = logical_dy * sensitivity
            if "t" in self.dragging_handle: change_y = -change_y
            if "l" in self.dragging_handle: change_x = -change_x
            if hasattr(self.clip, 'transform'):
                self.clip.transform.scale_x = max(0.01, self.clip.transform.scale_x + change_x)
                self.clip.transform.scale_y = max(0.01, self.clip.transform.scale_y + change_y)
        
        if self.dragging_handle and self.app:
            self.app.sync_clip_transform(self.clip)
            self.transform_changed.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_handle = None
        self.panning = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setCursor(Qt.CursorShape.ArrowCursor)

# FXTimeline removed as per PROHIBIDO constraint.

class EffectsDialog(QDialog):
    """
    Dialog for managing clip effects (FX) with a local sub-timeline.
    """
    def __init__(self, clip, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.rocky_app = parent # Assuming parent is RockyApp
        
        # Get FPS and Project Res
        fps = 30.0
        p_res = (1920, 1080)
        if parent and hasattr(parent, 'get_fps'):
            fps = parent.get_fps()
            # Try to get project resolution from engine or fallback to parent size
            if hasattr(parent, 'engine') and parent.engine:
                # Use engine resolution if available (most accurate for project)
                p_res = (1920, 1080) # Default
            elif hasattr(parent, 'width') and hasattr(parent, 'height'):
                p_res = (parent.width(), parent.height())
        elif hasattr(clip, 'model') and clip.model:
             fps = clip.model.get_fps()
             
        self.setWindowTitle(f"Video Event FX: {clip.name}")
        self.resize(900, 650)
        self.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Upper Section: Splitter for Viewer and FX Controls
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        
        # 1. Local Viewer
        self.viewer_container = QWidget()
        v_layout = QVBoxLayout(self.viewer_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        
        self.viewer_frame = QFrame()
        self.viewer_frame.setStyleSheet("background-color: #000000; border: 1px solid #444; border-radius: 4px;")
        self.viewer_frame.setMinimumWidth(400)
        viewer_layout = QVBoxLayout(self.viewer_frame)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.display_label = OverlayViewer()
        self.display_label.set_clip(clip)
        self.display_label.app = self.rocky_app
        self.display_label.project_res = p_res
        self.display_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        viewer_layout.addWidget(self.display_label)
        
        c_layout.addStretch()
        
        v_layout.addWidget(self.viewer_frame, stretch=1)
        
        # 2. FX Controls Area
        self.fx_area = QFrame()
        self.fx_area.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        fx_layout = QVBoxLayout(self.fx_area)
        
        label = QLabel("FX Parameters & Controls")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888888; font-size: 16px; font-weight: bold;")
        fx_layout.addWidget(label)
        
        splitter.addWidget(self.viewer_container)
        splitter.addWidget(self.fx_area)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, stretch=1)
        
        layout.addWidget(splitter, stretch=1)
        
        # Trigger initial preview
        QTimer.singleShot(100, lambda: self.seek_preview(0.0))
        # If thumbnails are already there, show them immediately
        if hasattr(clip, 'thumbnails') and clip.thumbnails:
            QTimer.singleShot(50, self.display_label.update)

    def seek_preview(self, time_s):
        """Render a single frame from the clip at time_s."""
        if not self.rocky_app or not hasattr(self.rocky_app, 'engine'):
            return
            
        # Use project/app FPS
        fps = 30.0
        if self.rocky_app and hasattr(self.rocky_app, 'get_fps'):
            fps = self.rocky_app.get_fps()
            
        global_time = (self.clip.start_frame / fps) + time_s
        
        try:
            frame_data = self.rocky_app.engine.evaluate(global_time)
            if frame_data is not None:
                self.display_frame(frame_data)
        except Exception as e:
            print(f"FX Preview Error: {e}")

    # Local playback removed as per PROHIBIDO constraint.

    def display_frame(self, frame_buffer):
        """Heavily optimized frame display."""
        height, width, channels = frame_buffer.shape
        bytes_per_line = channels * width
        image = QImage(frame_buffer.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image)
        
        # We store the pixmap directly. OverlayViewer.paintEvent handles scaling.
        # However, to avoid HUGE memory usage in UI, we can limit it to 1080p width
        if width > 1920:
            pixmap = pixmap.scaledToWidth(1920, Qt.TransformationMode.SmoothTransformation)
            
        self.display_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-render frame on resize
        self.seek_preview(0.0)
