import sys
import os
import random
import time
import rocky_core

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                             QApplication, QScrollArea, QFrame, QMainWindow, QLabel, QFileDialog, QProgressDialog, QMessageBox)
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPainter, QPainterPath, QPen, QColor
import subprocess
from PyQt5.QtCore import Qt, QTimer, QIODevice, QByteArray, QMutex, QMutexLocker, QRectF
from PyQt5.QtMultimedia import QAudioFormat, QAudioOutput, QAudio
import numpy as np

from .timeline import TimelinePanel
from .models import TimelineModel, TrackType
from .sidebar import SidebarPanel
from .ruler import TimelineRuler
from .master_meter import MasterMeterPanel
from .viewer import ViewerPanel
from .toolbar import RockyToolbar
from .settings_dialog import SettingsDialog
from .styles import MODERN_LABEL
from .asset_tabs import AssetTabsPanel

from PyQt5.QtCore import QThread, pyqtSignal

# Infrastructure (Workers)
from ..infrastructure.workers.proxy_gen import ProxyWorker
from ..infrastructure.workers.waveform import WaveformWorker
from ..infrastructure.workers.thumbnail import ThumbnailWorker


class AudioPlayer(QIODevice):
    level_updated = pyqtSignal(float, float)

    def __init__(self, sample_rate=44100, channels=2):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer = bytearray()
        self.mutex = QMutex()
        
        format = QAudioFormat()
        format.setSampleRate(sample_rate)
        format.setChannelCount(channels)
        format.setSampleSize(32)
        format.setCodec("audio/pcm")
        format.setByteOrder(QAudioFormat.LittleEndian)
        format.setSampleType(QAudioFormat.Float)
        
        self.output = QAudioOutput(format)
        # Reduced buffer to 100ms for lower latency response to rate changes
        self.output.setBufferSize(int(sample_rate * channels * 4 * 0.1)) 
        self.open(QIODevice.ReadOnly)
        self.output.start(self)


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
        except:
            pass

        return chunk_bytes

    def bytesAvailable(self):
        locker = QMutexLocker(self.mutex)
        return len(self.buffer) + super().bytesAvailable()

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
        if data is None or data.size == 0:
            return data
        
        current_len = data.size // 2
        if current_len == target_len or target_len <= 0:
            return data
            
        # Indices for interpolation
        old_indices = np.linspace(0, current_len - 1, current_len)
        new_indices = np.linspace(0, current_len - 1, target_len)
        
        # Split, Interp, and Re-interleave
        l_chan = data[0::2]
        r_chan = data[1::2]
        
        new_l = np.interp(new_indices, old_indices, l_chan).astype(np.float32)
        new_r = np.interp(new_indices, old_indices, r_chan).astype(np.float32)
        
        resampled = np.empty(target_len * 2, dtype=np.float32)
        resampled[0::2] = new_l
        resampled[1::2] = new_r
        return resampled

    def run(self):
        self.running = True
        while self.running:
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
                        locker = QMutexLocker(self.player.app_engine_lock) 
                        audio_content = self.engine.render_audio(render_start_time, content_duration)
                        del locker
                        
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
        
        self.player.output.resume()

    def stop_playback(self):
        self.player.output.suspend()

class RenderWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, engine, output_path, total_frames, fps, width, height):
        super().__init__()
        self.engine = engine
        self.output_path = output_path
        self.total_frames = total_frames
        self.fps = fps
        self.width = width
        self.height = height

    def run(self):
        audio_temp_path = self.output_path + ".audio.tmp"
        
        try:
            # 1. Renderizar Audio (Rápido)
            duration = self.total_frames / self.fps
            audio_samples = self.engine.render_audio(0, duration)
            with open(audio_temp_path, 'wb') as f:
                f.write(audio_samples.tobytes())
                
            # 2. Configurar FFmpeg para recibir Video por el pipe
            command = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.width}x{self.height}',
                '-pix_fmt', 'rgba',
                '-r', str(self.fps),
                '-i', '-', # Stdin para video
                '-f', 'f32le',
                '-ar', '44100',
                '-ac', '2',
                '-i', audio_temp_path, # Temp para audio
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                self.output_path
            ]
            
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 3. Renderizar Video Frame a Frame
            for i in range(self.total_frames):
                if self.isInterruptionRequested():
                    process.terminate()
                    break
                    
                timestamp = i / self.fps
                frame_data = self.engine.evaluate(timestamp)
                process.stdin.write(frame_data.tobytes())
                
                if i % 5 == 0:
                    self.progress.emit(int((i / self.total_frames) * 100))
                    
            process.stdin.close()
            process.wait()
            
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
                
            if process.returncode == 0:
                self.finished.emit(self.output_path)
            else:
                err_out = process.stderr.read().decode()
                self.error.emit(f"Fallo en FFmpeg: {err_out}")
                
        except Exception as e:
            self.error.emit(str(e))

