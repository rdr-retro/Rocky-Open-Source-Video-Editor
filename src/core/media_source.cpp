#include "media_source.h"
#include <libavutil/display.h>

static std::mutex g_ff_mtx;

// ============================================================================
// COLOR SOURCE IMPLEMENTATION
// ============================================================================

ColorSource::ColorSource(uint8_t r, uint8_t g, uint8_t b, uint8_t a) 
    : r(r), g(g), b(b), a(a) {}

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
    {
        std::lock_guard<std::mutex> lock(g_ff_mtx);
        
        // Optimización de importación: Limitar el escaneo de bytes iniciales
        AVDictionary* opts = nullptr;
        av_dict_set(&opts, "probesize", "5000000", 0);        // 5MB max para detectar formato
        av_dict_set(&opts, "analyzeduration", "1000000", 0); // 1s max para detectar streams
        av_dict_set(&opts, "flags", "fastseek", 0);          // Habilitar búsqueda rápida
        
        if (avformat_open_input(&fmt_ctx, path.c_str(), nullptr, &opts) < 0) {
            std::cerr << "[VideoSource] Failed to open: " << path << std::endl;
            is_valid = false;
            av_dict_free(&opts);
            return;
        }
        
        if (avformat_find_stream_info(fmt_ctx, nullptr) < 0) {
            std::cerr << "[VideoSource] Failed to find stream info: " << path << std::endl;
            is_valid = false;
            av_dict_free(&opts);
            return;
        }
        av_dict_free(&opts);
    }

    for (unsigned int i = 0; i < fmt_ctx->nb_streams; i++) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO && video_stream_idx == -1) {
            video_stream_idx = i;
        } else if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO && audio_stream_idx == -1) {
            audio_stream_idx = i;
        }
    }

    if (video_stream_idx != -1) {
        const AVCodec* v_codec = avcodec_find_decoder(fmt_ctx->streams[video_stream_idx]->codecpar->codec_id);
        if (v_codec) {
            codec_ctx = avcodec_alloc_context3(v_codec);
            avcodec_parameters_to_context(codec_ctx, fmt_ctx->streams[video_stream_idx]->codecpar);
            
            // Optimización de decodificación: Multihilo y flags de rendimiento
            codec_ctx->thread_count = 0; // Auto-detectar núcleos
            codec_ctx->thread_type = FF_THREAD_FRAME | FF_THREAD_SLICE;
            codec_ctx->flags2 |= AV_CODEC_FLAG2_FAST;
            
            {
                std::lock_guard<std::mutex> lock(g_ff_mtx);
                avcodec_open2(codec_ctx, v_codec, nullptr);
            }
        }
    }

    if (audio_stream_idx != -1) {
        const AVCodec* a_codec = avcodec_find_decoder(fmt_ctx->streams[audio_stream_idx]->codecpar->codec_id);
        if (a_codec) {
            audio_codec_ctx = avcodec_alloc_context3(a_codec);
            avcodec_parameters_to_context(audio_codec_ctx, fmt_ctx->streams[audio_stream_idx]->codecpar);
            audio_codec_ctx->thread_count = 0;
            audio_codec_ctx->thread_type = FF_THREAD_FRAME;
            {
                std::lock_guard<std::mutex> lock(g_ff_mtx);
                avcodec_open2(audio_codec_ctx, a_codec, nullptr);
            }
            audio_frame = av_frame_alloc();
        }
    }

    av_frame = av_frame_alloc();
    pkt = av_packet_alloc();
    is_valid = (fmt_ctx != nullptr && video_stream_idx != -1);
}

VideoSource::~VideoSource() {
    std::lock_guard<std::mutex> lock(g_ff_mtx);
    if (sws_ctx)    sws_freeContext(sws_ctx);
    if (av_frame)   av_frame_free(&av_frame);
    if (audio_frame) av_frame_free(&audio_frame);
    if (pkt)        av_packet_free(&pkt);
    if (codec_ctx)  avcodec_free_context(&codec_ctx);
    if (audio_codec_ctx) avcodec_free_context(&audio_codec_ctx);
    if (cached_swr) swr_free(&cached_swr);
    if (fmt_ctx)    avformat_close_input(&fmt_ctx);
}

