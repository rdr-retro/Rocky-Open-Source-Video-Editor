from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                                QSizePolicy, QPushButton, QStackedWidget, QDoubleSpinBox,
                                QScrollArea, QGroupBox, QFormLayout, QCheckBox)
from PySide6.QtCore import Qt, Signal, QTimer
from .effects_dialog import OverlayViewer
from . import design_tokens as dt

class VideoEventFXPanel(QWidget):
    """
    Panel version of the Media Transformer.
    Contextual: Shows transformation controls for the currently selected clip.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rocky_app = self._find_rocky_app()
        self.current_clip = None
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._init_ui()

    def _find_rocky_app(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'engine'):
                return widget
        return None

    def _init_ui(self):
        self.setStyleSheet(f"background-color: #1a1a1a; color: #e0e0e0;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        # Page 0: Placeholder (No clip selected)
        self.placeholder = QWidget()
        p_layout = QVBoxLayout(self.placeholder)
        msg = QLabel("SELECCIONA UN CLIP PARA EDITAR")
        msg.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(msg)
        self.stack.addWidget(self.placeholder)
        
        # Page 1: FX Editor
        self.editor_widget = QWidget()
        e_layout = QVBoxLayout(self.editor_widget)
        e_layout.setContentsMargins(10, 10, 10, 10)
        e_layout.setSpacing(10)
        
        # Layout matching EffectsDialog
        from PySide6.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Orientation.Vertical) # Vertical for panel-fit
        
        # 1. Overlay Viewer
        self.viewer_container = QWidget()
        v_layout = QVBoxLayout(self.viewer_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        self.viewer_frame = QFrame()
        self.viewer_frame.setStyleSheet("background-color: #000000; border: 1px solid #333; border-radius: 4px;")
        vf_layout = QVBoxLayout(self.viewer_frame)
        vf_layout.setContentsMargins(0, 0, 0, 0)
        
        self.display_label = OverlayViewer()
        self.display_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.display_label.app = self.rocky_app
        vf_layout.addWidget(self.display_label)
        
        v_layout.addWidget(self.viewer_frame, stretch=1)
        
        # 2. FX Controls Area (Scrollable)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background-color: #1a1a1a; border: none;")
        
        self.controls_container = QWidget()
        self.controls_container.setStyleSheet("background-color: #1a1a1a;")
        self.c_layout = QVBoxLayout(self.controls_container)
        self.c_layout.setContentsMargins(10, 10, 10, 10)
        self.c_layout.setSpacing(15)
        
        # Transformation Group
        self.trans_group = QGroupBox("TRANSFORMACIÓN")
        self.trans_group.setStyleSheet("""
            QGroupBox { 
                color: #888; 
                font-weight: bold; 
                font-size: 10px; 
                border: 1px solid #333; 
                margin-top: 15px; 
                padding-top: 10px;
                border-radius: 4px;
            } 
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 3px; 
            }
        """)
        t_form = QFormLayout(self.trans_group)
        t_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        t_form.setSpacing(8)
        
        # Spinboxes
        self.spin_x = self._create_spin(-10.0, 10.0)
        self.spin_y = self._create_spin(-10.0, 10.0)
        self.spin_sx = self._create_spin(0.01, 20.0, 1.0)
        self.spin_sy = self._create_spin(0.01, 20.0, 1.0)
        self.spin_rot = self._create_spin(-360.0, 360.0)
        
        t_form.addRow("Posición X", self.spin_x)
        t_form.addRow("Posición Y", self.spin_y)
        t_form.addRow("Escala X", self.spin_sx)
        t_form.addRow("Escala Y", self.spin_sy)
        t_form.addRow("Rotación", self.spin_rot)
        
        # Connect Spins
        self.spin_x.valueChanged.connect(self._on_transform_ui_changed)
        self.spin_y.valueChanged.connect(self._on_transform_ui_changed)
        self.spin_sx.valueChanged.connect(self._on_transform_ui_changed)
        self.spin_sy.valueChanged.connect(self._on_transform_ui_changed)
        self.spin_rot.valueChanged.connect(self._on_transform_ui_changed)
        
        self.c_layout.addWidget(self.trans_group)
        
        # Effects Group
        self.fx_list_group = QGroupBox("EFECTOS APLICADOS")
        self.fx_list_group.setStyleSheet(self.trans_group.styleSheet())
        self.fx_list_layout = QVBoxLayout(self.fx_list_group)
        self.c_layout.addWidget(self.fx_list_group)
        
        self.c_layout.addStretch()
        
        self.scroll.setWidget(self.controls_container)
        self.splitter.addWidget(self.viewer_container)
        self.splitter.addWidget(self.scroll)
        
        # Set initial sizes: Viewer gets 70%, Controls get 30%
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        
        # Force initial sizes (in pixels, will be adjusted by stretch factors)
        QTimer.singleShot(0, lambda: self.splitter.setSizes([700, 300]))
        
        e_layout.addWidget(self.splitter, stretch=1)
        
        e_layout.addWidget(self.splitter, stretch=1)

        self.stack.addWidget(self.editor_widget)
        self.stack.setCurrentIndex(0)

    def update_context(self, selected_clips):
        """Slot called when timeline selection changes."""
        print(f"DEBUG Transformador: update_context called with {len(selected_clips) if selected_clips else 0} clips")
        if not selected_clips:
            self.current_clip = None
            self.stack.setCurrentIndex(0)
            return
            
        clip = selected_clips[0]
        print(f"DEBUG Transformador: Selected clip: {clip.name if hasattr(clip, 'name') else clip}")
        if clip == self.current_clip:
            return
            
        self.current_clip = clip
        self._bind_clip_data(clip)
        self.stack.setCurrentIndex(1)

    def display_frame(self, frame_buffer):
        from PySide6.QtGui import QImage, QPixmap
        import numpy as np
        
        if not isinstance(frame_buffer, np.ndarray):
            return
            
        height, width, channels = frame_buffer.shape
        bytes_per_line = channels * width
        image = QImage(frame_buffer.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image)
        
        # We store the pixmap directly. OverlayViewer logic uses it.
        # This matches EffectsDialog logic.
        self.display_label.setPixmap(pixmap)
        self.display_label.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-render frame on resize
        if self.current_clip:
            self.seek_preview(0.0)

    def _bind_clip_data(self, clip):
        # Update Viewer
        self.display_label.set_clip(clip)
        if self.rocky_app:
            self.display_label.project_res = (self.rocky_app.width(), self.rocky_app.height())
        
        # Sync from Viewer to UI
        try:
            self.display_label.transform_changed.disconnect()
        except:
            pass
        self.display_label.transform_changed.connect(self._update_ui_from_transform)
        
        # Populate UI
        self._update_ui_from_transform()
        self._refresh_effects_list()
        
        # If thumbnails are already there, show them immediately (matches EffectsDialog)
        if hasattr(clip, 'thumbnails') and clip.thumbnails:
            QTimer.singleShot(50, self.display_label.update)
            
        # Trigger initial preview (at start of clip)
        QTimer.singleShot(100, lambda: self.seek_preview(0.0))


    def seek_preview(self, time_s):
        if not self.rocky_app or not hasattr(self.rocky_app, 'engine'):
            return
            
        if not self.current_clip:
            return
            
        fps = 30.0
        if self.rocky_app and hasattr(self.rocky_app, 'get_fps'):
            fps = self.rocky_app.get_fps()
            
        global_time = (self.current_clip.start_frame / fps) + time_s
        
        try:
            frame_data = self.rocky_app.engine.evaluate(global_time)
            if frame_data is not None:
                self.display_frame(frame_data)
        except Exception as e:
            print(f"Transformador Preview Error: {e}")

    # --- Internal Logic ---

    def _create_spin(self, min_val, max_val, initial=0.0):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(initial)
        spin.setDecimals(3)
        spin.setSingleStep(0.01)
        spin.setStyleSheet("""
            QDoubleSpinBox { 
                background: #111; 
                color: #eee; 
                border: 1px solid #333; 
                padding: 4px; 
                border-radius: 2px;
                min-width: 80px;
            }
        """)
        return spin

    def _on_transform_ui_changed(self):
        """UI -> Model Sync."""
        if not self.current_clip or not self.rocky_app: return
        
        self.current_clip.transform.x = self.spin_x.value()
        self.current_clip.transform.y = self.spin_y.value()
        self.current_clip.transform.scale_x = self.spin_sx.value()
        self.current_clip.transform.scale_y = self.spin_sy.value()
        self.current_clip.transform.rotation = self.spin_rot.value()
        
        # Notify app to sync with C++ engine and refresh preview
        self.rocky_app.sync_clip_transform(self.current_clip)
        self.display_label.update() # Refresh handles

    def _update_ui_from_transform(self):
        """Model -> UI Sync."""
        if not self.current_clip: return
        t = self.current_clip.transform
        
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        self.spin_sx.blockSignals(True)
        self.spin_sy.blockSignals(True)
        self.spin_rot.blockSignals(True)
        
        self.spin_x.setValue(t.x)
        self.spin_y.setValue(t.y)
        self.spin_sx.setValue(t.scale_x)
        self.spin_sy.setValue(t.scale_y)
        self.spin_rot.setValue(t.rotation)
        
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)
        self.spin_sx.blockSignals(False)
        self.spin_sy.blockSignals(False)
        self.spin_rot.blockSignals(False)

    def _refresh_effects_list(self):
        """Populate the effects section with applied plugins."""
        while self.fx_list_layout.count():
            item = self.fx_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not self.current_clip or not hasattr(self.current_clip, 'effects'):
            return
            
        if not self.current_clip.effects:
            msg = QLabel("Arrastra efectos aquí para aplicarlos")
            msg.setStyleSheet("color: #555; font-size: 10px; font-style: italic; margin: 10px;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fx_list_layout.addWidget(msg)
            return

        for i, effect in enumerate(self.current_clip.effects):
            self._add_effect_row(i, effect)

    def _add_effect_row(self, index, effect):
        row = QFrame()
        row.setStyleSheet("background-color: #222; border-radius: 4px; padding: 5px;")
        h_layout = QHBoxLayout(row)
        h_layout.setContentsMargins(5, 5, 5, 5)
        
        # Checkbox Enabled
        cb = QCheckBox()
        cb.setChecked(effect.get('enabled', True))
        cb.toggled.connect(lambda checked, idx=index: self._toggle_effect(idx, checked))
        h_layout.addWidget(cb)
        
        # Name
        name = QLabel(effect.get('name', 'Unknown FX'))
        name.setStyleSheet("color: #ccc; font-weight: bold; font-size: 11px;")
        h_layout.addWidget(name, stretch=1)
        
        # Delete Btn
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("QPushButton { background: transparent; color: #666; border: none; } QPushButton:hover { color: #f44; }")
        del_btn.clicked.connect(lambda _, idx=index: self._delete_effect(idx))
        h_layout.addWidget(del_btn)
        
        self.fx_list_layout.addWidget(row)

    def _toggle_effect(self, index, enabled):
        if self.current_clip and index < len(self.current_clip.effects):
            self.current_clip.effects[index]['enabled'] = enabled
            if self.rocky_app:
                # Trigger rebuild or selective sync? 
                # rebuild_engine is safer for OFX list changes
                self.rocky_app.rebuild_engine()
                # Re-seek to start to show effect change
                self.seek_preview(0.0)

    def _delete_effect(self, index):
        if self.current_clip and index < len(self.current_clip.effects):
            self.current_clip.effects.pop(index)
            self._refresh_effects_list()
            if self.rocky_app:
                self.rocky_app.rebuild_engine()
                self.seek_preview(0.0)
