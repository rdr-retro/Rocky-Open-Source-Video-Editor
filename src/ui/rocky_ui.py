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
from PySide6.QtGui import QImage, QPixmap, QIcon, QPainter, QPainterPath, QPen, QColor, QShortcut
import subprocess
import json
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize, QTimer, QMutex, QMutexLocker, QRectF, QThread, QIODevice, QByteArray
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput, QAudioSource, QAudioSink
import numpy as np
from .core.models import TimelineModel, TrackType, TICKS_PER_FRAME, TICKS_PER_SECOND
from .timeline.simple_timeline import SimpleTimeline
from .components.sidebar import SidebarPanel
from .components.ruler import TimelineRuler
from .components.master_meter import MasterMeterPanel
from .components.viewer import ViewerPanel
from .components.toolbar import RockyToolbar
from ..diagnostics.probe import PROBE
from .dialogs.settings_dialog import SettingsDialog
from .core.styles import MODERN_LABEL
from .panels.asset_tabs import AssetTabsPanel
from .panels.editor_panel import EditorPanel 
from .core import design_tokens as dt
from .components.panels import RockyPanel # New Panel System
 
from ..infrastructure.workers.import_worker import MediaImportWorker 
from ..infrastructure.workers.thumbnail import ThumbnailWorker 
from ..infrastructure.workers.proxy_gen import ProxyWorker 
from .dialogs.welcome_screen import WelcomeScreen

# ... (previous imports)





from .core.utils import get_resource_path, get_rounded_icon, get_platform_display_info
from ..infrastructure.workers.playback_workers import AudioPlayer, AudioWorker, VideoWorker, RenderWorker
from .core.controllers import ProjectController, PlaybackController, MediaController

