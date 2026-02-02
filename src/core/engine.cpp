#include "engine.h"
#include "ofx/host.h"
#include <cmath>

#ifdef ENABLE_ACCELERATE
#include <Accelerate/Accelerate.h>
#endif

// Define static constant for linker
const long long RockyEngine::TICKS_PER_SECOND;

void RockyEngine::setResolution(int w, int h) { std::lock_guard<std::mutex> lock(mtx); width = w; height = h; }
void RockyEngine::setFPS(double f) { std::lock_guard<std::mutex> lock(mtx); fps = f; }
void RockyEngine::addTrack(int type) { std::lock_guard<std::mutex> lock(mtx); trackTypes.push_back(type); }
void RockyEngine::setMasterGain(double gain) { std::lock_guard<std::mutex> lock(mtx); masterGain = gain; }

std::shared_ptr<Clip> RockyEngine::addClip(int trackIdx, std::string name, long long startTick, long long durTicks, long long offsetTicks, std::shared_ptr<MediaSource> src) {
    std::lock_guard<std::mutex> lock(mtx);
    auto clip = std::make_shared<Clip>(name, startTick, durTicks, offsetTicks, src, trackIdx);
    clipTree.add(startTick, startTick + durTicks, clip);
    return clip;
}

void RockyEngine::clear() {
    std::lock_guard<std::mutex> lock(mtx);
    clipTree.clear();
    trackTypes.clear();
}

/**
 * @brief Processes and composites a single video frame for a specific TICK.
 * 
 * Replaces evaluate(double time).
 * Uses absolute TICKS (1/60000 sec) for perfect determinism.
 * 
 * @param tick Absolute timeline tick.
 * @return py::array_t<uint8_t> RGBA Buffer.
 */
py::array_t<uint8_t> RockyEngine::evaluate(long long tick) {
    std::vector<std::shared_ptr<Clip>> visibleVideoClips;
    int curW, curH;
    double curFps;

    {
        std::lock_guard<std::mutex> lock(mtx);
        std::vector<std::shared_ptr<Clip>> activeClips = clipTree.query(tick);
        
        for (const auto& clip : activeClips) {
            bool isValidTrack = clip->trackIndex >= 0 && clip->trackIndex < static_cast<int>(trackTypes.size());
            if (isValidTrack && trackTypes[clip->trackIndex] == 1) { // 1 = VIDEO
                visibleVideoClips.push_back(clip);
            }
        }
        curW = width;
        curH = height;
        curFps = fps;
    }
    
    // Sort by track index ASCENDING (Painter's Algorithm)
    std::sort(visibleVideoClips.begin(), visibleVideoClips.end(), 
        [](const auto& first, const auto& second) {
            return first->trackIndex < second->trackIndex;
        }
    );

    const size_t totalPixelBytes = static_cast<size_t>(curW * curH * 4);
    
    // 1. LOCAL CANVAS
    std::vector<uint8_t> localCanvas(totalPixelBytes);
    
    // Fast Clear (Black Background)
    uint32_t* pixelPtr = reinterpret_cast<uint32_t*>(localCanvas.data());
    size_t pixelCount = totalPixelBytes / 4;
    const uint32_t bgColor = 0xFF000000; 
    std::fill_n(pixelPtr, pixelCount, bgColor);

    // 2. PARALLEL RENDERING
    std::vector<std::future<Frame>> futureFrames;
    futureFrames.reserve(visibleVideoClips.size());
    
    {
        // HEAVY WORK: Release GIL
        py::gil_scoped_release release;

        // STAGE A: Launch background renders
        // Note: Render uses TICK, so we pass TICK directly.
        for (auto& clip : visibleVideoClips) {
             futureFrames.push_back(std::async(std::launch::async, 
                [clip, tick, curW, curH, curFps]() {
                    return clip->render(tick, curW, curH, curFps);
                }
             ));
        }

        // STAGE B: Composite results
        for (size_t i = 0; i < visibleVideoClips.size(); ++i) {
            Frame currentLayer = futureFrames[i].get();
            if (currentLayer.data.empty()) continue;

            // --- APPLY EFFECTS ---
            auto clip = visibleVideoClips[i];
            for (const auto& effect : clip->effects) {
                if (effect.enabled) {
                    RockyOfxHost::getInstance().executePluginRender(
                        effect.pluginPath, 
                        currentLayer.data.data(),
                        currentLayer.data.data(),
                        currentLayer.width, 
                        currentLayer.height
                    );
                }
            }
            // ---------------------

            const uint8_t* src = currentLayer.data.data();
            uint8_t* dst = localCanvas.data();
            
            // Blending Logic
            const uint32_t* src32 = reinterpret_cast<const uint32_t*>(src);
            uint32_t* dst32 = reinterpret_cast<uint32_t*>(dst);
            const size_t pixelCount = totalPixelBytes / 4;

            for (size_t k = 0; k < pixelCount; ++k) {
                uint32_t s = src32[k];
                uint8_t alpha = (s >> 24) & 0xFF;
                if (alpha == 0) continue;
                if (alpha == 255) {
                    dst32[k] = s;
                } else {
                    uint32_t d = dst32[k];
                    uint32_t invAlpha = 255 - alpha;
                    
                    uint32_t rb = ((s & 0x00FF00FF) * alpha + (d & 0x00FF00FF) * invAlpha) >> 8;
                    uint32_t g  = ((s & 0x0000FF00) * alpha + (d & 0x0000FF00) * invAlpha) >> 8;
                    
                    dst32[k] = (rb & 0x00FF00FF) | (g & 0x0000FF00) | 0xFF000000;
                }
            }
        }
    }

    // CREATE NUMPY ARRAY: ZERO-COPY
    auto* ptr = new std::vector<uint8_t>(std::move(localCanvas));
    py::capsule free_when_done(ptr, [](void* f) {
        delete reinterpret_cast<std::vector<uint8_t>*>(f);
    });

    return py::array_t<uint8_t>(
        {curH, curW, 4},
        { (size_t)(curW * 4), (size_t)4, (size_t)1 },
        ptr->data(),
        free_when_done
    );
}

