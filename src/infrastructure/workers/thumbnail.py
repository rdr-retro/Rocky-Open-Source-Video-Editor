from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import rocky_core
import numpy as np
import os

class ThumbnailWorker(QThread):
    """Background worker to extract start/mid/end thumbnails for video clips."""
    finished = Signal(object, list)

    def __init__(self, clip, file_path):
        super().__init__()
        self.clip = clip
        self.file_path = file_path
        self._stopped = False
        
    def stop(self):
        self._stopped = True

    def run(self):
        print(f"DEBUG: ThumbnailWorker starting for {self.file_path}")
        try:
            # We use a dedicated source to avoid locking the main rendering engine
            src = None
            ext = self.file_path.lower().split('.')[-1]
            is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            
            if is_image:
                src = rocky_core.ImageSource(self.file_path)
            else:
                src = rocky_core.VideoSource(self.file_path)
            
            # ORIENTATION AWARE THUMBS
            from ..ffmpeg_utils import FFmpegUtils
            specs = FFmpegUtils.get_media_specs(self.file_path)
            rot = specs['rotation']
            
            tw, th = 160, 90
            if abs(rot) == 90 or abs(rot) == 270:
                tw, th = 90, 160
            
            duration = src.get_duration()
            if duration < 0: duration = 0 # Static image
            
            # Times to extract: 0%, 50%, 95%
            times = [0, duration * 0.5, max(0, duration - 0.1)]
            thumbs = []
            
            for t in times:
                if self._stopped: break
                # Optimized extraction at correct aspect ratio
                frame_data = src.get_frame(t, tw, th)
                if frame_data is not None:
                    # Convert raw RGBA data to QImage
                    height, width, channels = frame_data.shape
                    bytes_per_line = channels * width
                    
                    # Safety: Ensure contiguous memory for QImage constructor
                    if not frame_data.flags['C_CONTIGUOUS']:
                        frame_data = np.ascontiguousarray(frame_data)
                        
                    img = QImage(frame_data.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888).copy()
                    thumbs.append(img)
            
            if thumbs:
                print(f"DEBUG: ThumbnailWorker finished for {self.file_path}. Generated {len(thumbs)} thumbs.")
                self.finished.emit(self.clip, thumbs)
            else:
                print(f"DEBUG: ThumbnailWorker failed to generate any thumbs for {self.file_path}")
        except Exception as e:
            print(f"Thumbnail Extraction Failed for {self.file_path}: {e}")
