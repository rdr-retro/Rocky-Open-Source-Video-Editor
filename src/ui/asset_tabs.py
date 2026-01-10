from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, QPushButton, QInputDialog
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

class AssetTabsPanel(QFrame):
    """
    Premium tabbed panel for assets and effects, inspired by professional NLEs.
    Tabs are positioned at the bottom with high-end aesthetics.
    """
    resolution_changed = pyqtSignal(int, int) # width, height

    def __init__(self):
        super().__init__()
        self.setObjectName("AssetTabsPanel")
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            #AssetTabsPanel {
                background-color: #111111;
                border-right: 1px solid #000;
            }
            QTabWidget::pane {
                border-top: 1px solid #222;
                background: #111111;
            }

            QTabBar::tab {
                background: #151515;
                color: #888;
                padding: 10px 20px;
                margin-right: 1px;
                border-top: 2px solid transparent;
                font-family: 'Inter', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
                text-transform: none;
            }
            QTabBar::tab:selected {
                background: #111111;
                color: #00a3ff;
                border-top: 2px solid #00a3ff;
            }

            QTabBar::tab:hover:!selected {
                color: #bbb;
                background: #1a1a1a;
            }
            
            /* Aspect Ratio Card Styling */
            QPushButton.AspectCard {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                min-width: 100px;
                max-width: 100px;
                min-height: 120px;
                padding: 10px;
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
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setDocumentMode(True)

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

        # Grid-like container for Aspect Cards
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setContentsMargins(20, 10, 20, 10)
        grid_layout.setSpacing(15)
        grid_layout.setAlignment(Qt.AlignLeft)

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

        main_layout.addWidget(grid_widget)
        main_layout.addStretch()
        return container

    def _create_aspect_card(self, title, ratio_text, w_icon, h_icon, res_w, res_h, is_custom=False):
        card = QPushButton()
        card.setProperty("class", "AspectCard")
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(5)

        # The Visual Box (Miniature of the Aspect Ratio)
        visual_box = QFrame()
        visual_box.setFixedSize(w_icon, h_icon)
        visual_box.setProperty("class", "RatioBox")
        visual_box.setAttribute(Qt.WA_TransparentForMouseEvents) # Pass clicks to button
        layout.addWidget(visual_box, 0, Qt.AlignCenter)

        # Title Label
        title_label = QLabel(title)
        title_label.setProperty("class", "AspectTitle")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(title_label)

        # Subtitle (Resolution/Ratio)
        sub_label = QLabel(ratio_text)
        sub_label.setStyleSheet("color: #666; font-size: 9px;")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(sub_label)

        if is_custom:
            card.clicked.connect(self._on_custom_resolution)
        else:
            card.clicked.connect(lambda: self.resolution_changed.emit(res_w, res_h))

        return card

    def _on_custom_resolution(self):
        w, ok1 = QInputDialog.getInt(self, "Resolución Personalizada", "Ancho (px):", 1920, 100, 8192)
        if ok1:
            h, ok2 = QInputDialog.getInt(self, "Resolución Personalizada", "Alto (px):", 1080, 100, 8192)
            if ok2:
                self.resolution_changed.emit(w, h)

    def _on_custom_resolution(self):
        w, ok1 = QInputDialog.getInt(self, "Resolución Personalizada", "Ancho (px):", 1920, 100, 8192)
        if ok1:
            h, ok2 = QInputDialog.getInt(self, "Resolución Personalizada", "Alto (px):", 1080, 100, 8192)
            if ok2:
                self.resolution_changed.emit(w, h)

    def _create_empty_view(self):
        """Creates a clean, neutral container for each tab's content."""
        view = QFrame()
        view.setStyleSheet("background-color: #0d0d0d;")
        return view
