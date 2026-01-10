from PyQt5.QtCore import Qt
from ..models import TrackType
from .constants import *

class TimelineInteractions:
    def query_interaction_at(self, x: int, y: int, modifiers=None):
        target_clip = self.find_clip_at(x, y)
        if not target_clip:
            return MODE_IDLE, None
            
        track_y_offsets = self._get_track_vertical_offsets()
        track_y = track_y_offsets[target_clip.track_index]
        track_h = self.model.track_heights[target_clip.track_index]
        clip_x = self.timeToScreen(target_clip.start_frame / self.get_fps())
        clip_w = int(target_clip.duration_frames / self.get_fps() * self.pixels_per_second)
        
        is_alt = modifiers and (modifiers & Qt.AltModifier)
        trim_handle_w = RESIZE_MARGIN
        
        if is_alt and (x < clip_x + trim_handle_w or x > clip_x + clip_w - trim_handle_w):
            if x < clip_x + trim_handle_w:
                adj_clip = self._find_clip_ending_at(target_clip.start_frame, target_clip.track_index)
                if adj_clip: return MODE_ROLL_EDIT, adj_clip 
            else:
                adj_clip = self._find_clip_starting_at(target_clip.start_frame + target_clip.duration_frames, target_clip.track_index)
                if adj_clip: return MODE_ROLL_EDIT, target_clip

        if y < track_y + CLIP_HEADER_HEIGHT + TAG_MARGIN:
            if x < clip_x + TAG_MARGIN: return MODE_FADE_IN, target_clip
            if x > clip_x + clip_w - TAG_MARGIN: return MODE_FADE_OUT, target_clip
            
        if x < clip_x + trim_handle_w: return MODE_TRIM_LEFT, target_clip
        if x > clip_x + clip_w - trim_handle_w: return MODE_TRIM_RIGHT, target_clip
        
        if abs(x - (clip_x + clip_w // 2)) < 15:
            target_opacity_y = track_y + CLIP_HEADER_HEIGHT + int((1.0 - target_clip.start_opacity) * (track_h - CLIP_HEADER_HEIGHT))
            if abs(y - target_opacity_y) < 10:
                return MODE_GAIN, target_clip

        return MODE_MOVE, target_clip

    def handle_drag(self, event):
        if not self.active_clip and self.interaction_mode != MODE_PANNING:
            return

        delta_x = event.x() - self.drag_start_x
        delta_y = event.y() - self.interaction_start_y
        delta_f = int((delta_x / self.pixels_per_second) * self.get_fps())
        
        if self.interaction_mode == MODE_MOVE:
            self._handle_move_interaction(event, delta_f)
        elif self.interaction_mode == MODE_TRIM_LEFT:
            self._handle_trim_left_interaction(delta_f)
        elif self.interaction_mode == MODE_TRIM_RIGHT:
            self._handle_trim_right_interaction(delta_f)
        elif self.interaction_mode == MODE_ROLL_EDIT:
            self._handle_roll_interaction(delta_f)
        elif self.interaction_mode == MODE_GAIN:
            self._handle_gain_interaction(delta_y)
        elif self.interaction_mode == MODE_FADE_IN:
            self.active_clip.fade_in_frames = max(0, min(self.active_clip.duration_frames, self.original_fade_in + delta_f))
        elif self.interaction_mode == MODE_FADE_OUT:
            self.active_clip.fade_out_frames = max(0, min(self.active_clip.duration_frames, self.original_fade_out - delta_f))
        elif self.interaction_mode == MODE_PANNING:
            self._handle_panning_interaction(event, delta_x)

    def _handle_move_interaction(self, event, delta_frames):
        new_start = self.original_start + delta_frames
        snap_frame = self.find_snap_frame(new_start, self.active_clip)
        final_start = max(0, snap_frame if snap_frame != -1 else new_start)
        
        self.active_clip.start_frame = final_start
        if self.active_clip.linked_to:
            self.active_clip.linked_to.start_frame = final_start
        
        current_y = 0
        for track_idx, track_h in enumerate(self.model.track_heights):
            if current_y <= event.y() < current_y + track_h:
                original_type = self.model.track_types[self.active_clip.track_index]
                target_type = self.model.track_types[track_idx]
                if original_type == target_type:
                    # Move only the primary clip's track; the linked one usually stays in its domain
                    self.active_clip.track_index = track_idx
                break
            current_y += track_h

    def _handle_trim_left_interaction(self, delta_frames):
        new_start = self.original_start + delta_frames
        snap_frame = self.find_snap_frame(new_start, self.active_clip)
        if snap_frame != -1: new_start = snap_frame
            
        original_end = self.original_start + self.original_duration
        if 0 <= new_start < original_end - 5:
            prev_start = self.active_clip.start_frame
            self.active_clip.start_frame = new_start
            self.active_clip.duration_frames = original_end - new_start
            
            # Sync Trim
            if self.active_clip.linked_to:
                self.active_clip.linked_to.start_frame = new_start
                self.active_clip.linked_to.duration_frames = original_end - new_start
            
            if self.ripple_enabled:
                shift_delta = new_start - prev_start
                for clip in self.model.clips:
                    if clip != self.active_clip and clip.track_index == self.active_clip.track_index:
                        if clip.start_frame > prev_start:
                            clip.start_frame += shift_delta

    def _handle_trim_right_interaction(self, delta_frames):
        new_end = self.original_start + self.original_duration + delta_frames
        snap_frame = self.find_snap_frame(new_end, self.active_clip)
        if snap_frame != -1: new_end = snap_frame
            
        new_duration = max(5, new_end - self.active_clip.start_frame)
        prev_duration = self.active_clip.duration_frames
        self.active_clip.duration_frames = new_duration
        
        # Sync Trim
        if self.active_clip.linked_to:
            self.active_clip.linked_to.duration_frames = new_duration
        
        if self.ripple_enabled:
            shift_delta = new_duration - prev_duration
            if shift_delta != 0:
                for clip in self.model.clips:
                    if clip != self.active_clip and clip.track_index == self.active_clip.track_index:
                        if clip.start_frame >= self.active_clip.start_frame + min(prev_duration, new_duration) - 2:
                            clip.start_frame += shift_delta

    def _handle_roll_interaction(self, delta_frames):
        if not self.active_clip or not self.active_rolling_clip: return
        new_junction = self.original_start + self.original_duration + delta_frames
        min_d = 5
        if (new_junction > self.active_clip.start_frame + min_d and 
            new_junction < self.active_rolling_clip.start_frame + self.active_rolling_clip.duration_frames - min_d):
            self.active_clip.duration_frames = new_junction - self.active_clip.start_frame
            diff = new_junction - self.active_rolling_clip.start_frame
            self.active_rolling_clip.start_frame = new_junction
            self.active_rolling_clip.duration_frames -= diff

    def _handle_gain_interaction(self, delta_y_pixels):
        sensitivity = 100.0
        opacity_delta = -delta_y_pixels / sensitivity
        final_opacity = max(0.0, min(1.0, self.original_start_opacity + opacity_delta))
        self.active_clip.start_opacity = final_opacity
        self.active_clip.end_opacity = final_opacity

    def _handle_panning_interaction(self, event, delta_x_pixels):
        seconds_delta = delta_x_pixels / self.pixels_per_second
        self.visible_start_time = max(0.0, self.visible_start_time - seconds_delta)
        self.drag_start_x = event.x()
        self.view_updated.emit()
