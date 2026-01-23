from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, QPushButton, QInputDialog, QLayout, QSizePolicy, QScrollArea, QDialog, QSpinBox, QComboBox, QCheckBox, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize, QMimeData, QByteArray, QDataStream, QIODevice, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QDrag, QPixmap, QImage, QPainter, QColor, QPen, QLinearGradient
import os
import sys
import rocky_core
from . import design_tokens as dt

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # src/ui/asset_tabs.py -> ../.. -> root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_path, relative_path)

class FlowLayout(QLayout):
    """
    Standard FlowLayout implementation for PyQt.
    Allows elements to wrap intelligently to the next line when width is restricted.
    """
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()
        if spacing < 0:
            spacing = 10

        line_items = []
        
        for item in self.itemList:
            nextX = x + item.sizeHint().width() + spacing
            if nextX - spacing > rect.right() and lineHeight > 0:
                # Finish current line
                if not testOnly:
                    self._align_line(line_items, rect, y, lineHeight, spacing)
                
                x = rect.x()
                y = y + lineHeight + spacing
                nextX = x + item.sizeHint().width() + spacing
                lineHeight = 0
                line_items = []
            
            line_items.append(item)
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        
        # Finish last line
        if not testOnly:
            self._align_line(line_items, rect, y, lineHeight, spacing)
            
        return y + lineHeight - rect.y()

    def _align_line(self, items, rect, y, lineHeight, spacing):
        """Centers items in the current row."""
        if not items:
            return
            
        total_w = sum(item.sizeHint().width() for item in items) + (len(items) - 1) * spacing
        offset_x = (rect.width() - total_w) // 2
        
        curr_x = rect.x() + offset_x
        for item in items:
            item.setGeometry(QRect(QPoint(curr_x, y), item.sizeHint()))
            curr_x += item.sizeHint().width() + spacing

class DraggableEffectButton(QPushButton):
    def __init__(self, name, description, plugin_path=""):
        super().__init__()
        self.name = name
        self.description = description
        self.plugin_path = plugin_path
        self._drag_start_pos = None
        self._sweep_pos = 0.0

        self.setFixedSize(140, 110)
        
        # Load and prepare images
        fx_path = get_resource_path(os.path.join("src", "img", "fx.png"))
        self.base_pixmap = QPixmap(fx_path)
        if self.base_pixmap.isNull():
            # Fallback if image not found
            self.base_pixmap = QPixmap(140, 80)
            self.base_pixmap.fill(QColor("#1a1a1a"))
        else:
            # PROFESSIONAL SCALING: Scale to fill then crop center to avoid stretching
            self.base_pixmap = self.base_pixmap.scaled(140, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            # Center Crop
            crop_x = (self.base_pixmap.width() - 140) // 2
            crop_y = (self.base_pixmap.height() - 80) // 2
            self.base_pixmap = self.base_pixmap.copy(crop_x, crop_y, 140, 80)
        
        # Create Inverted Version
        img = self.base_pixmap.toImage()
        img.invertPixels()
        self.inverted_pixmap = QPixmap.fromImage(img)

        self.anim = QPropertyAnimation(self, b"sweep_pos")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setMouseTracking(True)

    @Property(float)
    def sweep_pos(self):
        return self._sweep_pos

    @sweep_pos.setter
    def sweep_pos(self, value):
        self._sweep_pos = value
        self.update()

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._sweep_pos)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._sweep_pos)
        self.anim.setEndValue(0.0)
        self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Border/Background
        is_hovered = self.underMouse()
        bg_rect = self.rect().adjusted(1, 1, -1, -1)
        
        border_color = QColor("#00a3ff") if is_hovered else QColor("#333")
        painter.setPen(QPen(border_color, 1.5 if is_hovered else 1))
        painter.setBrush(QColor("#181818"))
        painter.drawRoundedRect(bg_rect, dt.RADIUS_ELEMENT, dt.RADIUS_ELEMENT)

        # Image Area
        img_rect = QRect(2, 2, self.width()-4, 80)
        
        # Clip to rounded rect for image
        painter.setClipPath(self._get_rounded_path(img_rect, dt.RADIUS_ELEMENT))
        
        # 1. Base Image
        painter.drawPixmap(img_rect, self.base_pixmap)

        # 2. Inverted Reveal (Sweep)
        if self._sweep_pos > 0:
            reveal_w = int(img_rect.width() * self._sweep_pos)
            source_rect = QRect(0, 0, reveal_w, 80)
            target_rect = QRect(img_rect.x(), img_rect.y(), reveal_w, 80)
            painter.drawPixmap(target_rect, self.inverted_pixmap, source_rect)
            
            # 3. Vegas Line (The Sweep Edge)
            line_x = img_rect.x() + reveal_w
            painter.setPen(QPen(QColor("#00a3ff"), 2))
            painter.drawLine(line_x, img_rect.top(), line_x, img_rect.bottom())
            
            # Subglow for the line
            grad = QLinearGradient(line_x - 15, 0, line_x, 0)
            grad.setColorAt(0, QColor(0, 163, 255, 0))
            grad.setColorAt(1, QColor(0, 163, 255, 80))
            painter.fillRect(line_x - 15, img_rect.top(), 15, 80, grad)
        
        painter.setClipping(False)

        # 4. Text Overlay (Bottom Area)
        text_rect = QRect(0, 80, self.width(), 30)
        painter.setPen(QColor("#fff" if is_hovered else "#bbb"))
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.name)

    def _get_rounded_path(self, rect, radius):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self._drag_start_pos:
            return
            
        dist = (event.pos() - self._drag_start_pos).manhattanLength()
        if dist < 10:
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        data_str = f"{self.name}|{self.plugin_path}"
        mime.setData("application/x-rocky-effect", QByteArray(data_str.encode('utf-8')))
        drag.setMimeData(mime)
        pixmap = self.grab(QRect(0, 0, self.width(), 80))
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.CopyAction)

