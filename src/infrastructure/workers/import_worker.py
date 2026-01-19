from PySide6.QtCore import QThread, Signal
import rocky_core
import os

class MediaImportWorker(QThread):
    """
    Background worker to probe media files (duration, format, etc.) 
    without blocking the UI thread.
    """
    finished = Signal(str, float, object) # file_path, duration_frames, source
    error = Signal(str, str) # file_path, error_message

    def __init__(self, file_path, fps=30.0):
        super().__init__()
        self.file_path = file_path
        self.fps = fps

    def run(self):
        try:
            # We open a temporary context just to probe metadata
            # This is safer than passing a full VideoSource object across threads
            ext = os.path.basename(self.file_path).lower().split('.')[-1]
            is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            
            duration_frames = 0
            if not is_image:
                # Use a lightweight probe to avoid heavy decoder init here
                temp_src = rocky_core.VideoSource(self.file_path)
                real_dur_sec = temp_src.get_duration()
                duration_frames = int(real_dur_sec * self.fps) if real_dur_sec > 0 else 300
                # We let the source be destroyed here; main thread will create its own
            
            self.finished.emit(self.file_path, float(duration_frames), None) # Pass None for source
            
        except Exception as e:
            self.error.emit(self.file_path, str(e))
