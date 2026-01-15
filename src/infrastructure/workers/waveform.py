from PySide6.QtCore import QThread, Signal
import rocky_core

class WaveformWorker(QThread):
    """Background worker to analyze audio peaks without blocking the EDT."""
    finished = Signal(object, list)

    def __init__(self, clip, file_path):
        super().__init__()
        self.clip = clip
        self.file_path = file_path

    def run(self):
        try:
            # Dedicated source for analysis to avoid mutex contention with playback
            src = rocky_core.VideoSource(self.file_path)
            
            # DYNAMIC RESOLUTION:
            # Request 200 points per second of audio for high-res zooming
            duration = src.get_duration()
            if duration <= 0:
                duration = 60 # Fallback
                
            points = int(duration * 200)
            # Clamping: at least 1200 for short clips, max 200k for performance
            points = max(1200, min(points, 200000))
            
            print(f"Analyzing waveform for {self.file_path} ({points} points)...")
            peaks = src.get_waveform(points)
            if peaks:
                self.finished.emit(self.clip, list(peaks))
        except Exception as e:
            print(f"Waveform Analysis Failed for {self.file_path}: {e}")
