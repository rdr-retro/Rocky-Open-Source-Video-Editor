#include "engine.h"
#include "ofx/host.h"

#ifdef ENABLE_ACCELERATE
#include <Accelerate/Accelerate.h>
#endif

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
    
    // Sort by track index ASCENDING (Background [0] first, Foreground [N] last)
    // Painter's Algorithm: Draw bottom layers first, then overlay top layers.
    std::sort(visibleVideoClips.begin(), visibleVideoClips.end(), 
        [](const auto& first, const auto& second) {
            return first->trackIndex < second->trackIndex;
        }
    );

    const size_t totalPixelBytes = static_cast<size_t>(curW * curH * 4);
    
    // 1. LOCAL CANVAS (Thread Safety)
    // We use a local vector here to ensure that multiple calls to evaluate() 
    // (e.g. from Preview and Export threads) don't collide on a shared buffer.
    std::vector<uint8_t> localCanvas(totalPixelBytes);
    
    // Fast Clear (Black Background)
    uint32_t* pixelPtr = reinterpret_cast<uint32_t*>(localCanvas.data());
    size_t pixelCount = totalPixelBytes / 4;
    
    // 0xFF000000 in Little Endian (AABBGGRR) -> A=255, R=0, G=0, B=0
    const uint32_t bgColor = 0xFF000000; 
    std::fill_n(pixelPtr, pixelCount, bgColor);

    // 2. PARALLEL RENDERING (Latency Optimization)
    std::vector<std::future<Frame>> futureFrames;
    futureFrames.reserve(visibleVideoClips.size());
    
    {
        // HEAVY WORK: Release GIL
        py::gil_scoped_release release;
        const long targetFrameIndex = static_cast<long>(time * curFps + 0.001);

        // STAGE A: Launch background renders
        for (auto& clip : visibleVideoClips) {
             futureFrames.push_back(std::async(std::launch::async, 
                [clip, time, curW, curH, curFps, targetFrameIndex]() {
                    return clip->render(time, curW, curH, curFps, targetFrameIndex);
                }
             ));
        }

        // STAGE B: Composite results as they arrive
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
            
            // OPTIMIZACIÓN SENIOR: Blending con bitwise math para RGBA
            // Este bucle procesa 4 canales a la vez usando aritmética de enteros.
            const uint32_t* src32 = reinterpret_cast<const uint32_t*>(src);
            uint32_t* dst32 = reinterpret_cast<uint32_t*>(dst);
            const size_t pixelCount = totalPixelBytes / 4;

            for (size_t k = 0; k < pixelCount; ++k) {
                uint32_t s = src32[k];
                uint8_t alpha = (s >> 24) & 0xFF; // Asume RGBA (Little Endian: AABBGGRR)
                if (alpha == 0) continue;
                if (alpha == 255) {
                    dst32[k] = s;
                } else {
                    uint32_t d = dst32[k];
                    uint32_t invAlpha = 255 - alpha;
                    
                    // Blending optimizado: (S*A + D*(255-A)) >> 8
                    // Procesamos R+B juntos y G+A por separado para evitar overflow
                    uint32_t rb = ((s & 0x00FF00FF) * alpha + (d & 0x00FF00FF) * invAlpha) >> 8;
                    uint32_t g  = ((s & 0x0000FF00) * alpha + (d & 0x0000FF00) * invAlpha) >> 8;
                    
                    dst32[k] = (rb & 0x00FF00FF) | (g & 0x0000FF00) | 0xFF000000;
                }
            }
        }
    }

    // CREATE NUMPY ARRAY: ZERO-COPY
    // py::array_t puede robar la propiedad de un buffer de C++ para evitar el memcpy final.
    // Usamos py::capsule para que Python se encargue de liberar el std::vector cuando ya no se use.
    auto* ptr = new std::vector<uint8_t>(std::move(localCanvas));
    py::capsule free_when_done(ptr, [](void* f) {
        delete reinterpret_cast<std::vector<uint8_t>*>(f);
    });

    return py::array_t<uint8_t>(
        {curH, curW, 4},                        // Shape
        { (size_t)(curW * 4), (size_t)4, (size_t)1 }, // Strides
        ptr->data(),                            // Data pointer
        free_when_done                          // Owner (capsule)
    );
}

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
