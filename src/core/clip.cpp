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

    // 2. Fetch Source Frame (at FULL project resolution to maintain quality)
    // CRITICAL for quality: We fetch the FULL source frame.
    // If we passed w/h here, we might get a pre-scaled thumbnail which looks bad when zoomed.
    // 2. Fetch Source Frame (at project resolution)
    // Optimization: We could fetch at a smaller resolution if scale < 1.0, 
    // but for now we fetch at project size to maintain quality during zoom.
    Frame f = source->getFrame(localTime, w, h);
    if (f.data.empty()) return f;

    // 3. Apply Opacity Envelope
    float finalAlphaMult = getOpacityAt(absoluteFrame);
    if (finalAlphaMult < 1.0f) {
        // Optimization: Process 4 bytes at a time if possible? 
        // For now, simple loop for safety.
        size_t limit = f.data.size();
        uint8_t* ptr = f.data.data();
        for (size_t i = 3; i < limit; i += 4) {
             ptr[i] = (uint8_t)(ptr[i] * finalAlphaMult);
        }
    }

    // 4. Transform Logic - THE FIX
    // Canvas dimensions: w, h
    Frame outFrame(w, h, 4); 
    // Clear to transparent
    std::fill(outFrame.data.begin(), outFrame.data.end(), 0);

    // Coordinate Systems:
    // Source Space: (0,0) is Top-Left of the source image. Width/Height = f.width, f.height.
    // Dest Space:   (0,0) is Top-Left of the main canvas. Width/Height = w, h.

    // User Params:
    // transform.x, transform.y: OFFSET from the CENTER of the canvas.
    //    (0,0) means the image center is at the canvas center.
    //    (100,0) means the image center is 100px to the right.
    // transform.rotation: Degrees clockwise.
    // transform.scaleX/Y: Scaling factor.

    const double degToRad = M_PI / 180.0;
    double theta = transform.rotation * degToRad;
    double cos_t = std::cos(theta);
    double sin_t = std::sin(theta);
    
    // Safe Scales
    double sx = (std::abs(transform.scaleX) < 0.001) ? 0.001 : transform.scaleX;
    double sy = (std::abs(transform.scaleY) < 0.001) ? 0.001 : transform.scaleY;

    // Centers
    double srcCX = f.width * 0.5;
    double srcCY = f.height * 0.5;
    
    // Target Center on Canvas
    // CanvasCenter + Offset
    double dstCX = (w * 0.5) + transform.x;
    double dstCY = (h * 0.5) + transform.y;

    // Inverse Mapping Loop
    // We iterate over the DESTINATION pixels and find which SOURCE pixel maps to it.
    
    // Optimization: Calculate Bounding Box to minimize loops
    // Corners of the Scaled & Rotated Image in Dest Space
    double hw = srcCX * sx;
    double hh = srcCY * sy;

    // 4 corners relative to (0,0) BEFORE rotation/translation
    // Top-Left (-hw, -hh), Top-Right (hw, -hh), Bottom-Right (hw, hh), Bottom-Left (-hw, hh)
    double c_x[] = {-hw,  hw, hw, -hw};
    double c_y[] = {-hh, -hh, hh,  hh};
    
    double minX = w, maxX = 0;
    double minY = h, maxY = 0;
    
    for(int i=0; i<4; ++i) {
        // Rotate and Translate
        double rx = c_x[i] * cos_t - c_y[i] * sin_t + dstCX;
        double ry = c_x[i] * sin_t + c_y[i] * cos_t + dstCY;
        
        if (rx < minX) minX = rx;
        if (rx > maxX) maxX = rx;
        if (ry < minY) minY = ry;
        if (ry > maxY) maxY = ry;
    }

    // Clip to Canvas Bounds
    int startX = std::max(0, (int)std::floor(minX));
    int endX   = std::min(w, (int)std::ceil(maxX) + 1);
    int startY = std::max(0, (int)std::floor(minY));
    int endY   = std::min(h, (int)std::ceil(maxY) + 1);
    
    // Parallelize Y loop? For now single thread is safer inside evaluate's async
    // Precalculate safe bounds for source to avoid boundary checks inside inner loop
    int srcMaxX = f.width - 1;
    int srcMaxY = f.height - 1;
    
    // Access pointers
    const uint32_t* srcData = reinterpret_cast<const uint32_t*>(f.data.data());
    uint32_t* dstData = reinterpret_cast<uint32_t*>(outFrame.data.data());

    // Optimized calculation outside the pixel loop
    const double invSx = 1.0 / sx;
    const double invSy = 1.0 / sy;
    
    for (int y = startY; y < endY; ++y) {
        // Pre-calculate Y-dependent components of the inverse transform
        double bY = y - dstCY;
        double rX_base = bY * sin_t;
        double rY_base = bY * cos_t;
        uint32_t* rowDst = dstData + (y * w);

        for (int x = startX; x < endX; ++x) {
            double bX = x - dstCX;
            
            // Inverse Rotate + Scale + Translate
            double rX = (bX * cos_t + rX_base) * invSx;
            double rY = (-bX * sin_t + rY_base) * invSy;
            
            int iU = static_cast<int>(rX + srcCX);
            int iV = static_cast<int>(rY + srcCY);
            
            if (iU >= 0 && iU <= srcMaxX && iV >= 0 && iV <= srcMaxY) {
                rowDst[x] = srcData[iV * f.width + iU];
            }
        }
    }

    return outFrame;
}