int VideoSource::getRotation() const {
    if (video_stream_idx == -1 || !fmt_ctx) return 0;
    AVCodecParameters* par = fmt_ctx->streams[video_stream_idx]->codecpar;
    const AVPacketSideData *sd = av_packet_side_data_get(par->coded_side_data, par->nb_coded_side_data, AV_PKT_DATA_DISPLAYMATRIX);
    if (sd) {
        double rot = -av_display_rotation_get((const int32_t*)sd->data);
        while (rot < 0) rot += 360;
        if (std::abs(rot) < 0.1) return 0;
        return (int)std::round(rot);
    }
    AVDictionaryEntry *tag = av_dict_get(fmt_ctx->streams[video_stream_idx]->metadata, "rotate", NULL, 0);
    if (tag) return std::atoi(tag->value);
    return 0;
}

int VideoSource::getNativeWidth() const {
    if (codec_ctx && codec_ctx->width > 0) return codec_ctx->width;
    if (video_stream_idx != -1 && fmt_ctx->streams[video_stream_idx]->codecpar->width > 0)
        return fmt_ctx->streams[video_stream_idx]->codecpar->width;
    return -1;
}

int VideoSource::getNativeHeight() const {
    if (codec_ctx && codec_ctx->height > 0) return codec_ctx->height;
    if (video_stream_idx != -1 && fmt_ctx->streams[video_stream_idx]->codecpar->height > 0)
        return fmt_ctx->streams[video_stream_idx]->codecpar->height;
    return -1;
}

int VideoSource::getWidth() const {
    int w = getNativeWidth();
    int rot = getRotation();
    if (std::abs(rot) == 90 || std::abs(rot) == 270) return getNativeHeight();
    return w;
}

int VideoSource::getHeight() const {
    int h = getNativeHeight();
    int rot = getRotation();
    if (std::abs(rot) == 90 || std::abs(rot) == 270) return getNativeWidth();
    return h;
}

