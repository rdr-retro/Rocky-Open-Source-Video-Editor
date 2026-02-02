#pragma once
#include <string>
#include <vector>
#include <mutex>
#include <iostream>
#include <fstream>
#include "common.h"

// Forward declaration if needed, or include simple wav header
// We will implement a custom WAV parser for demonstration of "Native" code.

#include "media_source.h"

class NativeAudioSource : public MediaSource {
    std::string path;
    bool is_valid = false;
    double duration = 0.0;
    int sample_rate = 44100;
    int channels = 2;
    size_t total_samples = 0;
    
    // Raw PCM Data (Loaded in memory for maximum speed on Mac M4)
    // For large files, we'd map this, but for "Complete Substitute", memory is fine for <100MB songs.
    std::vector<float> pcm_data; // Interleaved L R L R
    
public:
    NativeAudioSource(std::string path);
    ~NativeAudioSource();
    
    // MediaSource implementations
    Frame getFrame(double localTime, int w, int h) override { return Frame(1, 1); }
    std::vector<float> getAudioSamples(double startTime, double duration) override;
    std::vector<float> getPeaks(double startTime, double duration, int numBuckets) override;
    double getDuration() override { return duration; }
    bool isValid() const { return is_valid; }
    int getSampleRate() const { return sample_rate; }
    int getChannels() const { return channels; }
    
private:
    // Internal decoders
    bool loadWAV(const std::string& filepath);
    bool loadWithFFmpeg(const std::string& filepath);
    bool loadMP3(const std::string& filepath); // Stub or minimal
};
