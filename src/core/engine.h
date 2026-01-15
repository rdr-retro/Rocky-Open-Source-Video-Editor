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
    std::vector<uint8_t> internalCanvas; // Reusable buffer to avoid re-allocations
    int width = 1280, height = 720;
    double fps = 30.0;
    double masterGain = 1.0;
    std::mutex mtx;

public:
    void setResolution(int w, int h);
    void setFPS(double f);
    void addTrack(int type);
    void setMasterGain(double gain);
    std::shared_ptr<Clip> addClip(int trackIdx, std::string name, long start, long dur, double offset, std::shared_ptr<MediaSource> src);
    void clear();
    py::array_t<uint8_t> evaluate(double time);
    py::array_t<float> render_audio(double startTime, double duration);
};
