#include "media_source.h"

// ============================================================================
// COLOR SOURCE IMPLEMENTATION
// ============================================================================

ColorSource::ColorSource(uint8_t r, uint8_t g, uint8_t b, uint8_t a) 
    : r(r), g(g), b(b), a(a) {}

/**
 * @brief Generates a solid color frame. Consistent O(N) complexity.
 */
Frame ColorSource::getFrame(double /*localTime*/, int w, int h) {
    Frame frame(w, h, 4);
    const size_t dataSize = frame.data.size();
    uint8_t* rawData = frame.data.data();

    for (size_t i = 0; i < dataSize; i += 4) {
        rawData[i]     = r;
        rawData[i + 1] = g;
        rawData[i + 2] = b;
        rawData[i + 3] = a;
    }
    return frame;
}

// ============================================================================
// VIDEO SOURCE IMPLEMENTATION (FFMPEG)
// ============================================================================

VideoSource::VideoSource(std::string p) : path(p) {
    std::cout << "[VideoSource] Constructor for " << path << std::endl;
    // Attempt to open input stream
    if (avformat_open_input(&fmt_ctx, path.c_str(), nullptr, nullptr) < 0) {
        std::cerr << "[VideoSource] Failed to open: " << path << std::endl;
        return;
    }

    if (avformat_find_stream_info(fmt_ctx, nullptr) < 0) {
        return;
    }

    // Find the primary streams
    for (unsigned int i = 0; i < fmt_ctx->nb_streams; i++) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO && video_stream_idx == -1) {
            video_stream_idx = i;
        } else if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO && audio_stream_idx == -1) {
            audio_stream_idx = i;
        }
    }

    // Initialize Video Decoder
    if (video_stream_idx != -1) {
        AVCodecID codec_id = fmt_ctx->streams[video_stream_idx]->codecpar->codec_id;
        const AVCodec* v_codec = nullptr;

        // DEBUG: Force Software Decoder for stability during initial dev
        // "h264_videotoolbox" can be unstable with multi-threaded access if not managed strictly
        v_codec = avcodec_find_decoder(codec_id);

        if (v_codec) {
            std::cout << "[VideoSource] Opened Video Codec: " << v_codec->name << " for " << path << std::endl;
            codec_ctx = avcodec_alloc_context3(v_codec);
            avcodec_parameters_to_context(codec_ctx, fmt_ctx->streams[video_stream_idx]->codecpar);
            
            // Limit threads to avoid overloading
            codec_ctx->thread_count = 1; 

            if (avcodec_open2(codec_ctx, v_codec, nullptr) < 0) {
                std::cerr << "[VideoSource] Failed to open codec." << std::endl;
            }
        } else {
             std::cerr << "[VideoSource] No codec found for ID " << codec_id << std::endl;
        }
    }

    // Initialize Audio Decoder
    if (audio_stream_idx != -1) {
        const AVCodec* a_codec = avcodec_find_decoder(fmt_ctx->streams[audio_stream_idx]->codecpar->codec_id);
        if (a_codec) {
            audio_codec_ctx = avcodec_alloc_context3(a_codec);
            avcodec_parameters_to_context(audio_codec_ctx, fmt_ctx->streams[audio_stream_idx]->codecpar);
            
            // Enable Multi-threading for audio if possible
            audio_codec_ctx->thread_count = 0; 
            audio_codec_ctx->thread_type = FF_THREAD_FRAME;
            
            avcodec_open2(audio_codec_ctx, a_codec, nullptr);
            audio_frame = av_frame_alloc();
        }
    }

    av_frame = av_frame_alloc();
    pkt = av_packet_alloc();
}

VideoSource::~VideoSource() {
    if (sws_ctx)    sws_freeContext(sws_ctx);
    if (av_frame)   av_frame_free(&av_frame);
    if (audio_frame) av_frame_free(&audio_frame);
    if (pkt)        av_packet_free(&pkt);
    if (codec_ctx)  avcodec_free_context(&codec_ctx);
    if (audio_codec_ctx) avcodec_free_context(&audio_codec_ctx);
    if (cached_swr) swr_free(&cached_swr);
    if (fmt_ctx)    avformat_close_input(&fmt_ctx);
}

