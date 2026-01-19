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
        """Returns the optimal FFmpeg command for proxy generation."""
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        hw = FFmpegUtils.detect_hardware()

        # Common input args
        cmd = [ffmpeg, "-y", "-i", input_path]

        # MAC M4 STRATEGY: ProRes Proxy via VideoToolbox
        # Decoding ProRes is hardware accelerated on M4 media engine.
        # It is significantly smoother to scrub than H.264 GOPs.
        if hw == "vt":
            if "prores_videotoolbox" in FFmpegUtils._available_encoders:
                 cmd.extend([
                     "-vf", "scale=-2:540",
                     "-c:v", "prores_videotoolbox", 
                     "-profile:v", "proxy", # lightest prores
                     "-c:a", "pcm_s16le",   # Fast audio
                     "-f", "mov"            # ProRes needs mov container
                 ])
            else:
                # Fallback to H.264 VT
                cmd.extend([
                     "-vf", "scale=-2:540",
                     "-c:v", "h264_videotoolbox", 
                     "-b:v", "2M", 
                     "-c:a", "aac",
                     "-ac", "2"
                ])

        # WINDOWS NVIDIA STRATEGY
        elif hw == "nvenc":
            cmd.extend([
                 "-vf", "scale=-2:540",
                 "-c:v", "h264_nvenc",
                 "-preset", "p1", # Fastest
                 "-tc", "0",      # Optimize for latency? No, proxy needs throughput
                 "-kv", "1",      # Keyframe every frame (I-Frame only) for seeking? 
                                  # No, checking "GOP" size effectively.
                                  # Let's keep smooth scrubbing in mind.
                                  # Short GOP is better.
                 "-g", "15",      # Short GOP (0.5s at 30fps)
                 "-b:v", "2M",
                 "-c:a", "aac"
            ])

        # QUICK SYNC / AMF / CPU Fallback
        else:
             codec = "h264_qsv" if hw == "qsv" else ("h264_amf" if hw == "amf" else "libx264")
             preset = "ultrafast" if hw == "cpu" else "fast"
             
             cmd.extend([
                 "-vf", "scale=-2:540",
                 "-c:v", codec,
                 "-g", "30"
             ])
             
             if hw == "cpu":
                 cmd.extend(["-preset", "ultrafast", "-crf", "28"])
             else:
                 cmd.extend(["-b:v", "2M"])

             cmd.extend(["-c:a", "aac", "-ac", "2"])

        cmd.append(output_path)
        return cmd
