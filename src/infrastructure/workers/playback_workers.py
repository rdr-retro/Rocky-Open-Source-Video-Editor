import sys
import os
import subprocess
import numpy as np
from PySide6.QtCore import Qt, Signal, QThread, QMutex, QMutexLocker, QIODevice, QRectF
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput, QAudioSource, QAudioSink
from ..ffmpeg_utils import FFmpegUtils
from ...ui.core.models import TICKS_PER_SECOND
import rocky_core

# Use PROBE if available, or a mock
try:
    from ...diagnostics.probe import PROBE
except ImportError:
    class MockProbe:
        def log_buffer_state(self, *args): pass
        def log_audio_request(self, *args): pass
    PROBE = MockProbe()

class AudioPlayer(QIODevice):
    level_updated = Signal(float, float)

    def __init__(self, sample_rate=44100, channels=2):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.ring_buffer = rocky_core.AudioRingBuffer(524288) 
        self.mutex = QMutex() 
        
        format = QAudioFormat()
        format.setSampleRate(sample_rate)
        format.setChannelCount(channels)
        format.setSampleFormat(QAudioFormat.SampleFormat.Float)
        
        self.audio_output = QAudioOutput()
        self.sink = QAudioSink(format)
        self.sink.setBufferSize(int(sample_rate * channels * 4 * 1.0))
        
        self.open(QIODevice.ReadOnly)
        self.sink.start(self)

    def write_samples(self, samples_np):
        if samples_np is not None:
            try:
                if samples_np.size >= 2:
                    l_peak = np.max(np.abs(samples_np[0::2]))
                    r_peak = np.max(np.abs(samples_np[1::2]))
                    self.level_updated.emit(float(l_peak), float(r_peak))
            except:
                pass
            self.ring_buffer.write(samples_np)

    def clear_buffer(self):
        self.ring_buffer.clear()
        
    def get_buffer_duration_ms(self):
        count = self.ring_buffer.get_available_read()
        if count == 0 and getattr(self, 'is_playing_safety_flag', False):
            PROBE.log_buffer_state(count, self.ring_buffer.get_available_write(), 524288)
        return (count / (self.sample_rate * 2)) * 1000.0

    def readData(self, maxlen):
        data = self.ring_buffer.read_bytes(maxlen)
        if not data:
            return b"\x00" * maxlen
        return data

    def bytesAvailable(self):
        return (self.ring_buffer.get_available_read() * 4) + super().bytesAvailable()

    def get_processed_us(self):
        return self.sink.processedUSecs()

