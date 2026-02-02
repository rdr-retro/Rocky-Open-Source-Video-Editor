#include "native_audio.h"
#include <cmath>
#include <algorithm>

// Utils
struct WavHeader {
    char riff[4];
    uint32_t overall_size;
    char wave[4];
    char fmt_chunk_marker[4];
    uint32_t length_of_fmt;
    uint16_t format_type; // 1 = PCM
    uint16_t channels;
    uint32_t sample_rate;
    uint32_t byterate;
    uint16_t block_align;
    uint16_t bits_per_sample;
    char data_chunk_header[4];
    uint32_t data_size;
};

#include "common.h"

NativeAudioSource::NativeAudioSource(std::string p) : path(p) {
    if (path.find(".wav") != std::string::npos || path.find(".WAV") != std::string::npos) {
        if (loadWAV(path)) {
            is_valid = true;
            std::cout << "[NativeAudio] Loaded WAV: " << path << " (" << duration << "s)" << std::endl;
            return;
        }
    }
    
    // Universal Fallback: Use FFmpeg to decode EVERYTHING into memory
    if (loadWithFFmpeg(path)) {
        is_valid = true;
        std::cout << "[NativeAudio] Loaded via FFmpeg (Cached): " << path << " (" << duration << "s)" << std::endl;
    } else {
        std::cerr << "[NativeAudio] Failed to load source: " << path << std::endl;
        is_valid = false;
    }
}

bool NativeAudioSource::loadWithFFmpeg(const std::string& filepath) {
    AVFormatContext* formatCtx = nullptr;
    if (avformat_open_input(&formatCtx, filepath.c_str(), nullptr, nullptr) != 0) return false;
    if (avformat_find_stream_info(formatCtx, nullptr) < 0) {
        avformat_close_input(&formatCtx);
        return false;
    }

    int audioStreamPos = -1;
    for (unsigned int i = 0; i < formatCtx->nb_streams; i++) {
        if (formatCtx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            audioStreamPos = i;
            break;
        }
    }

    if (audioStreamPos == -1) {
        avformat_close_input(&formatCtx);
        return false;
    }

    const AVCodec* codec = avcodec_find_decoder(formatCtx->streams[audioStreamPos]->codecpar->codec_id);
    AVCodecContext* codecCtx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codecCtx, formatCtx->streams[audioStreamPos]->codecpar);
    if (avcodec_open2(codecCtx, codec, nullptr) < 0) {
        avcodec_free_context(&codecCtx);
        avformat_close_input(&formatCtx);
        return false;
    }

    // Resampler setup: Force to 44100Hz Stereo Float
    SwrContext* swr = swr_alloc();
    av_opt_set_chlayout(swr, "in_chlayout", &codecCtx->ch_layout, 0);
    av_opt_set_int(swr, "in_sample_rate", codecCtx->sample_rate, 0);
    av_opt_set_sample_fmt(swr, "in_sample_fmt", codecCtx->sample_fmt, 0);

    AVChannelLayout out_layout;
    av_channel_layout_default(&out_layout, 2);
    av_opt_set_chlayout(swr, "out_chlayout", &out_layout, 0);
    av_opt_set_int(swr, "out_sample_rate", 44100, 0);
    av_opt_set_sample_fmt(swr, "out_sample_fmt", AV_SAMPLE_FMT_FLT, 0);
    swr_init(swr);

    sample_rate = 44100;
    channels = 2;

    AVPacket* packet = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();

    while (av_read_frame(formatCtx, packet) >= 0) {
        if (packet->stream_index == audioStreamPos) {
            if (avcodec_send_packet(codecCtx, packet) == 0) {
                while (avcodec_receive_frame(codecCtx, frame) == 0) {
                    // Convert and store
                    int out_samples = av_rescale_rnd(swr_get_delay(swr, codecCtx->sample_rate) + frame->nb_samples, 44100, codecCtx->sample_rate, AV_ROUND_UP);
                    
                    float* buffer = nullptr;
                    av_samples_alloc((uint8_t**)&buffer, nullptr, 2, out_samples, AV_SAMPLE_FMT_FLT, 0);
                    
                    int converted = swr_convert(swr, (uint8_t**)&buffer, out_samples, (const uint8_t**)frame->data, frame->nb_samples);
                    
                    if (converted > 0) {
                        size_t oldSize = pcm_data.size();
                        pcm_data.resize(oldSize + converted * 2);
                        std::copy(buffer, buffer + converted * 2, pcm_data.begin() + oldSize);
                    }
                    av_freep(&buffer);
                }
            }
        }
        av_packet_unref(packet);
    }

    duration = (double)pcm_data.size() / (sample_rate * channels);
    total_samples = pcm_data.size() / channels;

    av_frame_free(&frame);
    av_packet_free(&packet);
    swr_free(&swr);
    avcodec_free_context(&codecCtx);
    avformat_close_input(&formatCtx);
    return true;
}