/**
 * @brief Retrieves a specific video frame using FFmpeg seeking and decoding.
 * Implements a simple cache to avoid redundant decoding of the same frame.
 */
Frame VideoSource::getFrame(double localTime, int w, int h) {
    std::lock_guard<std::mutex> lock(mtx);
    if (!codec_ctx) return Frame(w, h);
    
    // Performance: Early exit if requesting the exact same frame again
    if (localTime == last_time && w == last_w && h == last_h) {
        return last_frame;
    }

    if (!fmt_ctx || video_stream_idx == -1) return Frame(w, h);

    const AVRational timeBase = fmt_ctx->streams[video_stream_idx]->time_base;
    const int64_t targetPts = static_cast<int64_t>(localTime / av_q2d(timeBase) + 0.001);
    
    // Seeking logic: Only seek if we are going backwards or jumping too far ahead
    if (localTime < last_time || localTime > last_time + 1.0) {
        if (avcodec_is_open(codec_ctx)) {
            avcodec_flush_buffers(codec_ctx);
        }
        av_seek_frame(fmt_ctx, video_stream_idx, targetPts, AVSEEK_FLAG_BACKWARD);
    }

    // Decoding Loop
    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_idx) {
            if (avcodec_send_packet(codec_ctx, pkt) >= 0) {
                while (avcodec_receive_frame(codec_ctx, av_frame) >= 0) {
                    if (av_frame->pts >= targetPts) {
                        Frame outputFrame(w, h, 4);
                        
                        // Smart Scaling: Maintain aspect ratio (Uniform Fit)
                        float srcAspect = (float)av_frame->width / av_frame->height;
                        float dstAspect = (float)w / h;
                        
                        int outW, outH, outX, outY;
                        if (srcAspect > dstAspect) {
                            outW = w;
                            outH = (int)(w / srcAspect);
                            outX = 0;
                            outY = (h - outH) / 2;
                        } else {
                            outH = h;
                            outW = (int)(h * srcAspect);
                            outY = 0;
                            outX = (w - outW) / 2;
                        }

                        sws_ctx = sws_getCachedContext(sws_ctx, 
                            av_frame->width, av_frame->height, static_cast<AVPixelFormat>(av_frame->format),
                            outW, outH, AV_PIX_FMT_RGBA, SWS_BILINEAR, nullptr, nullptr, nullptr);
                        
                        // Draw into the calculated sub-rectangle of the output frame
                        uint8_t* destPointers[4] = { outputFrame.data.data() + (outY * w * 4) + (outX * 4), nullptr, nullptr, nullptr };
                        int destStrides[4] = { w * 4, 0, 0, 0 };
                        
                        sws_scale(sws_ctx, av_frame->data, av_frame->linesize, 0, 
                                  av_frame->height, destPointers, destStrides);
                        
                        av_packet_unref(pkt);
                        
                        // Update cache
                        last_frame = outputFrame;
                        last_time = localTime;
                        last_w = w; last_h = h;
                        
                        return outputFrame;
                    }
                }
            }

        }
        av_packet_unref(pkt);
    }
    
    return last_frame; // Return last valid if end of stream or error
}

/**
 * @brief Decodes audio samples for a specific time range.
 * Resamples to 44100Hz Stereo Float.
 */
