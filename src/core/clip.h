#pragma once
#include "media_source.h"

enum class FadeType {
    LINEAR = 0,
    FAST = 1,
    SLOW = 2,
    SMOOTH = 3,
    SHARP = 4
};

struct ClipTransform {
    double x = 0;
    double y = 0;
    double scaleX = 1.0;
    double scaleY = 1.0;
    double rotation = 0;
    double anchorX = 0.5;
    double anchorY = 0.5;
};

struct Clip {
    std::string name;
    long startFrame, durationFrames;
    double sourceOffset;
    std::shared_ptr<MediaSource> source;
    int trackIndex;
    
    // Atributos extendidos del nucleo Java
    float opacity = 1.0f;
    long fadeInFrames = 0;
    long fadeOutFrames = 0;
    FadeType fadeInType = FadeType::LINEAR;
    FadeType fadeOutType = FadeType::LINEAR;
    ClipTransform transform;

    Clip(std::string n, long s, long d, double o, std::shared_ptr<MediaSource> src, int ti);

    float getFadeValue(FadeType type, double t, bool isFadeIn);
    float getOpacityAt(long absoluteFrame);
    Frame render(double time, int w, int h, double fps, long absoluteFrame);
};
