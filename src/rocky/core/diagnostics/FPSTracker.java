package rocky.core.diagnostics;

/**
 * Tracks actual rendering FPS by measuring frame intervals.
 */
public class FPSTracker {
    private long lastFrameTime = 0;
    private double measuredFPS = 0;
    private final java.util.concurrent.ConcurrentLinkedQueue<Long> frameTimes = new java.util.concurrent.ConcurrentLinkedQueue<>();
    
    public void recordFrame() {
        long now = System.currentTimeMillis();
        if (lastFrameTime > 0) {
            frameTimes.offer(now);
            // Keep last 30 samples
            while (frameTimes.size() > 30) {
                frameTimes.poll();
            }
            
            // Calculate FPS from average interval
            if (frameTimes.size() >= 5) {
                long sum = 0;
                int count = 0;
                long prev = lastFrameTime;
                for (Long time : frameTimes) {
                    sum += (time - prev);
                    prev = time;
                    count++;
                }
                double avgInterval = sum / (double) count;
                measuredFPS = avgInterval > 0 ? 1000.0 / avgInterval : 0;
            }
        }
        lastFrameTime = now;
    }
    
    public double getMeasuredFPS() {
        return measuredFPS;
    }
    
    public void reset() {
        frameTimes.clear();
        lastFrameTime = 0;
        measuredFPS = 0;
    }
}