Frame VideoSource::getFrame(double localTime, int w, int h) {
    if (w == -1) w = getWidth();
    if (h == -1) h = getHeight();

    if (last_frame && std::abs(localTime - last_time) < 0.001 && w == last_w && h == last_h) {
        return *last_frame;
    }

    std::lock_guard<std::mutex> lock(mtx);
    if (!is_valid || !codec_ctx) return Frame(w, h);

    const AVRational timeBase = fmt_ctx->streams[video_stream_idx]->time_base;
    const int64_t targetPts = static_cast<int64_t>(localTime / av_q2d(timeBase) + 0.001);
    
    if (localTime < last_time || localTime > last_time + 1.0) {
        if (avcodec_is_open(codec_ctx)) avcodec_flush_buffers(codec_ctx);
        av_seek_frame(fmt_ctx, video_stream_idx, targetPts, AVSEEK_FLAG_BACKWARD);
    }

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_idx) {
            if (avcodec_send_packet(codec_ctx, pkt) >= 0) {
                while (avcodec_receive_frame(codec_ctx, av_frame) >= 0) {
                    if (av_frame->pts >= targetPts) {
                        Frame outputFrame(w, h, 4);
                        std::fill(outputFrame.data.begin(), outputFrame.data.end(), 0);
                        
                        int rot = getRotation();
                        int nativeW = av_frame->width;
                        int nativeH = av_frame->height;
                        
                        float vW = (float)nativeW;
                        float vH = (float)nativeH;
                        if (std::abs(rot) == 90 || std::abs(rot) == 270) std::swap(vW, vH);
                        
                        float srcAspect = vW / vH;
                        float dstAspect = (float)w / h;


                        
                        int outW, outH, outX, outY;
                        if (srcAspect > dstAspect) {
                            outW = w; outH = (int)(w / srcAspect);
                            outX = 0; outY = (h - outH) / 2;
                        } else {
                            outH = h; outW = (int)(h * srcAspect);
                            outY = 0; outX = (w - outW) / 2;
                        }

                        int scaleTargetW = (std::abs(rot) == 90 || std::abs(rot) == 270) ? outH : outW;
                        int scaleTargetH = (std::abs(rot) == 90 || std::abs(rot) == 270) ? outW : outH;

                        SwsContext* new_ctx = sws_getCachedContext(sws_ctx, 
                            nativeW, nativeH, static_cast<AVPixelFormat>(av_frame->format),
                            scaleTargetW, scaleTargetH, AV_PIX_FMT_RGBA, SWS_BILINEAR, nullptr, nullptr, nullptr);
                        
                        if (!new_ctx) {
                            av_frame_unref(av_frame); av_packet_unref(pkt);
                            return Frame(w, h);
                        }
                        sws_ctx = new_ctx;
                        
                        std::vector<uint8_t> scaledData(scaleTargetW * scaleTargetH * 4);
                        uint8_t* scaledPointers[4] = { scaledData.data(), nullptr, nullptr, nullptr };
                        int scaledStrides[4] = { scaleTargetW * 4, 0, 0, 0 };
                        sws_scale(sws_ctx, av_frame->data, av_frame->linesize, 0, av_frame->height, scaledPointers, scaledStrides);
                        
                        const uint32_t* srcArr = reinterpret_cast<const uint32_t*>(scaledData.data());
                        uint32_t* dstArr = reinterpret_cast<uint32_t*>(outputFrame.data.data());
                        
                        if (rot == 90 || rot == -270) {
                            for (int y = 0; y < scaleTargetH; ++y) {
                                for (int x = 0; x < scaleTargetW; ++x) {
                                    int dx = (outW - 1 - y) + outX;
                                    int dy = x + outY;
                                    if (dx >= 0 && dx < w && dy >= 0 && dy < h)
                                        dstArr[dy * w + dx] = srcArr[y * scaleTargetW + x];
                                }
                            }
                        } else if (rot == 270 || rot == -90) {
                            for (int y = 0; y < scaleTargetH; ++y) {
                                for (int x = 0; x < scaleTargetW; ++x) {
                                    int dx = y + outX;
                                    int dy = (outH - 1 - x) + outY;
                                    if (dx >= 0 && dx < w && dy >= 0 && dy < h)
                                        dstArr[dy * w + dx] = srcArr[y * scaleTargetW + x];
                                }
                            }
                        } else if (rot == 180 || rot == -180) {
                            for (int y = 0; y < scaleTargetH; ++y) {
                                for (int x = 0; x < scaleTargetW; ++x) {
                                    int dx = (outW - 1 - x) + outX;
                                    int dy = (outH - 1 - y) + outY;
                                    if (dx >= 0 && dx < w && dy >= 0 && dy < h)
                                        dstArr[dy * w + dx] = srcArr[y * scaleTargetW + x];
                                }
                            }
                        } else {
                            for (int y = 0; y < scaleTargetH; ++y) {
                                if (y + outY >= 0 && y + outY < h && outX >= 0 && outX + scaleTargetW <= w) {
                                    std::memcpy(outputFrame.data.data() + ((y + outY) * w + outX) * 4, 
                                                scaledData.data() + (y * scaleTargetW) * 4, scaleTargetW * 4);
                                }
                            }
                        }

                        av_frame_unref(av_frame); av_packet_unref(pkt);
                        last_frame = std::make_shared<Frame>(outputFrame);
                        last_time = localTime; last_w = w; last_h = h;
                        return outputFrame;
                    }
                    av_frame_unref(av_frame);
                }
            }
        }
        av_packet_unref(pkt);
    }
    return last_frame ? *last_frame : Frame(w, h);
}

