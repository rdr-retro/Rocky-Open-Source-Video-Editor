import sys
import os
import random
import time

# Ensure we can load DLLs for version 3.8+ on Windows AND find FFmpeg in PATH
if os.name == 'nt':
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller mode: Root is _MEIPASS
            project_root = sys._MEIPASS
        else:
            # Dev mode: Root is two levels up from this file relative to src/ui/rocky_ui.py
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        ffmpeg_bin = os.path.join(project_root, "external", "ffmpeg", "bin")
        
        if os.path.isdir(ffmpeg_bin):
            # 1. Allow Python to load DLLs (for rocky_core extension)
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(ffmpeg_bin)
                print(f"Added DLL directory: {ffmpeg_bin}", flush=True)
            
            # 2. Allow subprocess calls (like ffmpeg -version) to find the binary
            os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]
            print(f"Added FFmpeg to PATH: {ffmpeg_bin}", flush=True)
            
    except Exception as e:
        print(f"Failed to setup FFmpeg paths: {e}", flush=True)

import rocky_core

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                             QApplication, QScrollArea, QFrame, QMainWindow, QLabel, QFileDialog, QProgressDialog, QMessageBox)
from PySide6.QtGui import QImage, QPixmap, QIcon, QPainter, QPainterPath, QPen, QColor
import subprocess
import json
from PySide6.QtCore import Qt, QTimer, QIODevice, QByteArray, QMutex, QMutexLocker, QRectF, QThread, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput, QAudioSource, QAudioSink
import numpy as np

from .timeline.simple_timeline import SimpleTimeline
from .models import TimelineModel, TrackType
from .sidebar import SidebarPanel
from .ruler import TimelineRuler
from .master_meter import MasterMeterPanel
from .viewer import ViewerPanel
from .toolbar import RockyToolbar
from .settings_dialog import SettingsDialog
from .styles import MODERN_LABEL
from .asset_tabs import AssetTabsPanel
from .editor_panel import EditorPanel 
from . import design_tokens as dt
from .panels import RockyPanel # New Panel System
 
from ..infrastructure.workers.import_worker import MediaImportWorker 
from ..infrastructure.workers.waveform import WaveformWorker
from ..infrastructure.workers.thumbnail import ThumbnailWorker 
from ..infrastructure.workers.proxy_gen import ProxyWorker 

# ... (previous imports)





class AudioPlayer(QIODevice):
    level_updated = Signal(float, float)

    def __init__(self, sample_rate=44100, channels=2):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer = bytearray()
        self.mutex = QMutex()
        
        format = QAudioFormat()
        format.setSampleRate(sample_rate)
        format.setChannelCount(channels)
        format.setSampleFormat(QAudioFormat.SampleFormat.Float)
        
        self.audio_output = QAudioOutput()
        self.sink = QAudioSink(format)
        # 100ms buffer approx
        self.sink.setBufferSize(int(sample_rate * channels * 4 * 0.1))
        
        self.open(QIODevice.ReadOnly)
        self.sink.start(self)


    def write_samples(self, samples_np):
        if samples_np is not None:
            locker = QMutexLocker(self.mutex)
            self.buffer.extend(samples_np.tobytes())

    def clear_buffer(self):
        locker = QMutexLocker(self.mutex)
        self.buffer.clear()
        
    def get_buffer_duration_ms(self):
        # 4 bytes per sample (float32) * 2 channels = 8 bytes per stereo sample
        locker = QMutexLocker(self.mutex)
        count = len(self.buffer) // 8
        return (count / self.sample_rate) * 1000.0

    def readData(self, maxlen):
        locker = QMutexLocker(self.mutex)
        if not self.buffer:
            # Si no hay datos, devolvemos silencio (bytes nulos) para evitar el error de PyQt
            return b"\x00" * maxlen
        
        actual = min(len(self.buffer), maxlen)
        chunk_bytes = bytes(self.buffer[:actual])
        del self.buffer[:actual] # Much faster than slicing for bytearray


        # Live Level Detection for Meters
        try:
            samples = np.frombuffer(chunk_bytes, dtype=np.float32)
            if samples.size >= 2:
                # Interleaved stereo peaks
                l_peak = np.max(np.abs(samples[0::2]))
                r_peak = np.max(np.abs(samples[1::2]))
                self.level_updated.emit(float(l_peak), float(r_peak))
        except Exception as e:
            # Prevent console spam if it fails repeatedly, but log it at least once or distinctively
            print(f"Audio Level Analysis Error: {e}", flush=True)

        return chunk_bytes

    def bytesAvailable(self):
        locker = QMutexLocker(self.mutex)
        return len(self.buffer) + super().bytesAvailable()

    def get_processed_us(self):
        """Returns the hardware audio clock time in microseconds."""
        return self.sink.processedUSecs()

