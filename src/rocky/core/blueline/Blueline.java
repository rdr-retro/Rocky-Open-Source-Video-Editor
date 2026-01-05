package rocky.core.blueline;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Blueline: El motor de tiempo maestro del editor.
 * Maneja la reproducción, el timecode y la sincronización con la UI.
 */
public class Blueline {
    // --- Configuración y Estado ---
    private int fps = 30;
    private double playbackRate = 1.0;
    private long maxFrames = Long.MAX_VALUE;

    private volatile double playheadFrame = 0; // Usamos double para interpolación suave
    private long playbackStartFrame = 0;       // Requerido por TimelinePanel
    private volatile boolean isPlaying = false;
    private long lastUpdateNanos = 0;

    // --- Estética ---
    private final Color PLAYHEAD_COLOR = Color.decode("#9d50bb"); // Morado Premium

    // --- Sistema de Eventos ---
    public interface PlayheadListener { 
        void onFrameChanged(long frame); 
    }
    private final List<PlayheadListener> listeners = new ArrayList<>();

    public void addListener(PlayheadListener l) { 
        listeners.add(l); 
    }

    // --- Lógica de Movimiento (Core) ---

    /**
     * Actualiza la posición del cabezal basándose en el tiempo transcurrido real.
     * Esto evita que la reproducción se ralentice si hay lag en la UI.
     */
    public void update() {
        if (!isPlaying) {
            lastUpdateNanos = 0;
            return;
        }

        long now = System.nanoTime();
        if (lastUpdateNanos > 0) {
            long elapsedNanos = now - lastUpdateNanos;
            double secondsElapsed = elapsedNanos / 1_000_000_000.0;
            
            // Delta timing: avance preciso independiente de los FPS de la UI
            double framesToAdvance = secondsElapsed * fps * playbackRate;
            setPlayheadFramePrecise(this.playheadFrame + framesToAdvance);
        }
        lastUpdateNanos = now;
    }

    private void setPlayheadFramePrecise(double frame) {
        // Limitar entre 0 y el final del proyecto
        this.playheadFrame = Math.max(0, Math.min(frame, maxFrames));
        
        // Notificar a la UI
        long currentFrame = getPlayheadFrame();
        for (PlayheadListener l : listeners) {
            l.onFrameChanged(currentFrame);
        }
    }

    public void startPlayback() {
        if (isPlaying) return;
        
        this.playbackStartFrame = getPlayheadFrame(); // Guarda dónde inició (Arregla el error de compilación)
        this.lastUpdateNanos = System.nanoTime();
        this.isPlaying = true;
        
        // Comunicación con el motor de audio/video
        if (rocky.core.engine.PlaybackIsolation.getInstance() != null) {
            rocky.core.engine.PlaybackIsolation.getInstance().setPlaybackActive(true);
        }
    }

    public void stopPlayback() {
        this.isPlaying = false;
        this.lastUpdateNanos = 0;
        
        if (rocky.core.engine.PlaybackIsolation.getInstance() != null) {
            rocky.core.engine.PlaybackIsolation.getInstance().setPlaybackActive(false);
        }
    }

    // --- Formateo de Tiempo ---

    /**
     * Convierte frames a formato HH:MM:SS:FF
     */
    public String formatTimecode(long frames) {
        long f = Math.abs(frames % fps);
        long totalSeconds = Math.abs(frames / fps);
        long s = totalSeconds % 60;
        long m = (totalSeconds / 60) % 60;
        long h = totalSeconds / 3600;
        return String.format("%02d:%02d:%02d;%02d", h, m, s, f);
    }

    public String formatTimecode() {
        return formatTimecode(getPlayheadFrame());
    }

    // --- Getters y Setters ---

    public long getPlayheadFrame() {
        return (long) Math.floor(playheadFrame);
    }

    public void setPlayheadFrame(long frame) {
        this.playheadFrame = frame;
        if (!isPlaying) lastUpdateNanos = 0;
        // Notificar cambio manual
        for (PlayheadListener l : listeners) l.onFrameChanged(frame);
    }

    public long getPlaybackStartFrame() {
        return playbackStartFrame;
    }

    public Color getColor() { return PLAYHEAD_COLOR; }
    
    public boolean isPlaying() { return isPlaying; }
    
    public double getPlaybackRate() { return playbackRate; }
    
    public void setPlaybackRate(double rate) { this.playbackRate = rate; }
    
    public void setFps(int fps) { this.fps = fps; }

    /**
     * Lógica para que la línea de tiempo siga al cabezal automáticamente.
     */
    public double calculateAutoScroll(double visibleStartTime, double visibleDuration) {
        if (!isPlaying) return -1;
        
        double currentTime = playheadFrame / (double) fps;
        // Si el cabezal sale de la vista (por la derecha o izquierda)
        if (currentTime > (visibleStartTime + visibleDuration) || currentTime < visibleStartTime) {
            return currentTime; // Indica a la UI que debe centrarse aquí
        }
        return -1;
    }
}