package rocky.core.engine;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;

/**
 * High-performance Color Management utilities.
 * Implements a "Lite" ACES Film Tone Mapper for a professional look.
 */
public class ColorManagement {
    private static final int[] ACES_LUT = new int[256];

    static {
        // Pre-calculate ACES Tone Mapping Curve (Narkowicz Approximation)
        // This gives a nice filmic highlight roll-off and contrast boost.
        for (int i = 0; i < 256; i++) {
            float x = i / 255.0f;
            
            // Narkowicz ACES RRT+ODT fit
            float a = 2.51f;
            float b = 0.03f;
            float c = 2.43f;
            float d = 0.59f;
            float e = 0.14f;
            float y = (x * (a * x + b)) / (x * (c * x + d) + e);
            
            ACES_LUT[i] = Math.min(255, Math.max(0, (int) (y * 255.0f)));
        }
    }

    /**
     * Applies the ACES tone mapping curve to an image in-place.
     * Uses a LUT for O(N) performance, suitable for real-time 4K preview.
     */
    public static void applyAces(BufferedImage image) {
        if (image == null) return;
        
        // Fast path for INT_ARGB/RGB (standard in Rocky)
        if (image.getRaster().getDataBuffer() instanceof DataBufferInt) {
            int[] pixels = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
            for (int i = 0; i < pixels.length; i++) {
                int argb = pixels[i];
                
                // Extract channels
                int alpha = argb & 0xFF000000; // Preserve alpha
                int r = (argb >> 16) & 0xFF;
                int g = (argb >> 8) & 0xFF;
                int b = argb & 0xFF;

                // Apply LUT
                r = ACES_LUT[r];
                g = ACES_LUT[g];
                b = ACES_LUT[b];

                // Pack back
                pixels[i] = alpha | (r << 16) | (g << 8) | b;
            }
        } else {
            // Slower fallback for other image types
            int w = image.getWidth();
            int h = image.getHeight();
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    int argb = image.getRGB(x, y);
                    int alpha = argb & 0xFF000000;
                    int r = ACES_LUT[(argb >> 16) & 0xFF];
                    int g = ACES_LUT[(argb >> 8) & 0xFF];
                    int b = ACES_LUT[argb & 0xFF];
                    image.setRGB(x, y, alpha | (r << 16) | (g << 8) | b);
                }
            }
        }
    }
}
