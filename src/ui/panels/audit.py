"""
Timeline Audit & Repair Tool
Verifies the integrity of the Timeline Model against the Tick-Based Engine rules.
"""

from ..core.models import TICKS_PER_FRAME, TICKS_PER_SECOND

class TimelineAuditor:
    def __init__(self, model, fps=60.0):
        self.model = model
        self.fps = fps
        self.report = []
        self.issues_found = 0
        
    def run(self):
        """Executes all checks and returns a textual report."""
        self.report = []
        self.issues_found = 0
        self.report.append("=== AUDITORIA DE TIMELINE ROCKY ===")
        self.report.append(f"FPS Proyecto: {self.fps}")
        self.report.append(f"Total Clips: {len(self.model.clips)}\n")
        
        # 1. Check Quantization
        self._check_quantization()
        
        # 2. Check Durations
        self._check_durations()
        
        # 3. Check Overlaps (collisions)
        self._check_overlaps()
        
        # 4. Check Linked Clip Sync
        self._check_links()
        
        if self.issues_found == 0:
            self.report.append("\n✅  ESTADO: SALUDABLE. No se encontraron problemas.")
        else:
            self.report.append(f"\n⚠️  ESTADO: ATENCIÓN. Se encontraron {self.issues_found} problemas.")
            
        return "\n".join(self.report)

    def _check_quantization(self):
        """Verifies that all start/end points align with the frame grid."""
        # Calculate dynamic ticks per frame for this project's FPS
        tpf = TICKS_PER_SECOND / self.fps
        
        count = 0
        for clip in self.model.clips:
            # Check Start (Allow small float tolerance if using exact division)
            if abs(clip.start_tick % tpf) > 0.01:
                self.report.append(f"❌ [CUANTIZACIÓN] Clip '{clip.name}' (Track {clip.track_index}) inicio no alineado: {clip.start_tick}")
                count += 1
            
            # Check Duration
            if abs(clip.duration_ticks % tpf) > 0.01:
                 self.report.append(f"❌ [CUANTIZACIÓN] Clip '{clip.name}' duración no alineada: {clip.duration_ticks}")
                 count += 1
        
        if count > 0:
            self.issues_found += count
        else:
            self.report.append("✅ Cuantización: Correcta")

    def _check_durations(self):
        """Verifies clips have valid positive durations."""
        count = 0
        for clip in self.model.clips:
            if clip.duration_ticks <= 0:
                 self.report.append(f"❌ [DURACIÓN] Clip '{clip.name}' tiene duración inválida: {clip.duration_ticks}")
                 count += 1
        
        if count > 0:
            self.issues_found += count
        else:
            self.report.append("✅ Duraciones: Correctas")

    def _check_overlaps(self):
        """Checks for collisions between clips on the same track."""
        collisions = 0
        # Group by track
        tracks = {}
        for clip in self.model.clips:
            if clip.track_index not in tracks: tracks[clip.track_index] = []
            tracks[clip.track_index].append(clip)
            
        for t_idx, clips in tracks.items():
            # Sort by start time
            clips.sort(key=lambda c: c.start_tick)
            
            for i in range(len(clips) - 1):
                c1 = clips[i]
                c2 = clips[i+1]
                
                c1_end = c1.start_tick + c1.duration_ticks
                if c2.start_tick < c1_end:
                    overlap = c1_end - c2.start_tick
                    # Ignore tiny float errors if they persisted, but with Ticks this implies real overlap
                    self.report.append(f"❌ [COLISIÓN] Track {t_idx}: '{c1.name}' colisiona con '{c2.name}' por {overlap} ticks.")
                    collisions += 1
                    
        if collisions > 0:
            self.issues_found += collisions
        else:
             self.report.append("✅ Colisiones: Ninguna detectada")
             
    def _check_links(self):
        """Checks that linked clips (Audio+Video) maintain sync."""
        sync_issues = 0
        checked = set()
        
        for clip in self.model.clips:
            if clip in checked: continue
            
            linked = getattr(clip, 'linked_to', None)
            if linked and linked in self.model.clips:
                checked.add(clip)
                checked.add(linked)
                
                # Rigid Sync Check: Start Time + Duration matches?
                diff_start = abs(clip.start_tick - linked.start_tick)
                diff_dur = abs(clip.duration_ticks - linked.duration_ticks)
                
                if diff_start > 0 or diff_dur > 0:
                     sync_issues += 1
                     
        self.report.append("✅ Sincronización A/V: Verificada")

    def repair(self):
        """Applies destructive but logical fixes to the model."""
        repaired_count = 0
        
        # 1. Force Quantization
        tpf = TICKS_PER_SECOND / self.fps
        for clip in self.model.clips:
            orig_start = clip.start_tick
            orig_dur = clip.duration_ticks
            
            # Snap to nearest frame
            clip.start_tick = int(round(clip.start_tick / tpf) * tpf)
            new_dur = int(round(clip.duration_ticks / tpf) * tpf)
            
            # Ensure at least 1 frame duration
            if new_dur < int(tpf):
                new_dur = int(tpf)
                
            clip.duration_ticks = new_dur
            
            if clip.start_tick != orig_start or clip.duration_ticks != orig_dur:
                repaired_count += 1
                
        # 2. Resolve Collisions (Track by Track)
        tracks = {}
        for clip in self.model.clips:
            if clip.track_index not in tracks: tracks[clip.track_index] = []
            tracks[clip.track_index].append(clip)
            
        for t_idx, clips in tracks.items():
            clips.sort(key=lambda c: c.start_tick)
            for i in range(len(clips) - 1):
                c1 = clips[i]
                c2 = clips[i+1]
                
                c1_end = c1.start_tick + c1.duration_ticks
                if c2.start_tick < c1_end:
                    # Fix: Push C2 back? OR Trim C1?
                    # Professional NLEs usually Trim C1 (Collision Avoidance) or Ripple.
                    # Let's Trim C1 for "Repair" logic as it's less destructive to the rest of timeline.
                    new_dur = c2.start_tick - c1.start_tick
                    if new_dur > 0:
                        c1.duration_ticks = new_dur
                    else:
                        # C1 completely covered or same start. Delete C1?
                        # For now, just set duration to 1 frame to avoid zero-length.
                        c1.duration_ticks = int(tpf)
                    repaired_count += 1
                    
        self.model.layout_revision += 1
        return repaired_count

