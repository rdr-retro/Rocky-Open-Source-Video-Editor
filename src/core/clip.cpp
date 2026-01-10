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
    // Usar absoluteFrame (entero) en lugar de time (double) para evitar jitter de redondeo
    double localTime = (double)(absoluteFrame - startFrame) / fps + sourceOffset;
    Frame f = source->getFrame(localTime, w, h);
    
    float finalAlphaMult = getOpacityAt(absoluteFrame);
    if (finalAlphaMult < 1.0f) {
        for (size_t i = 3; i < f.data.size(); i += 4) {
            f.data[i] = (uint8_t)(f.data[i] * finalAlphaMult);
        }
    }
    return f;
}
