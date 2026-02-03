import os
import random
import rocky_core
from PySide6.QtCore import Qt, QTimer
from ..models import ProxyStatus, TrackType, TICKS_PER_SECOND
from ....infrastructure.workers.thumbnail import ThumbnailWorker
from ....infrastructure.workers.proxy_gen import ProxyWorker

class MediaController:
    def __init__(self, main_window):
        self.mw = main_window

    def import_media(self, file_path, start_tick, preferred_track_idx=-1):
        """Starts the asynchronous media import process with Tick precision."""
        from ....infrastructure.workers.import_worker import MediaImportWorker
        self.mw.status_label.setText(f"Probing media: {os.path.basename(file_path)}...")
        worker = MediaImportWorker(file_path, self.mw.get_fps())
        
        # Worker emits: path, dur_ticks, source, width, height, rotation, fps
        worker.finished.connect(lambda path, dur, src, w, h, r, f: self._finish_import_logic(
            path, dur, src, w, h, r, f, start_tick, preferred_track_idx))
        worker.error.connect(self._on_import_error)
        
        self.mw._active_workers.append(worker)
        worker.finished.connect(lambda: self.mw._safe_remove_worker(worker))
        worker.start()

    def _on_import_error(self, path, message):
        from PySide6.QtWidgets import QMessageBox
        self.mw.status_label.setText(f"Error importando {os.path.basename(path)}")
        QMessageBox.warning(self.mw, "Error de Importación", f"No se pudo cargar {path}:\n{message}")

    def _finish_import_logic(self, file_path, project_duration_ticks, source, width, height, rotation, source_fps, start_tick, preferred_track_idx):
        from ..models import TimelineClip, TrackType
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QMessageBox
        from ..utils import get_resource_path
        
        is_forced_vertical = False
        file_name = os.path.basename(file_path)
        ext = file_name.lower().split('.')[-1]
        
        was_empty = (len(self.mw.model.clips) == 0)
        is_audio = ext in ["mp3", "wav", "aac", "m4a", "flac"]
        
        if was_empty and not is_audio and width > 300 and height > 300:
            msg = QMessageBox(self.mw)
            msg.setWindowTitle("Configuración de Proyecto")
            
            vis_w, vis_h = width, height
            rotation_mod = abs(rotation) % 360
            if rotation_mod == 90 or rotation_mod == 270:
                vis_w, vis_h = height, width
            
            is_vertical = vis_h > vis_w
            aspect_str = "VERTICAL" if is_vertical else "PANORÁMICO"
            
            suggested_res = (vis_w, vis_h)
            force_w, force_h = vis_w, vis_h
            if vis_w > vis_h: force_w, force_h = vis_h, vis_w
            
            btn_match = msg.addButton(f"Ajustar a {vis_w}x{vis_h}", QMessageBox.YesRole)
            btn_force_vert = msg.addButton(f"Forzar Video Vertical (Shorts)", QMessageBox.ActionRole)
            btn_keep = msg.addButton("Mantener Actual", QMessageBox.NoRole)
            
            msg.setDefaultButton(btn_match)
            msg.setText(f"El medio detectado es {aspect_str} ({vis_w}x{vis_h}).")
            
            logo_path = get_resource_path("logo.png")
            if os.path.exists(logo_path):
                msg.setIconPixmap(QPixmap(logo_path).scaled(64,64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            msg.exec() 
            clicked = msg.clickedButton()
            
            if clicked == btn_match:
                self.mw.on_resolution_changed(suggested_res[0], suggested_res[1])
            elif clicked == btn_force_vert:
                self.mw.on_resolution_changed(force_w, force_h)
                if vis_w > vis_h: is_forced_vertical = True
            elif was_empty:
                self.mw.on_resolution_changed(1920, 1080)
        
        is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
        is_video = not is_audio and not is_image
        
        source_fps = source_fps if source_fps > 0 else self.mw.get_fps()
        native_source_frames = int((project_duration_ticks / TICKS_PER_SECOND) * source_fps) if not is_image else -1
        
        if is_image:
            project_duration_ticks = int(30 * TICKS_PER_SECOND)
        
        if is_video:
            v_track = preferred_track_idx if preferred_track_idx != -1 and self.mw.model.track_types[preferred_track_idx] == TrackType.VIDEO else -1
            if v_track == -1:
                self.mw.add_track(TrackType.VIDEO)
                v_track = len(self.mw.model.track_types) - 1
            
            v_clip = TimelineClip(file_name, start_tick, project_duration_ticks, v_track)
            v_clip.file_path = file_path
            v_clip.source_duration_frames = native_source_frames
            v_clip.source_width = width
            v_clip.source_height = height
            v_clip.source_rotation = rotation
            v_clip.source_fps = source_fps
            
            final_rotation = (float(rotation) + 270) % 360 if is_forced_vertical and width > height else float(rotation)
            v_clip.transform.rotation = final_rotation
            
            content_w, content_h = (height, width) if abs(final_rotation) % 180 != 0 else (width, height)
            final_scale = min(self.mw.p_width / content_w, self.mw.p_height / content_h)
            v_clip.transform.scale_x = v_clip.transform.scale_y = 1.0 if abs(final_scale - 1.0) < 0.01 else final_scale
            
            self.mw.add_track(TrackType.AUDIO)
            a_track = len(self.mw.model.track_types) - 1
            a_clip = TimelineClip(f"[Audio] {file_name}", start_tick, project_duration_ticks, a_track)
            a_clip.file_path = file_path
            a_clip.source_duration_frames = native_source_frames
            a_clip.source_fps = source_fps
            
            v_clip.linked_to = a_clip
            a_clip.linked_to = v_clip
            self.mw.model.add_clip(v_clip)
            self.mw.model.add_clip(a_clip)
            self._start_thumbnail_analysis(v_clip)
            self._trigger_proxy_generation(v_clip)
        else:
            required_type = TrackType.AUDIO if is_audio else TrackType.VIDEO
            t_idx = preferred_track_idx if preferred_track_idx != -1 and self.mw.model.track_types[preferred_track_idx] == required_type else -1
            if t_idx == -1:
                self.mw.add_track(required_type)
                t_idx = len(self.mw.model.track_types) - 1
            
            clip = TimelineClip(file_name, start_tick, project_duration_ticks, t_idx)
            clip.file_path = file_path
            clip.source_duration_frames = native_source_frames
            clip.source_fps = source_fps
            self.mw.model.add_clip(clip)
            
            if is_image:
                clip.source_width = width
                clip.source_height = height
                self._start_thumbnail_analysis(clip)

        self.mw.on_structure_changed()
        self.mw.status_label.setText(f"Importado: {file_name}")

    def _start_thumbnail_analysis(self, clip):
        """Dispatches a worker to compute thumbnails for the clip."""
        if not clip.file_path: return
        worker = ThumbnailWorker(clip, clip.file_path)
        worker.finished.connect(lambda c, t: self.on_thumbnails_finished(c, t))
        self.mw._active_workers.append(worker)
        worker.finished.connect(lambda: self.mw._safe_remove_worker(worker))
        worker.start()

    def _trigger_proxy_generation(self, clip):
        """Dispatches a worker to create a low-res proxy if needed."""
        if not clip.file_path or clip.proxy_status != ProxyStatus.NONE: 
            return
        
        # Only proxy video files
        ext = clip.file_path.lower().split('.')[-1]
        if ext in ["mp3", "wav", "aac", "m4a", "flac", "jpg", "jpeg", "png", "gif", "bmp", "webp"]:
            return

        clip.proxy_status = ProxyStatus.GENERATING
        self.update_proxy_button_state()
        self.mw.timeline_widget.update()
        
        worker = ProxyWorker(clip, clip.file_path)
        worker.finished.connect(lambda c, p, s: self._on_proxy_finished(c, p, s))
        self.mw._active_workers.append(worker)
        worker.finished.connect(lambda: self.mw._safe_remove_worker(worker))
        worker.start()

    def on_thumbnails_finished(self, clip, thumbs):
        """Callback when Thumbnails are ready. Updates model and UI."""
        clip.thumbnails = thumbs
        self.mw.on_structure_changed() # Trigger timeline redraw

    def _on_proxy_finished(self, clip, proxy_path, success):
        """Callback when Proxy worker ends (success or failure)."""
        if success:
            clip.proxy_path = proxy_path
            clip.proxy_status = ProxyStatus.READY
        else:
            clip.proxy_status = ProxyStatus.ERROR
            print(f"Proxy Generation failed for {clip.name}")
            
        self.update_proxy_button_state()
        self.mw.on_structure_changed()

    def update_proxy_button_state(self):
        """Updates the PX button color based on the status of all video clips."""
        video_clips = [c for c in self.mw.model.clips if self.mw.model.track_types[c.track_index] == TrackType.VIDEO]
        if not video_clips:
            self.mw.toolbar.set_proxy_status_color('black')
            return

        any_generating = False
        any_error = False
        all_ready = True
        
        for c in video_clips:
            if c.proxy_status == ProxyStatus.GENERATING:
                any_generating = True
                all_ready = False
            elif c.proxy_status == ProxyStatus.ERROR:
                any_error = True
                all_ready = False
            elif c.proxy_status != ProxyStatus.READY:
                all_ready = False
        
        if any_generating:
            self.mw.toolbar.set_proxy_status_color('orange')
        elif any_error:
            self.mw.toolbar.set_proxy_status_color('red')
        elif all_ready:
            self.mw.toolbar.set_proxy_status_color('green')
        else:
            self.mw.toolbar.set_proxy_status_color('black')

    def on_proxy_toggle(self):
        use_proxies = self.mw.toolbar.btn_proxy.isChecked()
        self.mw.toolbar.set_proxy_status_color('black')
        self.update_proxy_button_state()
        self.mw.rebuild_engine()

    def instantiate_source(self, path, track_type=TrackType.VIDEO):
        if not path or not os.path.exists(path):
            return rocky_core.ColorSource(random.randint(50,200), 50, 100, 255)
            
        if path in self.mw.media_source_cache:
            return self.mw.media_source_cache[path]

        lower_path = path.lower()
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        if track_type == TrackType.VIDEO:
            if lower_path.endswith(image_extensions):
                source = rocky_core.ImageSource(path)
            else:
                source = rocky_core.VideoSource(path)
        else:
            audio_extensions = ('.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac')
            if lower_path.endswith(audio_extensions):
                source = rocky_core.NativeAudioSource(path)
            else:
                source = rocky_core.VideoSource(path)
            
        self.mw.media_source_cache[path] = source
        return source
