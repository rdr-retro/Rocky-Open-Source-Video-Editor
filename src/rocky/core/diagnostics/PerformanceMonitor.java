package rocky.core.diagnostics;

import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import javax.swing.SwingUtilities;

/**
 * Diagnoses micro-stutters with Zero-GC overhead during the render loop.
 */
public class PerformanceMonitor {

    public enum Mark {
        SEEK_START,
        DECODE_START,
        CONVERT_START,
        DRAW_START,
        DRAW_END
    }

    private long frameStartTime;
    // Indexed by Mark.ordinal()
    private final long[] checkpoints = new long[Mark.values().length];
    
    // GC Monitoring
    private final List<GarbageCollectorMXBean> gcBeans;
    private long lastGCTime = 0;
    private long lastGCPollTime = 0;
    
    // EDT Monitoring
    private final Thread edtMonitor;
    private volatile long lastEDTPing = System.currentTimeMillis();
    private volatile boolean running = true;

    // Buffer Health
    private final AtomicInteger bufferSize = new AtomicInteger(0);
    
    // Moving Averages (EMA)
    private double avgTotal = 0;

    public PerformanceMonitor() {
        this.gcBeans = ManagementFactory.getGarbageCollectorMXBeans();
        
        // EDT Monitor Thread
        edtMonitor = new Thread(() -> {
            while (running) {
                long now = System.currentTimeMillis();
                long diff = now - lastEDTPing;
                
                // If ping is old, EDT is blocked
                if (diff > 100 && diff < 5000) { // >100ms freeze
                    System.err.println("[PERF] EDT BLOCKED for " + diff + "ms");
                }
                
                // Ping EDT
                SwingUtilities.invokeLater(() -> {
                    lastEDTPing = System.currentTimeMillis();
                });
                
                try {
                    Thread.sleep(50);
                } catch (InterruptedException e) {}
            }
        }, "Perf-EDT-Monitor");
        edtMonitor.setDaemon(true);
        edtMonitor.start();
    }

    public void startFrame() {
        frameStartTime = System.nanoTime();
        // Reset checkpoints
        for(int i=0; i<checkpoints.length; i++) checkpoints[i] = -1;
        
        // Poll GC occasionally (every ~500ms)
        long now = System.currentTimeMillis();
        if (now - lastGCPollTime > 500) {
            checkGC();
            lastGCPollTime = now;
        }
    }

    public void mark(Mark label) {
        checkpoints[label.ordinal()] = System.nanoTime();
    }

    public void updateBufferSize(int size) {
        bufferSize.set(size);
    }

    public void endFrame() {
        long end = System.nanoTime();
        long totalMs = (end - frameStartTime) / 1_000_000;
        
        // EMA Update
        if (avgTotal == 0) avgTotal = totalMs;
        else avgTotal = avgTotal * 0.9 + totalMs * 0.1;

        // Only log if slow (e.g. < 30 FPS => > 33ms)
        if (totalMs > 30) {
            StringBuilder sb = new StringBuilder();
            sb.append(String.format("[PERF] Frame: %dms", totalMs));
            
            long seekTime = getDuration(Mark.SEEK_START, Mark.DECODE_START);
            long decodeTime = getDuration(Mark.DECODE_START, Mark.CONVERT_START);
            long convertTime = getDuration(Mark.CONVERT_START, Mark.DRAW_START);
            long drawTime = getDuration(Mark.DRAW_START, Mark.DRAW_END, end);
            
            if (seekTime >= 0) sb.append(String.format(" | Seek: %dms", seekTime));
            if (decodeTime >= 0) sb.append(String.format(" | Decode: %dms", decodeTime));
            if (convertTime >= 0) sb.append(String.format(" | Conv: %dms", convertTime));
            if (drawTime >= 0) sb.append(String.format(" | Draw: %dms", drawTime));
            
            sb.append(" | Q: ").append(bufferSize.get());
            
            if (bufferSize.get() == 0) {
                 sb.append(" [BUFFER UNDERRUN]");
            }

            System.out.println(sb.toString());
        }
    }
    
    private long getDuration(Mark start, Mark end) {
        return getDuration(start, end, -1);
    }

    private long getDuration(Mark startLabel, Mark endLabel, long fallbackEnd) {
        long s = checkpoints[startLabel.ordinal()];
        if (s == -1) return -1;
        
        long e = -1;
        if (endLabel != null) {
            e = checkpoints[endLabel.ordinal()];
        }
        
        if (e == -1) e = fallbackEnd;
        if (e == -1) return -1;
        
        return (e - s) / 1_000_000;
    }

    private void checkGC() {
        long totalGCTime = 0;
        for (GarbageCollectorMXBean bean : gcBeans) {
            long count = bean.getCollectionCount();
            if (count > 0) {
                totalGCTime += bean.getCollectionTime();
            }
        }
        
        long diff = totalGCTime - lastGCTime;
        if (lastGCTime > 0 && diff > 10) { // >10ms pause
            System.out.println("\n[PERF] GC PAUSE detected: " + diff + "ms\n");
        }
        lastGCTime = totalGCTime;
    }
    
    public void stop() {
        running = false;
    }
}