py::array_t<float> RockyEngine::render_audio(long long startTick, long long durationTicks) {
    std::vector<std::shared_ptr<Clip>> audioClips;
    double curMasterGain;
    
    // Calculate precise float duration for buffer sizing
    double durationSeconds = (double)durationTicks / TICKS_PER_SECOND;
    
    const int targetSampleRate = 44100;
    const int totalSamples = static_cast<int>(durationSeconds * targetSampleRate);

    {
        std::lock_guard<std::mutex> lock(mtx);
        
        long long endTick = startTick + durationTicks;
        std::vector<std::shared_ptr<Clip>> activeClips = clipTree.query(startTick, endTick);
        
        for (const auto& clip : activeClips) {
            if (clip->trackIndex >= 0 && clip->trackIndex < static_cast<int>(trackTypes.size()) && trackTypes[clip->trackIndex] == 2) {
                audioClips.push_back(clip);
            }
        }
        curMasterGain = masterGain;
    }
    
    std::vector<float> mixedAudio(totalSamples * 2, 0.0f);
    
    {
        py::gil_scoped_release release;
        
        for (const auto& clip : audioClips) {
            if (!clip->source) continue;
                
            // Intersection Range in TICKS
            long long intersectStart = std::max(startTick, clip->startTick);
            long long intersectEnd = std::min(startTick + durationTicks, clip->startTick + clip->durationTicks);
            
            if (intersectEnd > intersectStart) {
                long long overlapLenTicks = intersectEnd - intersectStart;
                double overlapLenSec = (double)overlapLenTicks / TICKS_PER_SECOND;
                
                // Local Time calculation
                long long tickOffsetIntoClip = intersectStart - clip->startTick + clip->sourceOffsetTicks;
                double localStartSec = (double)tickOffsetIntoClip / TICKS_PER_SECOND;
                
                // Get samples for just this overlap (Polymorphic)
                std::vector<float> samples = clip->source->getAudioSamples(localStartSec, overlapLenSec);
                
                // Mix into main buffer
                long long offsetFromReqStartTicks = intersectStart - startTick;
                double offsetFromReqStartSec = (double)offsetFromReqStartTicks / TICKS_PER_SECOND;
                int bufferOffset = static_cast<int>(offsetFromReqStartSec * targetSampleRate) * 2;
                
                size_t samplesToMix = std::min(mixedAudio.size() - bufferOffset, samples.size());
                
                if (samplesToMix > 0) {
                    float opacity = static_cast<float>(clip->opacity);
                    float* dstPtr = mixedAudio.data() + bufferOffset;
                    const float* srcPtr = samples.data();
                    
                    for (size_t i = 0; i < samplesToMix; ++i) {
                        dstPtr[i] += srcPtr[i] * opacity;
                    }
                }
            }
        }
        
        // Final pass: Master Gain & Limiter
        if (!mixedAudio.empty()) {
            float masterGainF = static_cast<float>(curMasterGain);
            for (float& sample : mixedAudio) {
                sample *= masterGainF;
                if (std::isnan(sample)) sample = 0.0f;
                if (sample > 1.0f) sample = 1.0f;
                if (sample < -1.0f) sample = -1.0f;
            }
        }
    }
    
    py::array_t<float> result(mixedAudio.size());
    std::copy(mixedAudio.begin(), mixedAudio.end(), result.mutable_data());
    return result;
}

