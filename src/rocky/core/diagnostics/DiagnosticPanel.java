package rocky.core.diagnostics;

import javax.swing.*;
import java.awt.*;
import java.text.DecimalFormat;

/**
 * Real-time diagnostic overlay for monitoring system health during playback.
 * Displays AV sync, queue status, memory pressure, and performance metrics.
 */
public class DiagnosticPanel extends JPanel {
    private final JLabel avSyncLabel = new JLabel("AV Sync: --");
    private final JLabel queueLabel = new JLabel("Queue: --");
    private final JLabel memoryLabel = new JLabel("Memory: --");
    private final JLabel decodeLabel = new JLabel("Decode: --");
    private final JLabel dropsLabel = new JLabel("Drops: --");
    private final JLabel cacheLabel = new JLabel("Cache: --");
    private final JLabel fpsLabel = new JLabel("FPS: --");
    
    private final DecimalFormat df = new DecimalFormat("0.0");
    private final DecimalFormat pf = new DecimalFormat("0");
    
    // Metrics
    private volatile double audioTimestamp = 0;
    private volatile double videoTimestamp = 0;
    private volatile int queueSize = 0;
    private volatile int queueCapacity = 200;
    private volatile long droppedFrames = 0;
    private volatile double memoryPressure = 0;
    private volatile double avgDecodeMs = 0;
    private volatile int cacheHits = 0;
    private volatile int cacheMisses = 0;
    private volatile double measuredFPS = 0;
    
    public DiagnosticPanel() {
        setLayout(new GridLayout(7, 1, 2, 2));
        setBackground(new Color(20, 20, 30, 220)); // Semi-transparent dark
        setBorder(BorderFactory.createLineBorder(new Color(157, 80, 187), 2));
        
        Font monoFont = new Font("Monospaced", Font.BOLD, 11);
        Color textColor = new Color(230, 230, 250);
        
        for (JLabel label : new JLabel[]{avSyncLabel, queueLabel, memoryLabel, decodeLabel, dropsLabel, cacheLabel, fpsLabel}) {
            label.setFont(monoFont);
            label.setForeground(textColor);
            add(label);
        }
        
        // Update UI every 100ms
        new Timer(100, e -> updateDisplay()).start();
    }
    
    private void updateDisplay() {
        // AV Sync
        double syncOffset = (videoTimestamp - audioTimestamp) * 1000; // ms
        Color syncColor = Math.abs(syncOffset) < 50 ? Color.GREEN : 
                          Math.abs(syncOffset) < 150 ? Color.YELLOW : Color.RED;
        avSyncLabel.setText(String.format("AV Sync: %s%dms", syncOffset > 0 ? "+" : "", (int)syncOffset));
        avSyncLabel.setForeground(syncColor);
        
        // Queue Status
        int queuePercent = (int)((queueSize / (double)queueCapacity) * 100);
        Color queueColor = queuePercent < 70 ? Color.GREEN : 
                           queuePercent < 90 ? Color.YELLOW : Color.RED;
        queueLabel.setText(String.format("Queue: %d/%d (%d%%)", queueSize, queueCapacity, queuePercent));
        queueLabel.setForeground(queueColor);
        
        // Memory Pressure
        int memPercent = (int)(memoryPressure * 100);
        Color memColor = memPercent < 60 ? Color.GREEN : 
                         memPercent < 80 ? Color.YELLOW : Color.RED;
        memoryLabel.setText(String.format("Memory: %d%% pressure", memPercent));
        memoryLabel.setForeground(memColor);
        
        // Decode Time
        Color decodeColor = avgDecodeMs < 30 ? Color.GREEN : 
                            avgDecodeMs < 100 ? Color.YELLOW : Color.RED;
        decodeLabel.setText(String.format("Decode: %.1fms avg", avgDecodeMs));
        decodeLabel.setForeground(decodeColor);
        
        // Frame Drops
        Color dropColor = droppedFrames == 0 ? Color.GREEN : 
                          droppedFrames < 10 ? Color.YELLOW : Color.RED;
        dropsLabel.setText(String.format("Drops: %d frames", droppedFrames));
        dropsLabel.setForeground(dropColor);
        
        // Cache Efficiency
        int totalRequests = cacheHits + cacheMisses;
        int hitRate = totalRequests > 0 ? (int)((cacheHits / (double)totalRequests) * 100) : 0;
        Color cacheColor = hitRate > 70 ? Color.GREEN : 
                           hitRate > 40 ? Color.YELLOW : Color.RED;
        cacheLabel.setText(String.format("Cache: %d%% hit rate", hitRate));
        cacheLabel.setForeground(cacheColor);
        
        // Measured FPS
        Color fpsColor = measuredFPS > 25 ? Color.GREEN : 
                         measuredFPS > 15 ? Color.YELLOW : Color.RED;
        fpsLabel.setText(String.format("FPS: %.1f", measuredFPS));
        fpsLabel.setForeground(fpsColor);
    }
    
    // Setters for external components to push metrics
    public void setAudioTimestamp(double seconds) { this.audioTimestamp = seconds; }
    public void setVideoTimestamp(double seconds) { this.videoTimestamp = seconds; }
    public void setQueueSize(int size) { this.queueSize = size; }
    public void setQueueCapacity(int capacity) { this.queueCapacity = capacity; }
    public void incrementDroppedFrames() { this.droppedFrames++; }
    public void resetDroppedFrames() { this.droppedFrames = 0; }
    public void setMemoryPressure(double pressure) { this.memoryPressure = pressure; }
    public void setAvgDecodeMs(double ms) { this.avgDecodeMs = ms; }
    public void recordCacheHit() { this.cacheHits++; }
    public void recordCacheMiss() { this.cacheMisses++; }
    public void resetCacheStats() { this.cacheHits = 0; this.cacheMisses = 0; }
    public void setMeasuredFPS(double fps) { this.measuredFPS = fps; }
    public void recordSyncSkip() { this.droppedFrames++; }
}