NativeAudioSource::~NativeAudioSource() {
    pcm_data.clear();
}

bool NativeAudioSource::loadWAV(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) return false;
    
    WavHeader header;
    file.read((char*)&header, sizeof(WavHeader));
    
    // Basic Validation
    if (std::string(header.riff, 4) != "RIFF" || std::string(header.wave, 4) != "WAVE") {
        return false;
    }
    
    sample_rate = header.sample_rate;
    channels = header.channels;
    
    // Skip to data
    // (Simplification: real WAVs have extra chunks, this is a basic parser)
    
    int bytesPerSample = header.bits_per_sample / 8;
    if (bytesPerSample == 0) return false;
    
    total_samples = header.data_size / (channels * bytesPerSample);
    duration = (double)total_samples / sample_rate;
    
    pcm_data.resize(total_samples * channels);
    
    if (header.bits_per_sample == 16) {
        std::vector<int16_t> buffer(total_samples * channels);
        file.read((char*)buffer.data(), buffer.size() * 2);
        
        // Convert to float
        for (size_t i = 0; i < buffer.size(); ++i) {
            pcm_data[i] = buffer[i] / 32768.0f;
        }
    } else if (header.bits_per_sample == 32) {
        // Assume Float
         file.read((char*)pcm_data.data(), pcm_data.size() * 4);
    }
    
    return true;
}

std::vector<float> NativeAudioSource::getAudioSamples(double startTime, double reqDuration) {
    if (!is_valid) return {};
    
    // Target specs
    int targetRate = 44100;
    size_t targetCount = (size_t)(reqDuration * targetRate);
    int targetChannels = 2;
    
    std::vector<float> output(targetCount * targetChannels, 0.0f);
    
    // Linear Interpolation Resampling (Simplest "Clean" Algo)
    double ratio = (double)sample_rate / targetRate;
    
    long startSample = (long)(startTime * sample_rate);
    
    for (size_t i = 0; i < targetCount; ++i) {
        double srcIdx = startSample + (i * ratio);
        long idx0 = (long)srcIdx;
        long idx1 = idx0 + 1;
        double frac = srcIdx - idx0;
        
        if (idx1 >= total_samples) break;
        if (idx0 < 0) continue;
        
        // Channel 0 (Left)
        float s0_L = pcm_data[idx0 * channels];
        float s1_L = pcm_data[idx1 * channels];
        float val_L = s0_L + (s1_L - s0_L) * frac;
        
        // Channel 1 (Right)
        float val_R = val_L;
        if (channels > 1) {
            float s0_R = pcm_data[idx0 * channels + 1];
            float s1_R = pcm_data[idx1 * channels + 1];
            val_R = s0_R + (s1_R - s0_R) * frac;
        }
        
        output[i * 2] = val_L;
        output[i * 2 + 1] = val_R;
    }
    
    return output;
}