class RockyApp(QMainWindow):
    """
    Main application window for the Rocky Video Editor.
    Integrates the Python-based UI with the C++ high-performance rendering engine.
    """

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.engine_lock = QMutex() # Protection for concurrent C++/Python access
        self.playback_rate = 1.0
        self.model.blueline.playback_rate = 1.0
        self.setWindowTitle("Rocky Video Editor")

        self.initialize_engine()

        self.initialize_ui_components()
        self.setup_event_connections()
        
        # Set Window Icon
        icon_path = os.path.join(os.getcwd(), "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(self._get_rounded_icon(icon_path))
        else:
            # Try to find it relative to the script if CWD is different
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path_alt = os.path.join(script_dir, "logo.png")
            if os.path.exists(icon_path_alt):
                self.setWindowIcon(self._get_rounded_icon(icon_path_alt))
        
    def _get_rounded_icon(self, path):
        """On macOS, applies a squircle-style rounding to the icon for better integration."""
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
        
        path = QPainterPath()
        rect = QRectF(padding, padding, content_size, content_size)
        path.addRoundedRect(rect, radius, radius)
        
        painter.setClipPath(path)
        # Draw the original scaled to fit the content area
        painter.drawPixmap(rect.toRect(), original)
        
        # Glass Border (Enhanced)
        painter.setClipping(False)
        glass_pen = QPen(QColor(255, 255, 255, 180)) # More opaque white (180/255)
        glass_pen.setWidth(3) # Slightly thicker
        painter.setPen(glass_pen)
        painter.drawPath(path)
        
        painter.end()
        
        return QIcon(rounded)
        
        # Start the heavy engine thread only after UI is ready (moved to showEvent)
        # self.audio_worker.start() <--- MOVED
        
    def showEvent(self, event):
        """Called when the window is shown. Safe place to start threads."""
        super().showEvent(event)
        if hasattr(self, 'audio_worker') and not self.audio_worker.isRunning():
            print("DEBUG: Starting AudioWorker with High Priority...", flush=True)
            self.audio_worker.start(QThread.HighPriority)


    def initialize_engine(self):
        """Initializes the C++ rendering engine."""
        try:
            print("DEBUG: initializing rocky_core...", flush=True)
            self.engine = rocky_core.RockyEngine()
            self.engine.set_resolution(1280, 720) # Default HD
            print("DEBUG: initializing AudioPlayer...", flush=True)
            self.audio_player = AudioPlayer()
            print("DEBUG: initializing AudioWorker...", flush=True)
            self.audio_worker = AudioWorker(self.engine, self.audio_player, self.model)
            self.audio_player.app_engine_lock = self.engine_lock # Share the lock

        except Exception as e:
            print(f"Critical Error: Could not initialize RockyEngine/Audio: {e}")

    def cleanup_resources(self):
        """Forceful but safe cleanup of threads before app exit."""
        print("DEBUG: Cleaning up resources...", flush=True)
        
         # 1. Stop Audio Worker
        if hasattr(self, 'audio_worker'):
            self.audio_worker.running = False
            self.audio_worker.wait(1000)
            if self.audio_worker.isRunning():
                self.audio_worker.terminate()
            
        # 2. Stop Waveform & Thumbnail Workers
        if hasattr(self, '_waveform_workers'):
            for worker in self._waveform_workers:
                worker.terminate()
                worker.wait(200)
        
        if hasattr(self, '_thumb_workers'):
            for worker in self._thumb_workers:
                worker.terminate()
                worker.wait(200)
        
        # 3. Stop Render Worker if active
        if hasattr(self, 'render_worker') and self.render_worker.isRunning():
            self.render_worker.terminate()
            self.render_worker.wait(500)
            
        print("DEBUG: Cleanup finished.", flush=True)

    def initialize_ui_components(self):
        """Standardizes the interface construction following Vegas Pro aesthetics."""
        self.setWindowTitle("Rocky Video Editor Pro")
        self.resize(1200, 850)
        self.setStyleSheet("background-color: #111111; color: #ffffff;") 
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Toolbar
        self.toolbar = RockyToolbar(self)
        main_layout.addWidget(self.toolbar)
        
        # 2. Main Vertical Splitter (Top Viewers / Bottom Timeline)
        self.main_vertical_splitter = QSplitter(Qt.Vertical)
        
        # Upper section (Asset Explorer, Viewer, Master Meter)
        self.upper_section = self._create_upper_section()
        self.main_vertical_splitter.addWidget(self.upper_section)
        
        # Lower section (Sidebar, Timeline)
        self.lower_section = self._create_lower_section()
        self.main_vertical_splitter.addWidget(self.lower_section)
        
        self.main_vertical_splitter.setStretchFactor(0, 2)  # Upper: MÁS espacio para el visor/assets
        self.main_vertical_splitter.setStretchFactor(1, 1)  # Lower: menos espacio para el timeline por defecto
        
        # Splitter styling (Universal)
        self.main_vertical_splitter.setHandleWidth(1)
        self.main_vertical_splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")


        # Establecer tamaños iniciales (Upper: mayor protagonismo, Lower: más compacto)
        self.main_vertical_splitter.setSizes([650, 350])
        
        main_layout.addWidget(self.main_vertical_splitter)
        
        # 3. Status Bar
        self.status_bar = self._create_status_bar()
        main_layout.addWidget(self.status_bar)

        # Initial data sync
        self.sidebar.refresh_tracks()
        self.on_time_changed(0, 0, "00:00:00;00", True) # Force initial timecode display
        self.rebuild_engine()
        
        # Absolute guarantee: Force a refresh after layout settles
        QTimer.singleShot(200, self.force_initial_render)

    def force_initial_render(self):
        """Ensures every technical number is painted on start."""
        for w in self.sidebar.track_widgets:
            w.update()
        self.timeline_widget.update()
        self.timeline_ruler.update()
        self.on_time_changed(0, 0, "00:00:00;00", True)
        
    def _create_upper_section(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.top_splitter = QSplitter(Qt.Horizontal)
        
        self.asset_tabs = AssetTabsPanel()
        self.viewer = ViewerPanel()
        self.master_meter = MasterMeterPanel()
        
        self.top_splitter.addWidget(self.asset_tabs)
        self.top_splitter.addWidget(self.viewer)
        self.top_splitter.addWidget(self.master_meter)
        
        self.top_splitter.setStretchFactor(0, 2) # Asset Tabs (General/Media) - More prominent
        self.top_splitter.setStretchFactor(1, 1) # Viewer
        self.top_splitter.setStretchFactor(2, 0) # Master Meter

        # Set explicit initial hierarchy (Asset Tabs: 600px, Viewer: 500px, Meter: 100px)
        self.top_splitter.setSizes([600, 500, 100])
        
        layout.addWidget(self.top_splitter)
        return container

    def _create_lower_section(self):
        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = SidebarPanel(self.model)
        
        timeline_container = QWidget()
        layout = QVBoxLayout(timeline_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.timeline_widget = TimelinePanel(self.model)
        self.sidebar.timeline = self.timeline_widget 
        self.timeline_ruler = TimelineRuler(self.timeline_widget)
        self.timeline_ruler.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.timeline_ruler, 0, Qt.AlignTop)
        
        self.timeline_scroll_area = QScrollArea()
        self.timeline_scroll_area.setWidgetResizable(True)
        self.timeline_scroll_area.setWidget(self.timeline_widget)
        self.timeline_scroll_area.setFrameShape(QFrame.NoFrame)  # Sin borde
        self.timeline_scroll_area.setContentsMargins(0, 0, 0, 0)
        self.timeline_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.timeline_scroll_area.setStyleSheet("""
            QScrollArea { 
                border: 0px; 
                background-color: #242424;
                margin: 0px;
                padding: 0px;
            }
        """)
        self.timeline_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.timeline_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.timeline_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.timeline_scroll_area.viewport().setContentsMargins(0, 0, 0, 0)
        self.timeline_scroll_area.viewport().setAutoFillBackground(True)
        self.timeline_scroll_area.viewport().setStyleSheet("background-color: #242424; border: none;")
        layout.addWidget(self.timeline_scroll_area, 1) # stretch 1
        
        splitter.addWidget(self.sidebar)
        splitter.addWidget(timeline_container)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1a1a1a;
            }
        """)
        return splitter

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
            
            # Format: "macOS 26.2 | 10 cores | 16 GB | Apple GPU | Metal"
            info_text = (f"{platform.os_name} {platform.os_version} | "
                        f"{platform.cpu_cores} cores | "
                        f"{platform.total_ram_mb // 1024} GB | "
                        f"{platform.gpu_info.vendor} | "
                        f"{backend}")
            
            self.platform_label.setText(info_text)
            
        except Exception as e:
            self.platform_label.setText(f"Platform: Unknown ({str(e)})")

    def setup_event_connections(self):
        """Standardizes the connection logic."""
        # Timeline -> Side UI synchronization
        self.timeline_widget.time_updated.connect(self.on_time_changed)
        
        # Scroll synchronization (Sidebar <-> Timeline)
        self.timeline_scroll_area.verticalScrollBar().valueChanged.connect(
            self.sidebar.scroll.verticalScrollBar().setValue
        )
        self.sidebar.scroll.verticalScrollBar().valueChanged.connect(
            self.timeline_scroll_area.verticalScrollBar().setValue
        )
        
        # Playback Engine
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.on_playback_tick)
        self.playback_timer.start(16) 
        
        # Signals
        self.timeline_widget.play_pause_requested.connect(self.toggle_play)
        self.timeline_widget.view_updated.connect(self.sync_scroll_to_view)
        self.timeline_scroll_area.horizontalScrollBar().valueChanged.connect(self.sync_view_to_scroll)
        self.timeline_widget.track_addition_requested.connect(self.sidebar.add_track)
        self.timeline_widget.structure_changed.connect(self.on_structure_changed)
        self.timeline_widget.hover_x_changed.connect(self.sync_hover_to_ruler)

        # Toolbar Actions
        self.toolbar.btn_open.clicked.connect(self.on_open)
        self.toolbar.btn_save.clicked.connect(self.on_save)
        self.toolbar.btn_render.clicked.connect(self.on_render)
        self.toolbar.btn_settings.clicked.connect(self.on_settings)
        self.toolbar.btn_proxy.clicked.connect(self.on_proxy_toggle)
        
        # Audio Master
        self.master_meter.fader.valueChanged.connect(self.on_master_gain_changed)
        self.audio_player.level_updated.connect(self.master_meter.meter.set_levels)
        
        # Viewer Controls
        self.viewer.btn_rewind.clicked.connect(lambda: self.timeline_widget.update_playhead_to_x(0))
        self.viewer.btn_play_pause.clicked.connect(self.toggle_play)
        self.viewer.btn_fullscreen.clicked.connect(self._toggle_fullscreen_viewer)
        self.viewer.slider_rate.valueChanged.connect(self.on_playback_rate_changed)
        self.viewer.slider_rate.sliderReleased.connect(self.on_playback_rate_released)


        # Asset Tabs
        self.asset_tabs.resolution_changed.connect(self.on_resolution_changed)


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
            "All Media (*.mp4 *.mov *.mkv *.avi *.png *.jpg *.jpeg *.bmp *.webp *.mp3 *.wav *.aac *.m4a *.flac);;"
            "Video Files (*.mp4 *.mov *.mkv *.avi);;"
            "Audio Files (*.mp3 *.wav *.aac *.m4a *.flac);;"
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;"
            "All Files (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(self, "Importar Media", "", file_filter)
        
        if file_path:
            start_frame = self.model.blueline.playhead_frame
            self.import_media(file_path, start_frame)
            self.status_label.setText(f"Importado: {os.path.basename(file_path)}")

    def import_media(self, file_path, start_frame, preferred_track_idx=-1):
        """
        Smart media importer that automates track creation and clip linking.
        Following Sony Vegas Pro workflow: Video creates paired tracks.
        """
        from .models import TimelineClip, TrackType
        
        file_name = os.path.basename(file_path)
        ext = file_name.lower().split('.')[-1]
        
        # Check if project was empty before this import to trigger auto-zoom
        was_empty = (len(self.model.clips) == 0)
        
        is_audio = ext in ["mp3", "wav", "aac", "m4a", "flac"]
        is_image = ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
        is_video = not is_audio and not is_image
        
        # Determine real duration for Video/Audio
        fps = self.timeline_widget.get_fps()
        duration = 150 # Default 5s for images
        
        if not is_image:
            temp_src = self._instantiate_source(file_path)
            real_dur_sec = temp_src.get_duration()
            if real_dur_sec > 0:
                duration = int(real_dur_sec * fps)
            elif real_dur_sec == 0: # Could be an error or empty file
                duration = 300 # Fallback 10s
        
        if is_video:
            # 1. Video Track
            v_track = preferred_track_idx if (preferred_track_idx != -1 and self.model.track_types[preferred_track_idx] == TrackType.VIDEO) else -1
            if v_track == -1:
                # Find first video track
                for i, t in enumerate(self.model.track_types):
                    if t == TrackType.VIDEO: v_track = i; break
            if v_track == -1:
                self.sidebar.add_track(TrackType.VIDEO)
                v_track = len(self.model.track_types) - 1
            
            v_clip = TimelineClip(file_name, start_frame, duration, v_track)
            v_clip.file_path = file_path
            
            # 2. Audio Track (Vegas Pro style: usually BELOW the video track)
            a_track = -1
            for i in range(v_track + 1, len(self.model.track_types)):
                if self.model.track_types[i] == TrackType.AUDIO:
                    a_track = i; break
            if a_track == -1:
                self.sidebar.add_track(TrackType.AUDIO)
                a_track = len(self.model.track_types) - 1
            
            a_clip = TimelineClip(f"[Audio] {file_name}", start_frame, duration, a_track)
            a_clip.file_path = file_path
            
            v_clip.linked_to = a_clip
            a_clip.linked_to = v_clip
            
            self.model.add_clip(v_clip)
            self.model.add_clip(a_clip)
            
            # Start asynchronous analysis
            self._start_waveform_analysis(a_clip)
            self._start_thumbnail_analysis(v_clip)
            
            # Start Proxy Generation
            self._trigger_proxy_generation(v_clip)
            
        else:
            t_idx = preferred_track_idx if preferred_track_idx != -1 else -1
            if t_idx == -1:
                search_type = TrackType.AUDIO if is_audio else TrackType.VIDEO
                for i, t in enumerate(self.model.track_types):
                    if t == search_type: t_idx = i; break
            
            if t_idx == -1:
                self.sidebar.add_track(TrackType.AUDIO if is_audio else TrackType.VIDEO)
                t_idx = len(self.model.track_types) - 1
            
            clip = TimelineClip(file_name, start_frame, duration, t_idx)
            clip.file_path = file_path
            self.model.add_clip(clip)
            
            if is_audio:
                self._start_waveform_analysis(clip)
            else:
                self._start_thumbnail_analysis(clip)
        
        self.timeline_widget.update()
        self.on_structure_changed()
        
        if was_empty:
             # Trigger cinematic "Zoom to Fit" animation
             QTimer.singleShot(100, self.timeline_widget.zoom_to_fit)
             
        return duration
        
    def on_save(self):
        self.status_label.setText("Proyecto guardado.")

    def on_render(self):
        """
        Inicia el proceso de exportación final del video con selección de parámetros pro.
        """
        from .export_dialog import ExportDialog
        dlg = ExportDialog(self)
        if not dlg.exec_():
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

        active_fps = self.timeline_widget.get_fps()
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
        
        # Crear y configurar Worker con la resolución elegida
        self.render_worker = RenderWorker(self.engine, output_path, total_frames, active_fps, render_w, render_h)

        self.render_worker.progress.connect(self.prog_dialog.setValue)
        self.render_worker.finished.connect(self._on_render_finished)
        self.render_worker.error.connect(self._on_render_error)
        
        self.prog_dialog.canceled.connect(self.render_worker.requestInterruption)
        
        self.render_worker.start()
        self.status_label.setText("Renderizando...")

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
        dlg.exec_()

    def toggle_play(self):
        """Toggles the playback state of the project blueline."""
        self.model.blueline.playing = not self.model.blueline.playing
        # If it's very close to 1.0, snap it
        if 0.95 < self.playback_rate < 1.05:
            self.playback_rate = 1.0
            
        self.model.blueline.playback_rate = self.playback_rate
        self.status_label.setText(f"Velocidad: {self.playback_rate:.1f}x")
        
        # Update playback timer interval if playing.
        if self.model.blueline.playing:
            self.playback_timer.setInterval(int(16 / max(0.1, self.playback_rate)))
            
            active_fps = self.timeline_widget.get_fps()
            # Capturamos el estado inicial para el Reloj Maestro
            self.playback_start_frame = self.model.blueline.playhead_frame
            self.playback_start_wall_time = time.perf_counter()
            
            start_time = self.model.blueline.playhead_frame / active_fps
            self.audio_worker.start_playback(start_time, active_fps, self.playback_rate)
        else:
            self.audio_worker.stop_playback()


    def on_playback_rate_changed(self, value):
        """Dynamic playback speed control (Scrubbing/Shuttle)."""
        new_rate = value / 100.0
        self.viewer.lbl_rate.setText(f"{new_rate:.1f}x")
        
        if self.model.blueline.playing:
            # Re-anclamos el reloj maestro para evitar saltos al cambiar la velocidad
            active_fps = self.timeline_widget.get_fps()
            elapsed_real_time = time.perf_counter() - self.playback_start_wall_time
            current_frame = self.playback_start_frame + (elapsed_real_time * active_fps * self.playback_rate)
            
            self.playback_start_frame = current_frame
            self.playback_start_wall_time = time.perf_counter()
            
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

        active_fps = self.timeline_widget.get_fps()
        
        # RELOJ MAESTRO: Calculamos el tiempo transcurrido real desde el inicio
        elapsed_real_time = time.perf_counter() - self.playback_start_wall_time
        current_frame = self.playback_start_frame + (elapsed_real_time * active_fps * self.playback_rate)


        
        # 1. Synchronize UI (Playhead and Timeline)
        playhead_screen_x = self.timeline_widget.update_playhead_position(current_frame)
        self.auto_scroll_playhead(playhead_screen_x)
        
        # 2. Synchronize Engine (Atomic Evaluation)
        engine_timestamp = current_frame / active_fps
        try:
            # Video (GUI Thread)
            rendered_frame = self.engine.evaluate(engine_timestamp)
            self.viewer.display_frame(rendered_frame)
            
            # NOTE: Audio is now handled by AudioWorker thread to ensure ZERO drops
            
        except Exception as rendering_error:
            print(f"Playback Error: Render evaluation failed: {rendering_error}")
            self.toggle_play() # Halt playback on critical failure

    def on_time_changed(self, timestamp, frame_index, timecode, forced):
        """
        Synchronizes the UI state when the playhead is manually moved.
        """
        # Actualizar el timecode gigante en el sidebar
        self.sidebar.header.set_timecode(timecode)
        
        # Forzamos el repintado inmediato de toda la barra lateral
        for w in self.sidebar.track_widgets:
            w.repaint()
        
        self.timeline_ruler.update() # Ensure ruler handle moves
        
        locker = QMutexLocker(self.engine_lock)
        rendered_frame = self.engine.evaluate(timestamp)
        del locker
        
        self.viewer.display_frame(rendered_frame)


    def on_structure_changed(self):
        """Triggered when clips are moved, added, or deleted."""
        self.sidebar.refresh_tracks()
        self.rebuild_engine()

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
        print(f"Project Resolution Changed: {width}x{height}")
        
        # Stop playback to avoid engine contention during resolution swap
        was_playing = self.model.blueline.playing
        if was_playing:
            self.toggle_play()

        locker = QMutexLocker(self.engine_lock)
        self.engine.set_resolution(width, height)
        del locker

        self.status_label.setText(f"Resolución: {width}x{height}")
        
        # Trigger a re-render of the current frame to show the new aspect ratio
        current_frame = self.model.blueline.playhead_frame
        active_fps = self.timeline_widget.get_fps()
        tc = self.model.format_timecode(current_frame, active_fps)
        self.on_time_changed(current_frame / active_fps, int(current_frame), tc, True)
        
        if was_playing:
            self.toggle_play()



    def _start_waveform_analysis(self, clip):
        """Launches a background thread to calculate the real audio waveform."""
        clip.waveform_computing = True
        worker = WaveformWorker(clip, clip.file_path)
        worker.finished.connect(self.on_waveform_finished)
        # We keep a reference to prevent GC
        if not hasattr(self, "_waveform_workers"): self._waveform_workers = []
        self._waveform_workers.append(worker)
        worker.start()

    def _start_thumbnail_analysis(self, clip):
        """Launches a background thread to extract keyframe thumbnails."""
        clip.thumbnails_computing = True
        worker = ThumbnailWorker(clip, clip.file_path)
        worker.finished.connect(self.on_thumbnails_finished)
        if not hasattr(self, "_thumb_workers"): self._thumb_workers = []
        self._thumb_workers.append(worker)
        worker.start()

    def on_waveform_finished(self, clip, peaks):
        """Callback when the C++ engine finishes scanning the audio file."""
        clip.waveform = peaks
        clip.waveform_computing = False
        self.timeline_widget.update()
        
        # Cleanup worker safely
        if hasattr(self, "_waveform_workers"):
            # Find the sender worker
            sender = self.sender()
            if sender in self._waveform_workers:
                self._waveform_workers.remove(sender)
                sender.deleteLater()




    def on_thumbnails_finished(self, clip, thumbs):
        """Callback when the C++ engine finishes extracting thumbnails."""
        clip.thumbnails = thumbs
        clip.thumbnails_computing = False
        self.timeline_widget.update()
        if hasattr(self, "_thumb_workers"):
            self._thumb_workers = [w for w in self._thumb_workers if w.clip != clip]

    def _trigger_proxy_generation(self, clip):
        """Starts the proxy generation process for a clip."""
        from .models import ProxyStatus
        clip.proxy_status = ProxyStatus.GENERATING
        self.update_proxy_button_state()
        
        worker = ProxyWorker(clip, clip.file_path)
        worker.finished.connect(self._on_proxy_finished)
        
        if not hasattr(self, "_proxy_workers"): self._proxy_workers = []
        self._proxy_workers.append(worker)
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
            
        # Cleanup
        if hasattr(self, "_proxy_workers"):
             self._proxy_workers = [w for w in self._proxy_workers if w is not self.sender()]

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

    def on_proxy_toggle(self):
        """User clicked the Global Proxy Toggle."""
        use_proxies = self.toolbar.btn_proxy.isChecked()
        print(f"Global Proxy Mode: {use_proxies}")
        self.toolbar.set_proxy_status_color('black') # Recalculate color
        self.update_proxy_button_state()
        self.rebuild_engine()

    def closeEvent(self, event):
        """Graceful shutdown sequence for threads and resources."""
        print("Shutting down Rocky Video Editor...")
        
        # 1. Stop Audio Worker
        if hasattr(self, 'audio_worker'):
            self.audio_worker.running = False
            self.audio_worker.wait(1000)
            
        # 2. Stop Waveform & Thumbnail Workers
        if hasattr(self, '_waveform_workers'):
            for worker in self._waveform_workers:
                worker.terminate()
                worker.wait(200)
        
        if hasattr(self, '_thumb_workers'):
            for worker in self._thumb_workers:
                worker.terminate()
                worker.wait(200)
        
        # 3. Stop Render Worker if active
        if hasattr(self, 'render_worker') and self.render_worker.isRunning():
            self.render_worker.terminate()
            self.render_worker.wait(500)
            
        event.accept()

    def rebuild_engine(self):
        """
        Deep synchronization between the high-level Python models and the 
        low-level C++ rendering core. 
        """
        self.engine.clear()
        active_fps = self.timeline_widget.get_fps()
        self.engine.set_fps(active_fps)
        
        # Sync Master Gain
        initial_gain = self.master_meter.fader.value() / 75.0
        self.engine.set_master_gain(initial_gain)
        
        # 1. Sync Tracks
        for track_type in self.model.track_types:
            cpp_track_type = rocky_core.VIDEO if track_type == TrackType.VIDEO else rocky_core.AUDIO
            self.engine.add_track(cpp_track_type)
            
        # 2. Sync Clips and Media Sources
        use_proxies = self.toolbar.btn_proxy.isChecked()
        print(f"DEBUG: Rebuilding Engine. Proxies Enabled: {use_proxies}")

        for clip in self.model.clips:
            from .models import ProxyStatus
            
            # Determine effective path
            path_to_use = clip.file_path
            if use_proxies and clip.proxy_status == ProxyStatus.READY and clip.proxy_path:
                print(f"DEBUG: Using Proxy for {clip.name} -> {clip.proxy_path}")
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
            
            # 3. Surface extended properties
            cpp_clip.opacity = clip.start_opacity
            cpp_clip.fade_in_frames = clip.fade_in_frames
            cpp_clip.fade_out_frames = clip.fade_out_frames
            cpp_clip.fade_in_type = rocky_core.FadeType(clip.fade_in_type.value)
            cpp_clip.fade_out_type = rocky_core.FadeType(clip.fade_out_type.value)
        
        # Visual Refresh
        # Visual Refresh
        current_frame = self.model.blueline.playhead_frame
        current_time = current_frame / active_fps
        tc = self.model.format_timecode(current_frame, active_fps)
        self.on_time_changed(current_time, int(current_frame), tc, True)

    def _instantiate_source(self, path):
        """Helper to determine the correct C++ backend for a file path."""
        if not path or not os.path.exists(path):
            return rocky_core.ColorSource(random.randint(50,200), 50, 100, 255)
            
        lower_path = path.lower()
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        if lower_path.endswith(image_extensions):
            return rocky_core.ImageSource(path)
            
        return rocky_core.VideoSource(path)

    def auto_scroll_playhead(self, abs_x):
        """
        Ensures the playhead remains visible without jarring jumps.
        Implements 'Sticky Edge' scrolling: when the cursor reaches 85% of the view,
        the timeline starts sliding smoothly under it.
        """
        viewport_width = self.timeline_scroll_area.viewport().width()
        if viewport_width <= 0:
            return
            
        scroll_bar = self.timeline_scroll_area.horizontalScrollBar()
        scroll_val = scroll_bar.value()
        rel_x = abs_x - scroll_val
        
        # Sticky threshold: 85% of the screen
        threshold = int(viewport_width * 0.85)
        
        if rel_x > threshold:
            # Shift the scrollbar precisely to keep the cursor at the threshold
            shift = rel_x - threshold
            scroll_bar.setValue(scroll_val + int(shift))
            
        elif rel_x < 0:
            # If playhead is before the view (e.g. after a manual jump), center it
            new_val = max(0, scroll_val + int(rel_x) - 100)
            scroll_bar.setValue(new_val)

    def sync_hover_to_ruler(self, x_coord):
        """Mirrors the mouse position to the timeline ruler for temporal reference."""
        self.timeline_ruler.mouse_x = x_coord
        self.timeline_ruler.update()
        
    def sync_scroll_to_view(self):
        """Aligns the horizontal scrollbar with the internal timeline view state."""
        scroll_bar = self.timeline_scroll_area.horizontalScrollBar()
        self.timeline_widget.updateGeometry()
        
        if self.timeline_widget.pixels_per_second > 0:
            target_value = int(self.timeline_widget.visible_start_time * self.timeline_widget.pixels_per_second)
            scroll_bar.blockSignals(True)
            scroll_bar.setValue(target_value)
            scroll_bar.blockSignals(False)

    def sync_view_to_scroll(self, scroll_value):
        """Aligns the internal timeline view state with the scrollbar position."""
        if self.timeline_widget.pixels_per_second > 0:
            self.timeline_widget.visible_start_time = scroll_value / float(self.timeline_widget.pixels_per_second)
            self.timeline_widget.update()
            self.timeline_ruler.update()

if __name__ == "__main__":
    import signal
    import faulthandler
    faulthandler.enable() # Dump stack trace on crash

    print("DEBUG: Initializing QApplication...", flush=True)
    
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
    
    # Set Application Identity
    app.setApplicationName("Rocky Video Editor")
    app.setApplicationDisplayName("Rocky Video Editor")
    app.setOrganizationName("Antigravity")
    
    # Windows Taskbar Icon Fix (AppUserModelID)
    if os.name == 'nt':
        import ctypes
        myappid = 'antigravity.rocky.videoeditor.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    # Set Taskbar Icon (Windows/Linux)
    icon_path = os.path.join(os.getcwd(), "logo.png")
    if not os.path.exists(icon_path):
        # Fallback to relative path
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(script_dir, "logo.png")

    if os.path.exists(icon_path):
        if sys.platform == "darwin":
            # Round for macOS Dock and add padding for visual consistency
            original = QPixmap(icon_path)
            size = original.size()
            rounded = QPixmap(size)
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # visual weight padding
            padding = size.width() * 0.09
            content_size = size.width() - (padding * 2)
            
            path = QPainterPath()
            rect = QRectF(padding, padding, content_size, content_size)
            path.addRoundedRect(rect, content_size*0.175, content_size*0.175)
            
            painter.setClipPath(path)
            painter.drawPixmap(rect.toRect(), original)
            
            # Glass Border (Enhanced)
            painter.setClipping(False)
            glass_pen = QPen(QColor(255, 255, 255, 180)) # More opaque white
            glass_pen.setWidth(3) # Slightly thicker
            painter.setPen(glass_pen)
            painter.drawPath(path)
            
            painter.end()
            app.setWindowIcon(QIcon(rounded))
        else:
            app.setWindowIcon(QIcon(icon_path))

    print("DEBUG: Creating TimelineModel...", flush=True)
    model = TimelineModel()
    
    print("DEBUG: Creating RockyApp...", flush=True)
    try:
        w = RockyApp(model)
        
        # Connect app exit to cleanup to prevent QThread destruction errors
        app.aboutToQuit.connect(w.cleanup_resources)
        
        print("DEBUG: Showing Window...", flush=True)
        w.show()
        
        print("DEBUG: Entering Event Loop...", flush=True)
        ret = app.exec_()
        sys.exit(ret)
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

