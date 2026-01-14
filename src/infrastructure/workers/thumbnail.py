from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import rocky_core
import numpy as np

class ThumbnailWorker(QThread):
    """Background worker to extract start/mid/end thumbnails for video clips."""
    finished = Signal(object, list)

    def __init__(self, clip, file_path):
        super().__init__()
        self.clip = clip
        self.file_path = file_path

    def run(self):
        try:
            # We use a dedicated source to avoid locking the main rendering engine
            src = None
            ext = self.file_path.lower().split('.')[-1]
            is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            
            if is_image:
                src = rocky_core.ImageSource(self.file_path)
            else:
                src = rocky_core.VideoSource(self.file_path)
            
            duration = src.get_duration()
            if duration < 0: duration = 0 # Static image
            
            # Times to extract: 0%, 50%, 95%
            times = [0, duration * 0.5, max(0, duration - 0.1)]
            thumbs = []
            
            for t in times:
                # 160x90 is a good thumbnail size for the timeline
                frame_data = src.get_frame(t, 160, 90)
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
                self.finished.emit(self.clip, thumbs)
        except Exception as e:
            print(f"Thumbnail Extraction Failed: {e}")