class RockyApp(QMainWindow):
    """
    Main application window for the Rocky Video Editor.
    Integrates the Python-based UI with the C++ high-performance rendering engine.
    """



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
        self._is_preview_draft = False
        self.cinema_mode = False
        self._ui_state_before_cinema = {}

        if not self.initialize_engine():
            # Fatal error handled inside initialize_engine
            return

        self.check_ffmpeg_availability()

        # Controller Initialization
        self.project_ctrl = ProjectController(self)
        self.playback_ctrl = PlaybackController(self)
        self.media_ctrl = MediaController(self)
        
        self.initialize_ui_components()
        self.setup_event_connections()
        self.setup_shortcuts()
        
        # Set Window Icon
        # Set Window Icon
        icon_path = get_resource_path("icon.png")
        
        if os.path.exists(icon_path):
            self.setWindowIcon(get_rounded_icon(icon_path))
        else:
            # Fallback
            logo_path = get_resource_path("logo.png")
            if os.path.exists(logo_path):
                self.setWindowIcon(get_rounded_icon(logo_path))
        
        # Start the heavy engine thread only after UI is ready (moved to showEvent)
        # self.audio_worker.start() <--- MOVED
        
    def on_show_welcome(self):
        """Manually triggers the welcome screen."""
        welcome = WelcomeScreen(self)
        # Use geometry() which includes position AND size to cover the app
        welcome.setGeometry(self.geometry())
        welcome.show()

    def _show_welcome_screen(self):
        """Helper to show welcome screen after geometry is stable on startup."""
        if not hasattr(self, '_welcome_shown'):
            self._welcome_shown = True
            self.on_show_welcome()

    def showEvent(self, event):
        """Called when the window is shown. Safe place to start threads and splash."""
        super().showEvent(event)
        if hasattr(self, 'audio_worker') and not self.audio_worker.isRunning():
            self.audio_worker.start(QThread.Priority.TimeCriticalPriority)
        if hasattr(self, 'video_worker') and not self.video_worker.isRunning():
            self.video_worker.start(QThread.Priority.HighPriority)
            
        # Show Welcome Screen on Startup (with slight delay for stable geometry)
        QTimer.singleShot(100, self._show_welcome_screen)

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
            
            # VIDEO WORKER: Async rendering to maintain 60fps UI
            self.video_worker = VideoWorker(self.engine, self.engine_lock)
            self.video_worker.frame_ready.connect(self._broadcast_frame)
            
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

        # 1.5 Stop Video Worker
        if hasattr(self, 'video_worker') and self.video_worker is not None:
            self.video_worker.running = False
            self.video_worker.requestInterruption()
            self.video_worker.wait(1000)
            if self.video_worker.isRunning():
                self.video_worker.terminate()
        
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
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)
        
        # 1. Toolbar
        self.toolbar = RockyToolbar(self)
        main_layout.addWidget(self.toolbar)

        # 1.5 Tools Panel (Removed from here, now part of flexible layout)
        # from .tools_panel import ToolsPanel
        # self.tools_panel = ToolsPanel(self)
        # main_layout.addWidget(self.tools_panel)
        
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
        layout.setContentsMargins(0, 0, 0, 0) # Removed 6px margin for maximum screen
        layout.setSpacing(0)
        
        # Create single flexible panel - starts as Viewer

        initial_content = ViewerPanel()
        self.main_panel = RockyPanel(initial_content, title="VISOR DE VIDEO")
        
        # Register initial viewer
        self.register_viewer(initial_content)
        
        # Initialize Viewer with current project resolution
        initial_content.set_project_resolution(self.p_width, self.p_height)
        
        layout.addWidget(self.main_panel, stretch=1)
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
        self.platform_label.setText(get_platform_display_info())

    def setup_event_connections(self):
        """Standardizes global event connections."""
        # 1. Global Toolbar Actions
        self.toolbar.action_open.triggered.connect(self.project_ctrl.on_open)
        self.toolbar.action_save.triggered.connect(self.project_ctrl.on_save)
        self.toolbar.action_save_as.triggered.connect(self.project_ctrl.on_save_as)
        self.toolbar.action_render.triggered.connect(self.on_render)
        self.toolbar.action_preferences.triggered.connect(self.on_settings)
        self.toolbar.action_welcome.triggered.connect(self.on_show_welcome)
        self.toolbar.btn_proxy.clicked.connect(self.media_ctrl.on_proxy_toggle)
        
        # Rotation Actions
        self.toolbar.action_rot_cw.triggered.connect(lambda: self.rotate_selection(90))
        self.toolbar.action_rot_ccw.triggered.connect(lambda: self.rotate_selection(-90))
        self.toolbar.action_rot_180.triggered.connect(lambda: self.rotate_selection(180))
    
        # Zoom Actions
        self.toolbar.action_zoom_in.triggered.connect(self.on_zoom_in)
        self.toolbar.action_zoom_out.triggered.connect(self.on_zoom_out)
        self.toolbar.action_zoom_fit.triggered.connect(self.on_zoom_fit)
        
        # Audit
        self.toolbar.action_audit.triggered.connect(self.on_run_audit)
        
        # Audio Levels
        self.audio_player.level_updated.connect(self.on_audio_levels_received)

    def setup_shortcuts(self):
        """Global key bindings for the application."""
        QShortcut(Qt.Key_Delete, self, self.delete_selection)
        QShortcut(Qt.Key_Space, self, self.toggle_play)
        # Cinema Mode Shortcut
        QShortcut("Ctrl+Alt+C", self, self.toggle_cinema_mode)

    def delete_selection(self):
        """Removes all selected clips from the model."""
        selected_clips = [c for c in self.model.clips if c.selected]
        if not selected_clips:
            return
        
        for clip in selected_clips:
            self.model.remove_clip(clip)
            
        self.on_structure_changed()
        self.status_label.setText(f"Eliminados {len(selected_clips)} clips.")

    def on_settings(self):
        """Muestra el diálogo de preferencias."""
        from .dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def toggle_cinema_mode(self):
        """Toggles a clean, distraction-free viewing mode."""
        self.cinema_mode = not self.cinema_mode
        
        if self.cinema_mode:
            # SAVE STATE
            self._ui_state_before_cinema = {
                "toolbar": self.toolbar.isVisible(),
                "status_bar": self.status_bar.isVisible(),
                "middle_margins": self.middle_section.layout().contentsMargins()
            }
            
            # HIDE DISTRACTIONS
            self.toolbar.hide()
            self.status_bar.hide()
            self.middle_section.layout().setContentsMargins(0, 0, 0, 0)
            
            # Find all RockyPanels and hide non-viewers
            for panel in self.findChildren(RockyPanel):
                if panel.current_type != "Viewer":
                    panel.hide()
                    # Also try to hide parents if they are splitters and now empty
                    parent = panel.parentWidget()
                    while parent and isinstance(parent, QSplitter):
                        # If all widgets in splitter are hidden, hide splitter
                        all_hidden = True
                        for i in range(parent.count()):
                            if parent.widget(i).isVisible():
                                all_hidden = False
                                break
                        if all_hidden:
                            parent.hide()
                        parent = parent.parentWidget()
            
            self.status_label.setText("Modo Cine Activo (Ctrl+Alt+C para salir)")
        else:
            # RESTORE STATE
            self.toolbar.setVisible(self._ui_state_before_cinema.get("toolbar", True))
            self.status_bar.setVisible(self._ui_state_before_cinema.get("status_bar", True))
            margins = self._ui_state_before_cinema.get("middle_margins")
            if margins:
                self.middle_section.layout().setContentsMargins(margins)
            
            # SHOW ALL PANELS (Restore standard visibility)
            for panel in self.findChildren(RockyPanel):
                panel.show()
                parent = panel.parentWidget()
                while parent and isinstance(parent, QSplitter):
                    parent.show()
                    parent = parent.parentWidget()
            
            self.status_label.setText("Ready")

    def rotate_selection(self, angle):
        """Rotates selected clips by given angle."""
        selected = [c for c in self.model.clips if c.selected]
        for c in selected:
            c.transform.rotation = (c.transform.rotation + angle) % 360
        if selected:
            self.on_structure_changed()
    
    def on_render(self):
        """Maneja el proceso de exportación del proyecto."""
        # 1. Elegir destino
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Video", "", "Video Files (*.mp4 *.mov)")
        if not file_path:
            return

        # 2. Configurar el Worker
        total_ticks = self.model.get_max_tick()
        fps = self.get_fps()
        total_frames = int((total_ticks / TICKS_PER_SECOND) * fps)
        
        if total_frames <= 0:
            QMessageBox.warning(self, "Exportación vacía", "La línea de tiempo está vacía.")
            return

        # Setup progress dialog
        progress = QProgressDialog("Renderizando Video...", "Cancelar", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0) # Show immediately
        
        self.render_worker = RenderWorker(
            self.engine, 
            self.engine_lock, 
            file_path, 
            total_frames, 
            fps, 
            self.p_width, 
            self.p_height,
            high_quality=True
        )
        
        self.render_worker.progress.connect(progress.setValue)
        self.render_worker.finished.connect(lambda path: self.status_label.setText(f"Exportación terminada: {path}"))
        self.render_worker.error.connect(lambda err: QMessageBox.critical(self, "Error de Render", err))
        
        # Ensure cleanup on finish
        self.render_worker.finished.connect(progress.close)
        self.render_worker.error.connect(progress.close)
        
        progress.canceled.connect(self.render_worker.requestInterruption)
        
        self.render_worker.start()

    def on_audio_levels_received(self, left, right):
        """Dispatches audio levels to ALL active vumeters."""
        for m in self.master_meter_registry:
            if hasattr(m, 'meter'):
                m.meter.set_levels(left, right)

    def on_clip_fx_clicked(self, clip):
        """Show the Video Event FX panel for the selected clip in the workspace."""
        from .components.panels import RockyPanel
        
        # 1. Select the clip and MARK as FX ACTIVE (Context indicator)
        for c in self.model.clips:
            c.selected = (c == clip)
            c.is_fx_active = (c == clip)
            
        self.on_timeline_selection_changed([clip])
        self.timeline_widget.update() # Visual refresh
        
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
        from .components.panels import RockyPanel
        
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
        from .core.models import ProxyStatus
        
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
        file_filter = "Rocky Project (*.rocky);;All Media (*.mp4 *.mov *.mkv *.avi *.png *.jpg *.jpeg *.bmp *.webp *.mp3 *.wav *.aac *.m4a *.flac);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir Proyecto o Media", "", file_filter)
        if file_path:
            if file_path.lower().endswith('.rocky'): self.project_ctrl.load_project(file_path)
            else: self.media_ctrl.import_media(file_path, self.model.blueline.playhead_tick)

    def import_media(self, file_path, start_tick, preferred_track_idx=-1):
        self.media_ctrl.import_media(file_path, start_tick, preferred_track_idx)


    def _finish_import_logic(self, file_path, project_duration_ticks, source, width, height, rotation, source_fps, start_tick, preferred_track_idx):
        """
        Completes the import process once metadata is available from the background thread.
        ULTRA-FAST: Avoids blocking calls on the UI thread.
        """
        # Cleanup import worker (the sender)
        sender = self.sender()
        if hasattr(self, "_active_workers") and sender in self._active_workers:
            self._active_workers.remove(sender)
            sender.deleteLater()
            
        from .core.models import TimelineClip, TrackType
        
        is_forced_vertical = False
        file_name = os.path.basename(file_path)
        ext = file_name.lower().split('.')[-1]
        

        
    def _safe_remove_worker(self, worker):
        """Standardized safe removal of background threads."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()

    def on_playback_tick(self): self.playback_ctrl.on_playback_tick()
    
    def set_preview_scaling(self, draft_mode: bool):
        """
        Maintains a constant rendering resolution to ensure coordinate stability.
        Only toggles the fast_mode flag for the viewer via internal state.
        """
        # VEGAS STYLE: We never drop the project resolution for the engine
        # because it changes the coordinate system of the clips.
        self._is_preview_draft = draft_mode 
        target_w, target_h = self.p_width, self.p_height
            
        # IDEMPOTENCY: Only send if the target resolution has changed
        if not hasattr(self, '_last_requested_res') or self._last_requested_res != (target_w, target_h):
            self.video_worker.request_resolution(target_w, target_h)
            self._last_requested_res = (target_w, target_h)


    def on_time_changed(self, timestamp, frame_index, timecode, forced, is_scrubbing=False, tick=None):
        """
        Synchronizes the UI state when the playhead is manually moved.
        [SCRUB OPTIMIZATION]: Reduces resolution and skips heavy UI during dragging.
        """
        if self.sidebar and not is_scrubbing:
            self.sidebar.header.set_timecode(timecode)
            for w in self.sidebar.track_widgets:
                w.update()
        elif self.sidebar:
            self.sidebar.header.set_timecode(timecode)
            
        if self.timeline_ruler:
            self.timeline_ruler.update()
        
        # CRITICAL FIX: Preview scaling logic
        # - During scrubbing: Use draft mode (low res)
        # - When scrubbing ends OR when not playing: Use full quality
        # - During playback: Full quality is ensured by toggle_play()
        if is_scrubbing:
            # Actively scrubbing: use draft mode
            self.set_preview_scaling(True)
        elif not self.model.blueline.playing:
            # Not scrubbing AND not playing: ensure HQ immediately
            # This prevents size changes when transitioning from scrub to play
            self.set_preview_scaling(False)

        # If seek is forced while playing, update references
        if forced and self.model.blueline.playing:
             self.playback_start_tick = tick if tick is not None else int(timestamp * TICKS_PER_SECOND)
             self.playback_start_audio_time = self.audio_player.get_processed_us()
             self.audio_player.clear_buffer()
             self.model.audio_samples_rendered = int(timestamp * 44100)

        # Request frame from worker
        target_tick = tick if tick is not None else int(timestamp * TICKS_PER_SECOND)
        self.video_worker.request_frame(target_tick)



    def on_structure_changed(self):
        """Triggered when clips are moved, added, or deleted."""
        # Refresh ALL sidebars in multi-panel layout
        from .components.sidebar import SidebarPanel
        for sidebar in self.findChildren(SidebarPanel):
            sidebar.refresh_tracks()
        self.rebuild_engine()
        
        # Refresh Contextual Panels (FX Panel)
        from .panels.fx_panel import VideoEventFXPanel
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
        self.model.track_heights.append(80)
        
        # Refresh ALL sidebars in multi-panel layout
        from .components.sidebar import SidebarPanel
        for sidebar in self.findChildren(SidebarPanel):
            sidebar.refresh_tracks()

    def _broadcast_frame(self, frame_buffer):
        """Send rendered frame to all registered viewer panels."""
        if frame_buffer is None: return

        try:
            height, width, channels = frame_buffer.shape
            
            # Use current UI state for Draft mode (Fast rendering hint)
            is_draft = getattr(self, '_is_preview_draft', False)
            
            for viewer in self.viewer_registry:
                try:
                    viewer.display_frame(frame_buffer, fast_mode=is_draft)
                except:
                    self.viewer_registry.remove(viewer)
        except Exception as e:
            print(f"Broadcast Error: {e}")


    def register_viewer(self, viewer_panel):
        """Register a viewer panel to receive frame broadcasts and connect controls."""
        if viewer_panel not in self.viewer_registry:
            self.viewer_registry.append(viewer_panel)
            
            # CRITICAL FIX: Set project resolution immediately to prevent shrinking
            # This ensures the viewer uses the correct aspect ratio from the start
            if hasattr(viewer_panel, 'set_project_resolution'):
                viewer_panel.set_project_resolution(self.p_width, self.p_height)
            
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

    def on_zoom_in(self):
        """Triggers zoom in on all active timelines."""
        if hasattr(self, 'timeline_widget'):
             self.timeline_widget.zoom_in()
        # Also sync others if needed
        for tl in self.timeline_registry:
            if tl != self.timeline_widget:
                tl.zoom_in()

    def on_zoom_out(self):
        """Triggers zoom out on all active timelines."""
        if hasattr(self, 'timeline_widget'):
             self.timeline_widget.zoom_out()
        # Also sync others
        for tl in self.timeline_registry:
            if tl != self.timeline_widget:
                tl.zoom_out()

    def on_zoom_fit(self):
        """Triggers Zoom to Fit on all active timelines."""
        if hasattr(self, 'timeline_widget'):
             self.timeline_widget.zoom_to_fit(animate=True)
        for tl in self.timeline_registry:
            if tl != self.timeline_widget:
                tl.zoom_to_fit(animate=True)

    def on_run_audit(self):
        """Runs the Timeline Auditor validation suite with Repair option."""
        from .panels.audit import TimelineAuditor
        auditor = TimelineAuditor(self.model, fps=self.get_fps())
        report = auditor.run()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Auditoría de Timeline")
        msg.setText(report)
        msg.setWindowIcon(self.windowIcon())
        
        # Determine icon based on issues
        has_issues = "❌" in report or "⚠️" in report
        
        if has_issues:
            msg.setIcon(QMessageBox.Warning)
            btn_repair = msg.addButton("Reparar Automáticamente", QMessageBox.ActionRole)
            msg.addButton("Cerrar", QMessageBox.RejectRole)
            
            msg.exec()
            
            if msg.clickedButton() == btn_repair:
                count = auditor.repair()
                QMessageBox.information(self, "Reparación Completa", f"Se han realizado {count} correcciones en la timeline.")
                # Refresh everything
                if self.timeline_widget:
                    self.timeline_widget.update()
        else:
            msg.setIcon(QMessageBox.Information)
            msg.addButton("Cerrar", QMessageBox.AcceptRole)
            msg.exec()


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
            timeline_widget.time_updated.connect(self.on_time_changed)
            timeline_widget.structure_changed.connect(self.on_structure_changed)
            
            # 2. UI Action Signals
            timeline_widget.play_pause_requested.connect(self.toggle_play)
            timeline_widget.view_updated.connect(self.sync_scroll_to_view)
            timeline_widget.hover_x_changed.connect(self.sync_hover_to_ruler)
            timeline_widget.clip_proxy_toggled.connect(self.on_clip_proxy_clicked)
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
        from .components.panels import RockyPanel
        # We find the root widget of the middle section
        root_layout = self.middle_section.layout()
        if root_layout.count() > 0:
            root_widget = root_layout.itemAt(0).widget()
            return RockyPanel.serialize_layout(root_widget)
        return None

    def load_layout_from_workspace(self, layout_data):
        """Clears current layout and reconstructs from data."""
        from .components.panels import RockyPanel
        
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
                    "sizes": [600, 32, 400],  # Viewer, Tools (Collapsed), Timeline
                    "children": [
                        {"type": "panel", "panel_type": "Viewer", "title": "VISOR DE VIDEO"},
                        {"type": "panel", "panel_type": "Tools", "title": "TOOLS"},
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
        from .components.panels import RockyPanel
        from .panels.editor_panel import EditorPanel
        from .panels.fx_panel import VideoEventFXPanel
        
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
            from .components.sidebar import SidebarPanel
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
            from .components.ruler import TimelineRuler
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

        self.p_width = width
        self.p_height = height
        # CRITICAL: Route through worker to avoid race conditions and ensure idempotency
        self.video_worker.request_resolution(width, height)
        self._last_engine_res = (width, height) # Update tracker immediately

        # Enhanced status message with aspect ratio
        self.status_label.setText(f"Resolución: {width}x{height} ({aspect_w}:{aspect_h} - {format_type})")
        
        # Update all viewer panels with new format info
        for viewer in self.viewer_registry:
            if hasattr(viewer, 'set_project_resolution'):
                # Updates both the aspect ratio logic AND the label
                viewer.set_project_resolution(width, height)
            elif hasattr(viewer, 'update_format_label'):
                # Fallback for older viewers (should not happen)
                viewer.update_format_label(width, height)
        
        # Trigger a re-render of the current frame to show the new aspect ratio
        current_frame = self.model.blueline.playhead_frame
        active_fps = self.get_fps()
        tc = self.model.format_timecode(current_frame, active_fps)
        self.on_time_changed(current_frame / active_fps, int(current_frame), tc, True)
        
        if was_playing:
            self.toggle_play()




    def on_thumbnails_finished(self, clip, thumbs): self.media_ctrl.on_thumbnails_finished(clip, thumbs)
    def _on_proxy_finished(self, clip, proxy_path, success): self.media_ctrl._on_proxy_finished(clip, proxy_path, success)
    def update_proxy_button_state(self): self.media_ctrl.update_proxy_button_state()
    def toggle_play(self): self.playback_ctrl.toggle_play()
    def on_playback_rate_changed(self, value): self.playback_ctrl.on_playback_rate_changed(value)
    def on_playback_rate_released(self): self.playback_ctrl.on_playback_rate_released()
    def _instantiate_source(self, path, track_type=None): return self.media_ctrl.instantiate_source(path, track_type)
    def _start_thumbnail_analysis(self, clip): self.media_ctrl._start_thumbnail_analysis(clip)
    def _trigger_proxy_generation(self, clip): self.media_ctrl._trigger_proxy_generation(clip)


            


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
        from .core.models import ProxyStatus

        for clip in self.model.clips:
            # Determine effective path
            path_to_use = clip.file_path
            proxy_active = False
            if use_proxies and clip.proxy_status == ProxyStatus.READY and clip.proxy_path:
                path_to_use = clip.proxy_path
                proxy_active = True
            
            track_type = self.model.track_types[clip.track_index]
            media_source = self._instantiate_source(path_to_use, track_type)
            
            cpp_clip = self.engine.add_clip(
                clip.track_index,
                clip.name,
                int(clip.start_tick),
                int(clip.duration_ticks),
                int(clip.source_offset_ticks),
                media_source
            )
            self.clip_map[clip] = cpp_clip
            
            # --- PROXY SCALE COMPENSATION ---
            # Critical: Proxies are always 540p in height (see FFmpegUtils.get_proxy_command).
            # The clip.transform.scale was calculated for the ORIGINAL source height.
            # If we don't adjust it, a 540p proxy will look shrunk in a 1080p project.
            comp_factor = 1.0
            if proxy_active and hasattr(clip, 'source_height') and clip.source_height > 0:
                comp_factor = float(clip.source_height) / 540.0
            
            # 3. Surface extended properties
            cpp_clip.opacity = clip.start_opacity
            cpp_clip.transform.x = clip.transform.x
            cpp_clip.transform.y = clip.transform.y
            cpp_clip.transform.scale_x = clip.transform.scale_x * comp_factor
            cpp_clip.transform.scale_y = clip.transform.scale_y * comp_factor
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
            cpp_clip.fade_in_ticks = int(clip.fade_in_ticks)
            cpp_clip.fade_out_ticks = int(clip.fade_out_ticks)
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

    def _instantiate_source(self, path, track_type=TrackType.VIDEO):
        """Helper to determine the correct C++ backend for a file path, using a cache."""
        if not path or not os.path.exists(path):
            return rocky_core.ColorSource(random.randint(50,200), 50, 100, 255)
            
        # Return from cache if we already opened this heavyweight file
        if path in self.media_source_cache:
            return self.media_source_cache[path]

        lower_path = path.lower()
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        if track_type == TrackType.VIDEO:
            if lower_path.endswith(image_extensions):
                source = rocky_core.ImageSource(path)
            else:
                source = rocky_core.VideoSource(path)
        else:
            # Use High-Performance Native Audio for ALL audio-only tracks (Starvation Fix)
            # This pre-loads the audio into memory for ultra-fast, jitter-free mixing.
            audio_extensions = ('.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac')
            if lower_path.endswith(audio_extensions):
                source = rocky_core.NativeAudioSource(path)
            else:
                # Fallback for weird formats
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
            from .components.ruler import TimelineRuler
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
            from .components.ruler import TimelineRuler
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
    # Enable High DPI (Must be before QApplication)
    # Qt6 defaults this to True, but we enforce it just in case.
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # CRITICAL FIX: Prevent rounding errors on fractional scaling (e.g. Mac Retina 150%/200%)
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

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

