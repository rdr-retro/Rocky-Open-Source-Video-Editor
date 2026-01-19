#include "engine.h"
#include "ofx/host.h"

void RockyEngine::setResolution(int w, int h) { std::lock_guard<std::mutex> lock(mtx); width = w; height = h; }
void RockyEngine::setFPS(double f) { std::lock_guard<std::mutex> lock(mtx); fps = f; }
void RockyEngine::addTrack(int type) { std::lock_guard<std::mutex> lock(mtx); trackTypes.push_back(type); }
void RockyEngine::setMasterGain(double gain) { std::lock_guard<std::mutex> lock(mtx); masterGain = gain; }

std::shared_ptr<Clip> RockyEngine::addClip(int trackIdx, std::string name, long start, long dur, double offset, std::shared_ptr<MediaSource> src) {
    std::lock_guard<std::mutex> lock(mtx);
    auto clip = std::make_shared<Clip>(name, start, dur, offset, src, trackIdx);
    clipTree.add(start, start + dur, clip);
    return clip;
}

void RockyEngine::clear() {
    std::lock_guard<std::mutex> lock(mtx);
    clipTree.clear();
    trackTypes.clear();
}

/**
 * @brief Processes and composites a single video frame for a specific time point.
 * 
 * Follows the "Vegas-style" compositing model where tracks with lower indices 
 * are rendered on top of tracks with higher indices.
 * 
 * @param time The project time in seconds.
 * @return py::array_t<uint8_t> A 4-channel (RGBA) NumPy array for Python consumption.
 */