std::vector<float> VideoSource::getAudioSamples(double startTime, double duration) {
    std::lock_guard<std::mutex> lock(mtx);
    if (!audio_codec_ctx || audio_stream_idx == -1) return {};

    double srcDur = getDuration();
    if (srcDur > 0.001) { // Evitar fmod por cero o valores insignificantes
        startTime = std::fmod(startTime, srcDur);
        if (startTime < 0) startTime += srcDur;
    }

    const int targetSampleRate = 44100;
    const int targetChannels = 2;
    const size_t targetSampleCount = static_cast<size_t>(duration * targetSampleRate) * targetChannels;
    std::vector<float> samples;
    samples.reserve(targetSampleCount);

    const double timeBase = av_q2d(fmt_ctx->streams[audio_stream_idx]->time_base);
    const int64_t startPts = static_cast<int64_t>(startTime / timeBase);

    // Optimized sequential reading vs seeking
    if (startTime < last_audio_time - 0.1 || startTime > last_audio_time + 0.5) {
        if (avcodec_is_open(audio_codec_ctx)) {
            avcodec_flush_buffers(audio_codec_ctx);
        }
        // Seek slightly before to satisfy keyframe/codec dependencies
        int64_t seekPts = std::max((int64_t)0, startPts - static_cast<int64_t>(0.2 / timeBase));
        av_seek_frame(fmt_ctx, audio_stream_idx, seekPts, AVSEEK_FLAG_BACKWARD);
        last_audio_time = -1.0; 
    }

    if (!cached_swr) {
        cached_swr = swr_alloc();
        av_opt_set_chlayout(cached_swr, "in_chlayout", &audio_codec_ctx->ch_layout, 0);
        av_opt_set_int(cached_swr, "in_sample_rate", audio_codec_ctx->sample_rate, 0);
        av_opt_set_sample_fmt(cached_swr, "in_sample_fmt", audio_codec_ctx->sample_fmt, 0);
        
        AVChannelLayout outLayout;
        av_channel_layout_default(&outLayout, targetChannels);
        av_opt_set_chlayout(cached_swr, "out_chlayout", &outLayout, 0);
        av_opt_set_int(cached_swr, "out_sample_rate", targetSampleRate, 0);
        av_opt_set_sample_fmt(cached_swr, "out_sample_fmt", AV_SAMPLE_FMT_FLT, 0);
        swr_init(cached_swr);
    }

    // Decoding Loop
    int loopSafety = 0;
    while (samples.size() < targetSampleCount && loopSafety < 10) {
        if (av_read_frame(fmt_ctx, pkt) < 0) {
            // SOPORTE PARA BUCLE: Si llegamos al final pero necesitamos más muestras, volvemos a empezar
            if (avcodec_is_open(audio_codec_ctx)) {
                avcodec_flush_buffers(audio_codec_ctx);
            }
            av_seek_frame(fmt_ctx, audio_stream_idx, 0, AVSEEK_FLAG_BACKWARD);
            last_audio_time = -1.0;
            loopSafety++;
            continue;
        }

        if (pkt->stream_index == audio_stream_idx) {
            if (avcodec_send_packet(audio_codec_ctx, pkt) >= 0) {
                while (avcodec_receive_frame(audio_codec_ctx, audio_frame) >= 0) {
                    double frameTime = audio_frame->pts * timeBase;
                    double frameDuration = (double)audio_frame->nb_samples / audio_codec_ctx->sample_rate;
                    double frameEnd = frameTime + frameDuration;

                    if (frameEnd > startTime) {
                        // Max possible output samples based on input + delay
                        int outCapacity = av_rescale_rnd(swr_get_delay(cached_swr, audio_codec_ctx->sample_rate) + audio_frame->nb_samples, targetSampleRate, audio_codec_ctx->sample_rate, AV_ROUND_UP);
                        std::vector<float> resampledBuffer(outCapacity * targetChannels);
                        uint8_t* outPtr[1] = { reinterpret_cast<uint8_t*>(resampledBuffer.data()) };
                        
                        int outSamples = swr_convert(cached_swr, outPtr, outCapacity, (const uint8_t**)audio_frame->data, audio_frame->nb_samples);
                        if (outSamples > 0) {
                            size_t frameSampleCount = outSamples * targetChannels;
                            size_t copyOffset = 0;
                            
                            // Handle if this frame starts BEFORE our desired start time
                            if (frameTime < startTime) {
                                double diff = startTime - frameTime;
                                copyOffset = static_cast<size_t>(diff * targetSampleRate) * targetChannels;
                                copyOffset = (copyOffset / targetChannels) * targetChannels; // Align
                            }
                            
                            if (copyOffset < frameSampleCount) {
                                size_t availToCopy = frameSampleCount - copyOffset;
                                size_t needToCopy = targetSampleCount - samples.size();
                                size_t actualCopy = std::min(availToCopy, needToCopy);
                                
                                samples.insert(samples.end(), resampledBuffer.begin() + copyOffset, resampledBuffer.begin() + copyOffset + actualCopy);
                            }
                        }
                    }
                    last_audio_time = frameEnd;
                    if (samples.size() >= targetSampleCount) break;
                }
            }
        }
        av_packet_unref(pkt);
        if (samples.size() >= targetSampleCount) break;
    }

    // Gap Fill: If we didn't get enough samples (EOF or skip), fill with silence
    if (samples.size() < targetSampleCount) {
        samples.resize(targetSampleCount, 0.0f);
    }

    return samples;
}

