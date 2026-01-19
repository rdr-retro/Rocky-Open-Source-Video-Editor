#include "clip.h"

Clip::Clip(std::string n, long s, long d, double o, std::shared_ptr<MediaSource> src, int ti)
    : name(n), startFrame(s), durationFrames(d), sourceOffset(o), source(src), trackIndex(ti) {}

float Clip::getFadeValue(FadeType type, double t, bool isFadeIn) {
    if (t < 0.0) t = 0.0;
    if (t > 1.0) t = 1.0;

    double val = t;
    switch (type) {
        case FadeType::LINEAR: val = t; break;
        case FadeType::FAST:   val = std::pow(t, 0.25); break;
        case FadeType::SLOW:   val = std::pow(t, 4.0); break;
        case FadeType::SMOOTH: val = t * t * (3.0 - 2.0 * t); break;
        case FadeType::SHARP:  val = 0.5 * (std::sin(M_PI * (t - 0.5)) + 1.0); break;
    }

    return (float)(isFadeIn ? val : 1.0 - val);
}

float Clip::getOpacityAt(long absoluteFrame) {
    long localFrame = absoluteFrame - startFrame;
    float currentOpacity = opacity;

    if (fadeInFrames > 0 && localFrame < fadeInFrames) {
        double t = (double)localFrame / fadeInFrames;
        currentOpacity *= getFadeValue(fadeInType, t, true);
    }
    else if (fadeOutFrames > 0 && localFrame > (durationFrames - fadeOutFrames)) {
        long fadeOutStart = durationFrames - fadeOutFrames;
        double t = (double)(localFrame - fadeOutStart) / fadeOutFrames;
        currentOpacity *= getFadeValue(fadeOutType, t, false);
    }
    
    return std::max(0.0f, std::min(1.0f, currentOpacity));
}

Frame Clip::render(double time, int w, int h, double fps, long absoluteFrame) {
    // 1. Calculate local time
    double localTime = (double)(absoluteFrame - startFrame) / fps + sourceOffset;
    
    // Support for looping
    double srcDur = source->getDuration();
    if (srcDur > 0) {
        localTime = std::fmod(localTime, srcDur);
        if (localTime < 0) localTime += srcDur;
    }

    // 2. Fetch Source Frame (at project resolution)
    // Optimization: We could fetch at a smaller resolution if scale < 1.0, 
    // but for now we fetch at project size to maintain quality during zoom.
    Frame f = source->getFrame(localTime, w, h);
    if (f.data.empty()) return f;

    // 3. Apply Opacity Envelope
    float finalAlphaMult = getOpacityAt(absoluteFrame);
    if (finalAlphaMult < 1.0f) {
        for (size_t i = 3; i < f.data.size(); i += 4) {
            f.data[i] = (uint8_t)(f.data[i] * finalAlphaMult);
        }
    }

    // 4. Transform Logic (Resize / Move)
    // If transform is default (scale=1, pos=0), return as is.
    if (transform.scaleX == 1.0 && transform.scaleY == 1.0 && transform.x == 0 && transform.y == 0) {
        return f;
    }

    // Create a new canvas to hold the transformed frame
    Frame outFrame(w, h, 4); 
    // Fill with transparency (0)
    std::fill(outFrame.data.begin(), outFrame.data.end(), 0);

    // [VEGAS COMPOSITING MODEL]
    // Calculate new dimensions
    int newW = (int)(w * transform.scaleX);
    int newH = (int)(h * transform.scaleY);
    
    if (newW <= 0 || newH <= 0) return outFrame;

    // Center of the frame (Anchor logic)
    int centerX = (int)(w * 0.5);
    int centerY = (int)(h * 0.5);
    
    int startX = centerX - (newW / 2) + (int)(transform.x * w);
    int startY = centerY - (newH / 2) - (int)(transform.y * h); // +Y is Up

    // Simple Nearest Neighbor Scaling (Fast for Real-time dev)
    // TODO: Switch to Bilinear or GL textures for production quality
    for (int dstY = 0; dstY < h; ++dstY) {
        int srcY_rel = dstY - startY;
        if (srcY_rel < 0 || srcY_rel >= newH) continue;
        
        int srcY = (int)((srcY_rel / (double)newH) * h);
        if (srcY < 0 || srcY >= h) continue;

        for (int dstX = 0; dstX < w; ++dstX) {
            int srcX_rel = dstX - startX;
            if (srcX_rel < 0 || srcX_rel >= newW) continue;
            
            int srcX = (int)((srcX_rel / (double)newW) * w);
            if (srcX < 0 || srcX >= w) continue;

            // Copy pixel
            const uint32_t* srcPix = reinterpret_cast<const uint32_t*>(f.data.data()) + (srcY * w + srcX);
            uint32_t* dstPix = reinterpret_cast<uint32_t*>(outFrame.data.data()) + (dstY * w + dstX);
            *dstPix = *srcPix;
        }
    }

    return outFrame;
}
