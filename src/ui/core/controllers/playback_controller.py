from PySide6.QtCore import Qt, QMutexLocker, QTimer
from ..models import TICKS_PER_SECOND

class PlaybackController:
    def __init__(self, main_window):
        self.mw = main_window
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.on_playback_tick)
        self._last_playback_tick = -1

    def toggle_play(self):
        """Toggles the playback state. Restores hidden panels if needed."""
        if hasattr(self.mw, 'middle_section') and self.mw.middle_section.isHidden():
            self.mw.middle_section.show()
            self.mw.status_label.setText("Interfaz restaurada")

        self.mw.model.blueline.playing = not self.mw.model.blueline.playing
        
        # Snap playback rate
        if 0.95 < self.mw.playback_rate < 1.05:
            self.mw.playback_rate = 1.0
            
        self.mw.model.blueline.playback_rate = self.mw.playback_rate
        self.mw.status_label.setText(f"Velocidad: {self.mw.playback_rate:.1f}x")
        
        if self.mw.model.blueline.playing:
            self.playback_timer.setInterval(int(16 / max(0.1, self.mw.playback_rate)))
            self.playback_timer.start()
            
            # Explicitly ensure we reset resolution for playback
            self.mw.set_preview_scaling(False)
            
            self.mw.audio_player.is_playing_safety_flag = True
            
            active_fps = self.mw.get_fps()
            self.mw.playback_start_tick = self.mw.model.blueline.playhead_tick
            self.mw.playback_start_audio_time = self.mw.audio_player.get_processed_us()
            
            start_time = self.mw.model.blueline.playhead_tick / TICKS_PER_SECOND
            self.mw.audio_worker.start_playback(start_time, active_fps, self.mw.playback_rate)
        else:
            self.playback_timer.stop()
            self.mw.audio_worker.stop_playback()
            self.mw.audio_player.is_playing_safety_flag = False
            
            # Restore High Quality
            self.mw.set_preview_scaling(False)
            
            self.mw.video_worker.request_frame(self.mw.model.blueline.playhead_tick)

            # Vegas Style
            if hasattr(self.mw, 'playback_start_tick'):
                tick = self.mw.playback_start_tick
                self.mw.model.blueline.set_playhead_tick(tick)
                
                fps = self.mw.get_fps()
                frame_index = tick / (TICKS_PER_SECOND / fps)
                tc = self.mw.model.format_timecode(tick, fps)
                self.mw.on_time_changed(tick / TICKS_PER_SECOND, int(frame_index), tc, True, tick=tick)
                self.mw.timeline_widget.update()

    def on_playback_rate_changed(self, value):
        new_rate = value / 100.0
        # self.viewer is not directly accessible here, we'll need to update it via registration
        for viewer in self.mw.viewer_registry:
            if hasattr(viewer, 'lbl_rate'):
                viewer.lbl_rate.setText(f"{new_rate:.1f}x")
        
        if self.mw.model.blueline.playing:
            current_audio = self.mw.audio_player.get_processed_us()
            elapsed_us = current_audio - self.mw.playback_start_audio_time
            if elapsed_us < 0: elapsed_us = 0
            elapsed_real_time = elapsed_us / 1_000_000.0
            
            current_tick = self.mw.playback_start_tick + int(elapsed_real_time * TICKS_PER_SECOND * self.mw.playback_rate)
            
            self.mw.playback_start_tick = current_tick
            self.mw.playback_start_audio_time = self.mw.audio_player.get_processed_us()
            
            self.mw.audio_player.clear_buffer()
            self.mw.model.audio_samples_rendered = int((current_tick / TICKS_PER_SECOND) * 44100)
        
        self.mw.playback_rate = new_rate
        self.mw.model.blueline.playback_rate = new_rate

    def on_playback_tick(self):
        if not self.mw.model.blueline.playing:
            return

        try:
            current_audio_time = self.mw.audio_player.get_processed_us()
            elapsed_us = current_audio_time - self.mw.playback_start_audio_time
            if elapsed_us < 0: elapsed_us = 0 
            elapsed_real_time = elapsed_us / 1_000_000.0
        except:
             elapsed_real_time = 0
             
        current_tick = self.mw.playback_start_tick + int(elapsed_real_time * TICKS_PER_SECOND * self.mw.playback_rate)

        if current_tick < self._last_playback_tick and self.mw.playback_rate > 0:
            current_tick = self._last_playback_tick
        self._last_playback_tick = current_tick

        playhead_screen_x = None
        for timeline in self.mw.timeline_registry:
            try:
                x = timeline.update_playhead_position(current_tick, forced=False)
                if playhead_screen_x is None:
                    playhead_screen_x = x
            except:
                pass
        
        if playhead_screen_x is not None:
            self.mw.auto_scroll_playhead(playhead_screen_x)
        
        self.mw.video_worker.request_frame(int(current_tick))
        self.mw.model.blueline.set_playhead_tick(current_tick)
