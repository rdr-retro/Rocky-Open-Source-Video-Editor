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

class TimeFormat(Enum):
    """
    Display format for the Time Ruler.
    """
    TIMECODE = 0 # HH:MM:SS:FF
    SECONDS = 1  # 120.5s
    FRAMES = 2   # 3500



@dataclass
class TimelineMarker:
    """
    A named point in absolute time.
    """
    frame: int
    name: str = ""
    color: str = "#FF9900" # Orange default

@dataclass
class Transform:
    """Spatial properties for a clip."""
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    anchor_x: float = 0.5
    anchor_y: float = 0.5

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "rotation": self.rotation,
            "anchor_x": self.anchor_x,
            "anchor_y": self.anchor_y
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Transform':
        return cls(
            data.get("x", 0.0),
            data.get("y", 0.0),
            data.get("scale_x", 1.0),
            data.get("scale_y", 1.0),
            data.get("rotation", 0.0),
            data.get("anchor_x", 0.5),
            data.get("anchor_y", 0.5)
        )

@dataclass
class TimelineRegion:
    """
    A named time range.
    """
    start_frame: int
    duration_frames: int
    name: str = ""
    color: str = "#00AAFF" # Blue default

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
        # Status: 0=None, 1=Generating, 2=Ready, 3=Error
        self.proxy_status = 0 
        self.proxy_path = None
        self.use_proxy = False
        
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
        # Overall clip opacity/gain level (Vegas-style center handle)
        self.opacity_level = 1.0  # 0.0 to 1.0 (100%)
        
        # Linking Logic
        self.linked_to: Optional['TimelineClip'] = None
        
        # View Interaction State
        self.selected = False
        self.is_fx_active = False # Indicator for contextual panels (FX/Props)
        
        # Audio Analysis Cache (Vegas Style)
        self.waveform = []
        self.waveform_computing = False
        
        # Video Analysis Cache
        self.thumbnails = []
        self.thumbnails_computing = False
        
        # Trimming Limits
        self.source_duration_frames = -1 # -1 for images, >0 for video/audio
        
        # Effects (OFX Plugins)
        self.effects = [] # List of dicts: {'name': str, 'path': str, 'enabled': bool}
        
        # Transform (Spatial properties for C++ engine)
        self.transform = Transform()
        
        # Metadata Cache (Optimización Audit)
        self.source_width = 0
        self.source_height = 0
        self.source_rotation = 0
        self.source_fps = 30.0

    def to_dict(self) -> dict:
        """Serializes the clip state to a dictionary for JSON storage."""
        return {
            "name": self.name,
            "start_frame": self.start_frame,
            "duration_frames": self.duration_frames,
            "track_index": self.track_index,
            "source_offset_frames": self.source_offset_frames,
            "file_path": self.file_path,
            "start_opacity": self.start_opacity,
            "end_opacity": self.end_opacity,
            "fade_in_frames": self.fade_in_frames,
            "fade_out_frames": self.fade_out_frames,
            "fade_in_type": self.fade_in_type.value,
            "fade_out_type": self.fade_out_type.value,
            "opacity_nodes": self.opacity_nodes,
            "opacity_level": self.opacity_level,
            "use_proxy": self.use_proxy,
            "effects": self.effects,
            "transform": self.transform.to_dict(),
            "source_width": self.source_width,
            "source_height": self.source_height,
            "source_rotation": self.source_rotation,
            "source_fps": self.source_fps
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TimelineClip':
        """Creates a TimelineClip instance from a dictionary."""
        clip = cls(
            data["name"], 
            data["start_frame"], 
            data["duration_frames"], 
            data["track_index"]
        )
        clip.source_offset_frames = data.get("source_offset_frames", 0)
        clip.file_path = data.get("file_path")
        clip.start_opacity = data.get("start_opacity", 1.0)
        clip.end_opacity = data.get("end_opacity", 1.0)
        clip.fade_in_frames = data.get("fade_in_frames", 0)
        clip.fade_out_frames = data.get("fade_out_frames", 0)
        clip.fade_in_type = FadeType(data.get("fade_in_type", 0))
        clip.fade_out_type = FadeType(data.get("fade_out_type", 0))
        clip.opacity_nodes = data.get("opacity_nodes", [])
        clip.opacity_level = data.get("opacity_level", 1.0)
        clip.use_proxy = data.get("use_proxy", False)
        clip.effects = data.get("effects", [])
        if "transform" in data:
            clip.transform = Transform.from_dict(data["transform"])
            
        clip.source_width = data.get("source_width", 0)
        clip.source_height = data.get("source_height", 0)
        clip.source_rotation = data.get("source_rotation", 0)
        clip.source_fps = data.get("source_fps", 30.0)
        return clip

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
        new_clip.opacity_level = self.opacity_level
        new_clip.selected = self.selected
        new_clip.linked_to = self.linked_to
        new_clip.waveform = self.waveform[:]
        new_clip.waveform_computing = self.waveform_computing
        new_clip.thumbnails = self.thumbnails[:]
        new_clip.thumbnails_computing = self.thumbnails_computing
        new_clip.effects = [e.copy() for e in self.effects]
        new_clip.transform = Transform(
            self.transform.x, self.transform.y,
            self.transform.scale_x, self.transform.scale_y,
            self.transform.rotation,
            self.transform.anchor_x, self.transform.anchor_y
        )
        new_clip.source_width = self.source_width
        new_clip.source_height = self.source_height
        new_clip.source_rotation = self.source_rotation
        new_clip.source_fps = self.source_fps
        return new_clip

    # --- Blue Line / Keyframe Logic ---
    # REMOVED per user request (Step 234)
    pass

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
        
        # Ruler Features
        self.time_format = TimeFormat.TIMECODE
        self.markers: List[TimelineMarker] = []
        self.regions: List[TimelineRegion] = []
        
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

    def to_dict(self) -> dict:
        """Serializes the entire project state."""
        return {
            "version": "1.0",
            "track_types": [tt.value for tt in self.track_types],
            "track_heights": self.track_heights,
            "clips": [clip.to_dict() for clip in self.clips]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TimelineModel':
        """Reconstructs the model from serialized data."""
        model = cls()
        model.track_types = [TrackType(v) for v in data.get("track_types", [])]
        model.track_heights = data.get("track_heights", [])
        
        # Reconstruct clips
        clips_data = data.get("clips", [])
        for c_data in clips_data:
            model.clips.append(TimelineClip.from_dict(c_data))
            
        model.layout_revision += 1
        return model

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
        """Standard SMPTE-like timecode formatting delegated to C++ core."""
        import rocky_core
        return rocky_core.RockyEngine.format_timecode(frame, fps)
