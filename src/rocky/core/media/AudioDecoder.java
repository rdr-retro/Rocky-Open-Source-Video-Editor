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
    private final double PROJECT_FPS = 30.0;

    public AudioDecoder(File file) {
        this.audioFile = file;
    }

    public boolean init() {
        try {
            System.out.println("[AudioDecoder] Initializing for: " + audioFile.getName());
            grabber = new FFmpegFrameGrabber(audioFile);
            grabber.setSampleRate(sampleRate);
            grabber.setAudioChannels(channels);
            grabber.start();
            System.out.println("[AudioDecoder] SUCCESS. Channels: " + grabber.getAudioChannels() + " Format: " + grabber.getSampleFormat());
            return true;
        } catch (Exception e) {
            System.err.println("[AudioDecoder] FAILED init: " + audioFile.getName());
            e.printStackTrace();
            return false;
        }
    }

    public long getTotalFrames() {
        if (grabber == null) return 0;
        double durationSecs = grabber.getLengthInTime() / 1000000.0;
        return (long)(durationSecs * PROJECT_FPS);
    }

    public int getSamplesPerFrame() {
        return (int)((sampleRate / PROJECT_FPS) * channels);
    }

    private short[] residualBuffer = null;
    private int residualOffset = 0;

    // Sliding Window Cache (approx 2 seconds of audio)
    private short[] slidingWindow = null;
    private long windowStartSample = -1;
    private final int WINDOW_SIZE_SAMPLES = 48000 * 2; 

    private short[] extractSamples(Frame frame) {
        if (frame == null || frame.samples == null) return null;
        
        int channels = frame.samples.length;
        int samplesPerChannel = 0;
        if (frame.samples[0] instanceof java.nio.Buffer) {
            samplesPerChannel = ((java.nio.Buffer)frame.samples[0]).remaining();
        }
        
        short[] output = new short[samplesPerChannel * channels];
        
        // Efficient extraction
        if (channels > 1 && frame.samples[1] != null) {
            for (int c = 0; c < channels; c++) {
                if (frame.samples[c] instanceof ShortBuffer) {
                    ShortBuffer sb = (ShortBuffer) frame.samples[c];
                    for (int s = 0; s < samplesPerChannel; s++) output[s * channels + c] = sb.get();
                } else if (frame.samples[c] instanceof java.nio.FloatBuffer) {
                    java.nio.FloatBuffer fb = (java.nio.FloatBuffer) frame.samples[c];
                    for (int s = 0; s < samplesPerChannel; s++) output[s * channels + c] = (short)(fb.get() * 32767);
                }
            }
        } else {
            if (frame.samples[0] instanceof ShortBuffer) {
                ((ShortBuffer)frame.samples[0]).get(output);
            } else if (frame.samples[0] instanceof java.nio.FloatBuffer) {
                java.nio.FloatBuffer fb = (java.nio.FloatBuffer) frame.samples[0];
                for (int i = 0; i < output.length; i++) output[i] = (short)(fb.get() * 32767);
            }
        }
        return output;
    }

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
                Frame frame = grabber.grabSamples();
                short[] s = extractSamples(frame);
                if (s == null) break;
                
                int toCopy = Math.min(s.length, buffer.length - filled);
                System.arraycopy(s, 0, buffer, filled, toCopy);
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
            System.err.println("[AudioDecoder] Error in getAudioSampleAt: " + e.getMessage());
            // e.printStackTrace();
        }
        return new short[]{0, 0}; 
    }

    public short[] getAudioSamples(long frameNumber, int durationFrames) {
        try {
            if (grabber == null) return null;
            
            // Mapping project frame to microseconds
            long targetTimestamp = (long)((frameNumber / PROJECT_FPS) * 1000000);
            
            // Optimization: Relax seek threshold to 30ms (approx 1 frame)
            // Smaller thresholds cause constant re-seeking due to minor timestamp jitter.
            long currentTs = grabber.getTimestamp();
            if (frameNumber == 0 || Math.abs(currentTs - targetTimestamp) > 33333) {
                 grabber.setTimestamp(targetTimestamp);
                 residualBuffer = null;
                 residualOffset = 0;
            }
            
            int samplesToGet = (int)((sampleRate / PROJECT_FPS) * durationFrames);
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

            while (filled < output.length) {
                Frame frame = grabber.grabSamples();
                if (frame == null) {
                    // System.out.println("[AudioDecoder] grabSamples() returned NULL (EOF?) at frame " + frameNumber);
                    break;
                }
                short[] frameSamples = extractSamples(frame);
                if (frameSamples == null) continue; 
                
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
