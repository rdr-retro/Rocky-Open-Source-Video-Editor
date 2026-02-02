import time
import numpy as np

class MultimediaDebugger:
    """
    Expert-level diagnostic tool for low-latency multimedia systems.
    Listens to the audio/video engine and detects anomalies like time-jumps,
    buffer starvation, and sync drift.
    """
    def __init__(self):
        self.last_audio_sample_requested = -1
        self.total_anomalies = 0
        self.logs = []
        self.start_time = time.time()
        print("[DIAGNOSTIC] Probe Initialized. Monitoring engine health...")

    def log_audio_request(self, start_sample, count, rate):
        """Monitors continuity of audio requests."""
        if self.last_audio_sample_requested != -1:
            diff = start_sample - self.last_audio_sample_requested
            
            # ANOMALY: Overlap (Rewind effect)
            if diff < 0:
                self._report("REWIND_DETECTED", f"Requested {count} samples starting at {start_sample}, but last request ended at {self.last_audio_sample_requested}. Gap: {diff}")
            
            # ANOMALY: Gap (Stutter effect)
            elif diff > 0 and diff > 10: # Allow small rounding errors
                 self._report("GAP_DETECTED", f"Audio discontinuity. Missing {diff} samples between requests.")

        self.last_audio_sample_requested = start_sample + count

    def log_buffer_state(self, available_read, available_write, capacity):
        """Monitors ring buffer health."""
        fullness = (available_read / capacity) * 100
        if available_read == 0:
            self._report("STARVATION", "Ring buffer is EMPTY. Audio thread will play silence.")
        elif available_write < 100:
             self._report("BUFFER_FULL", f"Ring buffer nearly FULL ({fullness:.1f}%). Samples might be dropped.")

    def _report(self, type, message):
        self.total_anomalies += 1
        timestamp = time.time() - self.start_time
        entry = f"[{timestamp:.3f}s] [{type}] {message}"
        self.logs.append(entry)
        print(entry)
        
        # Keep logs manageable
        if len(self.logs) > 1000:
            self.logs.pop(0)

    def get_summary(self):
        return {
            "total_anomalies": self.total_anomalies,
            "recent_logs": self.logs[-10:]
        }

# Singleton instance for easy access across workers
PROBE = MultimediaDebugger()
