package rocky.core.blueline;

import java.awt.*;

public class Blueline {
    private volatile double playheadFrame = 0;
    private long playbackStartFrame = 0;
    private volatile boolean isPlaying = false;
    private int fps = 30;
    private double playbackRate = 1.0;
    private final Color PLAYHEAD_COLOR = Color.decode("#9d50bb");
    private long lastUpdateNanos = 0;

    // --- Métodos que TimelinePanel necesita ---

    public Color getColor() {
        return PLAYHEAD_COLOR;
    }

    public boolean isPlaying() {
        return isPlaying;
    }

    public long getPlaybackStartFrame() {
        return playbackStartFrame;
    }

    public double getPlaybackRate() {
        return playbackRate;
    }

    public void setPlaybackRate(double rate) {
        this.playbackRate = rate;
    }

    /**
     * Versión compatible con el error de compilación.
     * Ahora acepta un parámetro long para no romper TimelinePanel.
     */
    public String formatTimecode(long frames) {
        long f = frames % fps;
        long totalSeconds = frames / fps;
        long s = totalSeconds % 60;
        long m = (totalSeconds / 60) % 60;
        long h = totalSeconds / 3600;
        return String.format("%02d:%02d:%02d;%02d", h, m, s, f);
    }

    // Sobrecarga por si acaso se usa sin argumentos en el futuro
    public String formatTimecode() {
        return formatTimecode(getPlayheadFrame());
    }

    // --- Lógica de Movimiento ---

    public void update() {
        if (!isPlaying) {
            lastUpdateNanos = 0;
            return;
        }

        long now = System.nanoTime();
        if (lastUpdateNanos > 0) {
            long elapsedNanos = now - lastUpdateNanos;
            double secondsElapsed = elapsedNanos / 1_000_000_000.0;
            this.playheadFrame += secondsElapsed * fps * playbackRate;
            if (this.playheadFrame < 0)
                this.playheadFrame = 0;
        }
        lastUpdateNanos = now;
    }

    public void startPlayback() {
        this.playbackStartFrame = getPlayheadFrame();
        this.lastUpdateNanos = System.nanoTime();
        this.isPlaying = true;
    }

    public void stopPlayback() {
        this.isPlaying = false;
        this.lastUpdateNanos = 0;
    }

    public long getPlayheadFrame() {
        return (long) Math.floor(playheadFrame);
    }

    public void setPlayheadFrame(long frame) {
        this.playheadFrame = frame;
    }

    public double calculateAutoScroll(double visibleStartTime, double visibleDuration) {
        if (!isPlaying)
            return -1;
        double currentTime = playheadFrame / (double) fps;
        if (currentTime > (visibleStartTime + visibleDuration) || currentTime < visibleStartTime) {
            return currentTime;
        }
        return -1;
    }
}