py::array_t<uint8_t> RockyEngine::evaluate(double time) {
    std::vector<std::shared_ptr<Clip>> visibleVideoClips;
    int curW, curH;
    double curFps;

    {
        std::lock_guard<std::mutex> lock(mtx);
        const long targetFrameIndex = static_cast<long>(time * fps + 0.001);
        std::vector<std::shared_ptr<Clip>> activeClips = clipTree.query(targetFrameIndex);
        
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
    
    // Sort by track index descending (Background first, Foreground last)
    std::sort(visibleVideoClips.begin(), visibleVideoClips.end(), 
        [](const auto& first, const auto& second) {
            return first->trackIndex > second->trackIndex;
        }
    );

    const size_t totalPixelBytes = static_cast<size_t>(curW * curH * 4);
    
    // 1. REUSE BUFFER (Memory Optimization)
    if (internalCanvas.size() != totalPixelBytes) {
        internalCanvas.resize(totalPixelBytes);
    }
    
    // Fast Clear (Gray Background)
    // Optimization: Use memset for faster clearing if strict color isn't required, 
    // but here we manually fill to match the "Professional Gray" (45, 45, 45)
    uint32_t* pixelPtr = reinterpret_cast<uint32_t*>(internalCanvas.data());
    size_t pixelCount = totalPixelBytes / 4;
    
    // 0xFF2D2D2D in Little Endian (AABBGGRR) -> A=255, R=45, G=45, B=45
    // Note: Verify endianness if porting to non-x86/ARM64
    const uint32_t bgColor = 0xFF2D2D2D; 
    std::fill_n(pixelPtr, pixelCount, bgColor);

    // 2. PARALLEL RENDERING (Latency Optimization)
    // Fetch and decode frames in parallel threads
    std::vector<std::future<Frame>> futureFrames;
    futureFrames.reserve(visibleVideoClips.size());
    
    {
        // HEAVY WORK: Release GIL
        py::gil_scoped_release release;
        const long targetFrameIndex = static_cast<long>(time * curFps + 0.001);

        for (auto& clip : visibleVideoClips) {
             futureFrames.push_back(std::async(std::launch::async, 
                [clip, time, curW, curH, curFps, targetFrameIndex]() {
                    return clip->render(time, curW, curH, curFps, targetFrameIndex);
                }
             ));
        }
        
        // 3. COMPOSITING LOOP (Wait and Blend)
        for (size_t i = 0; i < visibleVideoClips.size(); ++i) {
            Frame currentLayer = futureFrames[i].get(); // Block until this frame is ready
            
            if (currentLayer.data.empty()) continue;

            // --- APPLY EFFECTS ---
            auto clip = visibleVideoClips[i];
            for (const auto& effect : clip->effects) {
                if (effect.enabled) {
                    RockyOfxHost::getInstance().executePluginRender(
                        effect.pluginPath, 
                        currentLayer.data.data(), // Src (In-place)
                        currentLayer.data.data(), // Dst
                        currentLayer.width, 
                        currentLayer.height
                    );
                }
            }
            // ---------------------

            const uint8_t* src = currentLayer.data.data();
            uint8_t* dst = internalCanvas.data();
            
            // Optimization: Pointer arithmetic is faster than vector indexing
            // TODO: SIMD Intrinsics (NEON) could be added here for 4x speedup
            for (size_t k = 0; k < totalPixelBytes; k += 4) {
                const uint8_t alpha = src[k + 3];
                if (alpha == 0) continue; // Skip transparent pixels

                if (alpha == 255) {
                    // Opaque: Fast Copy
                    // Use a 32-bit copy for the whole pixel
                    *reinterpret_cast<uint32_t*>(dst + k) = *reinterpret_cast<const uint32_t*>(src + k);
                } else {
                    // Blending
                    // Formula: out = src * alpha + dst * (1 - alpha)
                    // Approximation using integer math: (src * alpha + dst * (255 - alpha)) >> 8
                    // This is much faster than float division
                    const uint32_t invAlpha = 255 - alpha;
                    
                    dst[k]     = (src[k]     * alpha + dst[k]     * invAlpha) >> 8;
                    dst[k + 1] = (src[k + 1] * alpha + dst[k + 1] * invAlpha) >> 8;
                    dst[k + 2] = (src[k + 2] * alpha + dst[k + 2] * invAlpha) >> 8;
                    dst[k + 3] = 255; // Keep canvas valid
                }
            }
        }
    }

    // CREATE NUMPY ARRAY: Requires GIL
    py::array_t<uint8_t> frameBuffer({curH, curW, 4});
    // We still copy to Python buffer for safety, but we saved the intermediate allocation
    std::memcpy(frameBuffer.mutable_data(), internalCanvas.data(), totalPixelBytes);
    return frameBuffer;
}
#ifdef ENABLE_ACCELERATE
#include <Accelerate/Accelerate.h>
#endif

py::array_t<float> RockyEngine::render_audio(double startTime, double duration) {
    std::vector<std::shared_ptr<Clip>> audioClips;
    double curFps;
    double curMasterGain;
    const int targetSampleRate = 44100;
    const int totalSamples = static_cast<int>(duration * targetSampleRate);

    {
        std::lock_guard<std::mutex> lock(mtx);
        const long startFrame = static_cast<long>(startTime * fps);
        const long endFrame = static_cast<long>((startTime + duration) * fps);
        std::vector<std::shared_ptr<Clip>> activeClips = clipTree.query(startFrame, endFrame);
        
        for (const auto& clip : activeClips) {
            if (clip->trackIndex >= 0 && clip->trackIndex < static_cast<int>(trackTypes.size()) && trackTypes[clip->trackIndex] == 2) {
                audioClips.push_back(clip);
            }
        }
        curFps = fps;
        curMasterGain = masterGain;
    }
    
    std::vector<float> mixedAudio(totalSamples * 2, 0.0f);
    
    {
        // HEAVY WORK: Release GIL
        py::gil_scoped_release release;
        
        for (const auto& clip : audioClips) {
            auto videoSrc = std::dynamic_pointer_cast<VideoSource>(clip->source);
            if (videoSrc) {
                double localStart = (startTime - (clip->startFrame / curFps)) + clip->sourceOffset;
                std::vector<float> samples = videoSrc->getAudioSamples(localStart, duration);
                
                size_t mixCount = std::min(mixedAudio.size(), samples.size());
                if (mixCount > 0) {
                    float opacity = static_cast<float>(clip->opacity);
#ifdef ENABLE_ACCELERATE
                    // Apple Silicon Hardware Acceleration: Vector Multiply-Add
                    vDSP_vsma(samples.data(), (vDSP_Stride)1, &opacity, mixedAudio.data(), (vDSP_Stride)1, mixedAudio.data(), (vDSP_Stride)1, (vDSP_Length)mixCount);
#else
                    for (size_t i = 0; i < mixCount; ++i) {
                        mixedAudio[i] += samples[i] * opacity;
                    }
#endif
                }
            }
        }
        
        // Final pass: Master Gain & Soft Limiter
        if (!mixedAudio.empty()) {
            float masterGainF = static_cast<float>(curMasterGain);
#ifdef ENABLE_ACCELERATE
            // Hardware Accelerated Master Scaling
            vDSP_vsmul(mixedAudio.data(), (vDSP_Stride)1, &masterGainF, mixedAudio.data(), (vDSP_Stride)1, (vDSP_Length)mixedAudio.size());
#else
            for (float& sample : mixedAudio) {
                sample *= masterGainF;
            }
#endif
            // Limiter pass still needs tanh or specialized HW vector processing
            for (float& sample : mixedAudio) {
                if (std::isnan(sample)) sample = 0.0f;
                if (sample > 1.0f || sample < -1.0f) {
                    sample = std::tanh(sample);
                }
            }
        }
    }
    
    py::array_t<float> result(mixedAudio.size());
    std::copy(mixedAudio.begin(), mixedAudio.end(), result.mutable_data());
    return result;
}
