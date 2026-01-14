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
            # 1200 points provides high-res detail for standard timeline zooms
            peaks = src.get_waveform(1200)
            if peaks:
                self.finished.emit(self.clip, list(peaks))
        except Exception as e:
            print(f"Waveform Analysis Failed for {self.file_path}: {e}")