std::vector<float> VideoSource::getAudioSamples(double startTime, double duration) {
    std::lock_guard<std::mutex> lock(mtx);
    if (!audio_codec_ctx || audio_stream_idx == -1) return {};

    const int target_channels = 2;
    const int target_sample_rate = 44100;
    const size_t target_sample_count = static_cast<size_t>(duration * target_sample_rate);
    std::vector<float> samples;
    samples.reserve(target_sample_count * target_channels);

    std::call_once(swr_init_flag, [this]() {
        // FFmpeg 7.x: Use new AVChannelLayout API
        AVChannelLayout out_ch_layout = AV_CHANNEL_LAYOUT_STEREO;
        swr_alloc_set_opts2(&cached_swr,
            &out_ch_layout, AV_SAMPLE_FMT_FLT, target_sample_rate,
            &audio_codec_ctx->ch_layout, audio_codec_ctx->sample_fmt, audio_codec_ctx->sample_rate,
            0, NULL);
        swr_init(cached_swr);
    });

    const AVRational timeBase = fmt_ctx->streams[audio_stream_idx]->time_base;
    const int64_t targetPts = static_cast<int64_t>(startTime / av_q2d(timeBase));

    if (std::abs(startTime - last_audio_time) > 0.5) {
        avcodec_flush_buffers(audio_codec_ctx);
        av_seek_frame(fmt_ctx, audio_stream_idx, targetPts, AVSEEK_FLAG_BACKWARD);
    }

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == audio_stream_idx) {
            if (avcodec_send_packet(audio_codec_ctx, pkt) >= 0) {
                while (avcodec_receive_frame(audio_codec_ctx, audio_frame) >= 0) {
                    double frameStart = audio_frame->pts * av_q2d(timeBase);
                    double frameEnd = frameStart + (double)audio_frame->nb_samples / audio_codec_ctx->sample_rate;

                    if (frameEnd > startTime) {
                        int out_samples = swr_get_out_samples(cached_swr, audio_frame->nb_samples);
                        std::vector<float> resampledBuffer(out_samples * target_channels);
                        float* out_data[1] = { resampledBuffer.data() };
                        swr_convert(cached_swr, (uint8_t**)out_data, out_samples, (const uint8_t**)audio_frame->data, audio_frame->nb_samples);

                        double copyStart = std::max(startTime, frameStart);
                        double copyEnd = std::min(startTime + duration, frameEnd);
                        if (copyEnd > copyStart) {
                            size_t copyOffset = static_cast<size_t>((copyStart - frameStart) * target_sample_rate) * target_channels;
                            size_t availToCopy = static_cast<size_t>((copyEnd - copyStart) * target_sample_rate) * target_channels;
                            if (samples.size() + availToCopy <= target_sample_count * target_channels) {
                                samples.insert(samples.end(), resampledBuffer.begin() + copyOffset, resampledBuffer.begin() + copyOffset + availToCopy);
                            }
                        }
                    }
                    last_audio_time = frameEnd;
                    av_frame_unref(audio_frame);
                    if (samples.size() >= target_sample_count * target_channels) break;
                }
            }
        }
        av_packet_unref(pkt);
        if (samples.size() >= target_sample_count * target_channels) break;
    }
    if (samples.size() < target_sample_count * target_channels) samples.resize(target_sample_count * target_channels, 0.0f);
    return samples;
}

std::vector<float> VideoSource::getWaveform(int points) {
    if (points <= 0) return {};
    std::vector<float> peaks(points * 2, 0.0f);
    double duration = getDuration();
    if (duration <= 0) return peaks;
    for (int i = 0; i < points; ++i) {
        double t = (double)i / points * duration;
        auto s = getAudioSamples(t, 0.05);
        float p = 0.0f;
        for (float val : s) p = std::max(p, std::abs(val));
        peaks[i*2] = p; peaks[i*2+1] = -p;
    }
    return peaks;
}

double VideoSource::getDuration() {
    if (!fmt_ctx) return 0.0;
    return (double)fmt_ctx->duration / AV_TIME_BASE;
}

// ============================================================================
// IMAGE SOURCE IMPLEMENTATION
// ============================================================================

ImageSource::ImageSource(std::string p) : path(p) {}

