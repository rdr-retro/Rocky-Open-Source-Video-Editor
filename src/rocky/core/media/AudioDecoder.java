package rocky.core.media;

import java.io.File;
import java.nio.ShortBuffer;
import org.bytedeco.javacv.*;
import org.bytedeco.ffmpeg.global.avutil;

/**
 * Extracts audio samples from media files using JavaCV.
 */
public class AudioDecoder {
    private File audioFile;
    private FFmpegFrameGrabber grabber;
    private int sampleRate = 48000;
    private int channels = 2;
    private long lastFrameNumber = -2;

    public AudioDecoder(File file) {
        this.audioFile = file;
    }

    public boolean init() {
        try {
            grabber = new FFmpegFrameGrabber(audioFile);
            grabber.setSampleRate(sampleRate);
            grabber.setAudioChannels(channels);
            grabber.start();
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public long getTotalFrames() {
        if (grabber == null) return 0;
        // FFmpeg lengths are in microseconds
        double durationSecs = grabber.getLengthInTime() / 1000000.0;
        return (long)(durationSecs * 30);
    }

    private short[] residualBuffer = null;
    private int residualOffset = 0;

    // Sliding Window Cache (approx 2 seconds of audio)
    private short[] slidingWindow = null;
    private long windowStartSample = -1;
    private final int WINDOW_SIZE_SAMPLES = 48000 * 2; 

    public short[] getAudioSampleAt(long sampleIndex) {
        try {
            if (grabber == null) return null;
            
            // 1. Check if sample is in sliding window
            if (slidingWindow != null && sampleIndex >= windowStartSample && 
                sampleIndex < windowStartSample + (slidingWindow.length / channels)) {
                int offset = (int)(sampleIndex - windowStartSample) * channels;
                return new short[]{slidingWindow[offset], slidingWindow[offset+1]};
            }
            
            // 2. Cache miss: Fetch a large block (Sliding Window)
            // We seek slightly before the sample to allow some reverse scrubbing buffer
            long seekTarget = Math.max(0, sampleIndex - (48000 / 2)); // 0.5s before
            long targetTimestamp = (long)((seekTarget / (double)sampleRate) * 1000000);
            grabber.setTimestamp(targetTimestamp);
            
            short[] buffer = new short[WINDOW_SIZE_SAMPLES * channels];
            int filled = 0;
            while (filled < buffer.length) {
                Frame frame = grabber.grabFrame(true, true, true, false);
                if (frame == null || frame.samples == null) break;
                
                ShortBuffer sb = (ShortBuffer) frame.samples[0];
                int toCopy = Math.min(sb.remaining(), buffer.length - filled);
                sb.get(buffer, filled, toCopy);
                filled += toCopy;
            }
            
            slidingWindow = buffer;
            windowStartSample = seekTarget;
            
            // Return requested sample from new buffer
            if (sampleIndex >= windowStartSample && sampleIndex < windowStartSample + (filled / channels)) {
                int offset = (int)(sampleIndex - windowStartSample) * channels;
                return new short[]{slidingWindow[offset], slidingWindow[offset+1]};
            }
        } catch (Exception e) {
            // e.printStackTrace();
        }
        return new short[]{0, 0}; 
    }

    public short[] getAudioSamples(long frameNumber, int durationFrames) {
        try {
            if (grabber == null) return null;
            
            // Mapping project frame (30fps) to microseconds
            long targetTimestamp = (long)((frameNumber / 30.0) * 1000000);
            
            // Optimization: If it's the next frame, don't seek! 
            if (frameNumber != lastFrameNumber + 1) {
                grabber.setTimestamp(targetTimestamp);
                residualBuffer = null;
                residualOffset = 0;
            }
            lastFrameNumber = frameNumber;
            
            int samplesToGet = (int)((sampleRate / 30.0) * durationFrames);
            short[] output = new short[samplesToGet * channels];
            int filled = 0;
            
            // 1. Take from residual first
            if (residualBuffer != null) {
                int available = residualBuffer.length - residualOffset;
                int toCopy = Math.min(available, output.length);
                System.arraycopy(residualBuffer, residualOffset, output, 0, toCopy);
                filled += toCopy;
                residualOffset += toCopy;
                
                if (residualOffset >= residualBuffer.length) {
                    residualBuffer = null;
                    residualOffset = 0;
                }
            }

            // 2. Grab more frames if needed
            while (filled < output.length) {
                Frame frame = grabber.grabFrame(true, true, true, false);
                if (frame == null || frame.samples == null) break;
                
                ShortBuffer sb = (ShortBuffer) frame.samples[0];
                short[] frameSamples = new short[sb.remaining()];
                sb.get(frameSamples);
                
                int needed = output.length - filled;
                int toCopy = Math.min(frameSamples.length, needed);
                
                System.arraycopy(frameSamples, 0, output, filled, toCopy);
                filled += toCopy;
                
                // Store leftovers
                if (toCopy < frameSamples.length) {
                    residualBuffer = frameSamples;
                    residualOffset = toCopy;
                }
            }
            
            return output;
        } catch (Exception e) {
            // e.printStackTrace();
        }
        return null;
    }

    public boolean hasAudio() {
        if (grabber == null) return false;
        return grabber.getAudioChannels() > 0;
    }

    public void close() {
        try {
            if (grabber != null) {
                grabber.stop();
                grabber.release();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
