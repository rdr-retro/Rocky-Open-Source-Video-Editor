#pragma once
#include "common.h"
#include <mutex>

class MediaSource {
public:
    virtual ~MediaSource() = default;
    virtual Frame getFrame(double localTime, int w, int h) = 0;
    virtual double getDuration() { return -1.0; } // Default: Infinite/Static
};

class ColorSource : public MediaSource {
    uint8_t r, g, b, a;
public:
    ColorSource(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);
    Frame getFrame(double localTime, int w, int h) override;
    double getDuration() override { return -1.0; }
};

class VideoSource : public MediaSource {
    std::string path;
    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* codec_ctx = nullptr;
    AVCodecContext* audio_codec_ctx = nullptr;
    int video_stream_idx = -1;
    int audio_stream_idx = -1;
    AVFrame* av_frame = nullptr;
    AVFrame* audio_frame = nullptr;
    AVPacket* pkt = nullptr;
    SwsContext* sws_ctx = nullptr;
    
    // Validation flag to prevent crashes with corrupted files (P6)
    bool is_valid = false;
    
    int last_w = -1, last_h = -1;
    std::shared_ptr<Frame> last_frame = nullptr;  // P5: Thread-safe frame caching
    double last_time = -1.0;
    double last_audio_time = -1.0;
    SwrContext* cached_swr = nullptr;
    std::once_flag swr_init_flag;  // P3: Thread-safe SwrContext initialization
    mutable std::mutex mtx;

public:
    VideoSource(std::string p);
    ~VideoSource();
    Frame getFrame(double localTime, int w, int h) override;
    std::vector<float> getAudioSamples(double startTime, double duration);
    std::vector<float> getWaveform(int points);
    double getDuration() override;
    bool isValid() const { return is_valid; }  // P6: Expose validation status
    
    // Resolution and Metadata Getters (Refined for immediate access)
    int getWidth() const;
    int getHeight() const;
    int getNativeWidth() const;
    int getNativeHeight() const;
    int getRotation() const; // Implemented in cpp
};

class ImageSource : public MediaSource {
    std::string path;
    Frame cached_frame = Frame(1, 1);
    int last_w = -1, last_h = -1;
    bool loaded = false;

public:
    ImageSource(std::string p);
    Frame getFrame(double localTime, int w, int h) override;
    double getDuration() override { return -1.0; }

private:
    void load(int w, int h);
};
