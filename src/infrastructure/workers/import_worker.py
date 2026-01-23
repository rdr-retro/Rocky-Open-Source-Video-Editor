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

    def run(self):
        # Result placeholders
        w, h, rot, fps, dur_frames = 1920, 1080, 0, self.fps, 300
        
        try:
            ext = os.path.basename(self.file_path).lower().split('.')[-1]
            is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            
            if not is_image:
                # STAGE 1: Fast Full Probe
                try:
                    ffp = FFmpegUtils.get_ffprobe_path()
                    cmd = [
                        ffp, '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height,r_frame_rate,duration:format=duration:side_data=rotation',
                        '-of', 'json', self.file_path
                    ]
                    # We give it 1.5s for the "Extreme" goal, but catch if it fails
                    output = subprocess.check_output(cmd, timeout=1.5).decode('utf-8')
                    data = json.loads(output)
                    
                    if 'streams' in data and data['streams']:
                        s = data['streams'][0]
                        w = s.get('width', w)
                        h = s.get('height', h)
                        rfps = s.get('r_frame_rate', '30/1')
                        if '/' in rfps:
                            num, den = map(int, rfps.split('/'))
                            fps = num / den if den > 0 else 30.0
                        else: fps = float(rfps)
                        
                        for sd in s.get('side_data', []):
                            if 'rotation' in sd: rot = int(sd['rotation']); break
                            
                        dur_sec = float(s.get('duration', data.get('format', {}).get('duration', 10.0)))
                        dur_frames = int(dur_sec * fps)
                
                except (subprocess.TimeoutExpired, Exception) as e:
                    print(f"DEBUG: Stage 1 Probe delayed or failed: {e}")
                    # STAGE 2: Emergency Fallback using Engine (No subprocess spawn)
                    # VideoSource is heavy but in a thread it's acceptable as fallback
                    try:
                        temp_src = rocky_core.VideoSource(self.file_path)
                        dur_sec = temp_src.get_duration()
                        dur_frames = int(dur_sec * fps) if dur_sec > 0 else 300
                        # Rotation/Dimensions will fallback to defaults if probe fails
                    except:
                        pass # Keep defaults
            
            # Sub-second emission
            self.finished.emit(self.file_path, float(dur_frames), None, w, h, rot, float(fps))
            
        except Exception as e:
            # Absolute last resort for worker survival
            self.error.emit(self.file_path, str(e))
