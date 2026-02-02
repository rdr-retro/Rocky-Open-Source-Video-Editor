#pragma once
#include "media_source.h"
#include <string>
#include <vector>

enum class FadeType {
    LINEAR = 0,
    FAST = 1,
    SLOW = 2,
    SMOOTH = 3,
    SHARP = 4
};

struct Effect {
    std::string name;
    std::string pluginPath;
    bool enabled = true;
    
    Effect(std::string n, std::string p) : name(n), pluginPath(p) {}
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
    long long startTick, durationTicks;
    long long sourceOffsetTicks;
    std::shared_ptr<MediaSource> source;
    int trackIndex;
    
    // Atributos extendidos del nucleo Java
    float opacity = 1.0f;
    long long fadeInTicks = 0;
    long long fadeOutTicks = 0;
    FadeType fadeInType = FadeType::LINEAR;
    FadeType fadeOutType = FadeType::LINEAR;
    ClipTransform transform;
    
    std::vector<Effect> effects;
    
    Clip() : startTick(0), durationTicks(0), sourceOffsetTicks(0), trackIndex(0), opacity(1.0f) {}
    Clip(std::string n, long long s, long long d, long long o, std::shared_ptr<MediaSource> src, int ti);

    float getFadeValue(FadeType type, double t, bool isFadeIn);
    float getOpacityAt(long long absoluteTick);
    Frame render(long long tick, int w, int h, double fps);
};
