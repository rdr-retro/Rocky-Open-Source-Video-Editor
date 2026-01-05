package rocky.core.engine;

import javax.sound.sampled.*;

/**
 * Diagnostic tool to verify if the OS audio line can be opened and played.
 */
public class AudioHardwareTest {
    public static void main(String[] args) {
        System.out.println("=== Audio Hardware Diagnostic ===");
        try {
            AudioFormat format = new AudioFormat(48000, 16, 2, true, false);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, format);
            
            if (!AudioSystem.isLineSupported(info)) {
                System.err.println("CRITICAL: Audio format NOT supported by hardware!");
                return;
            }
            
            SourceDataLine line = (SourceDataLine) AudioSystem.getLine(info);
            System.out.println("Opening audio line...");
            line.open(format);
            System.out.println("Starting audio line...");
            line.start();
            
            System.out.println("Generating 1-second 440Hz sine wave...");
            byte[] buffer = new byte[48000 * 4]; // 1s
            for (int i = 0; i < 48000; i++) {
                short s = (short) (Math.sin(2 * Math.PI * 440 * i / 48000.0) * 16383);
                buffer[i * 4] = (byte) (s & 0xFF);
                buffer[i * 4 + 1] = (byte) (s >> 8);
                buffer[i * 4 + 2] = (byte) (s & 0xFF);
                buffer[i * 4 + 3] = (byte) (s >> 8);
            }
            
            System.out.println("Writing to audio line...");
            int written = line.write(buffer, 0, buffer.length);
            System.out.println("Bytes written: " + written);
            
            line.drain();
            line.close();
            System.out.println("SUCCESS: Hardware audio path is functional.");
        } catch (Exception e) {
            System.err.println("FAILED: Audio hardware error:");
            e.printStackTrace();
        }
    }
}
