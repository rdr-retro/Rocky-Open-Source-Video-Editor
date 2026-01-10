from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QScrollArea, QSlider
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QMimeData
from PyQt5.QtGui import QColor, QPainter, QPen, QLinearGradient, QFont, QDrag
from .models import TrackType
from .styles import SLIDER_STYLE

class TimecodeHeader(QFrame):
    """Header que coincide exactamente con el Timeline Ruler (35px)"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(38) 
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setContentsMargins(0, 0, 0, 0) 
        self._current_tc = "00:00:00;00"

    def set_timecode(self, tc):
        if tc is None: return
        self._current_tc = tc
        self.repaint() # Force immediate repaint to prevent "ghosting" or loss

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Fondo oscuro Pro
        p.fillRect(self.rect(), QColor("#222222"))
        
        # TIMECODE GIGANTE (White and Right Aligned)
        p.setPen(QPen(Qt.white, 1))
        
        # Use a robust font stack to ensure it always renders nicely
        font = QFont("Roboto Mono", 22, QFont.Bold)
        font.setStyleHint(QFont.Monospace)
        if not font.exactMatch():
            font = QFont("Menlo", 22, QFont.Bold)
            if not font.exactMatch():
                font = QFont("Courier New", 22, QFont.Bold)
                
        p.setFont(font)
        
        # Right aligned with 10px padding
        draw_rect = self.rect().adjusted(0, 0, -10, 0)
        p.drawText(draw_rect, Qt.AlignRight | Qt.AlignVCenter, self._current_tc)
        
        # Línea inferior divisoria
        p.setPen(QPen(QColor("#444444"), 1))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)

class SidebarPanel(QWidget):
    def __init__(self, model, timeline=None):
        super().__init__()
        self.model = model
        self.timeline = timeline
        self._current_tc = "00:00:00;00"
        self.setFixedWidth(350)
        self.setAcceptDrops(True)
        
        # LAYOUT PRINCIPAL - CERO MÁRGENES
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # HEADER para alinearse con el Timeline Ruler (38px)
        self.header = TimecodeHeader(self)
        layout.addWidget(self.header, 0, Qt.AlignTop)
        
        # SCROLL AREA - CONFIGURACIÓN VEGAS PRO
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setLineWidth(0)
        self.scroll.setMidLineWidth(0)
        self.scroll.setContentsMargins(0, 0, 0, 0)
        self.scroll.setStyleSheet("""
            QScrollArea { 
                border: 0px;
                margin: 0px;
                padding: 0px;
                background: #242424;
            }
            QWidget {
                background: #242424;
            }
            QScrollBar:vertical { width: 0px; }
        """)
        
        # TRACK CONTAINER - CERO MÁRGENES
        self.track_container = QWidget()
        self.track_container.setContentsMargins(0, 0, 0, 0)
        self.track_layout = QVBoxLayout(self.track_container)
        self.track_layout.setContentsMargins(0, 0, 0, 0)
        self.track_layout.setSpacing(0)
        
        self.empty_area = QFrame()
        self.empty_area.setMinimumHeight(2000)
        self.empty_area.setStyleSheet("background-color: #242424; border: none;") # Match Timeline BG
        self.empty_area.setContentsMargins(0, 0, 0, 0)
        self.track_layout.addWidget(self.empty_area)
        
        self.track_widgets = []
        self.scroll.setWidget(self.track_container)
        self.scroll.setViewportMargins(0, 0, 0, 0)
        self.scroll.viewport().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)

        # FOOTER
        self.footer = QFrame()
        self.footer.setFixedHeight(35)
        self.footer.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333333;")
        self.footer.setContentsMargins(0, 0, 0, 0)
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(10, 0, 10, 0)
        self.rl = QLabel("Playback Rate: 1.00")
        self.rl.setStyleSheet("color: #00a3ff; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
        self.ss = QSlider(Qt.Horizontal)
        self.ss.setFixedWidth(100)
        self.ss.setRange(-400, 400)
        self.ss.setValue(100)
        self.ss.setStyleSheet(SLIDER_STYLE)
        f_layout.addWidget(self.rl)
        f_layout.addWidget(self.ss)
        f_layout.addStretch()
        layout.addWidget(self.footer)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_ui)
        self.refresh_timer.start(20)

    def contextMenuEvent(self, event):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Añadir pista de vídeo").triggered.connect(lambda: self.add_track(TrackType.VIDEO))
        menu.addAction("Añadir pista de audio").triggered.connect(lambda: self.add_track(TrackType.AUDIO))
        menu.exec_(event.globalPos())

    def add_track(self, ttype):
        self.model.track_types.append(ttype)
        self.model.track_heights.append(60)
        self.refresh_tracks()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("track:"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            from_idx = int(event.mimeData().text().split(":")[1])
            # Calculate absolute Y (using 38px header)
            abs_y = event.pos().y() + self.scroll.verticalScrollBar().value() - 38 
            
            # Find target index based on dynamic track heights
            to_idx = len(self.model.track_heights) - 1
            curr_y = 0
            for i, h in enumerate(self.model.track_heights):
                if curr_y <= abs_y < curr_y + h:
                    to_idx = i
                    break
                curr_y += h
            
            if from_idx != to_idx:
                # 1. Update the Model's track structure
                removed_type = self.model.track_types.pop(from_idx)
                removed_height = self.model.track_heights.pop(from_idx)
                self.model.track_types.insert(to_idx, removed_type)
                self.model.track_heights.insert(to_idx, removed_height)
                
                # 2. IMPORTANT: Re-map every clip's track_index
                for clip in self.model.clips:
                    if clip.track_index == from_idx:
                        clip.track_index = to_idx
                    elif from_idx < to_idx:
                        # Moving track DOWN: tracks between from and to move UP
                        if from_idx < clip.track_index <= to_idx:
                            clip.track_index -= 1
                    elif from_idx > to_idx:
                        # Moving track UP: tracks between to and from move DOWN
                        if to_idx <= clip.track_index < from_idx:
                            clip.track_index += 1
                
                self.model.layout_revision += 1
                if self.timeline:
                    self.timeline.structure_changed.emit()
                event.acceptProposedAction()
        except Exception as e:
            print(f"Track Reorder Error: {e}")
            pass

    def refresh_ui(self):
        for w in self.track_widgets:
            w.update_labels()
            w.update()

    def refresh_tracks(self):
        # 1. Clean up existing track widgets (leave empty_area)
        for w in self.track_widgets:
            w.setParent(None)
            w.deleteLater()
        self.track_widgets = []
        
        # 2. Re-create tracks from model
        for i, t in enumerate(self.model.track_types):
            track_height = self.model.track_heights[i] if i < len(self.model.track_heights) else 60
            w = TrackControlWidget(t, i, self)
            w.setFixedHeight(track_height)
            # Insert at top, before empty_area
            self.track_layout.insertWidget(i, w)
            self.track_widgets.append(w)
        
        # 3. Ensure empty_area is at the END and layout remains tight
        self.track_layout.removeWidget(self.empty_area)
        self.track_layout.addWidget(self.empty_area)
        
        self.refresh_ui()
        if self.timeline:
            self.timeline.updateGeometry()

class TrackControlWidget(QFrame):
    def __init__(self, track_type, index, sidebar):
        super().__init__()
        self.track_type, self.index, self.sidebar = track_type, index, sidebar
        self.setFixedWidth(350)
        self.setFixedHeight(60)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLineWidth(0)
        self.setFrameShape(QFrame.NoFrame)
        
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setGeometry(140, 25, 170, 20)
        self.slider.setStyleSheet(SLIDER_STYLE)
        
        self.lbl_value = QLabel("100,0 %" if track_type == TrackType.VIDEO else "0,0 dB", self)
        self.lbl_value.setGeometry(75, 12, 60, 15)
        
        self.text_color = QColor("#ffffff")
        self.update_labels()

    def update_labels(self):
        is_selected = self.index in self.sidebar.model.selected_tracks
        self.text_color = QColor("#000000") if is_selected else QColor("#ffffff")
        self.lbl_value.setStyleSheet(f"color: {self.text_color.name()}; font-size: 10px; border: none; background: none;")
        
        # Ajuste dinámico: solo ocultamos el slider si la pista es REALMENTE mínima ( < 25px )
        # Pero los NÚMEROS (lbl_value) se mantienen visibles más tiempo
        self.slider.setVisible(self.height() > 35)
        self.lbl_value.setVisible(self.height() > 22)
        
        # Reposicionamiento del número para que no se corte
        self.lbl_value.setGeometry(75, max(2, (self.height() - 15) // 2), 60, 15)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        is_selected = self.index in self.sidebar.model.selected_tracks
        p.fillRect(self.rect(), QColor('#748a91') if is_selected else QColor('#242424'))
        
        # Franja lateral (Refined Maroon for Video, Teal for Audio)
        scol = QColor("#9e364a") if self.track_type == TrackType.VIDEO else QColor("#369e93")
        p.fillRect(0, 0, 24, self.height(), scol)
        p.setPen(QColor("#000000"))
        p.drawLine(24, 0, 24, self.height())
        
        # Gripper (3 rayas)
        p.setPen(self.text_color)
        p.setBrush(self.text_color)
        for i in range(3):
            p.drawRect(6, 4 + i*3, 12, 1)
        
        # NÚMERO DE PISTA (Vegas Pro style - centrado verticalmente)
        # FORZAR COLOR EXPLÍCITO para máxima visibilidad
        p.setPen(QColor("#000000") if is_selected else QColor("#ffffff"))
        p.setFont(QFont("Inter", 12, QFont.Bold))
        p.drawText(2, 0, 20, self.height(), Qt.AlignCenter, str(self.index + 1))
        
        # Icono de tipo (abajo)
        if self.track_type == TrackType.VIDEO:
            p.setBrush(Qt.NoBrush)
            p.drawRect(6, 45, 12, 8)
        else:
            # Onda de audio
            mid_y = 48
            p.drawLine(5, mid_y, 7, mid_y-4)
            p.drawLine(7, mid_y-4, 10, mid_y+6)
            p.drawLine(10, mid_y+6, 13, mid_y-6)
            p.drawLine(13, mid_y-6, 16, mid_y+4)
            p.drawLine(16, mid_y+4, 19, mid_y)

        # Etiqueta de control
        p.setFont(QFont("Inter", 9))
        p.drawText(30, 24, "Nivel:" if self.track_type == TrackType.VIDEO else "Vol:")
        
        # VU Meters (si es audio)
        if self.track_type == TrackType.AUDIO:
            p.setFont(QFont("Inter", 7))
            p.setPen(QColor("#000000" if is_selected else "#cccccc"))
            # Numbers removed per user request (12 24 36 48)
            pass
        
        # Borde inferior (Coincide con el del TimelinePanel)
        p.setPen(QPen(Qt.black, 1))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos().x() < 24 and event.pos().y() < 15:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(f"track:{self.index}")
                drag.setMimeData(mime)
                drag.exec_(Qt.MoveAction)
                return
            
            if not (event.modifiers() & Qt.ControlModifier):
                self.sidebar.model.selected_tracks = [self.index]
                [setattr(c, 'selected', False) for c in self.sidebar.model.clips]
            else:
                if self.index in self.sidebar.model.selected_tracks:
                    self.sidebar.model.selected_tracks.remove(self.index)
                else:
                    self.sidebar.model.selected_tracks.append(self.index)
            if self.sidebar.timeline:
                self.sidebar.timeline.update()

    def contextMenuEvent(self, event):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Eliminar pista").triggered.connect(self.delete_track)
        menu.exec_(event.globalPos())

    def delete_track(self):
        self.sidebar.model.remove_track(self.index)
        self.sidebar.refresh_tracks()