class AudioWorker(QThread):
    def __init__(self, engine, player, model):
        super().__init__()
        self.engine = engine
        self.player = player
        self.model = model
        self.running = False
        self.fps = 30.0

    def run(self):
        self.running = True
        while self.running and not self.isInterruptionRequested():
            if not self.model.blueline.playing:
                self.msleep(50)
                continue

            current_buffer_ms = self.player.get_buffer_duration_ms()
            rate = getattr(self.model.blueline, 'playback_rate', 1.0)
            
            if current_buffer_ms < 1800:
                missing_ms = 2500 - current_buffer_ms
                missing_duration = missing_ms / 1000.0
                
                try:
                    if not hasattr(self.model, 'audio_samples_rendered'):
                        self.model.audio_samples_rendered = 0
                        
                    audio_final, consumed = self.engine.get_playback_batch(
                        self.model.audio_samples_rendered,
                        missing_duration,
                        rate
                    )
                    
                    if audio_final is not None and audio_final.size > 0:
                        PROBE.log_audio_request(self.model.audio_samples_rendered, consumed, rate)
                        self.player.write_samples(audio_final)
                        self.model.audio_samples_rendered += consumed
                except Exception as e:
                    print(f"AudioWorker Error: {e}")
            
            self.msleep(2)

    def start_playback(self, start_time, fps, rate=1.0):
        self.fps = fps
        self.player.clear_buffer()
        self.model.audio_samples_rendered = int(start_time * 44100)
        start_tick = int(start_time * TICKS_PER_SECOND)
        dur_ticks = int(2.0 * TICKS_PER_SECOND)
        initial = self.engine.render_audio(start_tick, dur_ticks)
        self.player.write_samples(initial)
        self.model.audio_samples_rendered += (initial.size // 2)
        self.player.sink.resume()

    def stop_playback(self):
        self.player.sink.suspend()

class VideoWorker(QThread):
    frame_ready = Signal(object)

    def __init__(self, engine, engine_lock):
        super().__init__()
        self.engine = engine
        self.engine_lock = engine_lock
        self.running = False
        self._target_timestamp = -1.0
        self._target_res = None
        self._mutex = QMutex()
        self._has_new_request = False

    def request_frame(self, tick):
        locker = QMutexLocker(self._mutex)
        self._target_timestamp = tick
        self._has_new_request = True

    def request_resolution(self, w, h):
        locker = QMutexLocker(self._mutex)
        self._target_res = (w, h)

    def run(self):
        self.running = True
        last_processed = -1.0
        
        while self.running and not self.isInterruptionRequested():
            timestamp = -1.0
            new_res = None
            locker = QMutexLocker(self._mutex)
            if self._has_new_request:
                timestamp = self._target_timestamp
                self._has_new_request = False
            if self._target_res:
                # Optimized: Only pick resolution if it's different from current
                new_res_val = self._target_res
                self._target_res = None
                
                if new_res_val != getattr(self, '_last_engine_res', (0, 0)):
                    new_res = new_res_val
                    self._last_engine_res = new_res_val
            del locker

            if new_res:
                locker = QMutexLocker(self.engine_lock)
                self.engine.set_resolution(new_res[0], new_res[1])
                del locker

            if timestamp != -1.0 and timestamp != last_processed:
                try:
                    locker = QMutexLocker(self.engine_lock)
                    frame = self.engine.evaluate(int(timestamp))
                    del locker
                    self.frame_ready.emit(frame)
                    last_processed = timestamp
                except Exception as e:
                    print(f"VideoWorker Error: {e}")
            self.msleep(2)

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
        ffmpeg_exe = FFmpegUtils.get_ffmpeg_path()
        audio_temp_path = self.output_path + ".audio.tmp"
        
        try:
            self.width = (self.width // 32) * 32
            self.height = (self.height // 32) * 32
            
            if self.width <= 0: self.width = 1280
            if self.height <= 0: self.height = 720

            locker = QMutexLocker(self.engine_lock)
            self.engine.set_resolution(self.width, self.height)
            if locker: del locker
            
            ticks_per_frame = TICKS_PER_SECOND / self.fps
            total_duration_ticks = int(self.total_frames * ticks_per_frame)
            
            audio_samples = self.engine.render_audio(0, total_duration_ticks)
            with open(audio_temp_path, 'wb') as f:
                f.write(audio_samples.tobytes())
                
            enc_config = FFmpegUtils.get_export_config(self.high_quality)
            
            command = [
                ffmpeg_exe, '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.width}x{self.height}',
                '-pix_fmt', 'rgba',
                '-r', str(self.fps),
                '-i', '-',
                '-f', 'f32le',
                '-ar', '44100',
                '-ac', '2',
                '-i', audio_temp_path,
                '-vf', f'format={enc_config.pix_fmt}',
                '-c:v', enc_config.codec
            ]
            
            command.extend(enc_config.preset_flag)
            command.extend(enc_config.quality_flag)
            command.extend(enc_config.extra_flags)
            command.extend([
                '-pix_fmt', enc_config.pix_fmt,
                '-c:a', 'aac',
                '-b:a', '192k',
                self.output_path
            ])
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as err_log:
                err_log_path = err_log.name

            with open(err_log_path, 'wb') as err_f:
                process = subprocess.Popen(
                    command, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.DEVNULL,
                    stderr=err_f,
                    startupinfo=startupinfo
                )
            
                tpf = TICKS_PER_SECOND / self.fps
                
                for i in range(self.total_frames):
                    if self.isInterruptionRequested():
                        process.terminate()
                        break
                        
                    tick = int(i * tpf)
                    frame_data = self.engine.evaluate(tick)
                    
                    try:
                        raw_bytes = frame_data.tobytes()
                        process.stdin.write(raw_bytes)
                        if i == 0:
                            process.stdin.flush()
                        if i % 30 == 0:
                            process.stdin.flush()
                    except BrokenPipeError:
                        break
                        
                    if i % 5 == 0:
                        self.progress.emit(int((i / self.total_frames) * 100))
                        
                process.stdin.close()
                process.wait()
            
            if process.returncode != 0:
                with open(err_log_path, 'r', errors='replace') as f:
                    err_out = f.read()
                self.error.emit(f"Fallo en FFmpeg (Code {process.returncode}):\n{err_out}")
            else:
                self.finished.emit(self.output_path)

            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
            if os.path.exists(err_log_path):
                os.remove(err_log_path)
                
        except Exception as e:
            print(f"RenderWorker Exception: {e}")
            self.error.emit(str(e))
