import os
import subprocess
from PySide6.QtCore import QThread, Signal

class ProxyWorker(QThread):
    """
    Background worker to generate a low-quality .mp4 proxy.
    Creates a .proxy/ folder next to the source file.
    """
    finished = Signal(object, str, bool) # clip, proxy_path, success
    
    def __init__(self, clip, source_path):
        super().__init__()
        self.clip = clip
        self.source_path = source_path
        self._process = None
        self._stopped = False
        
    def stop(self):
        """Safe cancellation from the main thread."""
        self._stopped = True
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1.0)
            except: pass
            self._process = None

    def run(self):
        try:
            if self._stopped: return
            source_dir = os.path.dirname(self.source_path)
            file_name = os.path.basename(self.source_path)
            proxy_dir = os.path.join(source_dir, ".proxy")
            
            if not os.path.exists(proxy_dir):
                os.makedirs(proxy_dir, exist_ok=True)
                
            # Proxy filename: original.mp4 -> original_proxy.mp4
            name_part, ext = os.path.splitext(file_name)
            proxy_filename = f"{name_part}_proxy.mp4"
            proxy_path = os.path.join(proxy_dir, proxy_filename)
            
            # If proxy already exists, we skip generation but verify it works
            if os.path.exists(proxy_path) and os.path.getsize(proxy_path) > 1000:
                 self.finished.emit(self.clip, proxy_path, True)
                 return
            
            if self._stopped: return

            # Generate Proxy using FFmpeg
            from ..ffmpeg_utils import FFmpegUtils
            command = FFmpegUtils.get_proxy_command(self.source_path, proxy_path)
            
            self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            _, stderr = self._process.communicate()
            
            if self._stopped: return

            if self._process and self._process.returncode == 0 and os.path.exists(proxy_path):
                self.finished.emit(self.clip, proxy_path, True)
            else:
                if not self._stopped:
                    print(f"Proxy Generation Failed: {stderr.decode() if stderr else 'Abort'}")
                self.finished.emit(self.clip, "", False)
                
        except Exception as e:
            if not self._stopped:
                print(f"Proxy Worker Exception: {e}")
            self.finished.emit(self.clip, "", False)
        finally:
            self._process = None
