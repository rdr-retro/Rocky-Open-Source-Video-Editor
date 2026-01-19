from PySide6.QtCore import QThread, Signal
import rocky_core
import os

class MediaImportWorker(QThread):
    """
    Background worker to probe media files (duration, format, etc.) 
    without blocking the UI thread.
    """
    finished = Signal(str, float, object, int, int) # file_path, duration_frames, source, width, height
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
            width = 0
            height = 0
            
            if not is_image:
                # Use a lightweight probe to avoid heavy decoder init here
                temp_src = rocky_core.VideoSource(self.file_path)
                real_dur_sec = temp_src.get_duration()
                duration_frames = int(real_dur_sec * self.fps) if real_dur_sec > 0 else 300
                
                # Extract Resolution
                if hasattr(temp_src, 'width'):
                    width = temp_src.width
                    height = temp_src.height
                else:
                    # Fallback methods if properties aren't directly exposed
                    try: width = temp_src.get_width()
                    except: width = 1920
                    try: height = temp_src.get_height()
                    except: height = 1080
                    
                # We let the source be destroyed here; main thread will create its own
            
            self.finished.emit(self.file_path, float(duration_frames), None, width, height) # Pass None for source
            
        except Exception as e:
            self.error.emit(self.file_path, str(e))
