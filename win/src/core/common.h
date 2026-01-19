#pragma once

#include <vector>
#include <string>
#include <memory>
#include <algorithm>
#include <iostream>
#include <cmath>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswscale/swscale.h>
#include <libavutil/imgutils.h>
#include <libavutil/opt.h>
#include <libswresample/swresample.h>
}

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace py = pybind11;

struct Frame {
    int width, height, channels;
    std::vector<uint8_t> data;

    Frame(int w, int h, int c = 4) : width(w), height(h), channels(c) {
        data.assign(w * h * c, 0);
    }
};
