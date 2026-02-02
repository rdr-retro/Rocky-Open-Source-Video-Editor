#include "native_audio.h"
#include <cmath>
#include <algorithm>
#include <iostream>
#include <vector>
#include <fstream>

// Use "common.h" regarding project-wide definitions
#include "common.h"

/**
 * @struct WavHeader
 * @brief Standard RIFF WAVE header structure.
 * Using #pragma pack(push, 1) ensures no padding bytes are inserted by the compiler,
 * matching the binary file format exactly.
 */
#pragma pack(push, 1)
struct WavHeader {
    char riff[4];               // "RIFF"
    uint32_t overall_size;      // File size - 8 bytes
    char wave[4];               // "WAVE"
    char fmt_chunk_marker[4];   // "fmt "
    uint32_t length_of_fmt;     // Length of format data
    uint16_t format_type;       // 1 = PCM
    uint16_t channels;          // Number of channels
    uint32_t sample_rate;       // Sampling rate (e.g., 44100)
    uint32_t byterate;          // (SampleRate * BitsPerSample * Channels) / 8
    uint16_t block_align;       // (BitsPerSample * Channels) / 8
    uint16_t bits_per_sample;   // 8, 16, 32, etc.
    char data_chunk_header[4];  // "data"
    uint32_t data_size;         // Size of data section
};
#pragma pack(pop)

// Constants for Audio Processing
static const int TARGET_SAMPLE_RATE = 44100;
static const int TARGET_CHANNELS = 2;

NativeAudioSource::NativeAudioSource(const std::string& filePath) 
    : path(filePath), is_valid(false), duration(0.0), sample_rate(0), channels(0), total_samples(0) 
{
    if (tryLoadWAV(path)) {
        std::cout << "[NativeAudio] Loaded WAV: " << path << " (" << duration << "s)" << std::endl;
        is_valid = true;
        return;
    }
    
    // Fallback: Use FFmpeg for robust decoding of compressed formats (MP3, AAC, etc.)
    if (loadWithFFmpeg(path)) {
        std::cout << "[NativeAudio] Loaded via FFmpeg (Cached): " << path << " (" << duration << "s)" << std::endl;
        is_valid = true;
    } else {
        std::cerr << "[NativeAudio] Failed to load source: " << path << std::endl;
        is_valid = false;
    }
}

NativeAudioSource::~NativeAudioSource() {
    pcm_data.clear();
}

// =================================================================================================
// WAV LOADING STRATEGY
// =================================================================================================

/**
 * @brief Attempts to load uncompressed WAV files directly for performance.
 * @return true if successfully loaded, false otherwise.
 */
bool NativeAudioSource::tryLoadWAV(const std::string& filepath) {
    if (filepath.find(".wav") == std::string::npos && filepath.find(".WAV") == std::string::npos) {
        return false; 
    }

    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) return false;
    
    WavHeader header;
    if (!file.read(reinterpret_cast<char*>(&header), sizeof(WavHeader))) {
        return false;
    }
    
    // 1. Validate Header Signature
    if (std::string(header.riff, 4) != "RIFF" || std::string(header.wave, 4) != "WAVE") {
        return false;
    }
    
    // 2. Validate Format (Only PCM supported directly)
    if (header.format_type != 1) {
        // Non-PCM WAVs (Float/Extensible) should fall back to FFmpeg
        return false;
    }

    this->sample_rate = header.sample_rate;
    this->channels = header.channels;
    
    int bytesPerSample = header.bits_per_sample / 8;
    if (bytesPerSample == 0 || this->channels == 0) return false;
    
    this->total_samples = header.data_size / (this->channels * bytesPerSample);
    
    // Safety: Prevent zero div
    if (this->sample_rate == 0) return false;
    this->duration = static_cast<double>(this->total_samples) / this->sample_rate;
    
    // 3. Read Data
    try {
        pcm_data.resize(this->total_samples * this->channels);
        
        if (header.bits_per_sample == 16) {
            std::vector<int16_t> buffer(this->total_samples * this->channels);
            file.read(reinterpret_cast<char*>(buffer.data()), buffer.size() * sizeof(int16_t));
            
            // Normalize 16-bit Int -> Float [-1.0, 1.0]
            for (size_t i = 0; i < buffer.size(); ++i) {
                pcm_data[i] = buffer[i] / 32768.0f;
            }
        } else if (header.bits_per_sample == 32) {
             // Assume 32-bit Float (rare in PCM type 1 headers but possible)
             // or 32-bit Int. For now, we strictly assume Float if 32-bit is passed here.
             file.read(reinterpret_cast<char*>(pcm_data.data()), pcm_data.size() * sizeof(float));
        } else {
            // 24-bit or 8-bit not implemented in fast loader -> Fallback to FFmpeg
            return false;
        }
    } catch (...) {
        return false;
    }
    
    return true;
}

