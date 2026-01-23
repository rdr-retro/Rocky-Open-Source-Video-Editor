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

    // 4. Transform Logic (Resize / Move / Rotate)
    // If transform is default, return as is.
    if (transform.scaleX == 1.0 && transform.scaleY == 1.0 && transform.x == 0 && transform.y == 0 && transform.rotation == 0.0) {
        return f;
    }

    // Create a new canvas (transparent)
    Frame outFrame(w, h, 4); 
    std::fill(outFrame.data.begin(), outFrame.data.end(), 0);

    // [VEGAS COMPOSITING MODEL]
    // 1. Calculate transformation matrix components
    // We map DST (output) pixels -> SRC (input) pixels (Inverse Mapping)
    
    // Convert degrees to radians
    double theta = transform.rotation * M_PI / 180.0;
    double cos_t = std::cos(theta);
    double sin_t = std::sin(theta);
    
    // Scale factors (avoid division by zero)
    double sx = (std::abs(transform.scaleX) < 0.001) ? 0.001 : transform.scaleX;
    double sy = (std::abs(transform.scaleY) < 0.001) ? 0.001 : transform.scaleY;
    
    // Anchor point in Source (usually center of source frame)
    // Adjust anchor based on user setting (transform.anchorX/Y are 0..1)
    double anchorSrcX = f.width * transform.anchorX;
    double anchorSrcY = f.height * transform.anchorY;

    // Center of Dest Canvas
    double centerDstX = w * 0.5;
    double centerDstY = h * 0.5;
    
    // Translation relative to center
    // If transform.x is relative to canvas width? Assuming absolute pixels or normalized?
    // In bindings it seems treated as pixels based on UI usage.
    double transX = transform.x;
    double transY = transform.y; 

    // Inverse Logic:
    // 1. Start at P_dst
    // 2. Subtract Effective Center (CenterDst + Translation)
    // 3. Inverse Rotate
    // 4. Inverse Scale
    // 5. Add Anchor Source
    
    // Precompute constants
    double offX = centerDstX + transX; // The point in DST corresponding to Anchor in SRC
    double offY = centerDstY - transY; // Y is inverted in UI usually, but let's stick to standard Graphics Y-down or Y-up?
                                       // In Clip::render previously: startY = centerY - ... - (transform.y * h)
                                       // This implies transform.y is normalized?
                                       // Let's assume transform.x/y are PIXELS for simplicity in specific C++ engine context unless normalized specified.
                                       // Previous code: int startX = centerX - (newW / 2) + (int)(transform.x * w);
                                       // It multiplied by w, so transform.x was Normalized.
                                       
    // Re-evaluating transform.x usage:
    // User passes 0, or calculated pixel values in python?
    // In subtitle_panel.py: sub_clip.transform.x = clip_x (PIXELS calculated from width)
    // Wait, previous python code: `clip_x = (width - img_w) / 2` -> Pixels.
    // But previous C++ code: `(int)(transform.x * w)`.
    // IF PYTHON PASSES PIXELS, AND C++ MULTIPLIES BY W, IT'S WRONG.
    // This explains why positioning was hard!
    
    // Let's FIX IT to be PIXELS.
    // If input is pixels, we use it directly.
    // BUT Python code previously used `rx = ... / preview.width()` (Normalized)?
    // Let's check subtitle_panel.py recent edit.
    // It calculated `clip_x` in pixels.
    // So C++ expects Pixels? Or Normalized?
    // `subtitle_panel.py`: `sub_clip.transform.x = 0.0`
    // If I change C++ to treat x/y as PIXELS, it's safer/clearer for this engine.
    
    // Let's assume passed values are PIXELS.
    double tX = transform.x;
    double tY = transform.y; // Standard cartesian: +Y is Up?? No, image logic usually +Y Down.
                             // Previous code: `centerY - ... - (transform.y * h)`. This inverted Y.
                             // We should stick to top-left origin +Y Down standard for simplicity.
    
    // Effective destination origin for the image
    // If I place image at (100, 100), that's top-left corner?
    // Or center?
    // Let's standardized: transform.x/y is the position of the ANCHOR on the CANVAS.
    
    double originX = tX + (w * 0.5); // If tX is offset from center?
    // Let's define: transform.x, transform.y are ABSOLUTE coordinates of top-left corner of the clip?
    // Previous C++: `startX = centerX - (newW/2) + ...` implies offset from center.
    // My Python code: `sub_clip.transform.y = ty` where ty is absolute Y.
    
    // Fix: Treat transform.x/y as ABSOLUTE TOP-LEFT coordinates if rotation is 0.
    // But with rotation, "Top-Left" is ambiguous.
    // Let's use: transform.x/y is the PIXEL position of the ANCHOR point.
    // And we Default Anchor to 0.5 (Center).
    
    // BUT Python sets `transform.x = 0`, `transform.y = ty` (Top-Left essentially).
    // And `anchor = 0.5`.
    // This is conflicting.
    
    // Compromise for minimal breaking changes:
    // Treat transform.x/y as PIXEL OFFSETS from CANVAS CENTER (0,0) if normalized=false, or absolute?
    // The cleanest for VSE is: X,Y top-left.
    // Let's write the loop to map efficiently.
    
    // Let's respect what `subtitle_panel.py` does:
    // It sets `sub_clip.transform.x = 0` (Left)
    // `sub_clip.transform.y = ty` (Top)
    
    // So we want the Source(0,0) to map to Dest(transform.x, transform.y).
    // Center of Source maps to Dest(transform.x + newW/2, transform.y + newH/2).
    
    // With rotation, we rotate around the Center.
    
    double srcW = (double)f.width;
    double srcH = (double)f.height;
    
    double cx = srcW * 0.5;
    double cy = srcH * 0.5;
    
    // Destination Center (where we want the source center to end up)
    // If x,y are top-left:
    double dstCX = transform.x + (srcW * sx * 0.5);
    double dstCY = transform.y + (srcH * sy * 0.5);
    
    // Optimization: Bounding box check to avoid iterating all WxH of canvas?
    // For now, iterate canvas WxH (slower but correct). 
    // Ideally we iterate only the bounding box of the rotated rect.
    
    // Bounding Box Calculation:
    // Corners relative to center: (-w/2, -h/2), (w/2, -h/2), ...
    // Rotate, Scale, + DstCenter.
    // Compute min/max X/Y.
    
    double hw = srcW * sx * 0.5;
    double hh = srcH * sy * 0.5;
    
    // Corners pre-rotation
    double c1x = -hw, c1y = -hh;
    double c2x =  hw, c2y = -hh;
    double c3x =  hw, c3y =  hh;
    double c4x = -hw, c4y =  hh;
    
    auto rotX = [&](double x, double y) { return x*cos_t - y*sin_t + dstCX; };
    auto rotY = [&](double x, double y) { return x*sin_t + y*cos_t + dstCY; };
    
    double rx1 = rotX(c1x, c1y), ry1 = rotY(c1x, c1y);
    double rx2 = rotX(c2x, c2y), ry2 = rotY(c2x, c2y);
    double rx3 = rotX(c3x, c3y), ry3 = rotY(c3x, c3y);
    double rx4 = rotX(c4x, c4y), ry4 = rotY(c4x, c4y);
    
    int minX = std::max(0, (int)std::floor(std::min({rx1, rx2, rx3, rx4})));
    int maxX = std::min(w, (int)std::ceil(std::max({rx1, rx2, rx3, rx4})) + 1);
    int minY = std::max(0, (int)std::floor(std::min({ry1, ry2, ry3, ry4})));
    int maxY = std::min(h, (int)std::ceil(std::max({ry1, ry2, ry3, ry4})) + 1);
    
    for (int y = minY; y < maxY; ++y) {
        for (int x = minX; x < maxX; ++x) {
            // Inverse map pixel (x,y) to Source space
            
            // 1. Relative to Center
            double dx = x - dstCX;
            double dy = y - dstCY;
            
            // 2. Inverse Rotate
            // Rotate by -theta
            double irx = dx * cos_t + dy * sin_t;
            double iry = -dx * sin_t + dy * cos_t;
            
            // 3. Inverse Scale
            double isx = irx / sx;
            double isy = iry / sy;
            
            // 4. Map to Source Coord
            // Source Center is (srcW/2, srcH/2)
            double u = isx + cx;
            double v = isy + cy;
            
            // Nearest Neighbor
            int srcX = (int)u;
            int srcY = (int)v;
            
            if (srcX >= 0 && srcX < f.width && srcY >= 0 && srcY < f.height) {
                const uint32_t* srcPix = reinterpret_cast<const uint32_t*>(f.data.data()) + (srcY * f.width + srcX);
                uint32_t* dstPix = reinterpret_cast<uint32_t*>(outFrame.data.data()) + (y * w + x);
                *dstPix = *srcPix;
            }
        }
    }

    return outFrame;
}
