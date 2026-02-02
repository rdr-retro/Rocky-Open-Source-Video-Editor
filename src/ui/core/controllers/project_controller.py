import os
import json
import rocky_core
from PySide6.QtWidgets import QFileDialog, QMessageBox
from ..models import TimelineModel

class ProjectController:
    def __init__(self, main_window):
        self.mw = main_window

    def on_open(self):
        file_path, _ = QFileDialog.getOpenFileName(self.mw, "Abrir Proyecto", "", "Rocky Project (*.rocky);;All Files (*)")
        if file_path:
            self.load_project(file_path)

    def on_save(self):
        if self.mw.project_path:
            self.save_project(self.mw.project_path)
        else:
            self.on_save_as()

    def on_save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Guardar Proyecto", "", "Rocky Project (*.rocky)")
        if file_path:
            if not file_path.endswith('.rocky'):
                file_path += '.rocky'
            self.save_project(file_path)

    def save_project(self, path):
        try:
            data = self.mw.model.to_dict()
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            self.mw.project_path = path
            self.mw.status_label.setText(f"Proyecto guardado: {os.path.basename(path)}")
            self.mw.setWindowTitle(f"Rocky Video Editor Pro - {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self.mw, "Error al guardar", f"No se pudo guardar el proyecto:\n{str(e)}")

    def load_project(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            new_model = TimelineModel.from_dict(data)
            
            if self.mw.model.blueline.playing:
                self.mw.toggle_play()
                
            self.mw.model = new_model
            if self.mw.sidebar:
                self.mw.sidebar.model = new_model
            if self.mw.timeline_widget:
                self.mw.timeline_widget.model = new_model
            
            self.mw.audio_worker.model = new_model
            self.mw.project_path = path
            self.mw.setWindowTitle(f"Rocky Video Editor Pro - {os.path.basename(path)}")
            
            self.mw.on_structure_changed()
            self.mw.status_label.setText(f"Proyecto cargado: {os.path.basename(path)}")
            
            # Recalculate waveforms and thumbnails
            for clip in self.mw.model.clips:
                if clip.file_path and os.path.exists(clip.file_path):
                    from ..models import TrackType
                    track_type = self.mw.model.track_types[clip.track_index]
                    if track_type == TrackType.VIDEO:
                        self.mw._start_thumbnail_analysis(clip)
                        self.mw._trigger_proxy_generation(clip)
            
        except Exception as e:
            QMessageBox.critical(self.mw, "Error al cargar", f"No se pudo cargar el proyecto:\n{str(e)}")
