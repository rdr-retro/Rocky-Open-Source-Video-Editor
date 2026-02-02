#include "clip.h"
#include "common.h" // For TICKS_PER_SECOND
#include <cmath>

Clip::Clip(std::string n, long long s, long long d, long long o,
           std::shared_ptr<MediaSource> src, int ti)
    : name(n), startTick(s), durationTicks(d), sourceOffsetTicks(o), source(src),
      trackIndex(ti) {}

float Clip::getFadeValue(FadeType type, double t, bool isFadeIn) {
  if (t < 0.0)
    t = 0.0;
  if (t > 1.0)
    t = 1.0;

  double val = t;
  switch (type) {
  case FadeType::LINEAR:
    val = t;
    break;
  case FadeType::FAST:
    val = std::pow(t, 0.25);
    break;
  case FadeType::SLOW:
    val = std::pow(t, 4.0);
    break;
  case FadeType::SMOOTH:
    val = t * t * (3.0 - 2.0 * t);
    break;
  case FadeType::SHARP:
    val = 0.5 * (std::sin(M_PI * (t - 0.5)) + 1.0);
    break;
  }

  return (float)(isFadeIn ? val : 1.0 - val);
}

float Clip::getOpacityAt(long long absoluteTick) {
  long long localTick = absoluteTick - startTick;
  float currentOpacity = opacity;

  if (fadeInTicks > 0 && localTick < fadeInTicks) {
    double t = (double)localTick / fadeInTicks;
    currentOpacity *= getFadeValue(fadeInType, t, true);
  } else if (fadeOutTicks > 0 &&
             localTick > (durationTicks - fadeOutTicks)) {
    long long fadeOutStart = durationTicks - fadeOutTicks;
    double t = (double)(localTick - fadeOutStart) / fadeOutTicks;
    currentOpacity *= getFadeValue(fadeOutType, t, false);
  }

  return std::max(0.0f, std::min(1.0f, currentOpacity));
}

Frame Clip::render(long long tick, int w, int h, double fps) {
  // 1. Calculate local time in SECONDS
  // Using global constant TICKS_PER_SECOND (60000) for deterministic conversion
  double localTime = (double)(tick - startTick + sourceOffsetTicks) / TICKS_PER_SECOND;

  // Support for looping
  double srcDur = source->getDuration();
  if (srcDur > 0) {
    localTime = std::fmod(localTime, srcDur);
    if (localTime < 0)
      localTime += srcDur;
  }

  // 2. Fetch Source Frame (at NATIVE resolution)
  int nativeW = source->getWidth();
  int nativeH = source->getHeight();
  Frame f = source->getFrame(localTime, nativeW, nativeH);
  if (f.data.empty())
    return f;

  // 3. Apply Opacity Envelope
  float finalAlphaMult = getOpacityAt(tick);
  if (finalAlphaMult < 1.0f) {
    size_t limit = f.data.size();
    uint8_t *ptr = f.data.data();
    for (size_t i = 3; i < limit; i += 4) {
      ptr[i] = (uint8_t)(ptr[i] * finalAlphaMult);
    }
  }

  // 4. Transform Logic
  Frame outFrame(w, h, 4);
  std::fill(outFrame.data.begin(), outFrame.data.end(), 0);

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
  double dstCX = (w * 0.5) + transform.x;
  double dstCY = (h * 0.5) + transform.y;

  // Optimize bounding box logic calculation...
  double hw = srcCX * sx;
  double hh = srcCY * sy;

  double c_x[] = {-hw, hw, hw, -hw};
  double c_y[] = {-hh, -hh, hh, hh};

  double minX = w, maxX = 0;
  double minY = h, maxY = 0;

  for (int i = 0; i < 4; ++i) {
    double rx = c_x[i] * cos_t - c_y[i] * sin_t + dstCX;
    double ry = c_x[i] * sin_t + c_y[i] * cos_t + dstCY;

    if (rx < minX) minX = rx;
    if (rx > maxX) maxX = rx;
    if (ry < minY) minY = ry;
    if (ry > maxY) maxY = ry;
  }

  int startX = std::max(0, (int)std::floor(minX));
  int endX = std::min(w, (int)std::ceil(maxX) + 1);
  int startY = std::max(0, (int)std::floor(minY));
  int endY = std::min(h, (int)std::ceil(maxY) + 1);

  int srcMaxX = f.width - 1;
  int srcMaxY = f.height - 1;

  const uint32_t *srcData = reinterpret_cast<const uint32_t *>(f.data.data());
  uint32_t *dstData = reinterpret_cast<uint32_t *>(outFrame.data.data());

  const double invSx = 1.0 / sx;
  const double invSy = 1.0 / sy;

  for (int y = startY; y < endY; ++y) {
    double bY = y - dstCY;
    double rX_base = bY * sin_t;
    double rY_base = bY * cos_t;
    uint32_t *rowDst = dstData + (y * w);

    for (int x = startX; x < endX; ++x) {
      double bX = x - dstCX;

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
