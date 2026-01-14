#include "engine.h"

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
    // printf("DEBUG: RockyEngine::evaluate(%.3f)\n", time);
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
    
    // Sort by track index descending
    std::sort(visibleVideoClips.begin(), visibleVideoClips.end(), 
        [](const auto& first, const auto& second) {
            return first->trackIndex > second->trackIndex;
        }
    );

    const size_t totalPixelBytes = static_cast<size_t>(curW * curH * 4);
    std::vector<uint8_t> canvas(totalPixelBytes, 0);
    // Professional Gray Background for the project canvas (RGB 45, 45, 45)
    for (size_t i = 0; i < totalPixelBytes; i += 4) {
        canvas[i]     = 45;  // R
        canvas[i + 1] = 45;  // G
        canvas[i + 2] = 45;  // B
        canvas[i + 3] = 255; // A
    }

    {
        // HEAVY WORK: Release GIL
        py::gil_scoped_release release;
        const long targetFrameIndex = static_cast<long>(time * curFps + 0.001);
        
        for (auto& clip : visibleVideoClips) {
            Frame currentLayer = clip->render(time, curW, curH, curFps, targetFrameIndex);
            
            for (size_t i = 0; i < totalPixelBytes; i += 4) {
                const float sourceAlpha = currentLayer.data[i + 3] / 255.0f;
                if (sourceAlpha > 0.0f) {
                    const float invAlpha = 1.0f - sourceAlpha;
                    canvas[i]     = static_cast<uint8_t>(currentLayer.data[i]     * sourceAlpha + canvas[i]     * invAlpha);
                    canvas[i + 1] = static_cast<uint8_t>(currentLayer.data[i + 1] * sourceAlpha + canvas[i + 1] * invAlpha);
                    canvas[i + 2] = static_cast<uint8_t>(currentLayer.data[i + 2] * sourceAlpha + canvas[i + 2] * invAlpha);
                }
            }
        }
    }

    // CREATE NUMPY ARRAY: Requires GIL (which we re-acquired when 'release' went out of scope)
    py::array_t<uint8_t> frameBuffer({curH, curW, 4});
    std::copy(canvas.begin(), canvas.end(), frameBuffer.mutable_data());
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
