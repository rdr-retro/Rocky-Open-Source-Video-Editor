import os
import sys
import subprocess
import tempfile
import ssl
import json
import numpy as np

# Bypass SSL certificate verification for model downloads
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

from PySide6.QtWidgets import (QLabel, QVBoxLayout, QWidget, QPushButton, 
                             QFileDialog, QProgressBar, QHBoxLayout, QSlider, 
                             QFrame, QColorDialog, QComboBox, QMessageBox, QScrollArea,
                             QSplitter, QGroupBox, QFormLayout, QSizePolicy, QApplication, QStackedWidget)
from PySide6.QtCore import Qt, QThread, Signal, QPoint, QSize, QTimer, QRectF
from PySide6.QtGui import QImage, QPixmap, QColor, QResizeEvent, QPainter, QPen, QFont

# Try to import external dependencies
try:
    import whisper
    from moviepy import VideoFileClip
except ImportError:
    whisper = None
    VideoFileClip = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None

# --- WORKER THREAD ---
class VideoProcessingThread(QThread):
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(str)
    progress_percent = Signal(int)
    
    def __init__(self, video_path, output_path, base_font_size, rel_pos, stroke_color, font_name):
        super().__init__()
        self.v_path = video_path
        self.o_path = output_path
        self.base_size = base_font_size
        self.rel_pos = rel_pos # Normalized [rx, ry]
        self.stroke_color = stroke_color
        self.font_name = font_name
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            import rocky_core
            from ..infrastructure.ffmpeg_utils import FFmpegUtils
        except ImportError as e:
            self.error.emit(f"Error importando Rocky Core: {e}")
            return
        
        if not whisper:
            self.error.emit("Falta biblioteca whisper.")
            return

        temp_files = []
        try:
            self.progress.emit("Auditando resolución y FPS...")
            
            # --- ROBUST METADATA (FFMPEG) ---
            width, height, rotation, fps = 1920, 1080, 0, 30.0
            try:
                ffp = FFmpegUtils.get_ffprobe_path()
                cmd = [ffp, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:side_data=rotation', '-of', 'json', self.v_path]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                data = json.loads(proc.stdout)
                if 'streams' in data and data['streams']:
                    stream = data['streams'][0]
                    width = stream.get('width', 1920)
                    height = stream.get('height', 1080)
                    # Parse FPS
                    rfps = stream.get('r_frame_rate', '30/1')
                    if '/' in rfps:
                        num, den = map(int, rfps.split('/'))
                        fps = num / den if den > 0 else 30.0
                    else: fps = float(rfps)
                    
                    for sd in stream.get('side_data', []):
                        if 'rotation' in sd: rotation = int(sd['rotation']); break
            except Exception as e:
                print(f"DEBUG: Metadata probe failed: {e}")

            # Visual dimensions (after rotation)
            vis_w = width if rotation % 180 == 0 else height
            vis_h = height if rotation % 180 == 0 else width
            
            engine = rocky_core.RockyEngine()
            engine.set_resolution(vis_w, vis_h) 
            engine.set_fps(fps)
            
            self.progress.emit("Preparando audio...")
            video_ref = VideoFileClip(self.v_path)
            duration = video_ref.duration
            fd, temp_audio = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            temp_files.append(temp_audio)
            video_ref.audio.write_audiofile(temp_audio, codec='pcm_s16le', logger=None)
            video_ref.close()
            
            if self._cancelled: return
            self.progress.emit("Transcribiendo...")
            model = whisper.load_model("base")
            result = model.transcribe(temp_audio, fp16=False, word_timestamps=True)
            
            # --- TRACKS (Z-ORDER) ---
            engine.add_track(rocky_core.VIDEO) # Index 0: Background
            engine.add_track(rocky_core.VIDEO) # Index 1: Subtitles (TOP)
            
            # --- BACKGROUND ---
            vid_src = rocky_core.VideoSource(os.path.abspath(self.v_path))
            vid_clip = engine.add_clip(0, "Media", 0, int(duration * fps), 0.0, vid_src)
            vid_clip.transform.x = 0.0
            vid_clip.transform.y = 0.0
            vid_clip.transform.rotation = float(rotation)
            vid_clip.transform.scale_x = 1.0 
            vid_clip.transform.scale_y = 1.0
            vid_clip.opacity = 1.0

            # --- SUBTITLES ---
            self.progress.emit("Generando textos...")
            font_size = int(self.base_size)
            pil_font = None
            
            font_candidates = []
            if self.font_name == "Impact":
                font_candidates = ["/Library/Fonts/Impact.ttf", "/System/Library/Fonts/Supplemental/Impact.ttf", "Impact"]
            elif self.font_name == "Arial":
                font_candidates = ["/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "Arial"]
            else:
                font_candidates = ["/Library/Fonts/Arial.ttf", "Arial"]
                
            for f_path in font_candidates:
                try: pil_font = ImageFont.truetype(f_path, font_size); break
                except: continue
            if not pil_font: pil_font = ImageFont.load_default()
            
            target_y_engine = 0.5 - self.rel_pos[1]
            
            all_words = []
            for s in result.get("segments", []):
                for w in s.get("words", []): all_words.append(w)
            
            count = len(all_words)
            for i, word in enumerate(all_words):
                if self._cancelled: break
                text = word["word"].strip().upper()
                if not text: continue
                
                dummy = Image.new('RGBA', (1,1))
                draw = ImageDraw.Draw(dummy)
                bbox = draw.textbbox((0,0), text, font=pil_font)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                pad = max(10, int(font_size * 0.2))
                iw, ih = int(tw + pad*2), int(th + pad*2)
                
                img = Image.new('RGBA', (iw, ih), (0,0,0,0))
                d = ImageDraw.Draw(img)
                tx, ty = (iw-tw)/2, (ih-th)/2
                sw = max(3, int(font_size * 0.1))
                for ox in range(-sw, sw+1):
                    for oy in range(-sw, sw+1):
                        if ox*ox+oy*oy <= sw*sw: d.text((tx+ox, ty+oy), text, font=pil_font, fill="black")
                d.text((tx, ty), text, font=pil_font, fill="#FFFF00")
                
                fd, ipath = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                img.save(ipath)
                temp_files.append(ipath)
                
                s_clip = engine.add_clip(1, f"S{i}", int(word["start"]*fps), int(max(0.1, word["end"]-word["start"])*fps), 0.0, rocky_core.ImageSource(ipath))
                s_clip.opacity = 1.0
                s_clip.transform.scale_x = float(iw / vis_w)
                s_clip.transform.scale_y = float(ih / vis_h)
                s_clip.transform.x = 0.0 
                s_clip.transform.y = float(target_y_engine)
                
                if i % 10 == 0: self.progress_percent.emit(20 + int((i/count)*30))

            if self._cancelled: return
            self.progress.emit("Exportando video...")
            
            ffmpeg_exe = FFmpegUtils.get_ffmpeg_path()
            cmd = [
                ffmpeg_exe, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-s', f'{vis_w}x{vis_h}', '-pix_fmt', 'rgba', '-r', str(fps),
                '-i', '-', '-i', temp_audio, 
                '-vf', 'format=yuv420p', 
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18',
                '-c:a', 'aac', '-b:a', '192k', '-map', '0:v', '-map', '1:a', self.o_path
            ]
            
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            total = int(duration * fps)
            for i in range(total):
                if self._cancelled: proc.terminate(); break
                proc.stdin.write(engine.evaluate(i/fps).tobytes())
                if i % 30 == 0: self.progress_percent.emit(50 + int((i/total)*50))
            
            proc.stdin.close(); proc.wait()
            if proc.returncode == 0: 
                self.progress_percent.emit(100)
                self.finished.emit(self.o_path)
            else: self.error.emit(f"Falla FFmpeg: {proc.returncode}")
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            for f in temp_files:
                if os.path.exists(f): 
                    try: os.remove(f)
                    except: pass

# --- UI COMPONENTS ---

class DraggableText(QLabel):
    moved = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__("SUBTÍTULOS", parent)
        self.setStyleSheet("background: rgba(255, 235, 59, 1.0); color: black; border: 2px solid white; font-weight: 900; font-size: 10px; padding: 2px; text-transform: uppercase;")
        self.setAlignment(Qt.AlignCenter); self.setCursor(Qt.SizeAllCursor); self.setFixedSize(110, 26)
        self._dragging = False; self._offset = QPoint()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._dragging, self._offset = True, e.pos()

    def mouseMoveEvent(self, e):
        if self._dragging:
            np = self.mapToParent(e.pos()) - self._offset
            p = self.parentWidget().rect()
            np.setX(max(0, min(np.x(), p.width() - self.width())))
            np.setY(max(0, min(np.y(), p.height() - self.height())))
            self.move(np); self.moved.emit(np)

    def mouseReleaseEvent(self, e): self._dragging = False

class SubtitleViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_aspect = 16/9; self.stage_rect = QRectF()
        self.text_overlay = DraggableText(self); self.text_overlay.hide()
        self.setMinimumHeight(280)

    def set_aspect(self, w, h):
        self.p_aspect = w / h; self.text_overlay.show(); self.update()
        QTimer.singleShot(200, self._init_pos)

    def _get_stage_geometry(self):
        lw, lh = self.width(), self.height()
        if lw < 10 or lh < 10: return QRectF()
        l_aspect = lw / lh
        if self.p_aspect > l_aspect: sw = lw * 0.85; sh = sw / self.p_aspect
        else: sh = lh * 0.85; sw = sh * self.p_aspect
        return QRectF((lw-sw)//2, (lh-sh)//2, sw, sh)

    def _init_pos(self):
        sr = self._get_stage_geometry()
        if sr.width() <= 0: return
        self.text_overlay.move(int(sr.x() + (sr.width()-110)/2), int(sr.y() + sr.height()*0.8))

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); painter.fillRect(self.rect(), QColor(20, 20, 20))
        self.stage_rect = self._get_stage_geometry()
        if self.stage_rect.isEmpty(): return
        painter.setBrush(QColor(0, 0, 0)); painter.setPen(Qt.NoPen); painter.drawRect(self.stage_rect)
        painter.setPen(QPen(QColor(100, 100, 100), 1, Qt.DashLine)); painter.drawRect(self.stage_rect)
        lw, lh, sx, sy, sw, sh = self.width(), self.height(), self.stage_rect.x(), self.stage_rect.y(), self.stage_rect.width(), self.stage_rect.height()
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1)); painter.drawLine(int(lw/2), int(sy), int(lw/2), int(sy+sh)); painter.drawLine(int(sx), int(lh/2), int(sx+sw), int(lh/2))
        painter.setPen(QColor(150, 150, 150)); painter.setFont(QFont("Inter", 8)); painter.drawText(self.rect().adjusted(12,-12,-12,-12), Qt.AlignBottom | Qt.AlignLeft, f"AUDIO: {int(self.p_aspect*1000)}x1000")

    def resizeEvent(self, e): super().resizeEvent(e); self.update()

class SubtitlePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.current_clip = None; self.stroke_color = "#ff0000"; self._active_workers = []
        self._init_ui()
        
    def _init_ui(self):
        self.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; font-family: 'Inter';")
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        self.stack = QStackedWidget(); self.main_layout.addWidget(self.stack)
        page0 = QWidget(); p_lay = QVBoxLayout(page0); msg = QLabel("SELECCIONA UN CLIP EN LA LÍNEA DE TIEMPO")
        msg.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;"); msg.setAlignment(Qt.AlignCenter); p_lay.addWidget(msg); self.stack.addWidget(page0)
        page1 = QWidget(); e_lay = QVBoxLayout(page1); e_lay.setContentsMargins(0,0,0,0); e_lay.setSpacing(0)
        split = QSplitter(Qt.Vertical); self.viewer = SubtitleViewer(); split.addWidget(self.viewer)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background-color: #1a1a1a;")
        c_wid = QWidget(); c_lay = QVBoxLayout(c_wid); c_lay.setContentsMargins(12,5,12,12); c_lay.setSpacing(10)
        grp = QGroupBox("CONFIGURACIÓN DE TEXTO"); grp.setStyleSheet("QGroupBox { color: #888; font-weight: bold; font-size: 10px; border: 1px solid #333; margin-top: 12px; padding-top: 8px; border-radius: 4px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }")
        form = QFormLayout(grp); self.f_combo = QComboBox(); self.f_combo.addItems(["Impact", "Arial", "Comic Sans"]); self.f_combo.setStyleSheet("background: #111; border: 1px solid #333; padding: 3px;")
        self.s_slider = QSlider(Qt.Horizontal); self.s_slider.setRange(20, 200); self.s_slider.setValue(100)
        form.addRow("Fuente", self.f_combo); form.addRow("Tamaño", self.s_slider); c_lay.addWidget(grp)
        grp_act = QGroupBox("ACCIONES"); grp_act.setStyleSheet(grp.styleSheet()); a_lay = QVBoxLayout(grp_act); a_lay.setSpacing(8)
        self.btn_run = QPushButton("GENERAR VIDEO SUBTITULADO"); self.btn_run.setStyleSheet("background: #673AB7; color: white; padding: 12px; font-weight: bold; border-radius: 4px;"); self.btn_run.clicked.connect(self.start_process)
        self.pbar = QProgressBar(); self.pbar.setVisible(False); self.pbar.setStyleSheet("QProgressBar { border: none; background: #111; height: 4px; } QProgressBar::chunk { background: #00a3ff; }")
        self.status = QLabel("AUDITORÍA DE RENDER LISTA"); self.status.setStyleSheet("color: #666; font-size: 8px; font-weight: bold;"); self.status.setAlignment(Qt.AlignCenter)
        a_lay.addWidget(self.btn_run); a_lay.addWidget(self.pbar); a_lay.addWidget(self.status); c_lay.addWidget(grp_act)
        c_lay.addStretch(); scroll.setWidget(c_wid); split.addWidget(scroll); split.setStretchFactor(0, 7); split.setStretchFactor(1, 3); e_lay.addWidget(split); self.stack.addWidget(page1)

    def update_context(self, selection):
        if not selection or not hasattr(selection[0], 'file_path') or not selection[0].file_path: self.stack.setCurrentIndex(0); return
        clip = selection[0]; self.current_clip = clip
        
        # PERFORMANCE OPTIMIZATION: Use metadata cache from TimelineClip
        # This eliminates synchronous ffprobe calls on the UI thread.
        try:
            w, h = getattr(clip, 'source_width', 0), getattr(clip, 'source_height', 0)
            rot = getattr(clip, 'source_rotation', 0)
            
            # Use safe fallback if cache is empty
            if w <= 0 or h <= 0:
                from ..infrastructure.ffmpeg_utils import FFmpegUtils
                ffp = FFmpegUtils.get_ffprobe_path()
                cmd = [ffp, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:side_data=rotation', '-of', 'json', clip.file_path]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                data = json.loads(res.stdout)
                s = data['streams'][0]; w, h = s['width'], s['height']; rot = 0
                for sd in s.get('side_data', []):
                    if 'rotation' in sd: rot = int(sd['rotation']); break
            
            if rot % 180 != 0: w, h = h, w
            self.viewer.set_aspect(w, h); self.status.setText(f"VIDEO: {os.path.basename(clip.file_path).upper()}"); self.stack.setCurrentIndex(1)
        except Exception as e:
            print(f"DEBUG: SubtitlePanel context update failed: {e}")
            self.stack.setCurrentIndex(0)

    def start_process(self):
        if not self.current_clip: return
        out, _ = QFileDialog.getSaveFileName(self, "Exportar Video con Subtítulos", "video_final.mp4", "*.mp4")
        if not out: return
        sr = self.viewer._get_stage_geometry()
        if sr.height() > 0: rel_y = (self.viewer.text_overlay.y() + (self.viewer.text_overlay.height()/2) - sr.y()) / sr.height()
        else: rel_y = 0.8
        self.btn_run.setEnabled(False); self.pbar.setVisible(True); self.pbar.setValue(0)
        worker = VideoProcessingThread(self.current_clip.file_path, out, self.s_slider.value(), (0.5, rel_y), self.stroke_color, self.f_combo.currentText())
        worker.progress.connect(self.status.setText); worker.progress_percent.connect(self.pbar.setValue)
        worker.finished.connect(lambda p: self._on_done(p, worker)); worker.error.connect(lambda e: self._on_error(e, worker))
        self._active_workers.append(worker); worker.start()

    def _on_done(self, p, worker):
        if worker in self._active_workers: self._active_workers.remove(worker)
        self.pbar.setVisible(False); self.btn_run.setEnabled(True); QMessageBox.information(self, "Éxito", f"El video se ha generado correctamente:\n{p}")

    def _on_error(self, e, worker):
        if worker in self._active_workers: self._active_workers.remove(worker)
        self.pbar.setVisible(False); self.btn_run.setEnabled(True); QMessageBox.critical(self, "Error de Render", f"Fallo en el proceso:\n{e}")

    def closeEvent(self, event):
        for w in self._active_workers:
            if w.isRunning(): w.cancel(); w.wait()
        super().closeEvent(event)
