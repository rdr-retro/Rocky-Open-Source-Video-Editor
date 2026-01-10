import os
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

class ProxyWorker(QThread):
    """
    Background worker to generate a low-quality .mp4 proxy.
    Creates a .proxy/ folder next to the source file.
    """
    finished = pyqtSignal(object, str, bool) # clip, proxy_path, success
    
    def __init__(self, clip, source_path):
        super().__init__()
        self.clip = clip
        self.source_path = source_path
        
    def run(self):
        try:
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

            # Generate Proxy using FFmpeg
            # Scale to 540p height, ultrafast preset for speed, crf 28 for low size/quality
            command = [
                'ffmpeg', '-y',
                '-i', self.source_path,
                '-vf', 'scale=-2:540',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '28',
                '-c:a', 'aac',
                '-ac', '2',
                proxy_path
            ]
            
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            _, stderr = process.communicate()
            
            if process.returncode == 0 and os.path.exists(proxy_path):
                self.finished.emit(self.clip, proxy_path, True)
            else:
                print(f"Proxy Generation Failed: {stderr.decode()}")
                self.finished.emit(self.clip, "", False)
                
        except Exception as e:
            print(f"Proxy Worker Exception: {e}")
            self.finished.emit(self.clip, "", False)