class CustomResolutionDialog(QDialog):
    """
    Advanced dialog for custom project resolution settings.
    Includes presets, aspect ratio lock, and modern aesthetics.
    """
    def __init__(self, parent=None, current_w=1920, current_h=1080):
        super().__init__(parent)
        self.setWindowTitle("Resolución Personalizada")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #111111;
                color: #ffffff;
            }
            QLabel {
                color: #999;
                font-size: 11px;
                font-family: 'Inter', sans-serif;
            }
            QLabel#Header {
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 20px;
            }
            QSpinBox, QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
                color: #fff;
                padding: 8px;
                font-size: 12px;
            }
            QSpinBox:focus, QComboBox:focus {
                border-color: #00a3ff;
            }
            QPushButton#ActionBtn {
                background-color: #00a3ff;
                color: #000;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton#ActionBtn:hover {
                background-color: #33b5ff;
            }
            QPushButton#CancelBtn {
                background-color: transparent;
                color: #666;
                border: none;
                padding: 10px;
            }
            QPushButton#CancelBtn:hover {
                color: #999;
            }
            QCheckBox {
                color: #888;
                font-size: 11px;
                spacing: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        header = QLabel("Ajustes de Fotograma")
        header.setObjectName("Header")
        layout.addWidget(header)

        # Presets
        layout.addWidget(QLabel("PREAJUSTES COMUNES"))
        self.preset_combo = QComboBox()
        self.presets = {
            "Personalizado": (current_w, current_h),
            "YouTube 4K (3840x2160)": (3840, 2160),
            "YouTube Full HD (1920x1080)": (1920, 1080),
            "Instagram/TikTok (1080x1920)": (1080, 1920),
            "Instagram Square (1080x1080)": (1080, 1080),
            "DCI 4K (4096x2160)": (4096, 2160),
            "Twitter HD (1280x720)": (1280, 720)
        }
        self.preset_combo.addItems(self.presets.keys())
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addWidget(self.preset_combo)

        # Width & Height
        dims_layout = QHBoxLayout()
        
        v_w = QVBoxLayout()
        v_w.addWidget(QLabel("ANCHO (PX)"))
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 8192)
        self.w_spin.setValue(current_w)
        self.w_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.w_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.w_spin.valueChanged.connect(self._on_dims_manually_changed)
        v_w.addWidget(self.w_spin)
        
        v_h = QVBoxLayout()
        v_h.addWidget(QLabel("ALTO (PX)"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 8192)
        self.h_spin.setValue(current_h)
        self.h_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.h_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_spin.valueChanged.connect(self._on_dims_manually_changed)
        v_h.addWidget(self.h_spin)

        dims_layout.addLayout(v_w)
        dims_layout.addLayout(v_h)
        layout.addLayout(dims_layout)

        # Aspect Ratio Lock
        self.cb_lock = QCheckBox("Bloquear relación de aspecto")
        self.cb_lock.setChecked(True)
        self.current_ratio = current_w / current_h
        layout.addWidget(self.cb_lock)

        # ---------------------------------------------------------------------
        # RECOGNITION SYSTEM (Auto-Detect)
        # ---------------------------------------------------------------------
        self.btn_detect = QPushButton("Detectar desde medio...")
        self.btn_detect.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #00a3ff;
                border: 1px solid #00a3ff;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #00a3ff; color: #000; }
        """)
        self.btn_detect.clicked.connect(self._on_auto_detect_clicked)
        layout.addWidget(self.btn_detect)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("Aplicar Resolución")
        ok_btn.setObjectName("ActionBtn")
        ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_preset_changed(self, index):
        preset_name = self.preset_combo.currentText()
        if preset_name != "Personalizado":
            w, h = self.presets[preset_name]
            self.w_spin.blockSignals(True)
            self.h_spin.blockSignals(True)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            self.w_spin.blockSignals(False)
            self.h_spin.blockSignals(False)
            self.current_ratio = w / h

    def _on_dims_manually_changed(self):
        self.preset_combo.setCurrentText("Personalizado")
        if self.cb_lock.isChecked():
            sender = self.sender()
            if sender == self.w_spin:
                self.h_spin.blockSignals(True)
                self.h_spin.setValue(int(self.w_spin.value() / self.current_ratio))
                self.h_spin.blockSignals(False)
            else:
                self.w_spin.blockSignals(True)
                self.w_spin.setValue(int(self.h_spin.value() * self.current_ratio))
                self.w_spin.blockSignals(False)
        else:
            self.current_ratio = self.w_spin.value() / self.h_spin.value()

    def _on_auto_detect_clicked(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from ..infrastructure.ffmpeg_utils import FFmpegUtils
        import rocky_core
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar medio para reconocer formato", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if file_path:
            # STAGE 1: Fast Probe (Returns NATIVE params)
            specs = FFmpegUtils.get_media_specs(file_path)
            w, h, rot = specs['width'], specs['height'], specs['rotation']
            
            # Manual Swap Logic for Stage 1
            if abs(rot) == 90 or abs(rot) == 270:
                w, h = h, w
            
            # STAGE 2: Engine Fallback (Returns VISUAL params directly)
            if w <= 0 or h <= 0:
                try:
                    temp_src = rocky_core.VideoSource(file_path); 
                    if temp_src.isValid():
                        w, h, rot = temp_src.get_width(), temp_src.get_height(), temp_src.get_rotation()
                except: pass
            
            if w <= 0 or h <= 0: w, h = 1920, 1080
            
            self.w_spin.blockSignals(True)
            self.h_spin.blockSignals(True)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            self.w_spin.blockSignals(False)
            self.h_spin.blockSignals(False)
            
            self.current_ratio = w / h if h != 0 else 1.0
            self.preset_combo.setCurrentText("Personalizado")
            
            QMessageBox.information(self, "Formato Detectado", f"Se ha detectado {w}x{h}.\n\nRelación de aspecto actualizada.")

    def get_resolution(self):
        return self.w_spin.value(), self.h_spin.value()

class AssetTabsPanel(QFrame):
    """
    Premium tabbed panel for assets and effects, inspired by professional NLEs.
    Tabs are positioned at the bottom with high-end aesthetics.
    """
    resolution_changed = Signal(int, int) # width, height

    def __init__(self):
        super().__init__()
        self.setObjectName("AssetTabsPanel")
        self.setMinimumWidth(450)
        self.setStyleSheet(f"""
            #AssetTabsPanel {{
                background-color: #111111;
                border: none;
            }}
            QTabWidget::pane {{
                border: none;
                background: #111111;
            }}


            QTabBar::tab {{
                background: transparent;
                color: #777;
                padding: 10px 20px;
                margin-right: 15px;
                border-bottom: 2px solid transparent;
                border-top-left-radius: {dt.RADIUS_ELEMENT}px;
                border-top-right-radius: {dt.RADIUS_ELEMENT}px;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: #00a3ff;
                border-bottom: 2px solid #00a3ff;
            }}

            QTabBar::tab:hover:!selected {{
                color: #bbb;
            }}
            
            /* Aspect Ratio Card Styling */
            QPushButton.AspectCard {{
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 0px;
                min-width: 100px;
                max-width: 250px;
                min-height: 120px;
                padding: 15px;
            }}
            QPushButton.AspectCard:hover {{
                background-color: #222;
                border-color: #00a3ff;
            }}
            QPushButton.AspectCard:pressed {{
                background-color: #00a3ff;
            }}

            QLabel.AspectTitle {{
                color: #e0e0e0;
                font-size: 10px;
                font-weight: 600;
                margin-top: 8px;
            }}
            
            /* Visual Geometry Boxes */
            QFrame.RatioBox {{
                background-color: #333;
                border: 1px solid #555;
            }}
            QPushButton.AspectCard:hover QFrame.RatioBox {{
                border-color: #00a3ff;
            }}

            QLabel.SectionHeader {{
                color: #00a3ff;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.2px;
                margin-top: 15px;
                margin-left: 20px;
                margin-bottom: 10px;
                text-transform: uppercase;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.South)
        self.tabs.setDocumentMode(True)
        # Ensure full text visibility (no "Gene...")
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.tabBar().setUsesScrollButtons(True)



        # 2. Transiciones
        self.tab_transitions = self._create_empty_view()
        self.tabs.addTab(self.tab_transitions, "Transiciones")

        # 3. Efectos
        self.tab_effects = self._create_effects_view()
        self.tabs.addTab(self.tab_effects, "Efectos")

        # 4. Generadores de medios
        self.tab_generators = self._create_empty_view()
        self.tabs.addTab(self.tab_generators, "Generadores de medios")

        layout.addWidget(self.tabs)

        # Load Invert Plugin
        plugin_path = os.path.abspath("plugins/invert.ofx")
        if os.path.exists(plugin_path):
            print(f"Loading Invert OFX: {plugin_path}")
            success = rocky_core.load_ofx_plugin(plugin_path)
            if success:
                print("Invert Plugin Loaded Successfully!")
                self._add_effect_button("Invertir Color", "Negativo / Invertir", plugin_path=plugin_path)
        else:
            print(f"Invert OFX Not Found at: {plugin_path}")

    def _create_effects_view(self):
        container = QFrame()
        container.setStyleSheet("background-color: #111111;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 5, 0, 0)
        main_layout.setSpacing(0)

        header = QLabel("BIBLIOTECA DE EFECTOS")
        header.setProperty("class", "SectionHeader")
        main_layout.addWidget(header)
        
        # Grid for Effects
        self.effects_grid = QWidget()
        self.effects_grid.setStyleSheet("background: transparent;")
        self.effects_layout = FlowLayout(self.effects_grid)
        self.effects_layout.setContentsMargins(20, 20, 20, 20)
        self.effects_layout.setSpacing(25)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(self.effects_grid)
        
        main_layout.addWidget(scroll)
        return container

    def _add_effect_button(self, name, description, plugin_path=""):
        btn = DraggableEffectButton(name, description, plugin_path)
        self.effects_layout.addWidget(btn)

    def _create_general_view(self):
        container = QFrame()
        container.setStyleSheet("background-color: #111111;")
        main_layout = QVBoxLayout(container)

        main_layout.setContentsMargins(0, 5, 0, 0)
        main_layout.setSpacing(0)

        header = QLabel("FORMATO DE PROYECTO")
        header.setProperty("class", "SectionHeader")
        main_layout.addWidget(header)

        # Scrollable container for Aspect Cards to prevent window forcing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid_layout = FlowLayout(grid_widget)
        grid_layout.setContentsMargins(20, 10, 20, 10)
        grid_layout.setSpacing(15)

        # 1. 16:9 Wide
        grid_layout.addWidget(self._create_aspect_card("Panorámico", "16:9", 40, 22, 1920, 1080))
        # 2. 21:9 Ultrawide
        grid_layout.addWidget(self._create_aspect_card("Cinemático", "21:9", 44, 18, 2560, 1080))
        # 3. 4:3 Box
        grid_layout.addWidget(self._create_aspect_card("Clásico", "4:3", 32, 24, 1440, 1080))
        # 4. 9:16 Vertical
        grid_layout.addWidget(self._create_aspect_card("Vertical", "9:16", 20, 36, 1080, 1920))
        # 5. 1:1 Square
        grid_layout.addWidget(self._create_aspect_card("Cuadrado", "1:1", 30, 30, 1080, 1080))
        # 6. Custom
        btn_custom = self._create_aspect_card("Personalizado", "...", 30, 30, 0, 0, True)
        grid_layout.addWidget(btn_custom)

        scroll.setWidget(grid_widget)
        main_layout.addWidget(scroll)
        return container

    def _create_aspect_card(self, title, ratio_text, w_icon, h_icon, res_w, res_h, is_custom=False):
        card = QPushButton()
        card.setProperty("class", "AspectCard")
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)

        # The Visual Box (Miniature of the Aspect Ratio)
        visual_box = QFrame()
        visual_box.setFixedSize(w_icon, h_icon)
        visual_box.setProperty("class", "RatioBox")
        visual_box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Pass clicks to button
        layout.addWidget(visual_box, 0, Qt.AlignmentFlag.AlignCenter)

        # Title Label
        title_label = QLabel(title)
        title_label.setProperty("class", "AspectTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title_label)

        # Subtitle (Resolution/Ratio)
        sub_label = QLabel(ratio_text)
        sub_label.setStyleSheet("color: #666; font-size: 9px;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(sub_label)

        if is_custom:
            card.clicked.connect(self._on_custom_resolution)
        else:
            card.clicked.connect(lambda: self.resolution_changed.emit(res_w, res_h))

        return card

    def _on_custom_resolution(self):
        dlg = CustomResolutionDialog(self)
        if dlg.exec():
            w, h = dlg.get_resolution()
            self.resolution_changed.emit(w, h)

    def _create_empty_view(self):
        """Creates a clean, neutral container for each tab's content."""
        view = QFrame()
        view.setStyleSheet("background-color: #0d0d0d;")
        return view
