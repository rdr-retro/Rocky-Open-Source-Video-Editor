import numpy as np
import subprocess
import os
import sys

# Mock C++ Classes
class ClipTransform:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0.0
        self.anchor_x = 0.5
        self.anchor_y = 0.5

class MockClip:
    def __init__(self, track_idx, name, start, duration, offset, file_path):
        self.track_idx = track_idx
        self.name = name
        self.start = start
        self.duration = duration
        self.offset = offset
        self.file_path = file_path # Crucial: Stored python-side
        self.transform = ClipTransform()
        self.effects = []
        self.opacity = 1.0
        
        # Audio specific placeholders
        self.fade_in_frames = 0
        self.fade_out_frames = 0
        self.fade_in_type = 0
        self.fade_out_type = 0

class ExperimentalEngine:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.fps = 30.0
        self.clips = []
        print("[ExperimentalEngine] Initialized (Python-FFmpeg Core)")

    def set_resolution(self, w, h):
        self.width = int(w)
        self.height = int(h)

    def set_fps(self, f):
        self.fps = f

    def add_track(self, type_id):
        pass

    def add_clip(self, track_idx, name, start, dur, offset, media_source):
        # rocky_ui calls: engine.add_clip(x, y, z, media_source)
        # We need the path. 
        # In the C++ bindings, media_source is a specialized C++ object (VideoSource/MediaSource).
        # We assume for this experiment that 'media_source' has a 'path' attribute
        # OR we modify rocky_ui to pass the path. 
        # CHECK: rocky_ui.py lines ~2250 show it passes 'src' which is created via 'rocky_core.VideoSource(file_path)'
        # So 'media_source' is an object.
        # We will try to read a python attribute, but if it's a pybind11 object it might not expose 'path' easily 
        # unless bound.
        # WORKAROUND: In rocky_ui, we will modify the call site to strict pass the path string if needed,
        # or we accept that maybe the binding exposes it.
        # Let's hope binding exposes it or we patch rocky_ui.
        
        # For now, let's assume we patch rocky_ui to pass 'file_path' as the LAST argument 
        # or we attach it to the media_source object in python.
        
        path = getattr(media_source, "file_path", None)
        if not path:
             # Fallback: maybe it's just the name if unique? No.
             path = name # Often the filename. 
        
        c = MockClip(track_idx, name, start, dur, offset, path)
        self.clips.append(c)
        return c

    def set_master_gain(self, gain):
        pass
        
    def clear(self):
        self.clips = []

    def evaluate(self, time):
        # Green Screen for Video
        arr = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        arr[:, :, 1] = 255 
        arr[:, :, 3] = 255
        return arr

    def render_audio(self, start_time, duration):
        """
        Renders audio using FFmpeg CLI via subprocess.
        Output: float32 numpy array.
        """
        # SAMPLE_RATE = 44100 # Match Engine Native for now
        SAMPLE_RATE = 44100
        
        total_samples = int(duration * SAMPLE_RATE)
        mixed = np.zeros(total_samples * 2, dtype=np.float32) # Stereo
        
        # Find active clips
        # Convert time to frames
        start_frame_req = start_time * self.fps
        end_frame_req = (start_time + duration) * self.fps
        
        for clip in self.clips:
            clip_end = clip.start + clip.duration
            
            # Check overlap
            if clip.start < end_frame_req and clip_end > start_frame_req:
                # Calculate intersection
                # We need data from 'start_time' to 'start_time+duration'
                
                # Logic:
                # 1. Map requested time to timeline time.
                # 2. Map timeline time to clip local time.
                # 3. Map clip local time to source file time.
                
                # Complex mix is hard in pure python without overhead, 
                # but let's try for ONE clip (simplest case).
                
                if not clip.file_path or not os.path.exists(clip.file_path):
                    continue
                    
                # Calculate relative offset
                # time_in_clip_start = start_time - (clip.start / self.fps)
                # source_seek = time_in_clip_start + clip.offset
                
                # If negative (request starts before clip), we pad?
                # Simplified:
                
                req_start_sec = start_time
                req_end_sec = start_time + duration
                
                clip_start_sec = clip.start / self.fps
                clip_end_sec = clip_end / self.fps
                
                # Overlap in seconds
                overlap_start = max(req_start_sec, clip_start_sec)
                overlap_end = min(req_end_sec, clip_end_sec)
                
                if overlap_end > overlap_start:
                    overlap_dur = overlap_end - overlap_start
                    
                    # Source seek
                    time_into_clip = overlap_start - clip_start_sec
                    # clip.offset is likely in seconds (double).
                    source_seek = time_into_clip + clip.offset
                    
                    # Buffer insert position
                    buffer_offset_sec = overlap_start - req_start_sec
                    buffer_offset_samples = int(buffer_offset_sec * SAMPLE_RATE) * 2
                    
                    # Run FFmpeg
                    # ffmpeg -ss <seek> -t <dur> -i <file> -f f32le -ar 44100 -ac 2 pipe:1
                    
                    cmd = [
                        "ffmpeg",
                        "-ss", f"{source_seek:.3f}",
                        "-t", f"{overlap_dur:.3f}",
                        "-i", clip.file_path,
                        "-f", "f32le",
                        "-ar", str(SAMPLE_RATE),
                        "-ac", "2",
                        "-vn", # No video
                        "-loglevel", "quiet",
                        "pipe:1"
                    ]
                    
                    try:
                        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        data = np.frombuffer(proc.stdout, dtype=np.float32)
                        
                        # Add to mix
                        target_len = len(data)
                        
                        # Safety bounds
                        space_left = len(mixed) - buffer_offset_samples
                        to_copy = min(space_left, target_len)
                        
                        if to_copy > 0:
                            mixed[buffer_offset_samples : buffer_offset_samples + to_copy] += data[:to_copy]
                            
                    except Exception as e:
                        print(f"ExpEngine Error: {e}")

        return mixed

    @staticmethod
    def format_timecode(frame, fps):
        # Simple HH:MM:SS:FF
        total_seconds = int(frame / fps)
        ff = int(frame % fps)
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    @staticmethod
    def resample_audio(input_data, target_len):
         # Dummy linear interpolation if needed
         return input_data # Or implement basics