void ImageSource::load(int w, int h) {
    if (w <= 0 || h <= 0) return;
    
    std::lock_guard<std::mutex> lock(mtx);
    if (loaded && last_w == w && last_h == h) return;
    
    AVFormatContext* fmt = nullptr;
    AVDictionary* opts = nullptr;
    av_dict_set(&opts, "probesize", "5000000", 0);
    
    if (avformat_open_input(&fmt, path.c_str(), nullptr, &opts) < 0) {
        std::cerr << "[ImageSource] Failed to open file: " << path << std::endl;
        cached_frame = Frame(w, h);
        is_valid = false;
        av_dict_free(&opts);
        return;
    }
    av_dict_free(&opts);
    
    if (avformat_find_stream_info(fmt, nullptr) < 0) {
        std::cerr << "[ImageSource] Failed to find stream info: " << path << std::endl;
        avformat_close_input(&fmt);
        cached_frame = Frame(w, h);
        is_valid = false;
        return;
    }
    
    int stream_idx = -1;
    for (unsigned i = 0; i < fmt->nb_streams; i++) {
        if (fmt->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            stream_idx = (int)i;
            break;
        }
    }
    
    if (stream_idx == -1) {
        std::cerr << "[ImageSource] No video stream found in image file: " << path << std::endl;
        avformat_close_input(&fmt);
        cached_frame = Frame(w, h);
        is_valid = false;
        return;
    }
    
    const AVCodec* codec = avcodec_find_decoder(fmt->streams[stream_idx]->codecpar->codec_id);
    if (!codec) {
        std::cerr << "[ImageSource] Codec not found for image: " << path << std::endl;
        avformat_close_input(&fmt);
        cached_frame = Frame(w, h);
        is_valid = false;
        return;
    }
    
    AVCodecContext* ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(ctx, fmt->streams[stream_idx]->codecpar);
    if (avcodec_open2(ctx, codec, nullptr) < 0) {
        std::cerr << "[ImageSource] Failed to open codec for image: " << path << std::endl;
        avcodec_free_context(&ctx);
        avformat_close_input(&fmt);
        cached_frame = Frame(w, h);
        is_valid = false;
        return;
    }
    
    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();
    bool frame_received = false;
    
    while (av_read_frame(fmt, pkt) >= 0) {
        if (pkt->stream_index == stream_idx) {
            if (avcodec_send_packet(ctx, pkt) >= 0) {
                if (avcodec_receive_frame(ctx, frame) >= 0) {
                    Frame out(w, h, 4);
                    std::fill(out.data.begin(), out.data.end(), 0);
                    
                    float src_aspect = (float)frame->width / (float)frame->height;
                    float dst_aspect = (float)w / (float)h;
                    
                    int outW, outH, outX, outY;
                    if (src_aspect > dst_aspect) {
                        outW = w;
                        outH = (int)((float)w / src_aspect);
                        outX = 0;
                        outY = (h - outH) / 2;
                    } else {
                        outH = h;
                        outW = (int)((float)h * src_aspect);
                        outY = 0;
                        outX = (w - outW) / 2;
                    }
                    
                    // Force RGBA with Alpha channel for PNG transparency
                    SwsContext* sws = sws_getContext(
                        frame->width, frame->height, static_cast<AVPixelFormat>(frame->format),
                        outW, outH, AV_PIX_FMT_RGBA, SWS_BILINEAR, nullptr, nullptr, nullptr);
                    
                    if (sws) {
                        uint8_t* dest[4] = { out.data.data() + (outY * w * 4) + (outX * 4), nullptr, nullptr, nullptr };
                        int strides[4] = { w * 4, 0, 0, 0 };
                        sws_scale(sws, frame->data, frame->linesize, 0, frame->height, dest, strides);
                        sws_freeContext(sws);
                        cached_frame = out;
                        frame_received = true;
                    }
                    av_frame_unref(frame);
                    av_packet_unref(pkt);
                    break;
                }
            }
        }
        av_packet_unref(pkt);
    }
    
    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&ctx);
    avformat_close_input(&fmt);
    
    if (!frame_received) {
        std::cerr << "[ImageSource] Failed to receive frame from image: " << path << std::endl;
        is_valid = false;
    } else {
        loaded = true;
        is_valid = true;
    }
    last_w = w;
    last_h = h;
}

Frame ImageSource::getFrame(double /*localTime*/, int w, int h) {
    load(w, h);
    return cached_frame;
}
