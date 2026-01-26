#include "engine.h"
#include "../platform/common/platform_detector.h"
#include "../hardware/optimizer.h"
#include "../infrastructure/config/runtime_config.h"
#include "../infrastructure/logging/logger.h"
#include "../core/ofx/host.h"
#include <pybind11/stl.h>

PYBIND11_MODULE(rocky_core, m) {
    // Exception Handler
    py::register_exception_translator([](std::exception_ptr p) {
        try {
            if (p) std::rethrow_exception(p);
        } catch (const std::exception &e) {
            py::set_error(PyExc_RuntimeError, e.what());
        } catch (...) {
            py::set_error(PyExc_RuntimeError, "Unknown Internal C++ Error");
        }
    });

    // Effect Binding
    py::class_<Effect>(m, "Effect")
        .def(py::init<std::string, std::string>())
        .def_readwrite("name", &Effect::name)
        .def_readwrite("plugin_path", &Effect::pluginPath)
        .def_readwrite("enabled", &Effect::enabled);

    // Platform Detection
    py::enum_<rocky::OS>(m, "OS")
        .value("Unknown", rocky::OS::Unknown)
        .value("Windows", rocky::OS::Windows)
        .value("macOS", rocky::OS::macOS)
        .value("Linux", rocky::OS::Linux)
        .export_values();
    
    py::enum_<rocky::RenderBackend>(m, "RenderBackend")
        .value("Software", rocky::RenderBackend::Software)
        .value("Metal", rocky::RenderBackend::Metal)
        .value("DirectX11", rocky::RenderBackend::DirectX11)
        .value("DirectX12", rocky::RenderBackend::DirectX12)
        .value("Vulkan", rocky::RenderBackend::Vulkan)
        .value("CUDA", rocky::RenderBackend::CUDA)
        .value("OpenCL", rocky::RenderBackend::OpenCL)
        .export_values();
    
    py::class_<rocky::GPUInfo>(m, "GPUInfo")
        .def(py::init<>())
        .def_readonly("vendor", &rocky::GPUInfo::vendor)
        .def_readonly("model", &rocky::GPUInfo::model)
        .def_readonly("vram_mb", &rocky::GPUInfo::vram_mb)
        .def_readonly("supports_metal", &rocky::GPUInfo::supports_metal)
        .def_readonly("supports_vulkan", &rocky::GPUInfo::supports_vulkan);
    
    py::class_<rocky::PlatformInfo>(m, "PlatformInfo")
        .def(py::init<>())
        .def_readonly("os", &rocky::PlatformInfo::os)
        .def_readonly("os_name", &rocky::PlatformInfo::os_name)
        .def_readonly("os_version", &rocky::PlatformInfo::os_version)
        .def_readonly("cpu_cores", &rocky::PlatformInfo::cpu_cores)
        .def_readonly("total_ram_mb", &rocky::PlatformInfo::total_ram_mb)
        .def_readonly("gpu_info", &rocky::PlatformInfo::gpu_info);
    
    py::class_<rocky::OptimizationProfile>(m, "OptimizationProfile")
        .def(py::init<>())
        .def_readonly("worker_threads", &rocky::OptimizationProfile::worker_threads)
        .def_readonly("frame_cache_size", &rocky::OptimizationProfile::frame_cache_size)
        .def_readonly("preferred_backend", &rocky::OptimizationProfile::preferred_backend);
    
    // Runtime Configuration (Singleton)
    py::class_<rocky::RuntimeConfig>(m, "RuntimeConfig")
        .def_static("get_instance", &rocky::RuntimeConfig::getInstance, py::return_value_policy::reference)
        .def("initialize", &rocky::RuntimeConfig::initialize)
        .def("shutdown", &rocky::RuntimeConfig::shutdown)
        .def("get_platform_info", &rocky::RuntimeConfig::getPlatformInfo)
        .def("get_optimization_profile", &rocky::RuntimeConfig::getOptimizationProfile)
        .def("is_hardware_acceleration_available", &rocky::RuntimeConfig::isHardwareAccelerationAvailable);
    
    // Logger
    py::class_<rocky::Logger>(m, "Logger")
        .def_static("init", &rocky::Logger::init)
        .def_static("info", &rocky::Logger::info)
        .def_static("warning", &rocky::Logger::warning)
        .def_static("error", &rocky::Logger::error);

    // Original bindings
    py::enum_<FadeType>(m, "FadeType")
        .value("LINEAR", FadeType::LINEAR)
        .value("FAST", FadeType::FAST)
        .value("SLOW", FadeType::SLOW)
        .value("SMOOTH", FadeType::SMOOTH)
        .value("SHARP", FadeType::SHARP)
        .export_values();

    py::class_<ClipTransform>(m, "ClipTransform")
        .def(py::init<>())
        .def_readwrite("x", &ClipTransform::x)
        .def_readwrite("y", &ClipTransform::y)
        .def_readwrite("scale_x", &ClipTransform::scaleX)
        .def_readwrite("scale_y", &ClipTransform::scaleY)
        .def_readwrite("rotation", &ClipTransform::rotation)
        .def_readwrite("anchor_x", &ClipTransform::anchorX)
        .def_readwrite("anchor_y", &ClipTransform::anchorY);

    py::class_<MediaSource, std::shared_ptr<MediaSource>>(m, "MediaSource")
        .def("get_duration", &MediaSource::getDuration)
        .def("get_frame", [](MediaSource& self, double time, int w, int h) {
            Frame f(1, 1);
            {
                py::gil_scoped_release release;
                f = self.getFrame(time, w, h);
            }
            py::array_t<uint8_t> result({f.height, f.width, f.channels});
            std::copy(f.data.begin(), f.data.end(), result.mutable_data());
            return result;
        }, py::arg("time"), py::arg("w"), py::arg("h"));
    
    py::class_<ColorSource, MediaSource, std::shared_ptr<ColorSource>>(m, "ColorSource")
        .def(py::init<uint8_t, uint8_t, uint8_t, uint8_t>(), py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a") = 255);

    py::class_<VideoSource, MediaSource, std::shared_ptr<VideoSource>>(m, "VideoSource")
        .def(py::init<std::string>())
        .def("get_width", &VideoSource::getWidth)
        .def("get_height", &VideoSource::getHeight)
        .def("get_rotation", &VideoSource::getRotation)
        .def("get_waveform", &VideoSource::getWaveform, py::call_guard<py::gil_scoped_release>());

    py::class_<ImageSource, MediaSource, std::shared_ptr<ImageSource>>(m, "ImageSource")
        .def(py::init<std::string>());

    py::class_<Clip, std::shared_ptr<Clip>>(m, "Clip")
        .def(py::init<>())
        .def_readwrite("opacity", &Clip::opacity)
        .def_readwrite("fade_in_frames", &Clip::fadeInFrames)
        .def_readwrite("fade_out_frames", &Clip::fadeOutFrames)
        .def_readwrite("fade_in_type", &Clip::fadeInType)
        .def_readwrite("fade_out_type", &Clip::fadeOutType)
        .def_readwrite("transform", &Clip::transform)
        .def_readwrite("effects", &Clip::effects);

    py::class_<RockyEngine>(m, "RockyEngine")
        .def(py::init<>())
        .def("set_resolution", &RockyEngine::setResolution)
        .def("set_fps", &RockyEngine::setFPS)
        .def("add_track", &RockyEngine::addTrack)
        .def("add_clip", &RockyEngine::addClip)
        .def("set_master_gain", &RockyEngine::setMasterGain)
        .def("evaluate", &RockyEngine::evaluate)
        .def("render_audio", &RockyEngine::render_audio)
        .def("clear", &RockyEngine::clear)
        .def_static("format_timecode", &RockyEngine::formatTimecode)
        .def_static("resample_audio", &RockyEngine::resampleAudio);
    
    // OpenFX Bindings
    m.def("load_ofx_plugin", [](std::string path) {
        return RockyOfxHost::getInstance().loadPlugin(path);
    });

    m.attr("VIDEO") = 1;
    m.attr("AUDIO") = 2;
}