class AudioWorker(QThread):
    def __init__(self, engine, player, model):
        super().__init__()
        self.engine = engine
        self.player = player
        self.model = model
        self.running = False
        self.last_audio_render_time = -1.0
        self.fps = 30.0

    def _resample_stereo(self, data, target_len):
        if data is None or data.size == 0 or target_len <= 0:
            return data
            
        import rocky_core
        # Direct C++ call: No-copy where possible and multithreaded-safe
        return rocky_core.RockyEngine.resample_audio(data, target_len)

    def run(self):
        self.running = True
        while self.running and not self.isInterruptionRequested():
            if not self.model.blueline.playing:
                self.msleep(50)
                continue

            current_buffer_ms = self.player.get_buffer_duration_ms()
            
            # Use shared playback rate
            rate = getattr(self.model.blueline, 'playback_rate', 1.0)
            
            # Reducimos drásticamente el buffer para reaccionar rápido (Objetivo: 300ms)
            if current_buffer_ms < 150:
                missing_ms = 300 - current_buffer_ms
                missing_duration = missing_ms / 1000.0 # Physical time to fill
                
                try:
                    if not hasattr(self.model, 'audio_samples_rendered'):
                        self.model.audio_samples_rendered = 0
                        
                    render_start_time = self.model.audio_samples_rendered / 44100.0
                    
                    # SCALE timeline duration by rate
                    # If we need 0.5s of real audio but playing at 2x, we need 1.0s of content
                    content_duration = missing_duration * rate
                    
                    if content_duration > 0:
                        # CRITICAL FIX: We do NOT use the Python locker here.
                        # The C++ RockyEngine HAS its own internal std::mutex for render_audio.
                        # Using the Python engine_lock here causes deadlocks with the GIL 
                        # because render_audio releases the GIL internally.
                        audio_content = self.engine.render_audio(render_start_time, content_duration)
                        
                        if audio_content is not None and audio_content.size > 0:
                            # Resample timeline content to fit physical time
                            target_sample_count = int(missing_duration * 44100)
                            
                            if rate != 1.0:
                                audio_final = self._resample_stereo(audio_content, target_sample_count)
                            else:
                                audio_final = audio_content
                            
                            self.player.write_samples(audio_final)
                            # Update tracking based on TIMELINE time consumed
                            self.model.audio_samples_rendered += int(content_duration * 44100)
                    else:
                        # If rate is 0, we just wait
                        pass
                        
                except Exception as e:
                    print(f"AudioWorker Error: {e}")
            
            self.msleep(20)
        

    def start_playback(self, start_time, fps, rate=1.0):
        self.fps = fps
        self.player.clear_buffer()
        # Convertimos el tiempo inicial a muestras exactas
        self.model.audio_samples_rendered = int(start_time * 44100)
        
        # Pre-buffer inicial muy potente (1.2s) para garantizar arranque suave
        initial = self.engine.render_audio(start_time, 1.2)
        self.player.write_samples(initial)

        self.model.audio_samples_rendered += (initial.size // 2)
        
        self.player.sink.resume()

    def stop_playback(self):
        self.player.sink.suspend()

class RenderWorker(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, engine, engine_lock, output_path, total_frames, fps, width, height, high_quality=False):
        super().__init__()
        self.engine = engine
        self.engine_lock = engine_lock
        self.output_path = output_path
        self.total_frames = total_frames
        self.fps = fps
        self.width = width
        self.height = height
        self.high_quality = high_quality

    def run(self):
        # 0. Robust FFmpeg Detection
        from ..infrastructure.ffmpeg_utils import FFmpegUtils
        ffmpeg_exe = FFmpegUtils.get_ffmpeg_path()

        audio_temp_path = self.output_path + ".audio.tmp"
        
        try:
            # 1. Ensure dimensions are aligned to 32 (Ultra-Safe HW Alignment)
            # Some media engines (AMD/Intel) prefer 32 or 64 alignment for strides.
            # 32 is a safe bet for 99% of hardware.
            self.width = (self.width // 32) * 32
            self.height = (self.height // 32) * 32
            
            # Prevent 0 dimensions
            if self.width <= 0: self.width = 1280
            if self.height <= 0: self.height = 720

            # Sync engine resolution for RENDER
            locker = QMutexLocker(self.engine_lock)
            self.engine.set_resolution(self.width, self.height)
            if locker: del locker
            
            # 2. Render Audio (Rápido)
            duration = self.total_frames / self.fps
            audio_samples = self.engine.render_audio(0, duration)
            with open(audio_temp_path, 'wb') as f:
                f.write(audio_samples.tobytes())
                
            # 3. Configurar FFmpeg
            # Hardware Acceleration Logic
            enc_config = FFmpegUtils.get_export_config(self.high_quality)
            
            # Explicitly force pixel format conversion via filter to prevent HW encoder 
            # from receiving raw RGBA if it expects NV12/YUV.
            # We map input (rgba) -> Filter (format=pix_fmt) -> Encoder
            
            command = [
                ffmpeg_exe, '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.width}x{self.height}',
                '-pix_fmt', 'rgba', # Input from Engine is ALWAYS RGBA
                '-r', str(self.fps),
                '-i', '-', # Stdin 0
                '-f', 'f32le',
                '-ar', '44100',
                '-ac', '2',
                '-i', audio_temp_path, # Input 1
                '-vf', f'format={enc_config.pix_fmt}', # Force SW conversion before encoder
                '-c:v', enc_config.codec
            ]
            
            # Add Preset/Quality flags
            command.extend(enc_config.preset_flag)
            command.extend(enc_config.quality_flag)
            
            # Add Extra flags
            command.extend(enc_config.extra_flags)
            
            # Common flags
            command.extend([
                '-pix_fmt', enc_config.pix_fmt,
                '-c:a', 'aac',
                '-b:a', '192k',
                self.output_path
            ])
            
            # Windows-specific: Hide console window
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE

            # IMPORTANT: We avoid stderr=subprocess.PIPE to prevent deadlocks on Windows
            # when the pipe buffer fills up. Instead, we'll redirect to a log file if needed,
            # or just let it go to the parent console. For now, we'll use a temporary file
            # to capture errors without blocking.
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as err_log:
                err_log_path = err_log.name

            with open(err_log_path, 'wb') as err_f:
                process = subprocess.Popen(
                    command, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.DEVNULL, # We don't need stdout 
                    stderr=err_f,
                    startupinfo=startupinfo
                )
            
                # 4. Renderizar Video Frame a Frame
                for i in range(self.total_frames):
                    if self.isInterruptionRequested():
                        process.terminate()
                        break
                        
                    timestamp = i / self.fps
                    frame_data = self.engine.evaluate(timestamp)
                    
                    try:
                        raw_bytes = frame_data.tobytes()
                        # DEBUG: Verify exact byte alignment
                        if i == 0:
                            expected_bytes = self.width * self.height * 4
                            actual_bytes = len(raw_bytes)
                            if expected_bytes != actual_bytes:
                                print("CRITICAL ERROR: Buffer Size Mismatch! This causes render artifacts/glitches.", flush=True)

                        process.stdin.write(raw_bytes)
                        
                        # CRITICAL: Flush immediately after the first frame to ensure 
                        # FFmpeg locks onto the stream start without buffer shift.
                        if i == 0:
                            process.stdin.flush()
                            
                        # Periodic flush to avoid large memory buildup 
                        if i % 30 == 0:
                            process.stdin.flush()
                    except BrokenPipeError:
                        break
                        
                    if i % 5 == 0:
                        self.progress.emit(int((i / self.total_frames) * 100))
                        
                process.stdin.close()
                process.wait()
            
            # Check for errors
            if process.returncode != 0:
                with open(err_log_path, 'r', errors='replace') as f:
                    err_out = f.read()
                self.error.emit(f"Fallo en FFmpeg (Code {process.returncode}):\n{err_out}")
            else:
                self.finished.emit(self.output_path)

            # Cleanup
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
            if os.path.exists(err_log_path):
                os.remove(err_log_path)

                
        except Exception as e:
            print(f"RenderWorker Exception: {e}")
            self.error.emit(str(e))
        finally:
            # Note: We don't restore resolution here because the UI might have changed.
            # The next time the user interacts with the UI or changes resolution, 
            # it will be resynced. Or we could pass the original resolution to the worker.
            pass

class RockyApp(QMainWindow):
    """
    Main application window for the Rocky Video Editor.
    Integrates the Python-based UI with the C++ high-performance rendering engine.
    """

    @staticmethod
    def get_resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        else:
            # Dev mode: src/ui/rocky_ui.py -> ../.. -> root
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        return os.path.join(base_path, relative_path)

    def _get_rounded_icon(self, path):
        """On macOS, applies a squircle-style rounding to the icon for better integration."""
        if not os.path.exists(path):
            return QIcon()
            
        original = QPixmap(path)
        if sys.platform != "darwin":
            return QIcon(original)
            
        # Create a rounded version for macOS with internal padding (Visual Weight fix)
        size = original.size()
        rounded = QPixmap(size)
        rounded.fill(Qt.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # macOS standard icons occupy ~82% of the canvas for correct visual weight
        padding = size.width() * 0.09 # 9% padding on each side
        content_size = size.width() - (padding * 2)
        radius = content_size * 0.175
        
        path_qt = QPainterPath() # Renamed to avoid shadowing path arg
        rect = QRectF(padding, padding, content_size, content_size)
        path_qt.addRoundedRect(rect, radius, radius)
        
        painter.setClipPath(path_qt)
        # Draw the original scaled to fit the content area
        painter.drawPixmap(rect.toRect(), original)
        
        # Glass Border (Enhanced)
        painter.setClipping(False)
        glass_pen = QPen(QColor(255, 255, 255, 180)) # More opaque white (180/255)
        glass_pen.setWidth(3) # Slightly thicker
        painter.setPen(glass_pen)
        painter.drawPath(path_qt)
        
        painter.end()
        
        return QIcon(rounded)

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.clip_map = {} # Maps Python TimelineClip -> C++ Clip object
        self.engine_lock = QMutex() # Protection for concurrent C++/Python access
        self.playback_rate = 1.0
        self.model.blueline.playback_rate = 1.0
        self.setWindowTitle("Rocky Video Editor")
        self.project_path = None
        self.media_source_cache = {} # Cache to avoid re-opening heavy 4K files
        self.fx_dialogs = {} # Track open FX windows {clip_id: dialog}
        self._active_workers = [] # Unified tracking for all background threads
        self.viewer_registry = [] # Track all active viewer panels for frame broadcasting
        self.timeline_registry = [] # Track all active timeline widgets for playhead sync
        self.master_meter_registry = [] # Track all active master meter panels for gain sync
        
        # PROJECT DIMENSIONS (Persistent State)
        self.p_width = 1920
        self.p_height = 1080

        if not self.initialize_engine():
            # Fatal error handled inside initialize_engine
            return

        self.check_ffmpeg_availability()

        self.initialize_ui_components()
        self.setup_event_connections()
        
        # Set Window Icon
        # Use proper resource path resolution for Frozen/Dev modes
        icon_path = self.get_resource_path(os.path.join("src", "img", "icon.png"))
        
        if os.path.exists(icon_path):
            self.setWindowIcon(self._get_rounded_icon(icon_path))
        else:
            print(f"WARNING: Icon not found at {icon_path}. Trying logo.png...", flush=True)
            # Fallback to logo.png if icon.png is missing for some reason
            logo_path = self.get_resource_path(os.path.join("src", "img", "logo.png"))
            if os.path.exists(logo_path):
                self.setWindowIcon(self._get_rounded_icon(logo_path))
        
        # Start the heavy engine thread only after UI is ready (moved to showEvent)
        # self.audio_worker.start() <--- MOVED
        
    def showEvent(self, event):
        """Called when the window is shown. Safe place to start threads."""
        super().showEvent(event)
        if hasattr(self, 'audio_worker') and not self.audio_worker.isRunning():
            self.audio_worker.start(QThread.HighPriority)

    def closeEvent(self, event):
        """Called when the window is closed. Ensure all threads are stopped."""
        self.cleanup_resources()
        event.accept()
        super().closeEvent(event)


    def initialize_engine(self):
        """Initializes the C++ rendering engine. Returns True on success."""
        try:
            self.engine = rocky_core.RockyEngine()
            # Default Template: 1920x1080 (Matches user request standard)
            self.engine.set_resolution(1920, 1080) 
            self.audio_player = AudioPlayer()
            self.audio_worker = AudioWorker(self.engine, self.audio_player, self.model)
            self.audio_player.app_engine_lock = self.engine_lock # Share the lock
            return True

        except Exception as e:
            err_msg = f"Critical Error: Could not initialize RockyEngine/Audio: {e}"
            print(err_msg, flush=True)
            QMessageBox.critical(None, "Startup Failure", f"Failed to initialize Rocky Engine.\n\nThe application will now close.\n\nError: {e}")
            sys.exit(1)
            return False

    def check_ffmpeg_availability(self):
        """Checks if FFmpeg is available in the system PATH."""
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            print("WARNING: FFmpeg not found!", flush=True)
            QMessageBox.warning(None, "Missing Dependency", 
                "FFmpeg was not found in your system PATH.\n\n"
                "You can edit videos, but 'Export' and 'Proxy Generation' features will be disabled or fail.\n"
                "Please install FFmpeg to use these features.")


    def cleanup_resources(self):
        """Forceful but safe cleanup of threads before app exit."""
        
        # 1. Stop Audio Worker (CRITICAL)
        if hasattr(self, 'audio_worker') and self.audio_worker is not None:
            self.audio_worker.running = False
            self.audio_worker.requestInterruption()
            if not self.audio_worker.wait(2000):
                self.audio_worker.terminate()
        
        if hasattr(self, 'audio_player') and self.audio_player is not None:
            try: self.audio_player.sink.stop()
            except: pass
        
        # 2. Stop ALL active background workers (Waveform, Thumbnails, Proxies, Import)
        if hasattr(self, "_active_workers"):
            for worker in self._active_workers[:]: # Use slice to avoid modification issues
                try:
                    # Prefer safe STOP method implemented in recent workers
                    if hasattr(worker, 'stop'):
                        worker.stop()
                    else:
                        worker.requestInterruption()
                    
                    if not worker.wait(3000): # Give 3s to join safely
                        print(f"WARNING: Worker {worker} timed out, forcing termination...", flush=True)
                        worker.terminate()
                        worker.wait(500)
                except Exception as e:
                    print(f"ERROR: Failed to cleanup worker {worker}: {e}")
            self._active_workers.clear()
            
        # 3. Stop Render Worker if active
        if hasattr(self, 'render_worker') and self.render_worker is not None:
            if self.render_worker.isRunning():
                self.render_worker.requestInterruption()
                self.render_worker.wait(1000)
                if self.render_worker.isRunning():
                    self.render_worker.terminate()
            

    def initialize_ui_components(self):
        """Standardizes the interface construction following Blender Aesthetics."""
        self.setWindowTitle("Rocky Video Editor Pro")
        self.resize(1200, 850)
        # Background of the window = Gap color (Dark Grey/Black)
        self.setStyleSheet("background-color: #1a1a1a; color: #ffffff;") 
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Toolbar
        self.toolbar = RockyToolbar(self)
        main_layout.addWidget(self.toolbar)
        
        # Setup Workspace callbacks
        self.toolbar.workspace_bar.on_save_requested = self.save_current_layout_to_workspace
        self.toolbar.workspace_bar.on_load_requested = self.load_layout_from_workspace
        
        # 2. Middle Section
        self.middle_section = self._create_middle_section()
        main_layout.addWidget(self.middle_section, stretch=1)
        
        # 3. Status Bar
        self.status_bar = self._create_status_bar()
        main_layout.addWidget(self.status_bar)

        # 4. Workspaces Initialization
        QTimer.singleShot(0, self._init_default_workspace)

        # Initial data sync
        if self.sidebar:
            self.sidebar.refresh_tracks()
            
        self.on_time_changed(0, 0, "00:00:00;00", True) # Force initial timecode display
        self.rebuild_engine()
        
        # Absolute guarantee: Force a refresh after layout settles
        QTimer.singleShot(200, self.force_initial_render)

    def force_initial_render(self):
        """Ensures every technical number is painted on start."""
        if self.sidebar:
            for w in self.sidebar.track_widgets:
                w.update()
        if self.timeline_widget:
            self.timeline_widget.update()
        if self.timeline_ruler:
            self.timeline_ruler.update()
            
        self.on_time_changed(0, 0, "00:00:00;00", True)




    # _wrap_rounded_panel removed (replaced by RockyPanel)

    def _create_middle_section(self):
        """Creates a single flexible panel that can be any type."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        
        # Create single flexible panel - starts as Viewer
        from .viewer import ViewerPanel
        initial_content = ViewerPanel()
        self.main_panel = RockyPanel(initial_content, title="VISOR DE VIDEO")
        
        # Register initial viewer
        self.register_viewer(initial_content)
        
        layout.addWidget(self.main_panel)
        return container


    def _create_status_bar(self):
        status_frame = QFrame()
        status_frame.setFixedHeight(25)
        status_frame.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333333;")
        layout = QHBoxLayout(status_frame)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # Status label (left)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #00a3ff; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Spacer
        layout.addStretch()
        
        # Platform info label (right)
        self.platform_label = QLabel()
        self.platform_label.setStyleSheet("color: #888888; font-family: 'Inter'; font-size: 10px;")
        self._update_platform_label()
        layout.addWidget(self.platform_label)
        
        return status_frame
    
    def _update_platform_label(self):
        """Update platform information in status bar"""
        try:
            config = rocky_core.RuntimeConfig.get_instance()
            config.initialize()
            
            platform = config.get_platform_info()
            profile = config.get_optimization_profile()
            
            # Backend name mapping
            backend_names = {
                rocky_core.RenderBackend.Software: "CPU",
                rocky_core.RenderBackend.Metal: "Metal",
                rocky_core.RenderBackend.DirectX11: "DX11",
                rocky_core.RenderBackend.DirectX12: "DX12",
                rocky_core.RenderBackend.Vulkan: "Vulkan",
                rocky_core.RenderBackend.CUDA: "CUDA",
                rocky_core.RenderBackend.OpenCL: "OpenCL"
            }
            
            backend = backend_names.get(profile.preferred_backend, "Unknown")
            
            # Format: "macOS 15.1 | 10 cores | 16 GB | Apple Apple M4 | Metal"
            gpu_display = platform.gpu_info.vendor
            if platform.gpu_info.model and platform.gpu_info.model != "Integrated GPU":
                if platform.gpu_info.model not in gpu_display:
                    gpu_display = f"{gpu_display} {platform.gpu_info.model}"
                else:
                    gpu_display = platform.gpu_info.model
            
            info_text = (f"{platform.os_name} {platform.os_version} | "
                        f"{platform.cpu_cores} cores | "
                        f"{platform.total_ram_mb // 1024} GB | "
                        f"{gpu_display} | "
                        f"{backend}")
            
            self.platform_label.setText(info_text)
            
        except Exception as e:
            self.platform_label.setText(f"Platform: Unknown ({str(e)})")

    def setup_event_connections(self):
        """Standardizes global event connections."""
        # 1. Global Toolbar Actions
        self.toolbar.action_open.triggered.connect(self.on_open)
        self.toolbar.action_save.triggered.connect(self.on_save)
        self.toolbar.action_save_as.triggered.connect(self.on_save_as)
        self.toolbar.action_render.triggered.connect(self.on_render)
        self.toolbar.action_preferences.triggered.connect(self.on_settings)
        self.toolbar.btn_proxy.clicked.connect(self.on_proxy_toggle)
        
        # Rotation Actions
        self.toolbar.action_rot_cw.triggered.connect(lambda: self.rotate_selection(90))
        self.toolbar.action_rot_ccw.triggered.connect(lambda: self.rotate_selection(-90))
        self.toolbar.action_rot_180.triggered.connect(lambda: self.rotate_selection(180))
        
        # 2. Playback Engine Timer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.on_playback_tick)
        self.playback_timer.start(16) 
        
        # 3. Audio & Master Synchronization
        self.audio_player.level_updated.connect(self.on_audio_levels_received)

    def on_audio_levels_received(self, left, right):
        """Dispatches audio levels to ALL active vumeters."""
        for m in self.master_meter_registry:
            if hasattr(m, 'meter'):
                m.meter.set_levels(left, right)

    def on_clip_fx_clicked(self, clip):
        """Show the Video Event FX panel for the selected clip in the workspace."""
        from .panels import RockyPanel
        
        # 1. Select the clip (ensures context sync)
        for c in self.model.clips:
            c.selected = (c == clip)
        self.on_timeline_selection_changed([clip])
        
        # 2. Find a panel to host the FX controls
        target_panel = None
        
        # Priority 1: A panel already showing MediaTransformer
        for panel in self.findChildren(RockyPanel):
            if panel.current_type == "MediaTransformer":
                target_panel = panel
                break
        
        # Priority 2: A panel showing Properties (contextual buddy)
        if not target_panel:
            for panel in self.findChildren(RockyPanel):
                if panel.current_type == "Properties":
                    target_panel = panel
                    break
        
        # 3. If no panel is found, create one by splitting the right-most panel
        if not target_panel:
            # Look for the root splitter or any large panel to split
            # In our Blender system, we can find the rightmost panel
            panels = self.findChildren(RockyPanel)
            if panels:
                # Target the largest panel (usually Viewer or Timeline)
                target_panel = panels[0]
                for p in panels:
                    if p.width() * p.height() > target_panel.width() * target_panel.height():
                        target_panel = p
                
                # Split it vertically
                target_panel.split(Qt.Orientation.Horizontal)
                # After split, find the NEWLY created panel. 
                # Our split logic creates a brother. Let's search again.
                for p in self.findChildren(RockyPanel):
                    if p != target_panel and p.current_type == target_panel.current_type:
                        target_panel = p # This is the new clone
                        break
        
        # 4. Switch and Refresh
        if target_panel:
            target_panel.change_panel_type("MediaTransformer")
            # Update header icon/title to reflect the change
            target_panel.header.update_type_icon("MediaTransformer")
            target_panel.header.set_title("TRANSFORMADOR DE MEDIOS")
            
            # Re-dispatched to ensure the new content_area widget gets the clip data
            self.on_timeline_selection_changed([clip])
        else:
            # Extremely rare case: No panels exist at all (not possible in standard Rocky)
            print("WARNING: Could not find or create a panel for FX.")

    def show_subtitle_panel(self):
        """Contextual switch to subtitle panel for selected clips."""
        from .panels import RockyPanel
        
        # 1. Get currently selected clips
        selected = [c for c in self.model.clips if c.selected]
        if not selected:
             print("SubtitlePanel: No clips selected.")
             return
             
        # 2. Find a panel to host the subtitle controls
        target_panel = None
        for panel in self.findChildren(RockyPanel):
            if panel.current_type == "SubtitleGenerator":
                target_panel = panel
                break
        
        if not target_panel:
            for panel in self.findChildren(RockyPanel):
                if panel.current_type == "Properties" or panel.current_type == "MediaTransformer":
                    target_panel = panel
                    break
                    
        # 3. If no contextual panel found, split largest
        if not target_panel:
            panels = self.findChildren(RockyPanel)
            if panels:
                target_panel = panels[0]
                for p in panels:
                    if p.width() * p.height() > target_panel.width() * target_panel.height():
                        target_panel = p
                target_panel.split(Qt.Orientation.Horizontal)
                for p in self.findChildren(RockyPanel):
                    if p != target_panel and p.current_type == target_panel.current_type:
                        target_panel = p
                        break
        
        # 4. Switch
        if target_panel:
            target_panel.change_panel_type("SubtitleGenerator")
            target_panel.header.update_type_icon("SubtitleGenerator")
            target_panel.header.set_title("SUBTÍTULOS AUTOMÁTICOS")
            
            # Dispatch context
            self.on_timeline_selection_changed(selected)


    def rotate_selection(self, delta_degrees):
        """
        Manually rotates the selected clips by delta_degrees (e.g. 90 or -90).
        This fixes orientation issues when metadata is ambiguous.
        """
        selected_clips = [c for c in self.model.clips if c.selected]
        if not selected_clips:
            self.status_label.setText("Selecciona un clip para rotar.")
            return

        for clip in selected_clips:
            # Accumulate rotation
            new_rot = (clip.transform.rotation + delta_degrees) % 360
            clip.transform.rotation = new_rot
            
            # Reset/Adjust scale to fit if aspect ratio swaps? 
            # Or just rotate?
            # User might want to just rotate 90.
            # If we switch from landscape to portrait visual, we might want to refit.
            # But let's keep it simple: Just rotate. The user can scale if needed.
            
            # Force Engine Update
            self.rebuild_engine()
        
        self.timeline_widget.update()
        
        # Immediate feedback
        current_frame = self.model.blueline.playhead_frame
        fps = self.get_fps()
        timestamp = current_frame / fps
        self.on_time_changed(timestamp, current_frame, "Rotation Update", True)
        
        self.status_label.setText(f"Selección rotada {delta_degrees}°")

    def on_clip_proxy_clicked(self, clip):
        """Handler for when a clip's PX button is clicked."""
        from .models import ProxyStatus
        
        if clip.proxy_status == ProxyStatus.NONE or clip.proxy_status == ProxyStatus.ERROR:
            # Start Generation logic
            print(f"Starting proxy generation for {clip.name}")
            self._trigger_proxy_generation(clip)
            
        elif clip.proxy_status == ProxyStatus.READY:
            # Toggle proxy usage for this specific clip
            clip.use_proxy = not getattr(clip, 'use_proxy', False)
            print(f"Proxy for {clip.name} toggled to: {clip.use_proxy}")
            self.timeline_widget.update()
            
            # If the global toggle is ON, we need to rebuild the engine to swap the source
            if self.toolbar.btn_proxy.isChecked():
                self.rebuild_engine()
            
        self.update_proxy_button_state()

    def _toggle_fullscreen_viewer(self):
        if self.viewer.isFullScreen():
            self.viewer.setParent(None) # Detach
            self.viewer.showNormal()
            # Restore to layout (Viewer is index 1 in top_splitter)
            self.top_splitter.insertWidget(1, self.viewer)
            # Re-apply stretch factors roughly
            self.top_splitter.setStretchFactor(0, 1)
            self.top_splitter.setStretchFactor(1, 2)
        else:
            self.viewer.setParent(None) # Detach to make it a top-level window
            self.viewer.showFullScreen()

    def on_open(self):
        """
        Handles media file importation via the professional File Dialog.
        """
        file_filter = (
            "Rocky Project (*.rocky);;"
            "All Media (*.mp4 *.mov *.mkv *.avi *.png *.jpg *.jpeg *.bmp *.webp *.mp3 *.wav *.aac *.m4a *.flac);;"
            "Video Files (*.mp4 *.mov *.mkv *.avi);;"
            "Audio Files (*.mp3 *.wav *.aac *.m4a *.flac);;"
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;"
            "All Files (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir Proyecto o Media", "", file_filter)
        
        if file_path:
            if file_path.lower().endswith('.rocky'):
                self.load_project(file_path)
            else:
                start_frame = self.model.blueline.playhead_frame
                self.import_media(file_path, start_frame)
                self.status_label.setText(f"Importado: {os.path.basename(file_path)}")

    def import_media(self, file_path, start_frame, preferred_track_idx=-1):
        """
        Starts the asynchronous media import process.
        """
        self.status_label.setText(f"Probing media: {os.path.basename(file_path)}...")
        
        worker = MediaImportWorker(file_path, self.get_fps())
        
        # We need to pass the state (start_frame, preferred_track_idx) to the finish method
        # We can use a lambda or partial to "bind" these values
        # Worker emits: path, duration, source, width, height, rotation, fps
        worker.finished.connect(lambda path, dur, src, w, h, r, f: self._finish_import_logic(path, dur, src, w, h, r, f, start_frame, preferred_track_idx))
        worker.error.connect(self._on_import_error)
        
        self._active_workers.append(worker)
        # Use built-in finished for deletion safety
        worker.finished.connect(lambda: self._safe_remove_worker(worker))
        worker.start()

    def _on_import_error(self, path, message):
        self.status_label.setText(f"Error importando {os.path.basename(path)}")
        QMessageBox.warning(self, "Error de Importación", f"No se pudo cargar {path}:\n{message}")

    def _finish_import_logic(self, file_path, duration, source, width, height, rotation, fps, start_frame, preferred_track_idx):
        """
        Completes the import process once metadata is available from the background thread.
        ULTRA-FAST: Avoids blocking calls on the UI thread.
        """
        # Cleanup import worker (the sender)
        sender = self.sender()
        if hasattr(self, "_active_workers") and sender in self._active_workers:
            self._active_workers.remove(sender)
            sender.deleteLater()
            
        from .models import TimelineClip, TrackType
        
        is_forced_vertical = False
        file_name = os.path.basename(file_path)
        ext = file_name.lower().split('.')[-1]
        
        # PERFORMANCE OPTIMIZATION: Do NOT instantiate C++ sources on the UI thread if possible.
        # We start by checking if it's already cached.
        source = self.media_source_cache.get(file_path)
        
        # Check if project was empty before this import to trigger auto-zoom/resolution-match
        was_empty = (len(self.model.clips) == 0)
        
        # SMART PROVISIONING: Ask to match resolution on first import
        if was_empty and width > 0 and height > 0:
            msg = QMessageBox()
            msg.setWindowTitle("Configuración de Proyecto")
            
            # THE FIX: Calculate EFFECTIVE Visual Dimensions
            vis_w = width
            vis_h = height
            rotation_mod = abs(rotation) % 360
            
            if rotation_mod == 90 or rotation_mod == 270:
                vis_w, vis_h = height, width
            
            # Detect format and calculate aspect ratio
            is_vertical = vis_h > vis_w
            aspect_str = "VERTICAL" if is_vertical else "PANORÁMICO"
            
            # Calculate aspect ratio
            from math import gcd
            divisor = gcd(vis_w, vis_h)
            aspect_w = vis_w // divisor
            aspect_h = vis_h // divisor
            
            # Suggest common presets for vertical videos
            suggested_res = (vis_w, vis_h)
            preset_name = f"{vis_w}x{vis_h}"
            
            if is_vertical:
                # Common vertical presets
                common_vertical = {
                    (1080, 1920): "Instagram/TikTok/YouTube Shorts (9:16)",
                    (1080, 1350): "Instagram Post (4:5)",
                    (720, 1280): "HD Vertical (9:16)",
                }
                # Check if it matches a common preset
                if (vis_w, vis_h) in common_vertical:
                    preset_name = common_vertical[(vis_w, vis_h)]
                # Fuzzy Match for 9:16
                elif abs(vis_w/vis_h - 9/16) < 0.05:
                     if abs(vis_w - 1080) < 200:
                         suggested_res = (1080, 1920)
                         preset_name = "Instagram/TikTok/YouTube Shorts (1080x1920)"
            
            msg.setText(f"El medio detectado es {aspect_str} ({vis_w}x{vis_h}).")
            
            # --- USER CHOICE STRATEGY ---
            # Instead of just Yes/No, we give 3 robust options.
            # 1. Match Detected
            # 2. force Vertical (Shorts)
            # 3. Keep current
            
            btn_match = msg.addButton(f"Ajustar a {vis_w}x{vis_h}", QMessageBox.YesRole)
            
            # Smart "Force Vertical" button logic
            # If we detected Horizontal, offer Vertical. If detected Vertical, offer Horizontal?
            # Usually the problem is False Horizontal (Metadata missing).
            
            # Calculate the "Inverted" resolution for the Force button
            force_w, force_h = vis_w, vis_h
            if vis_w > vis_h: # If detected landscape, offer portrait
                force_w, force_h = vis_h, vis_w
            
            btn_force_vert = msg.addButton(f"Forzar Video Vertical (Shorts)", QMessageBox.ActionRole)
            btn_keep = msg.addButton("Mantener Actual", QMessageBox.NoRole)
            
            msg.setDefaultButton(btn_match)
            
            # Icon Logic
            msg.setWindowIcon(self.windowIcon())
            logo_path = self.get_resource_path(os.path.join("src", "img", "logo.png"))
            if os.path.exists(logo_path):
                src_pix = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg.setIconPixmap(src_pix)
            
            msg.exec() 
            clicked = msg.clickedButton()
            
            if clicked == btn_match:
                # Apply detected
                self.on_resolution_changed(suggested_res[0], suggested_res[1])
            elif clicked == btn_force_vert:
                # Apply FORCED VERTICAL (1080x1920 usually)
                self.on_resolution_changed(force_w, force_h)
                # If we detected landscape but user forced vertical, we must rotate the clip content
                if vis_w > vis_h:
                    is_forced_vertical = True
            else:
                # Keep current (do nothing or default 1080p if first time)
                if was_empty:
                    self.on_resolution_changed(1920, 1080)
        
        is_audio = ext in ["mp3", "wav", "aac", "m4a", "flac"]
        is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
        is_video = not is_audio and not is_image
        
        fps = self.get_fps()
        # duration and source_duration are passed from worker (in frames)
        source_duration = duration if not is_image else -1
        
        if is_image:
           # Default 30s for images if type is image
           duration = int(30 * fps)
           source_duration = -1

        if is_video:
            # 1. Video Track
            v_track = -1
            if preferred_track_idx != -1 and preferred_track_idx < len(self.model.track_types):
                if self.model.track_types[preferred_track_idx] == TrackType.VIDEO:
                    v_track = preferred_track_idx
            
            if v_track == -1:
                self.add_track(TrackType.VIDEO)
                v_track = len(self.model.track_types) - 1
            
            v_clip = TimelineClip(file_name, start_frame, duration, v_track)
            v_clip.file_path = file_path
            v_clip.source_duration_frames = source_duration
            
            # --- METADATA CACHE (Instant UI Optimization) ---
            v_clip.source_width = width
            v_clip.source_height = height
            v_clip.source_rotation = rotation
            v_clip.source_fps = fps
            
            # DEFERRED SOURCE LOADING: Avoid blocking UI thread
            # We schedule the heavy load for the NEXT event loop cycle
            if file_path not in self.media_source_cache:
                QTimer.singleShot(0, lambda: self._instantiate_source(file_path))
            
            # --- INITIAL TRANSFORMATION (Aspect Fit) ---
            # THE FIX: Do NOT swap width/height logic for the calculation of scale.
            # The engine now handles rotation (w,h) internally correctly.
            # We just need to fit the "Visual Box" into the "Project Box".
            
            # Apply detection or forced override
            final_rotation = float(rotation)
            if is_forced_vertical:
                # Use 270 (-90) as it is often the correct visual rotation for missing metadata
                final_rotation = (final_rotation + 270) % 360
            
            v_clip.transform.rotation = final_rotation
            
            # Dimensions of the content AS SEEN by the user (after rotation)
            content_w = width
            content_h = height
            
            # Recalculate visual bounds based on final rotation
            if abs(final_rotation) % 180 != 0:
                 content_w, content_h = height, width
            
            # Project dimensions
            p_w, p_h = self.p_width, self.p_height
            
            # Calculate Scale to Fit (Uniform Scale)
            # content_aspect = content_w / content_h
            # project_aspect = p_w / p_h
            
            scale_x = 1.0
            scale_y = 1.0
            
            # Fitting Logic:
            # We want the content rectangle to fit inside the project rectangle
            # scaling uniformly.
            
            scale_w = p_w / content_w
            scale_h = p_h / content_h
            
            # Choose the smaller scale to ensure 'Fit Inside' (Letterboxing)
            final_scale = min(scale_w, scale_h)
            
            # If the user wants to FILL (Zoom), they can increase it manually.
            # For import, 'Fit' is safer.
            v_clip.transform.scale_x = final_scale
            v_clip.transform.scale_y = final_scale
            
            # Reset scaling if it's very close to 1.0 (avoid floating point fuzz)
            if abs(final_scale - 1.0) < 0.01:
                v_clip.transform.scale_x = 1.0
                v_clip.transform.scale_y = 1.0
            
            # 2. Audio Track
            a_track = -1
            self.add_track(TrackType.AUDIO)
            a_track = len(self.model.track_types) - 1
            
            a_clip = TimelineClip(f"[Audio] {file_name}", start_frame, duration, a_track)
            a_clip.file_path = file_path
            a_clip.source_duration_frames = source_duration
            a_clip.source_fps = fps
            
            v_clip.linked_to = a_clip
            a_clip.linked_to = v_clip
            
            self.model.add_clip(v_clip)
            self.model.add_clip(a_clip)
            
            # Trigger background workers (Async by nature)
            self._start_waveform_analysis(a_clip)
            self._start_thumbnail_analysis(v_clip)
            self._trigger_proxy_generation(v_clip)
            
        else:
            required_type = TrackType.AUDIO if is_audio else TrackType.VIDEO
            t_idx = -1
            if preferred_track_idx != -1 and preferred_track_idx < len(self.model.track_types):
                if self.model.track_types[preferred_track_idx] == required_type:
                    t_idx = preferred_track_idx
            
            if t_idx == -1:
                self.add_track(required_type)
                t_idx = len(self.model.track_types) - 1
            
            clip = TimelineClip(file_name, start_frame, duration, t_idx)
            clip.file_path = file_path
            clip.source_duration_frames = source_duration
            clip.source_width = width
            clip.source_height = height
            clip.source_rotation = rotation
            clip.source_fps = fps
            
            if file_path not in self.media_source_cache:
                QTimer.singleShot(0, lambda: self._instantiate_source(file_path))
                
            self.model.add_clip(clip)
            
            if is_audio:
                self._start_waveform_analysis(clip)
            else:
                self._start_thumbnail_analysis(clip)
        
        self.timeline_widget.update()
        self.on_structure_changed()
        
        # Trigger cinematic "Zoom to Fit" animation on every import
        QTimer.singleShot(100, lambda: self.timeline_widget.zoom_to_fit(animate=True))
        self.status_label.setText(f"Importado: {file_name}")
        
    def _safe_remove_worker(self, worker):
        """Standardized safe removal of background threads."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()

    def on_save(self):
        if self.project_path:
            self.save_project(self.project_path)
        else:
            self.on_save_as()

    def on_save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Proyecto", "", "Rocky Project (*.rocky)")
        if file_path:
            if not file_path.endswith('.rocky'):
                file_path += '.rocky'
            self.save_project(file_path)

    def save_project(self, path):
        try:
            data = self.model.to_dict()
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            self.project_path = path
            self.status_label.setText(f"Proyecto guardado: {os.path.basename(path)}")
            # Optional: update window title
            self.setWindowTitle(f"Rocky Video Editor Pro - {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el proyecto:\n{str(e)}")

    def load_project(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            from .models import TimelineModel
            new_model = TimelineModel.from_dict(data)
            
            # Stop playback
            if self.model.blueline.playing:
                self.toggle_play()
                
            # Replace model
            self.model = new_model
            if self.sidebar:
                self.sidebar.model = new_model
            if self.timeline_widget:
                self.timeline_widget.model = new_model
            # Re-initialize workers or reconnect if needed
            self.audio_worker.model = new_model
            
            self.project_path = path
            self.setWindowTitle(f"Rocky Video Editor Pro - {os.path.basename(path)}")
            
            # Rebuild and refresh
            self.on_structure_changed()
            self.status_label.setText(f"Proyecto cargado: {os.path.basename(path)}")
            
            # Recalculate waveforms and thumbnails for loaded clips
            for clip in self.model.clips:
                if clip.file_path and os.path.exists(clip.file_path):
                    ext = clip.file_path.lower().split('.')[-1]
                    is_audio = ext in ["mp3", "wav", "aac", "m4a", "flac"]
                    if is_audio:
                        self._start_waveform_analysis(clip)
                    else:
                        self._start_thumbnail_analysis(clip)
                        self._trigger_proxy_generation(clip)
            
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar", f"No se pudo cargar el proyecto:\n{str(e)}")

    def on_render(self):
        """
        Inicia el proceso de exportación final del video con selección de parámetros pro.
        """
        from .export_dialog import ExportDialog
        dlg = ExportDialog(self)
        if not dlg.exec():
            return
            
        config = dlg.get_selected_config()
        
        output_path, _ = QFileDialog.getSaveFileName(self, "Exportar Video", "video_final.mp4", "MPEG-4 (*.mp4)")
        if not output_path:
            return

        # Ensure we render with High Quality (Originals)
        if self.toolbar.btn_proxy.isChecked():
            self.toolbar.btn_proxy.setChecked(False)
            self.on_proxy_toggle() 

        total_frames = self.model.get_max_frame()
        if total_frames <= 0:
            QMessageBox.warning(self, "Renderizar", "El timeline está vacío.")
            return

        active_fps = self.get_fps()
        render_w = config["width"]
        render_h = config["height"]

        # Detener reproducción si está activa
        if self.model.blueline.playing:
            self.toggle_play()

        # Crear Dialogo de Progreso
        self.prog_dialog = QProgressDialog("Exportando video...", "Cancelar", 0, 100, self)
        self.prog_dialog.setWindowTitle("Rocky Render")
        self.prog_dialog.setWindowModality(Qt.WindowModal)
        self.prog_dialog.setMinimumDuration(0)
        
        high_quality = config.get("high_quality", False)
        
        # Crear y configurar Worker con la resolución elegida
        self.render_worker = RenderWorker(self.engine, self.engine_lock, output_path, total_frames, active_fps, render_w, render_h, high_quality)

        self.render_worker.progress.connect(self.prog_dialog.setValue)
        self.render_worker.finished.connect(self._on_render_finished)
        self.render_worker.error.connect(self._on_render_error)
        
        self.prog_dialog.canceled.connect(self.render_worker.requestInterruption)
        
        self.render_worker.start()
        self.status_label.setText(f"Renderizando... ({'Alta Fidelidad' if high_quality else 'Normal'})")

    def _on_render_finished(self, path):
        self.prog_dialog.close()
        self.status_label.setText(f"Renderizado finalizado: {path}")
        QMessageBox.information(self, "Renderizar", f"¡Video exportado con éxito!\n{path}")

    def _on_render_error(self, message):
        self.prog_dialog.close()
        self.status_label.setText("Error en el render.")
        QMessageBox.critical(self, "Error de Render", f"Ocurrió un error al exportar:\n{message}")

    def on_settings(self):
        self.status_label.setText("Abriendo ajustes del proyecto...")
        dlg = SettingsDialog(self)
        
        # Pre-fill current settings
        if hasattr(dlg, 'w_spin'):
            dlg.w_spin.setValue(self.p_width)
            dlg.h_spin.setValue(self.p_height)
            
        if dlg.exec():
            settings = dlg.get_settings()
            
            new_w = settings["width"]
            new_h = settings["height"]
            new_fps = settings["fps"]
            
            
            # 1. Update Persistent State
            self.p_width = new_w
            self.p_height = new_h
            
            # 2. Update Engine Configuration
            self.engine.set_resolution(new_w, new_h)
            self.engine.set_fps(new_fps)
            
            # 3. Update Viewer UI
            for viewer in self.viewer_registry:
                if hasattr(viewer, 'update_format_label'):
                    viewer.update_format_label(new_w, new_h)
            
            # 4. Refresh Application
            self.status_label.setText(f"Proyecto configurado a {new_w}x{new_h}")
            
            # Force a full engine sync
            self.rebuild_engine()
            self.timeline_widget.update()
            
            # Re-evaluate current frame to show changes immediately
            current_frame = self.model.blueline.playhead_frame
            fps = self.get_fps()
            timestamp = current_frame / fps
            self.on_time_changed(timestamp, current_frame, "00:00:00;00", True)

            fps = self.get_fps()
            timestamp = current_frame / fps
            self.on_time_changed(timestamp, current_frame, "00:00:00;00", True)

    def on_resolution_changed(self, width, height):
        """
        Handles requests to change the project resolution (e.g. from Import auto-detect).
        Updates state, engine, and UI immediately.
        """
        
        # 1. Update Persistent State
        self.p_width = width
        self.p_height = height
        
        # 2. Update Engine Configuration
        self.engine.set_resolution(width, height)
        
        # 3. Update Viewer UI
        for viewer in self.viewer_registry:
            if hasattr(viewer, 'update_format_label'):
                viewer.update_format_label(width, height)
        
        # 4. Refresh Application
        self.status_label.setText(f"Resolución actualizada a {width}x{height}")
        
        # Force a full engine sync
        self.rebuild_engine()
        self.timeline_widget.update()
        
        # Re-evaluate current frame to show changes immediately
        current_frame = self.model.blueline.playhead_frame
        fps = self.get_fps()
        timestamp = current_frame / fps
        self.on_time_changed(timestamp, current_frame, "Resolution Update", True)

    def toggle_play(self):
        """Toggles the playback state. Restores hidden panels if needed."""
        # Restoration logic - Show middle section if it was hidden
        if hasattr(self, 'middle_section') and self.middle_section.isHidden():
            self.middle_section.show()
            self.status_label.setText("Interfaz restaurada")
            # If it's empty, we might want to recreate a panel, but let's assume at least one exists or was hidden

        self.model.blueline.playing = not self.model.blueline.playing
        # If it's very close to 1.0, snap it
        if 0.95 < self.playback_rate < 1.05:
            self.playback_rate = 1.0
            
        self.model.blueline.playback_rate = self.playback_rate
        self.status_label.setText(f"Velocidad: {self.playback_rate:.1f}x")
        
        # Update playback timer interval if playing.
        if self.model.blueline.playing:
            self.playback_timer.setInterval(int(16 / max(0.1, self.playback_rate)))
            
            active_fps = self.get_fps()
            # Capturamos el estado inicial para el Reloj Maestro
            self.playback_start_frame = self.model.blueline.playhead_frame
            self.playback_start_audio_time = self.audio_player.get_processed_us()
            
            start_time = self.model.blueline.playhead_frame / active_fps
            self.audio_worker.start_playback(start_time, active_fps, self.playback_rate)
        else:
            self.audio_worker.stop_playback()
            
            # Vegas Style: Return to start position on stop
            if hasattr(self, 'playback_start_frame'):
                self.model.blueline.set_playhead_frame(self.playback_start_frame)
                fps = self.get_fps()
                tc = self.model.format_timecode(self.playback_start_frame, fps)
                self.on_time_changed(self.playback_start_frame / fps, int(self.playback_start_frame), tc, True)
                self.timeline_widget.update()


    def on_playback_rate_changed(self, value):
        """Dynamic playback speed control (Scrubbing/Shuttle)."""
        new_rate = value / 100.0
        self.viewer.lbl_rate.setText(f"{new_rate:.1f}x")
        
        if self.model.blueline.playing:
            # Re-anclamos el reloj maestro para evitar saltos al cambiar la velocidad
            active_fps = self.get_fps()
            
            # Use Audio Clock for accurate elapsed time
            current_audio = self.audio_player.get_processed_us()
            elapsed_us = current_audio - self.playback_start_audio_time
            if elapsed_us < 0: elapsed_us = 0
            elapsed_real_time = elapsed_us / 1_000_000.0
            
            current_frame = self.playback_start_frame + (elapsed_real_time * active_fps * self.playback_rate)
            
            self.playback_start_frame = current_frame
            self.playback_start_audio_time = self.audio_player.get_processed_us()
            
            # IMMEDIATELY clear the audio buffer to apply the new rate without lag
            self.audio_player.clear_buffer()
            # Reset the rendered samples tracker to current timeline position so worker starts fresh
            self.model.audio_samples_rendered = int((current_frame / active_fps) * 44100)
        
        self.playback_rate = new_rate
        self.model.blueline.playback_rate = new_rate

    def on_playback_rate_released(self):
        """Spring-loaded reset: Returns to 1.0x speed."""
        self.on_playback_rate_changed(100) # Force 1.0x

    def on_playback_tick(self):

        """
        Main execution pulse for project playback.
        Uses a Wall-Clock Master Sync to prevent A/V drift.
        """
        if not self.model.blueline.playing:
            return

        active_fps = self.get_fps()
        
        # RELOJ MAESTRO: Calculamos el tiempo transcurrido REAL basado en el AUDIO
        # Esto previene el desincronismo (Drift). Si el audio se adelanta/atrasa, el video lo sigue.
        try:
            current_audio_time = self.audio_player.get_processed_us()
            elapsed_us = current_audio_time - self.playback_start_audio_time
            if elapsed_us < 0: elapsed_us = 0 # Prevención de relojes negativos
            elapsed_real_time = elapsed_us / 1_000_000.0
        except:
             # Fallback si el audio falla
             elapsed_real_time = 0
             
        current_frame = self.playback_start_frame + (elapsed_real_time * active_fps * self.playback_rate)


        
        # 1. Synchronize UI (Playhead and Timeline)
        # Update all registered timelines equally
        playhead_screen_x = None
        for timeline in self.timeline_registry:
            try:
                x = timeline.update_playhead_position(current_frame, forced=False)
                if playhead_screen_x is None:  # Use first timeline for scroll reference
                    playhead_screen_x = x
            except:
                pass
        
        if playhead_screen_x is not None:
            self.auto_scroll_playhead(playhead_screen_x)
        
        # 2. Synchronize Engine (Atomic Evaluation)
        engine_timestamp = current_frame / active_fps
        try:
            # Video (GUI Thread)
            locker = QMutexLocker(self.engine_lock)
            rendered_frame = self.engine.evaluate(engine_timestamp)
            del locker
            
            self._broadcast_frame(rendered_frame)
            
            # NOTE: Audio is now handled by AudioWorker thread to ensure ZERO drops
            
        except Exception as rendering_error:
            print(f"Playback Error: Render evaluation failed: {rendering_error}")
            self.toggle_play() # Halt playback on critical failure

    def on_time_changed(self, timestamp, frame_index, timecode, forced):
        """
        Synchronizes the UI state when the playhead is manually moved.
        """
        if self.sidebar:
            # Actualizar el timecode gigante en el sidebar
            self.sidebar.header.set_timecode(timecode)
            
            # Forzamos el repintado de toda la barra lateral
            for w in self.sidebar.track_widgets:
                w.update()
        
        if self.timeline_ruler:
            self.timeline_ruler.update() # Ensure ruler handle moves
        
        # If seek is forced while playing (manual seek during playback), update start reference
        if forced and self.model.blueline.playing:
             self.playback_start_frame = frame_index
             self.playback_start_audio_time = self.audio_player.get_processed_us()
        
        locker = QMutexLocker(self.engine_lock)
        rendered_frame = self.engine.evaluate(timestamp)
        del locker
        
        self._broadcast_frame(rendered_frame)


    def on_structure_changed(self):
        """Triggered when clips are moved, added, or deleted."""
        # Refresh ALL sidebars in multi-panel layout
        from .sidebar import SidebarPanel
        for sidebar in self.findChildren(SidebarPanel):
            sidebar.refresh_tracks()
        self.rebuild_engine()
        
        # Refresh Contextual Panels (FX Panel)
        from .fx_panel import VideoEventFXPanel
        for fx_panel in self.findChildren(VideoEventFXPanel):
             if fx_panel.current_clip:
                  fx_panel._refresh_effects_list()
        if self.timeline_widget:
            self.timeline_widget.updateGeometry() # Force scrollbar update
        if self.timeline_ruler:
            self.timeline_ruler.update()
        self.update_proxy_button_state() # Link Master Button to Clip State

    def add_track(self, ttype):
        """Adds a track to the model and updates UI globally."""
        self.model.track_types.append(ttype)
        self.model.track_heights.append(60)
        
        # Refresh ALL sidebars in multi-panel layout
        from .sidebar import SidebarPanel
        for sidebar in self.findChildren(SidebarPanel):
            sidebar.refresh_tracks()

    def _broadcast_frame(self, frame_buffer):
        """Send rendered frame to all registered viewer panels."""
        for viewer in self.viewer_registry:
            try:
                viewer.display_frame(frame_buffer)
            except:
                # Remove dead viewers
                self.viewer_registry.remove(viewer)

    def register_viewer(self, viewer_panel):
        """Register a viewer panel to receive frame broadcasts and connect controls."""
        if viewer_panel not in self.viewer_registry:
            self.viewer_registry.append(viewer_panel)
            
            # Connect standard controls if they exist
            if hasattr(viewer_panel, 'btn_rewind'):
                viewer_panel.btn_rewind.clicked.connect(lambda: self.on_rewind())
            if hasattr(viewer_panel, 'btn_play_pause'):
                viewer_panel.btn_play_pause.clicked.connect(self.toggle_play)
            if hasattr(viewer_panel, 'btn_fullscreen'):
                viewer_panel.btn_fullscreen.clicked.connect(self._toggle_fullscreen_viewer)
            if hasattr(viewer_panel, 'slider_rate'):
                viewer_panel.slider_rate.valueChanged.connect(self.on_playback_rate_changed)
                viewer_panel.slider_rate.sliderReleased.connect(self.on_playback_rate_released)

    def on_rewind(self):
        """Handles rewind request from any viewer."""
        timeline = self.get_active_timeline()
        if timeline:
            timeline.update_playhead_to_x(0)

    def unregister_viewer(self, viewer_panel):
        """Unregister a viewer panel from frame broadcasts."""
        if viewer_panel in self.viewer_registry:
            self.viewer_registry.remove(viewer_panel)

    def register_master_meter(self, meter_panel):
        """Register a master meter panel to sync with main audio output."""
        if meter_panel not in self.master_meter_registry:
            self.master_meter_registry.append(meter_panel)
            # Connect fader to main gain control
            if hasattr(meter_panel, 'fader'):
                meter_panel.fader.valueChanged.connect(self.on_master_gain_changed)

    def unregister_master_meter(self, meter_panel):
        """Unregister a master meter panel."""
        if meter_panel in self.master_meter_registry:
            if hasattr(meter_panel, 'fader'):
                try:
                    meter_panel.fader.valueChanged.disconnect(self.on_master_gain_changed)
                except:
                    pass
            self.master_meter_registry.remove(meter_panel)

    def register_timeline(self, timeline_widget):
        """Register a timeline widget to sync with main playback."""
        if timeline_widget not in self.timeline_registry:
            self.timeline_registry.append(timeline_widget)
            
            # 1. Sync Playhead & Structure
            # Avoid duplicate connections if already connected
            try:
                timeline_widget.time_updated.disconnect(self.on_time_changed)
            except: pass
            timeline_widget.time_updated.connect(self.on_time_changed)
            
            try:
                timeline_widget.structure_changed.disconnect(self.on_structure_changed)
            except: pass
            timeline_widget.structure_changed.connect(self.on_structure_changed)
            
            # 2. UI Action Signals
            try:
                timeline_widget.play_pause_requested.disconnect(self.toggle_play)
            except: pass
            timeline_widget.play_pause_requested.connect(self.toggle_play)
            
            try:
                timeline_widget.view_updated.disconnect(self.sync_scroll_to_view)
            except: pass
            timeline_widget.view_updated.connect(self.sync_scroll_to_view)
            
            try:
                timeline_widget.hover_x_changed.disconnect(self.sync_hover_to_ruler)
            except: pass
            timeline_widget.hover_x_changed.connect(self.sync_hover_to_ruler)
            
            try:
                timeline_widget.clip_proxy_toggled.disconnect(self.on_clip_proxy_clicked)
            except: pass
            timeline_widget.clip_proxy_toggled.connect(self.on_clip_proxy_clicked)
            
            try:
                timeline_widget.clip_fx_toggled.disconnect(self.on_clip_fx_clicked)
            except: pass
            timeline_widget.clip_fx_toggled.connect(self.on_clip_fx_clicked)

    def sync_timeline_registration(self, widget):
        """Recursively find and register all timelines within a widget."""
        from .timeline.simple_timeline import SimpleTimeline
        if isinstance(widget, SimpleTimeline):
            self.register_timeline(widget)
        
        for child in widget.findChildren(SimpleTimeline):
            self.register_timeline(child)

    def save_current_layout_to_workspace(self):
        """Serializes current layout and returns it."""
        from .panels import RockyPanel
        # We find the root widget of the middle section
        root_layout = self.middle_section.layout()
        if root_layout.count() > 0:
            root_widget = root_layout.itemAt(0).widget()
            return RockyPanel.serialize_layout(root_widget)
        return None

    def load_layout_from_workspace(self, layout_data):
        """Clears current layout and reconstructs from data."""
        from .panels import RockyPanel
        
        # 1. Unregister everything first
        self.viewer_registry.clear()
        self.master_meter_registry.clear()
        self.timeline_registry.clear()
        
        # 2. Clear middle section
        root_layout = self.middle_section.layout()
        while root_layout.count() > 0:
            item = root_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        
        # 3. Reconstruct
        new_root = RockyPanel.deserialize_layout(layout_data, self)
        if new_root:
            root_layout.addWidget(new_root)
            self.main_panel = new_root # Update reference if needed
            
        # 4. Refresh sidebar and others
        self.on_structure_changed()
        self.update()

    def _init_default_workspace(self):
        """Creates the initial default workspace button with standard layout."""
        # Layout matching the user's image:
        # - Left side: Viewer (top) + Timeline (bottom) in vertical split
        # - Right side: Effects/Properties panel
        
        default_layout = {
            "type": "splitter",
            "orientation": 1, # Horizontal (left-right)
            "sizes": [1000, 400],  # 70% left, 30% right
            "children": [
                {
                    "type": "splitter",
                    "orientation": 2, # Vertical (top-bottom)
                    "sizes": [600, 400],  # 60% viewer, 40% timeline
                    "children": [
                        {"type": "panel", "panel_type": "Viewer", "title": "VISOR DE VIDEO"},
                        {"type": "panel", "panel_type": "Timeline", "title": "LÍNEA DE TIEMPO"}
                    ]
                },
                {"type": "panel", "panel_type": "Effects", "title": "EFECTOS"}
            ]
        }
        
        # Create "Genérico" workspace with this layout
        self.toolbar.workspace_bar.add_workspace("Genérico", default_layout)
        
        # New "Shorts" Workspace: Optimized for vertical content
        shorts_layout = {
            "type": "splitter",
            "orientation": 1, # Root is Left-Right Split
            "sizes": [1000, 400], 
            "children": [
                {
                    "type": "splitter",
                    "orientation": 2, # Left part is Top-Bottom Split
                    "sizes": [600, 400], 
                    "children": [
                        {
                            "type": "splitter",
                            "orientation": 1, # Top-Left is Effects + Meter
                            "sizes": [400, 65],
                            "children": [
                                {"type": "panel", "panel_type": "Effects", "title": "EFECTOS"},
                                {"type": "panel", "panel_type": "MasterMeter", "title": "VÚMETRO MAESTRO"}
                            ]
                        },
                        {"type": "panel", "panel_type": "Timeline", "title": "LÍNEA DE TIEMPO"}
                    ]
                },
                {"type": "panel", "panel_type": "Viewer", "title": "VISOR DE VIDEO"}
            ]
        }
        self.toolbar.workspace_bar.add_workspace("Shorts", shorts_layout)
        
        self.toolbar.workspace_bar.set_active("Genérico")
        
        if self.timeline_widget:
            self.timeline_widget.selection_changed.connect(self.on_timeline_selection_changed)

    def on_timeline_selection_changed(self, selection):
        """Dispatches selection changes to whichever properties or FX panel is active."""
        # Find all RockyPanel descendants and check their content
        from .panels import RockyPanel
        from .editor_panel import EditorPanel
        from .fx_panel import VideoEventFXPanel
        
        # Traverse the entire widget tree to find active contextual panels
        # This is robust for multiple splitters/panels
        for panel in self.findChildren(RockyPanel):
            content = panel.content_area.layout().itemAt(0).widget() if panel.content_area.layout().count() > 0 else None
            if content and hasattr(content, 'update_context'):
                content.update_context(selection)

    def unregister_timeline(self, timeline_widget):
        """Unregister a timeline widget from playback sync."""
        if timeline_widget in self.timeline_registry:
            try:
                timeline_widget.time_updated.disconnect(self.on_time_changed)
                timeline_widget.structure_changed.disconnect(self.on_structure_changed)
            except:
                pass
            self.timeline_registry.remove(timeline_widget)

    def get_active_timeline(self):
        """Get the first active timeline from registry, or None."""
        return self.timeline_registry[0] if self.timeline_registry else None

    def get_active_viewer(self):
        """Get the first active viewer from registry, or None."""
        return self.viewer_registry[0] if self.viewer_registry else None

    def get_fps(self):
        """Get FPS from active timeline or return default 30."""
        timeline = self.get_active_timeline()
        if timeline and hasattr(timeline, 'get_fps'):
            return timeline.get_fps()
        return 30  # Default FPS

    @property
    def timeline_widget(self):
        """Backward compatibility: Get active timeline."""
        return self.get_active_timeline()

    @property
    def sidebar(self):
        """Dynamic lookup: Find the sidebar associated with the active timeline."""
        timeline = self.get_active_timeline()
        if not timeline: return None
        # Sidebar is usually a sibling in the dynamic panel layout
        parent = timeline.parent()
        if parent:
            from .sidebar import SidebarPanel
            # Search siblings or children of parent
            res = parent.findChild(SidebarPanel)
            if res: return res
            # Search in grandparents (Splitter)
            gp = parent.parent()
            if gp: return gp.findChild(SidebarPanel)
        return None

    @property
    def timeline_ruler(self):
        """Dynamic lookup: Find the ruler associated with the active timeline."""
        timeline = self.get_active_timeline()
        if not timeline: return None
        parent = timeline.parent()
        if parent:
            from .ruler import TimelineRuler
            return parent.findChild(TimelineRuler)
        return None

    @property
    def master_meter(self):
        """Dynamic lookup: Find the FIRST active master meter registry entry."""
        return self.master_meter_registry[0] if self.master_meter_registry else None

    def get_master_gain(self):
        """Safely get master gain from meter or return default 1.0."""
        meter = self.master_meter
        if meter and hasattr(meter, 'fader'):
            return meter.fader.value() / 75.0
        return 1.0 # Default gain

    @property
    def viewer(self):
        """Backward compatibility: Get active viewer."""
        return self.get_active_viewer()

    def on_master_gain_changed(self, value):
        """
        Maps the 0-100 fader to linear gain.
        """
        gain = value / 75.0
        self.engine.set_master_gain(gain)
        self.status_label.setText(f"Master Volume: {int(value)}%")

    def on_resolution_changed(self, width, height):
        """
        Updates the global project resolution in the engine.
        Affects both preview and final render.
        """
        # Calculate aspect ratio for display
        from math import gcd
        divisor = gcd(width, height)
        aspect_w = width // divisor
        aspect_h = height // divisor
        
        # Determine format type
        is_vertical = height > width
        format_type = "Vertical" if is_vertical else "Horizontal"
        
        print(f"Project Resolution Changed: {width}x{height} ({aspect_w}:{aspect_h} - {format_type})")
        
        # Stop playback to avoid engine contention during resolution swap
        was_playing = self.model.blueline.playing
        if was_playing:
            self.toggle_play()

        locker = QMutexLocker(self.engine_lock)
        self.p_width = width
        self.p_height = height
        self.engine.set_resolution(width, height)
        del locker

        # Enhanced status message with aspect ratio
        self.status_label.setText(f"Resolución: {width}x{height} ({aspect_w}:{aspect_h} - {format_type})")
        
        # Update all viewer panels with new format info
        for viewer in self.viewer_registry:
            if hasattr(viewer, 'update_format_label'):
                viewer.update_format_label(width, height)
        
        # Trigger a re-render of the current frame to show the new aspect ratio
        current_frame = self.model.blueline.playhead_frame
        active_fps = self.get_fps()
        tc = self.model.format_timecode(current_frame, active_fps)
        self.on_time_changed(current_frame / active_fps, int(current_frame), tc, True)
        
        if was_playing:
            self.toggle_play()



    def _start_waveform_analysis(self, clip):
        """Launches a background thread to calculate the real audio waveform."""
        clip.waveform_computing = True
        worker = WaveformWorker(clip, clip.file_path)
        worker.finished.connect(self.on_waveform_finished)
        # Built-in finished for safe cleanup
        worker.finished.connect(lambda: self._safe_remove_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _start_thumbnail_analysis(self, clip):
        """Launches a background thread to extract keyframe thumbnails."""
        clip.thumbnails_computing = True
        worker = ThumbnailWorker(clip, clip.file_path)
        worker.finished.connect(self.on_thumbnails_finished)
        # Built-in finished for safe cleanup
        worker.finished.connect(lambda: self._safe_remove_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def on_waveform_finished(self, clip, peaks):
        """Callback when the C++ engine finishes scanning the audio file."""
        clip.waveform = peaks
        clip.waveform_computing = False
        self.timeline_widget.update()
        
        # Refresh FX dialog if open
        dlg = self.fx_dialogs.get(id(clip))
        if dlg: dlg.sub_timeline.update()




    def on_thumbnails_finished(self, clip, thumbs):
        """Callback when the C++ engine finishes extracting thumbnails."""
        clip.thumbnails = thumbs
        clip.thumbnails_computing = False
        self.timeline_widget.update()
        
        # Refresh FX dialog if open (Critical for the "Loading" placeholder)
        dlg = self.fx_dialogs.get(id(clip))
        if dlg: 
            dlg.display_label.update()

    def _trigger_proxy_generation(self, clip):
        """Starts the proxy generation process for a clip."""
        from .models import ProxyStatus
        clip.proxy_status = ProxyStatus.GENERATING
        self.update_proxy_button_state()
        
        worker = ProxyWorker(clip, clip.file_path)
        worker.finished.connect(self._on_proxy_finished)
        # Built-in finished for safe cleanup
        worker.finished.connect(lambda: self._safe_remove_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_proxy_finished(self, clip, proxy_path, success):
        """Callback when proxy generation completes."""
        from .models import ProxyStatus
        if success:
            clip.proxy_path = proxy_path
            clip.proxy_status = ProxyStatus.READY
            clip.use_proxy = True # Default to using it if available?
            print(f"Proxy Ready for {clip.name}")
        else:
            clip.proxy_status = ProxyStatus.ERROR
            print(f"Proxy Failed for {clip.name}")
            
        self.update_proxy_button_state()
        
        # If the global toggle is ON, we might need to refresh the engine to swap to this new proxy
        if self.toolbar.btn_proxy.isChecked() and success:
            self.rebuild_engine()

    def update_proxy_button_state(self):
        """Determines the color of the global proxy button based on all clips."""
        from .models import ProxyStatus, TrackType
        # Logic: 
        # If ANY is generating -> Orange
        # If ANY error -> Red
        # If ALL ready -> Green
        # Else -> Black
        
        any_generating = False
        any_error = False
        start_check = False
        
        # Only care about Video clips
        video_clips = [c for c in self.model.clips if self.model.track_types[c.track_index] == TrackType.VIDEO]
        
        if not video_clips:
            self.toolbar.set_proxy_status_color('black')
            return

        all_ready = True
        for c in video_clips:
            if c.proxy_status == ProxyStatus.GENERATING:
                any_generating = True
            elif c.proxy_status == ProxyStatus.ERROR:
                any_error = True
                all_ready = False
            elif c.proxy_status != ProxyStatus.READY:
                all_ready = False
        
        if any_generating:
            self.toolbar.set_proxy_status_color('orange')
        elif any_error:
            self.toolbar.set_proxy_status_color('red')
        elif all_ready:
            self.toolbar.set_proxy_status_color('green')
        else:
            # Mixed state or none
            self.toolbar.set_proxy_status_color('black')
            # If no proxies are active, maybe uncheck? Or leave user preference?
            # User said: "el boton azul... se vincula". Suggests 1:1.
            # If ALL are None, maybe uncheck. 
            # But "active" means different things (existence vs usage).
            # Let's keep it simple: Color update is enough for now.

    def on_proxy_toggle(self):
        """User clicked the Global Proxy Toggle."""
        use_proxies = self.toolbar.btn_proxy.isChecked()
        print(f"Global Proxy Mode: {use_proxies}")
        self.toolbar.set_proxy_status_color('black') # Recalculate color
        self.update_proxy_button_state()
        self.rebuild_engine()

            


    def rebuild_engine(self):
        """
        Deep synchronization between the high-level Python models and the 
        low-level C++ rendering core. 
        """
        # CRITICAL: Stop playback to avoid engine contention during rebuild
        was_playing = self.model.blueline.playing
        if was_playing:
            self.toggle_play()

        locker = QMutexLocker(self.engine_lock)
        self.engine.clear()
        self.clip_map = {} # Reset map
        active_fps = self.get_fps()
        self.engine.set_fps(active_fps)
        
        # Sync Master Gain
        initial_gain = self.get_master_gain()
        self.engine.set_master_gain(initial_gain)
        
        # 1. Sync Tracks
        for track_type in self.model.track_types:
            cpp_track_type = rocky_core.VIDEO if track_type == TrackType.VIDEO else rocky_core.AUDIO
            self.engine.add_track(cpp_track_type)
            
        # 2. Sync Clips and Media Sources
        use_proxies = self.toolbar.btn_proxy.isChecked()

        for clip in self.model.clips:
            from .models import ProxyStatus
            
            # Determine effective path
            path_to_use = clip.file_path
            if use_proxies and clip.proxy_status == ProxyStatus.READY and clip.proxy_path:
                path_to_use = clip.proxy_path
            
            media_source = self._instantiate_source(path_to_use)
            
            cpp_clip = self.engine.add_clip(
                clip.track_index,
                clip.name,
                int(clip.start_frame),
                int(clip.duration_frames),
                clip.source_offset_frames / active_fps,
                media_source
            )
            self.clip_map[clip] = cpp_clip
            
            # 3. Surface extended properties
            cpp_clip.opacity = clip.start_opacity
            cpp_clip.transform.x = clip.transform.x
            cpp_clip.transform.y = clip.transform.y
            cpp_clip.transform.scale_x = clip.transform.scale_x
            cpp_clip.transform.scale_y = clip.transform.scale_y
            cpp_clip.transform.rotation = clip.transform.rotation
            cpp_clip.transform.anchor_x = clip.transform.anchor_x
            cpp_clip.transform.anchor_y = clip.transform.anchor_y

            # 4. Sync Effects
            if hasattr(clip, 'effects') and clip.effects:
                cpp_effects_list = []
                for eff in clip.effects:
                    # Robust key check for plugin path
                    path = eff.get('path') or eff.get('plugin_path') or ''
                    name = eff.get('name', 'Unknown')
                    enabled = eff.get('enabled', True)
                    
                    if path:
                        c_eff = rocky_core.Effect(name, path)
                        c_eff.enabled = enabled
                        cpp_effects_list.append(c_eff)
                
                cpp_clip.effects = cpp_effects_list
            cpp_clip.fade_in_frames = int(clip.fade_in_frames)
            cpp_clip.fade_out_frames = int(clip.fade_out_frames)
            cpp_clip.fade_in_type = rocky_core.FadeType(clip.fade_in_type.value)
            cpp_clip.fade_out_type = rocky_core.FadeType(clip.fade_out_type.value)
            
    def sync_clip_transform(self, clip):
        """Syncs the transform of a specific clip to the engine and refreshes UI."""
        if clip in self.clip_map:
            cpp_clip = self.clip_map[clip]
            cpp_clip.transform.x = clip.transform.x
            cpp_clip.transform.y = clip.transform.y
            cpp_clip.transform.scale_x = clip.transform.scale_x
            cpp_clip.transform.scale_y = clip.transform.scale_y
            cpp_clip.transform.rotation = clip.transform.rotation
            cpp_clip.transform.anchor_x = clip.transform.anchor_x
            cpp_clip.transform.anchor_y = clip.transform.anchor_y
            
            # 1. Refresh global viewer (real-time feedback in main window)
            current_frame = self.model.blueline.playhead_frame
            active_fps = self.get_fps()
            tc = self.model.format_timecode(current_frame, active_fps)
            self.on_time_changed(current_frame / active_fps, int(current_frame), tc, True)
            
            # 2. Refresh FX dialog preview if open
            dlg = self.fx_dialogs.get(id(clip))
            if dlg:
                dlg.seek_preview(dlg.sub_timeline.playhead_time)
                
            return True
        return False
        
        # Visual Refresh
        current_frame = self.model.blueline.playhead_frame
        current_time = current_frame / active_fps
        tc = self.model.format_timecode(current_frame, active_fps)
        
        # Note: on_time_changed will internally lock the engine to evaluate
        # We release the locker here before calling it to avoid double-locking if it's the same mutex
        del locker

        self.on_time_changed(current_time, int(current_frame), tc, True)
        
        if was_playing:
            self.toggle_play()

    def _instantiate_source(self, path):
        """Helper to determine the correct C++ backend for a file path, using a cache."""
        if not path or not os.path.exists(path):
            return rocky_core.ColorSource(random.randint(50,200), 50, 100, 255)
            
        # Return from cache if we already opened this heavyweight file
        if path in self.media_source_cache:
            return self.media_source_cache[path]

        lower_path = path.lower()
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        source = None
        if lower_path.endswith(image_extensions):
            source = rocky_core.ImageSource(path)
        else:
            source = rocky_core.VideoSource(path)
            
        self.media_source_cache[path] = source
        return source

    def auto_scroll_playhead(self, abs_x):
        """Ensures the playhead remains visible within the active timeline's scroll area."""
        timeline = self.get_active_timeline()
        if not timeline: return
        
        from PySide6.QtWidgets import QScrollArea
        scroll_area = timeline.findAncestor(QScrollArea) if hasattr(timeline, 'findAncestor') else None
        # Fallback manual parent check
        if not scroll_area:
            p = timeline.parent()
            while p:
                if isinstance(p, QScrollArea):
                    scroll_area = p
                    break
                p = p.parent()
        
        if not scroll_area: return

        viewport_width = scroll_area.viewport().width()
        if viewport_width <= 0: return
            
        scroll_bar = scroll_area.horizontalScrollBar()
        scroll_val = scroll_bar.value()
        rel_x = abs_x - scroll_val
        
        threshold = int(viewport_width * 0.85)
        if rel_x > threshold:
            shift = rel_x - threshold
            scroll_bar.setValue(scroll_val + int(shift))
        elif rel_x < 0:
            new_val = max(0, scroll_val + int(rel_x) - 100)
            scroll_bar.setValue(new_val)

    def sync_hover_to_ruler(self, x_coord):
        """Mirrors mouse position to the timeline ruler. Finds ruler dynamically."""
        timeline = self.get_active_timeline()
        if not timeline: return
        
        # Ruler is usually a sibling in the same layout
        parent = timeline.parent()
        if parent:
            from .ruler import TimelineRuler
            rules = parent.findChildren(TimelineRuler)
            for r in rules:
                r.mouse_x = x_coord
                r.update()
        
    def sync_scroll_to_view(self):
        """Aligns the horizontal scrollbar with the internal timeline view state."""
        timeline = self.get_active_timeline()
        if not timeline: return
        
        from PySide6.QtWidgets import QScrollArea
        p = timeline.parent()
        scroll_area = None
        while p:
            if isinstance(p, QScrollArea):
                scroll_area = p
                break
            p = p.parent()
            
        if not scroll_area: return
        
        scroll_bar = scroll_area.horizontalScrollBar()
        timeline.updateGeometry()
        
        if timeline.pixels_per_second > 0:
            target_value = int(timeline.visible_start_time * timeline.pixels_per_second)
            scroll_bar.blockSignals(True)
            scroll_bar.setValue(target_value)
            scroll_bar.blockSignals(False)

    def sync_view_to_scroll(self, scroll_value):
        """Aligns timeline view state with scrollbar. (Triggered from ScrollArea inside panel)"""
        timeline = self.get_active_timeline()
        if not timeline: return
        timeline.update()
        # Find sibling ruler
        parent = timeline.parent()
        if parent:
            from .ruler import TimelineRuler
            for r in parent.findChildren(TimelineRuler):
                r.update()

def main():
    import signal
    import faulthandler
    
    # 1. Setup Standard Streams for Windowed Mode (No Console)
    # PyInstaller --noconsole/--windowed sets stdout/stderr to None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
        
    # 2. Enable faulthandler only if we have a valid stderr
    # (Though we just ensured we do, checking file validation is safer)
    try:
        faulthandler.enable() # Dump stack trace on crash
    except Exception:
        pass # Skip if still failing

    
    # macOS branding fix
    if sys.platform == "darwin":
        sys.argv[0] = "Rocky Video Editor"
        try:
            import ctypes
            libc = ctypes.CDLL(None)
            libc.setprogname(b"Rocky Video Editor")
        except Exception:
            pass

    # Enable High DPI (Must be before QApplication)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)
    
    # [MACOS FIX] Force Fusion style to Ensure QSS scrollbar rounding works
    from PySide6.QtWidgets import QStyleFactory
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Windows Taskbar Icon Fix (AppUserModelID)
    if os.name == 'nt':
        import ctypes
        myappid = 'antigravity.rocky.videoeditor.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    # Set Taskbar Icon (Windows/Linux)
    # Handle PyInstaller frozen state
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # root
        
    icon_path = os.path.join(base_path, "src", "img", "logo.png")
    
    # Fallback search if not found (e.g. running from different CWD)
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.getcwd(), "src", "img", "logo.png")

    if os.path.exists(icon_path):
        if sys.platform == "darwin":
            # High-Quality macOS Icon with High-DPI (Retina) support
            original = QPixmap(icon_path)
            
            # Use a higher resolution canvas for the icon (512x512 is standard pro size)
            icon_size = 512
            rounded = QPixmap(icon_size, icon_size)
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Visual weight padding (macOS aesthetic)
            padding = icon_size * 0.09
            content_size = icon_size - (padding * 2)
            radius = content_size * 0.175
            
            path = QPainterPath()
            rect = QRectF(padding, padding, content_size, content_size)
            path.addRoundedRect(rect, radius, radius)
            
            # Clip and Draw original with Smooth Scaling
            painter.setClipPath(path)
            painter.drawPixmap(rect.toRect(), original.scaled(int(content_size), int(content_size), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Double-layered Glass Border for premium feel
            painter.setClipping(False)
            
            # Inner subtle glow
            glow_pen = QPen(QColor(255, 255, 255, 40))
            glow_pen.setWidth(6)
            painter.setPen(glow_pen)
            painter.drawPath(path)
            
            # Main Sharp Border
            glass_pen = QPen(QColor(255, 255, 255, 180))
            glass_pen.setWidth(2)
            painter.setPen(glass_pen)
            painter.drawPath(path)
            
            painter.end()
            
            # Set high DPI icon
            icon = QIcon()
            icon.addPixmap(rounded)
            app.setWindowIcon(icon)
        else:
            app.setWindowIcon(QIcon(icon_path))

    model = TimelineModel()
    
    try:
        w = RockyApp(model)
        
        # Connect app exit to cleanup to prevent QThread destruction errors
        app.aboutToQuit.connect(w.cleanup_resources)
        
        w.showMaximized()
        
        ret = app.exec()
        sys.exit(ret)
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

