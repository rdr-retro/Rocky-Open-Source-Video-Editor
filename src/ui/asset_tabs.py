from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, QPushButton, QInputDialog, QLayout, QSizePolicy, QScrollArea, QDialog, QSpinBox, QComboBox, QCheckBox
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize
from PySide6.QtGui import QFont, QIcon

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
            spacing = 10  # Default fallback

        for item in self.itemList:
            nextX = x + item.sizeHint().width() + spacing
            if nextX - spacing > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spacing
                nextX = x + item.sizeHint().width() + spacing
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()

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
        self.setStyleSheet("""
            #AssetTabsPanel {
                background-color: #111111;
                border: none;
            }
            QTabWidget::pane {
                border: none;
                background: #111111;
            }


            QTabBar::tab {
                background: transparent;
                color: #777;
                padding: 10px 20px;
                margin-right: 15px;
                border-bottom: 2px solid transparent;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: transparent;
                color: #00a3ff;
                border-bottom: 2px solid #00a3ff;
            }

            QTabBar::tab:hover:!selected {
                color: #bbb;
            }
            
            /* Aspect Ratio Card Styling */
            QPushButton.AspectCard {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                min-width: 100px;
                max-width: 250px;
                min-height: 120px;
                padding: 15px;
            }
            QPushButton.AspectCard:hover {
                background-color: #222;
                border-color: #00a3ff;
            }
            QPushButton.AspectCard:pressed {
                background-color: #00a3ff;
            }

            QLabel.AspectTitle {
                color: #e0e0e0;
                font-size: 10px;
                font-weight: 600;
                margin-top: 8px;
            }
            
            /* Visual Geometry Boxes */
            QFrame.RatioBox {
                background-color: #333;
                border: 1px solid #555;
            }
            QPushButton.AspectCard:hover QFrame.RatioBox {
                border-color: #00a3ff;
            }

            QLabel.SectionHeader {
                color: #00a3ff;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.2px;
                margin-top: 15px;
                margin-left: 20px;
                margin-bottom: 10px;
                text-transform: uppercase;
            }
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

        # 1. General (Configuración del Proyecto)
        self.tab_general = self._create_general_view()
        self.tabs.addTab(self.tab_general, "General")

        # 2. Transiciones
        self.tab_transitions = self._create_empty_view()
        self.tabs.addTab(self.tab_transitions, "Transiciones")

        # 3. Efectos
        self.tab_effects = self._create_empty_view()
        self.tabs.addTab(self.tab_effects, "Efectos")

        # 4. Generadores de medios
        self.tab_generators = self._create_empty_view()
        self.tabs.addTab(self.tab_generators, "Generadores de medios")

        layout.addWidget(self.tabs)

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