double VideoSource::getDuration() {
    if (!fmt_ctx) return 0.0;
    return (double)fmt_ctx->duration / AV_TIME_BASE;
}

std::vector<float> VideoSource::getWaveform(int points) {
    if (audio_stream_idx == -1 || points <= 0) return {};
    
    std::vector<float> peaks(points, 0.0f);
    double duration = getDuration();
    if (duration <= 0) return {};

    AVFormatContext* temp_fmt_ctx = nullptr;
    if (avformat_open_input(&temp_fmt_ctx, path.c_str(), nullptr, nullptr) < 0) return {};
    if (avformat_find_stream_info(temp_fmt_ctx, nullptr) < 0) {
        avformat_close_input(&temp_fmt_ctx);
        return {};
    }

    const AVCodec* a_codec = avcodec_find_decoder(temp_fmt_ctx->streams[audio_stream_idx]->codecpar->codec_id);
    if (!a_codec) {
        avformat_close_input(&temp_fmt_ctx);
        return {};
    }

    AVCodecContext* a_ctx = avcodec_alloc_context3(a_codec);
    avcodec_parameters_to_context(a_ctx, temp_fmt_ctx->streams[audio_stream_idx]->codecpar);
    if (avcodec_open2(a_ctx, a_codec, nullptr) < 0) {
        avcodec_free_context(&a_ctx);
        avformat_close_input(&temp_fmt_ctx);
        return {};
    }

    AVFrame* a_frame = av_frame_alloc();
    AVPacket* a_pkt = av_packet_alloc();
    
    int64_t total_samples = (int64_t)(duration * a_ctx->sample_rate);
    int64_t samples_per_point = total_samples / points;
    if (samples_per_point < 1) samples_per_point = 1;

    int64_t current_samples = 0;
    int points_computed = 0;
    float current_max = 0;

    while (av_read_frame(temp_fmt_ctx, a_pkt) >= 0) {
        if (a_pkt->stream_index == audio_stream_idx) {
            if (avcodec_send_packet(a_ctx, a_pkt) >= 0) {
                while (avcodec_receive_frame(a_ctx, a_frame) >= 0) {
                    int data_size = av_get_bytes_per_sample(a_ctx->sample_fmt);
                    int chans = a_ctx->ch_layout.nb_channels;
                    bool is_planar = av_sample_fmt_is_planar(a_ctx->sample_fmt);

                    for (int s = 0; s < a_frame->nb_samples; ++s) {
                        for (int ch = 0; ch < std::min(chans, 8); ++ch) {
                            float val = 0;
                            uint8_t* ptr = nullptr;
                            
                            if (is_planar && ch < AV_NUM_DATA_POINTERS && a_frame->data[ch]) {
                                ptr = a_frame->data[ch] + s * data_size;
                            } else if (!is_planar && a_frame->data[0]) {
                                ptr = a_frame->data[0] + (s * chans + ch) * data_size;
                            }
                            
                            if (ptr) {
                                if (a_ctx->sample_fmt == AV_SAMPLE_FMT_FLTP || a_ctx->sample_fmt == AV_SAMPLE_FMT_FLT) 
                                    val = std::abs(*(float*)ptr);
                                else if (a_ctx->sample_fmt == AV_SAMPLE_FMT_S16P || a_ctx->sample_fmt == AV_SAMPLE_FMT_S16) 
                                    val = std::abs(*(int16_t*)ptr) / 32768.0f;
                            }
                            
                            if (val > current_max) current_max = val;
                        }
                        current_samples++;
                        if (current_samples >= samples_per_point) {
                            if (points_computed < points) {
                                peaks[points_computed++] = std::min(1.0f, current_max);
                            }
                            current_max = 0;
                            current_samples = 0;
                        }
                    }
                }
            }
        }
        av_packet_unref(a_pkt);
    }

    av_frame_free(&a_frame);
    av_packet_free(&a_pkt);
    avcodec_free_context(&a_ctx);
    avformat_close_input(&temp_fmt_ctx);
    
    return peaks;
}