std::pair<py::array_t<float>, long> RockyEngine::getPlaybackBatch(long currentSamplesRendered, double missingPhysDuration, double rate) {
    if (missingPhysDuration <= 0.0001) {
        return { py::array_t<float>(0), 0 };
    }
    
    // 1. Calculate Start Time (Seconds)
    // We assume currentSamplesRendered aligns with 0 at time 0.
    double renderStartTimeSec = (double)currentSamplesRendered / 44100.0;
    
    // Convert to Ticks
    long long startTick = (long long)(renderStartTimeSec * TICKS_PER_SECOND);
    
    // 2. Calculate Content Duration Needed (in Ticks)
    // If playing at 2.0x, we move through timeline 2x faster.
    double contentDurationSec = missingPhysDuration * rate;
    long long contentDurationTicks = (long long)(contentDurationSec * TICKS_PER_SECOND);
    
    // 3. Render (GIL is handled inside render_audio)
    py::array_t<float> audioContent = render_audio(startTick, contentDurationTicks);
    
    // 4. Resample if necessary (Rate != 1.0)
    py::array_t<float> finalAudio;
    int targetSampleCount = (int)(missingPhysDuration * 44100);
    
    auto r = audioContent.unchecked<1>();
    bool needsResample = (r.size() / 2 != targetSampleCount);
    
    if (needsResample) {
        finalAudio = resampleAudio(audioContent, targetSampleCount);
    } else {
        finalAudio = audioContent;
    }
    
    // 5. Samples Consumed (on the timeline, effectively)
    // Actually, this return value adds to currentSamplesRendered passed back in next loop.
    // So it should represent how much "timeline time" (in samples) we advanced?
    // NO. `audio_samples_rendered` tracks the PLAYHEAD time in audio domain. 
    // If rate is 2.0, we advanced 2x seconds.
    // So we return sample count corresponding to `contentDurationSec`.
    
    long consumed = (long)(contentDurationSec * 44100.0);
    
    return { finalAudio, consumed };
}

std::string RockyEngine::formatTimecode(long long tick, double fps) {
    // 60000 ticks = 1 sec
    double total_seconds = (double)tick / TICKS_PER_SECOND;
    
    int h = static_cast<int>(total_seconds / 3600);
    int m = static_cast<int>(std::fmod(total_seconds / 60.0, 60.0));
    int s = static_cast<int>(std::fmod(total_seconds, 60.0));
    
    // Exact frames:
    long long ticksPerFrame = (long long)(TICKS_PER_SECOND / fps);
    if (ticksPerFrame == 0) ticksPerFrame = 1000;
    long long f = (tick / ticksPerFrame) % (long long)fps;
    
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%02d:%02d:%02d;%02lld", h, m, s, f);
    return std::string(buf);
}

py::array_t<float> RockyEngine::resampleAudio(py::array_t<float> input, int targetLen) {
    if (input.size() == 0 || targetLen <= 0) return input;
    
    auto r = input.unchecked<1>();
    size_t currentLen = r.size() / 2;
    
    if (currentLen == (size_t)targetLen) return input;
    
    std::vector<float> resampled(targetLen * 2);
    float factor = static_cast<float>(currentLen - 1) / (targetLen - 1);
    
    for (int i = 0; i < targetLen; ++i) {
        float pos = i * factor;
        int idx = static_cast<int>(pos);
        float frac = pos - idx;
        
        int idx1 = idx * 2;
        int idx2 = std::min<int>((idx + 1) * 2, (currentLen - 1) * 2);
        
        resampled[i * 2] = r(idx1) * (1.0f - frac) + r(idx2) * frac;
        resampled[i * 2 + 1] = r(idx1 + 1) * (1.0f - frac) + r(idx2 + 1) * frac;
    }
    
    py::array_t<float> result(resampled.size());
    std::copy(resampled.begin(), resampled.end(), result.mutable_data());
    return result;
}
