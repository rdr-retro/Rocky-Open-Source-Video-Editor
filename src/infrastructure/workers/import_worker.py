from PySide6.QtCore import QThread, Signal
import os
import json
import subprocess
import rocky_core
from ..ffmpeg_utils import FFmpegUtils

class MediaImportWorker(QThread):
    """
    ULTRA-FAST & RESILIENT Media Prober.
    Aims for <1s response while providing multi-stage fallbacks to 
    prevent timeouts from blocking the project.
    """
    # Emits: file_path, duration_frames, source (None), width, height, rotation, fps
    finished = Signal(str, float, object, int, int, int, float) 
    error = Signal(str, str)

    def __init__(self, file_path, fps=30.0):
        super().__init__()
        self.file_path = file_path
        self.fps = fps
        self._stopped = False
        
    def stop(self):
        self._stopped = True

    def run(self):
        # Result placeholders
        w, h, rot, fps, dur_frames = 1920, 1080, 0, self.fps, 300
        
        try:
            ext = os.path.basename(self.file_path).lower().split('.')[-1]
            is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            
            if not is_image:
                # STAGE 1: Robust Full Probe (Returns NATIVE dimensions)
                specs = FFmpegUtils.get_media_specs(self.file_path)
                w, h, rot, fps = specs['width'], specs['height'], specs['rotation'], specs['fps']
                
                # Apply swap for STAGE 1 (ffprobe)
                if abs(rot) == 90 or abs(rot) == 270:
                    w, h = h, w
                    
                dur_sec = specs['duration']
                dur_frames = int(dur_sec * fps)
                
                # STAGE 2: Emergency Fallback using Engine (Returns VISUAL dimensions)
                if w <= 0 or h <= 0:
                    try:
                        temp_src = rocky_core.VideoSource(self.file_path)
                        # NO SWAP NEEDED HERE - Engine getters are now visual-aware
                        w = temp_src.get_width()
                        h = temp_src.get_height()
                        rot = temp_src.get_rotation()
                    except:
                        pass
            
            # Sub-second emission
            self.finished.emit(self.file_path, float(dur_frames), None, w, h, rot, float(fps))
            
        except Exception as e:
            # Absolute last resort for worker survival
            self.error.emit(self.file_path, str(e))