// =================================================================================================
// FFMPEG LOADING STRATEGY
// =================================================================================================

/**
 * @brief Helper to find the first valid audio stream index.
 */
int findBestAudioStream(AVFormatContext* fmt_ctx) {
    for (unsigned int i = 0; i < fmt_ctx->nb_streams; i++) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

bool NativeAudioSource::loadWithFFmpeg(const std::string& filepath) {
    AVFormatContext* formatCtx = nullptr;
    AVCodecContext* codecCtx = nullptr;
    SwrContext* swr = nullptr;
    AVPacket* packet = nullptr;
    AVFrame* frame = nullptr;
    bool success = false;

    // RAII Cleanup Helper (Lambda)
    auto cleanup = [&]() {
        if (frame) av_frame_free(&frame);
        if (packet) av_packet_free(&packet);
        if (swr) swr_free(&swr);
        if (codecCtx) avcodec_free_context(&codecCtx);
        if (formatCtx) avformat_close_input(&formatCtx);
    };

    if (avformat_open_input(&formatCtx, filepath.c_str(), nullptr, nullptr) != 0) return false;
    if (avformat_find_stream_info(formatCtx, nullptr) < 0) { cleanup(); return false; }

    int streamIdx = findBestAudioStream(formatCtx);
    if (streamIdx == -1) { cleanup(); return false; }

    const AVCodec* codec = avcodec_find_decoder(formatCtx->streams[streamIdx]->codecpar->codec_id);
    if (!codec) { cleanup(); return false; }

    codecCtx = avcodec_alloc_context3(codec);
    if (!codecCtx) { cleanup(); return false; }

    if (avcodec_parameters_to_context(codecCtx, formatCtx->streams[streamIdx]->codecpar) < 0) { cleanup(); return false; }
    
    if (avcodec_open2(codecCtx, codec, nullptr) < 0) { cleanup(); return false; }

    // Initialize Resampler: Force standardize to 44.1kHz Stereo Float
    swr = swr_alloc();
    av_opt_set_chlayout(swr, "in_chlayout", &codecCtx->ch_layout, 0);
    av_opt_set_int(swr, "in_sample_rate", codecCtx->sample_rate, 0);
    av_opt_set_sample_fmt(swr, "in_sample_fmt", codecCtx->sample_fmt, 0);

    AVChannelLayout out_layout;
    av_channel_layout_default(&out_layout, TARGET_CHANNELS);
    av_opt_set_chlayout(swr, "out_chlayout", &out_layout, 0);
    av_opt_set_int(swr, "out_sample_rate", TARGET_SAMPLE_RATE, 0);
    av_opt_set_sample_fmt(swr, "out_sample_fmt", AV_SAMPLE_FMT_FLT, 0);
    
    if (swr_init(swr) < 0) { cleanup(); return false; }

    // Commit standardized properties
    this->sample_rate = TARGET_SAMPLE_RATE;
    this->channels = TARGET_CHANNELS;

    packet = av_packet_alloc();
    frame = av_frame_alloc();

    // Decode Loop
    while (av_read_frame(formatCtx, packet) >= 0) {
        if (packet->stream_index == streamIdx) {
            if (avcodec_send_packet(codecCtx, packet) == 0) {
                while (avcodec_receive_frame(codecCtx, frame) == 0) {
                    
                    // Resample Frame
                    int max_out_samples = av_rescale_rnd(
                        swr_get_delay(swr, codecCtx->sample_rate) + frame->nb_samples, 
                        TARGET_SAMPLE_RATE, codecCtx->sample_rate, AV_ROUND_UP
                    );
                    
                    if (max_out_samples > 0) {
                        float* buffer = nullptr;
                        // Align 0 (auto)
                        if (av_samples_alloc((uint8_t**)&buffer, nullptr, TARGET_CHANNELS, max_out_samples, AV_SAMPLE_FMT_FLT, 0) >= 0) {
                            
                            int valid_samples = swr_convert(swr, (uint8_t**)&buffer, max_out_samples, (const uint8_t**)frame->data, frame->nb_samples);
                            
                            if (valid_samples > 0) {
                                size_t oldSize = pcm_data.size();
                                pcm_data.resize(oldSize + valid_samples * TARGET_CHANNELS);
                                
                                // Direct Memory Copy (Efficient)
                                std::copy(buffer, buffer + valid_samples * TARGET_CHANNELS, pcm_data.begin() + oldSize);
                            }
                            av_freep(&buffer);
                        }
                    }
                }
            }
        }
        av_packet_unref(packet);
    }

    if (this->sample_rate > 0 && this->channels > 0) {
        this->total_samples = pcm_data.size() / this->channels;
        this->duration = static_cast<double>(this->total_samples) / this->sample_rate;
        success = true;
    }

    cleanup();
    return success;
}

// =================================================================================================
// AUDIO RETRIEVAL
// =================================================================================================

/**
 * @brief Retrieves audio samples for a specific time range, applying resampling if necessary.
 * Utilizes linear interpolation for smooth playback at non-native speeds.
 */
std::vector<float> NativeAudioSource::getAudioSamples(double startTime, double reqDuration) {
    if (!is_valid || pcm_data.empty()) return {};

    size_t targetCount = static_cast<size_t>(reqDuration * TARGET_SAMPLE_RATE);
    std::vector<float> output(targetCount * TARGET_CHANNELS, 0.0f);
    
    // If exact match (rare but possible), we could optimize. 
    // But currently we always assume possible slight rate variance or start offsets.

    long startSample = static_cast<long>(startTime * sample_rate);
    double ratio = static_cast<double>(sample_rate) / TARGET_SAMPLE_RATE;
    
    // Pre-calculate boundary to avoid check inside loop
    long total_limit = static_cast<long>(total_samples);

    for (size_t i = 0; i < targetCount; ++i) {
        double srcIdx = startSample + (i * ratio);
        long idx0 = static_cast<long>(srcIdx);
        
        if (idx0 >= total_limit - 1) break; // End of stream
        if (idx0 < 0) continue; // Before start (silence)
        
        long idx1 = idx0 + 1;
        float frac = static_cast<float>(srcIdx - idx0);
        
        // Channel 0 (Left)
        float s0_L = pcm_data[idx0 * channels];
        float s1_L = pcm_data[idx1 * channels];
        output[i * 2] = s0_L + (s1_L - s0_L) * frac;
        
        // Channel 1 (Right)
        if (channels > 1) {
            float s0_R = pcm_data[idx0 * channels + 1];
            float s1_R = pcm_data[idx1 * channels + 1];
            output[i * 2 + 1] = s0_R + (s1_R - s0_R) * frac;
        } else {
            // Mono -> Stereo Duplicate
            output[i * 2 + 1] = output[i * 2]; 
        }
    }
    
    return output;
}

/**
 * @brief Generates Min/Max visualization peaks for waveform drawing.
 * Optimized to iterate only the necessary samples.
 */
std::vector<float> NativeAudioSource::getPeaks(double startTime, double reqDuration, int numBuckets) {
    if (!is_valid || numBuckets <= 0 || pcm_data.empty()) return {};

    std::vector<float> peaks(numBuckets * 2, 0.0f);
    
    long startSample = static_cast<long>(startTime * sample_rate);
    long durationSamples = static_cast<long>(reqDuration * sample_rate);
    
    if (durationSamples <= 0) return peaks;

    double samples_per_bucket = static_cast<double>(durationSamples) / numBuckets;
    long total_limit = static_cast<long>(total_samples);

    for (int i = 0; i < numBuckets; ++i) {
        long bucketStart = startSample + static_cast<long>(i * samples_per_bucket);
        long bucketEnd = startSample + static_cast<long>((i + 1) * samples_per_bucket);
        
        // Bounds clamping
        bucketStart = std::max(0L, std::min(total_limit, bucketStart));
        bucketEnd = std::max(0L, std::min(total_limit, bucketEnd));

        if (bucketStart >= bucketEnd) continue; // Silent bucket

        float minVal = 0.0f;
        float maxVal = 0.0f;
        bool first = true;

        /*
         * OPTIMIZATION: Stride iteration for very dense zoom levels
         * If bucket > 1000 samples, step to avoid O(N) on huge files
         */
        int step = 1;
        long regionSize = bucketEnd - bucketStart;
        if (regionSize > 500) step = regionSize / 100; // Sample max 100 pts per bucket

        for (long s = bucketStart; s < bucketEnd; s += step) {
             // Process interleaved channels
             for (int c = 0; c < channels; ++c) {
                float val = pcm_data[s * channels + c];
                if (first) {
                    minVal = maxVal = val;
                    first = false;
                } else {
                    if (val < minVal) minVal = val;
                    if (val > maxVal) maxVal = val;
                }
            }
        }
        
        peaks[i * 2] = minVal;
        peaks[i * 2 + 1] = maxVal;
    }

    return peaks;
}

