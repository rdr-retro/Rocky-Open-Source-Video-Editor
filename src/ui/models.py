from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

class TrackType(Enum):
    """Enumeration of supported timeline track domains."""
    VIDEO = 1
    AUDIO = 2

class FadeType(Enum):
    """Interpolation algorithms for opacity and volume envelopes."""
    LINEAR = 0
    FAST = 1
    SLOW = 2
    SMOOTH = 3
    SHARP = 4

class ProxyStatus(Enum):
    NONE = 0
    GENERATING = 1
    READY = 2
    ERROR = 3

class TimelineClip:
    """
    Representation of a media segment on the timeline.
    Holds spatial (track), temporal, and aesthetic (opacity/fade) properties.
    """
    def __init__(self, name: str, start_frame: int, duration_frames: int, track_index: int):
        self.name = name
        self.start_frame = start_frame
        self.duration_frames = duration_frames
        self.track_index = track_index
        
        # Source Mapping
        self.source_offset_frames = 0
        self.media_source_id = None
        self.file_path = None
        self.proxy_path = None
        self.proxy_status = ProxyStatus.NONE
        self.use_proxy = False
        
        # Aesthetic Envelopes
        self.start_opacity = 1.0
        self.end_opacity = 1.0
        self.fade_in_frames = 0
        self.fade_out_frames = 0
        self.fade_in_type = FadeType.LINEAR
        self.fade_out_type = FadeType.LINEAR
        # Keyframe nodes: list of [frame_offset, value, curve_type]
        self.opacity_nodes = [] 
        
        # Linking Logic
        self.linked_to: Optional['TimelineClip'] = None
        
        # View Interaction State
        self.selected = False
        
        # Audio Analysis Cache (Vegas Style)
        self.waveform = []
        self.waveform_computing = False

        # Physical Previews (Start, Mid, End)
        self.thumbnails = [] # List of QImage or QPixmap
        self.thumbnails_computing = False
        
    def copy(self) -> 'TimelineClip':
        """Deep copy of the clip for split or duplication operations."""
        new_clip = TimelineClip(self.name, self.start_frame, self.duration_frames, self.track_index)
        new_clip.start_opacity = self.start_opacity
        new_clip.end_opacity = self.end_opacity
        new_clip.fade_in_frames = self.fade_in_frames
        new_clip.fade_out_frames = self.fade_out_frames
        new_clip.fade_in_type = self.fade_in_type
        new_clip.fade_out_type = self.fade_out_type
        new_clip.source_offset_frames = self.source_offset_frames
        new_clip.media_source_id = self.media_source_id
        new_clip.file_path = self.file_path
        new_clip.proxy_path = self.proxy_path
        new_clip.proxy_status = self.proxy_status
        new_clip.use_proxy = self.use_proxy
        new_clip.opacity_nodes = [n[:] for n in self.opacity_nodes]
        new_clip.selected = self.selected
        new_clip.linked_to = self.linked_to
        new_clip.waveform = self.waveform[:]
        new_clip.waveform_computing = self.waveform_computing
        new_clip.thumbnails = self.thumbnails[:]
        new_clip.thumbnails_computing = self.thumbnails_computing
        return new_clip

class BlueLine:
    """
    Represents the project-wide master temporal controller (The Playhead).
    Handles playback state and current cursor position.
    """
    def __init__(self):
        self.playhead_frame = 0.0
        self.playing = False
        self.color = "#00aaff" # Signature Rocky Blue
        
    def set_playhead_frame(self, frame: float):
        """Sets the precise absolute frame index."""
        self.playhead_frame = max(0.0, float(frame))

class TimelineModel:
    """
    Central data repository for the project structure.
    Manages tracks, clips, and the project playhead.
    """
    def __init__(self):
        self.clips: List[TimelineClip] = []
        self.track_heights: List[int] = []
        self.track_types: List[TrackType] = []
        self.selected_tracks: List[int] = [] # Track selection state
        self.blueline = BlueLine()
        self.audio_samples_rendered = 0
        self.layout_revision = 0
        
    def remove_track(self, index: int):
        """Deletes a track and its clips, shifting subsequent track indices."""
        if 0 <= index < len(self.track_types):
            self.track_types.pop(index)
            self.track_heights.pop(index)
            
            # Remove clips on the deleted track
            self.clips = [c for c in self.clips if c.track_index != index]
            
            # Shift track_index for clips on subsequent tracks
            for clip in self.clips:
                if clip.track_index > index:
                    clip.track_index -= 1
            
            # Update selected tracks
            new_selection = []
            for t_idx in self.selected_tracks:
                if t_idx == index: continue
                elif t_idx > index: new_selection.append(t_idx - 1)
                else: new_selection.append(t_idx)
            self.selected_tracks = new_selection
            
            self.layout_revision += 1
        
    def add_clip(self, clip: TimelineClip):
        """Appends a clip and increments state revision."""
        self.clips.append(clip)
        self.layout_revision += 1
        
    def remove_clip(self, clip: TimelineClip):
        """Removes a clip and increments state revision."""
        if clip in self.clips:
            self.clips.remove(clip)
            self.layout_revision += 1


    def get_max_frame(self) -> int:
        """Calculates the end boundary of the last clip in the project."""
        max_f = 0
        for clip in self.clips:
            end = clip.start_frame + clip.duration_frames
            if end > max_f:
                max_f = end
        return int(max_f)

    @staticmethod
    def format_timecode(frame: float, fps: float) -> str:
        """Standard SMPTE-like timecode formatting."""
        total_seconds = frame / fps
        h = int(total_seconds // 3600)
        m = int((total_seconds // 60) % 60)
        s = int(total_seconds % 60)
        f = int(frame % fps)
        return f"{h:02}:{m:02}:{s:02};{f:02}"