// ============================================================================
// IMAGE SOURCE IMPLEMENTATION
// ============================================================================

ImageSource::ImageSource(std::string p) : path(p) {}

Frame ImageSource::getFrame(double /*localTime*/, int w, int h) {
    if (!loaded || w != last_w || h != last_h) {
        load(w, h);
    }
    return cached_frame;
}

/**
 * @brief Decodes a static image using FFmpeg.
 * Unlike VideoSource, this is optimized for single-frame retrieval.
 */
void ImageSource::load(int w, int h) {
    AVFormatContext* imgFmtCtx = nullptr;
    
    if (avformat_open_input(&imgFmtCtx, path.c_str(), nullptr, nullptr) < 0) return;
    if (avformat_find_stream_info(imgFmtCtx, nullptr) < 0) {
        avformat_close_input(&imgFmtCtx);
        return;
    }

    int videoIdx = -1;
    for (unsigned int i = 0; i < imgFmtCtx->nb_streams; i++) {
        if (imgFmtCtx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            videoIdx = i;
            break;
        }
    }

    if (videoIdx == -1) {
        avformat_close_input(&imgFmtCtx);
        return;
    }

    const AVCodec* codec = avcodec_find_decoder(imgFmtCtx->streams[videoIdx]->codecpar->codec_id);
    AVCodecContext* imgCodecCtx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(imgCodecCtx, imgFmtCtx->streams[videoIdx]->codecpar);
    
    if (avcodec_open2(imgCodecCtx, codec, nullptr) < 0) {
        avcodec_free_context(&imgCodecCtx);
        avformat_close_input(&imgFmtCtx);
        return;
    }

    AVFrame* tempFrame = av_frame_alloc();
    AVPacket* tempPkt = av_packet_alloc();

    if (av_read_frame(imgFmtCtx, tempPkt) >= 0) {
        if (avcodec_send_packet(imgCodecCtx, tempPkt) >= 0) {
            if (avcodec_receive_frame(imgCodecCtx, tempFrame) >= 0) {
                cached_frame = Frame(w, h, 4);
                
                // Smart Scaling for Static Images
                float srcAspect = (float)tempFrame->width / tempFrame->height;
                float dstAspect = (float)w / h;
                
                int outW, outH, outX, outY;
                if (srcAspect > dstAspect) {
                    outW = w;
                    outH = (int)(w / srcAspect);
                    outX = 0;
                    outY = (h - outH) / 2;
                } else {
                    outH = h;
                    outW = (int)(h * srcAspect);
                    outY = 0;
                    outX = (w - outW) / 2;
                }

                SwsContext* scaler = sws_getContext(
                    tempFrame->width, tempFrame->height, static_cast<AVPixelFormat>(tempFrame->format),
                    outW, outH, AV_PIX_FMT_RGBA, SWS_BILINEAR, nullptr, nullptr, nullptr);
                
                uint8_t* dest[4] = { cached_frame.data.data() + (outY * w * 4) + (outX * 4), nullptr, nullptr, nullptr };
                int destLinesizes[4] = { w * 4, 0, 0, 0 };
                
                sws_scale(scaler, tempFrame->data, tempFrame->linesize, 0, 
                          tempFrame->height, dest, destLinesizes);
                
                sws_freeContext(scaler);

                loaded = true;
                last_w = w; 
                last_h = h;
            }
        }
        av_packet_unref(tempPkt);
    }

    // Explicit resource cleanup
    av_packet_free(&tempPkt);
    av_frame_free(&tempFrame);
    avcodec_free_context(&imgCodecCtx);
    avformat_close_input(&imgFmtCtx);
}
