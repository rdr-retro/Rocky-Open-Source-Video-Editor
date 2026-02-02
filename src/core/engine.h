#pragma once
#include "common.h"
#include "clip.h"
#include "interval_tree.h"
#include <mutex>
#include <future>
#include <thread>

class RockyEngine {
    std::vector<int> trackTypes;
    IntervalTree<std::shared_ptr<Clip>> clipTree;
    int width = 1280, height = 720;
    double fps = 30.0;
    double masterGain = 1.0;
    std::mutex mtx;

public:
    static const long long TICKS_PER_SECOND = 60000;

    void setResolution(int w, int h);
    void setFPS(double f);
    void addTrack(int type);
    void setMasterGain(double gain);
    std::shared_ptr<Clip> addClip(int trackIdx, std::string name, long long startTick, long long durTicks, long long offsetTicks, std::shared_ptr<MediaSource> src);
    void clear();
    py::array_t<uint8_t> evaluate(long long tick);
    py::array_t<float> render_audio(long long startTick, long long durationTicks);
    
    // Optimized playback pump (Moves Python loop logic to C++)
    // Returns: (AudioData, TimelineSamplesConsumed)
    std::pair<py::array_t<float>, long> getPlaybackBatch(long currentSamplesRendered, double missingPhysDuration, double rate);
    
    // UTILS (Migración desde Python para rendimiento extremo)
    static std::string formatTimecode(long long tick, double fps);
    static py::array_t<float> resampleAudio(py::array_t<float> input, int targetLen);
};
