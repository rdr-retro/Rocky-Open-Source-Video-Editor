import os
import sys
import subprocess
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class EncoderConfig:
    codec: str # "libx264", "h264_videotoolbox", "h264_nvenc", etc.
    preset_flag: Tuple[str, str] # ("-preset", "fast")
    quality_flag: Tuple[str, str] # ("-crf", "23") or ("-q:v", "60") or ("-global_quality", "25")
    pix_fmt: str # "yuv420p" usually, but sometimes "nv12" preferred for HW
    extra_flags: List[str]

class FFmpegUtils:
    _cached_ffmpeg_path: Optional[str] = None
    _available_encoders: List[str] = []
    _hardware_detected: Optional[str] = None # "vt", "nvenc", "qsv", "amf", "cpu"

    @staticmethod
    def get_ffmpeg_path() -> str:
        """Robustly finds ffmpeg binary."""
        if FFmpegUtils._cached_ffmpeg_path:
            return FFmpegUtils._cached_ffmpeg_path

        ffmpeg_exe = "ffmpeg"
        if getattr(sys, 'frozen', False):
             base_path = sys._MEIPASS
        else:
             base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

        bin_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
        possible_paths = [
            os.path.join(base_path, "external", "ffmpeg", "bin", bin_name),
            os.path.join(base_path, "external", "ffmpeg", bin_name),
            os.path.join(base_path, bin_name)
        ]

        found = False
        for p in possible_paths:
            if os.path.exists(p) and os.access(p, os.X_OK):
                ffmpeg_exe = p
                found = True
                break
        
        # If not found in bundle, assume system path (or homebrew on M4)
        if not found and sys.platform == "darwin":
             # Common homebrew paths if not in PATH for GUI apps
             if os.path.exists("/opt/homebrew/bin/ffmpeg"):
                 ffmpeg_exe = "/opt/homebrew/bin/ffmpeg"
             elif os.path.exists("/usr/local/bin/ffmpeg"):
                 ffmpeg_exe = "/usr/local/bin/ffmpeg"

        FFmpegUtils._cached_ffmpeg_path = ffmpeg_exe
        return ffmpeg_exe

    @staticmethod
    def get_ffprobe_path() -> str:
        """Robustly finds ffprobe binary."""
        ffmpeg_bin = FFmpegUtils.get_ffmpeg_path()
        if "ffmpeg" in ffmpeg_bin:
            ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
            if os.path.exists(ffprobe_bin):
                return ffprobe_bin
        return "ffprobe"

    @staticmethod
    def detect_hardware():
        """Scans for available hardware encoders."""
        if FFmpegUtils._hardware_detected:
            return FFmpegUtils._hardware_detected

        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        try:
            # Hide output on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            cmd = [ffmpeg, "-encoders"]
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                startupinfo=startupinfo
            )
            output = result.stdout + result.stderr # Check both streams just in case
            
            # DEBUG: Trace check
            print(f"DEBUG: FFmpeg -encoders output length: {len(output)}")
            if len(output) < 500:
                 print(f"DEBUG: Output content: {output}")

            encoders = []
            for line in output.splitlines():
                if "h264_videotoolbox" in line: encoders.append("h264_videotoolbox")
                if "h264_nvenc" in line: encoders.append("h264_nvenc")
                if "h264_qsv" in line: encoders.append("h264_qsv")
                if "h264_amf" in line: encoders.append("h264_amf")
            
            FFmpegUtils._available_encoders = encoders
            
            # Priority Detection
            if "h264_videotoolbox" in encoders:
                FFmpegUtils._hardware_detected = "vt" # Apple Silicon / Mac
            elif "h264_nvenc" in encoders:
                FFmpegUtils._hardware_detected = "nvenc" # NVIDIA
            elif "h264_qsv" in encoders:
                FFmpegUtils._hardware_detected = "qsv" # Intel QuickSync
            elif "h264_amf" in encoders:
                FFmpegUtils._hardware_detected = "amf" # AMD
            else:
                FFmpegUtils._hardware_detected = "cpu"

            print(f"DEBUG: Hardware Detection Result: {FFmpegUtils._hardware_detected}", flush=True)

        except Exception as e:
            print(f"ERROR: FFmpeg detection failed: {e}", flush=True)
            FFmpegUtils._hardware_detected = "cpu"

        return FFmpegUtils._hardware_detected

    @staticmethod
    def get_export_config(high_fidelity: bool) -> EncoderConfig:
        """Returns optimal encoding flags based on hardware and quality preference."""
        hw = FFmpegUtils.detect_hardware()

        # -------------------------------------------------------------
        #  APPLE MEDIA ENGINE (M4 / Apple Silicon)
        # -------------------------------------------------------------
        if hw == "vt":
            # VideoToolbox is incredibly fast on M4
            # No 'preset' in standard sense, controlled by bitrate/quality
            if high_fidelity:
                # ~Visually Lossless
                return EncoderConfig(
                    codec="h264_videotoolbox",
                    preset_flag=("-allow_sw", "1"), # Allow SW fallback if HW busy (rare)
                    quality_flag=("-q:v", "85"),    # 1-100 scale, 85 is excellent
                    pix_fmt="yuv420p",
                    extra_flags=["-profile:v", "high"]
                )
            else:
                # Standard
                return EncoderConfig(
                    codec="h264_videotoolbox",
                    preset_flag=("-allow_sw", "1"),
                    quality_flag=("-q:v", "60"),    # 60 is standard good
                    pix_fmt="yuv420p",
                    extra_flags=[]
                )

        # -------------------------------------------------------------
        #  NVIDIA NVENC (Windows)
        # -------------------------------------------------------------
        elif hw == "nvenc":
            if high_fidelity:
                return EncoderConfig(
                    codec="h264_nvenc",
                    preset_flag=("-preset", "p6"), # P6 = slower, better quality
                    quality_flag=("-cq", "19"),    # Constant Quality
                    pix_fmt="yuv420p",
                    extra_flags=["-rc", "vbr"]
                )
            else:
                return EncoderConfig(
                    codec="h264_nvenc",
                    preset_flag=("-preset", "p4"), # P4 = medium
                    quality_flag=("-cq", "26"),
                    pix_fmt="yuv420p",
                    extra_flags=["-rc", "vbr"]
                )

        # -------------------------------------------------------------
        #  INTEL QUICK SYNC (QSV)
        # -------------------------------------------------------------
        elif hw == "qsv":
             if high_fidelity:
                return EncoderConfig(
                    codec="h264_qsv",
                    preset_flag=("-preset", "slow"), 
                    quality_flag=("-global_quality", "18"), 
                    pix_fmt="nv12", # QSV often prefers nv12
                    extra_flags=["-look_ahead", "1"]
                )
             else:
                return EncoderConfig(
                    codec="h264_qsv",
                    preset_flag=("-preset", "medium"), 
                    quality_flag=("-global_quality", "25"), 
                    pix_fmt="nv12",
                    extra_flags=[]
                )

        # -------------------------------------------------------------
        #  CPU FALLBACK (x264)
        # -------------------------------------------------------------
        else:
            if high_fidelity:
                return EncoderConfig(
                    codec="libx264",
                    preset_flag=("-preset", "slow"),
                    quality_flag=("-crf", "17"),
                    pix_fmt="yuv420p",
                    extra_flags=[]
                )
            else:
                return EncoderConfig(
                    codec="libx264",
                    preset_flag=("-preset", "medium"),
                    quality_flag=("-crf", "23"),
                    pix_fmt="yuv420p",
                    extra_flags=[]
                )

    @staticmethod
    def get_proxy_command(input_path: str, output_path: str) -> List[str]:
        """
        Returns the optimal FFmpeg command for proxy generation.
        PRESERVES NATIVE ORIENTATION: Uses -noautorotate and maps metadata
        to ensure the proxy is a perfect structural clone of the raw media.
        """
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        hw = FFmpegUtils.detect_hardware()
        
        # 1. Gather input specs
        specs = FFmpegUtils.get_media_specs(input_path)
        rot = specs.get('rotation', 0)
        
        # 2. Base Command (Disable auto-rotation to keep original tag context)
        cmd = [ffmpeg, "-y", "-noautorotate", "-i", input_path]

        # 3. Scaling Strategy (Scale native dimensions to fit ~540 height)
        # We always scale native height to 540 and width proportionally.
        # Since tags are preserved, the engine will handle the visual swap correctly.
        scale_filter = "scale=-2:540,setsar=1"

        # 4. Hardware Encoding Segments
        if hw == "vt":
            # MAC Apple Silicon
            if "prores_videotoolbox" in FFmpegUtils._available_encoders:
                 cmd.extend([
                     "-vf", scale_filter,
                     "-c:v", "prores_videotoolbox", 
                     "-profile:v", "proxy",
                     "-c:a", "pcm_s16le",
                     "-f", "mov"
                 ])
            else:
                cmd.extend([
                     "-vf", scale_filter,
                     "-c:v", "h264_videotoolbox", 
                     "-b:v", "2M", 
                     "-c:a", "aac", "-ac", "2"
                ])
        elif hw == "nvenc":
            # NVIDIA
            cmd.extend([
                 "-vf", scale_filter,
                 "-c:v", "h264_nvenc",
                 "-preset", "p1", 
                 "-g", "15",
                 "-b:v", "2M",
                 "-c:a", "aac"
            ])
        else:
            # CPU / Other
            codec = "h264_qsv" if hw == "qsv" else ("h264_amf" if hw == "amf" else "libx264")
            cmd.extend([
                "-vf", scale_filter,
                "-c:v", codec,
                "-g", "30"
            ])
            if hw == "cpu":
                cmd.extend(["-preset", "ultrafast", "-crf", "28"])
            else:
                cmd.extend(["-b:v", "2000k"])
            cmd.extend(["-c:a", "aac", "-ac", "2"])

        # 5. CRITICAL: METADATA PERSISTENCE
        # Map all metadata and explicitly re-apply rotation tag in case it was lost
        cmd.extend(["-map_metadata", "0", f"-metadata:s:v:0", f"rotate={rot}"])
        
        cmd.append(output_path)
        return cmd
    @staticmethod
    def get_media_specs(file_path: str) -> dict:
        """
        ULTRA-ROBUST Prober for all media types.
        Returns common specs using FFprobe with Apple-specific tag support.
        If FFprobe fails, returns width=0 to signal Engine Fallback.
        """
        specs = {'width': 0, 'height': 0, 'fps': 30.0, 'rotation': 0, 'duration': 10.0}
        
        try:
            ffp = FFmpegUtils.get_ffprobe_path()
            cmd = [
                ffp, '-v', 'error', '-select_streams', 'v:0',
                '-analyzeduration', '20M', '-probesize', '20M',
                '-show_entries', 'stream=width,height,r_frame_rate,duration:format=duration:side_data=rotation',
                '-of', 'json', file_path
            ]
            
            # Robust 4.0s timeout is enough for local SSDs; 10.0s was causing "hang" feel
            output = subprocess.check_output(cmd, timeout=4.0).decode('utf-8')
            data = json.loads(output)
            
            if 'streams' in data and data['streams']:
                s = data['streams'][0]
                specs['width'] = s.get('width', 0)
                specs['height'] = s.get('height', 0)
                
                # FPS Robust parsing
                rfps = s.get('r_frame_rate', '30/1')
                try:
                    if '/' in rfps:
                        num, den = map(int, rfps.split('/'))
                        specs['fps'] = num / den if den > 0 else 30.0
                    else:
                        specs['fps'] = float(rfps or 30.0)
                except: specs['fps'] = 30.0
                
                # Rotation search
                rot = 0
                for sd in s.get('side_data', []):
                    if 'rotation' in sd: rot = int(sd['rotation']); break
                if rot == 0:
                    rot = int(s.get('tags', {}).get('rotate', 0))
                if rot == 0:
                    rot = int(data.get('format', {}).get('tags', {}).get('rotate', 0))
                
                specs['rotation'] = rot
                specs['duration'] = float(s.get('duration', data.get('format', {}).get('duration', 10.0)))
                
        except Exception as e:
            print(f"INFO: FFprobe stage skipped for {os.path.basename(file_path)}: {e}")
            
        return specs
