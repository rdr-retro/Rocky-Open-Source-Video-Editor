from setuptools import setup, Extension
import pybind11
import os
import platform

# Force arm64 for Apple Silicon Homebrew compatibility
os.environ["ARCHFLAGS"] = "-arch arm64"

# Homebrew paths for Apple Silicon
HB_INCLUDE = "/opt/homebrew/include"
HB_LIB = "/opt/homebrew/lib"

extra_compile_args = []
extra_link_args = []
include_dirs = [pybind11.get_include()]
library_dirs = []
libraries = ['avformat', 'avcodec', 'swscale', 'avutil', 'swresample']

if platform.system() == "Windows":
    # Windows Setup
    # Check if we are using MinGW (often passed via --compiler=mingw32 or detected by setuptools)
    import sys
    is_mingw = any("mingw" in arg.lower() for arg in sys.argv)
    
    if is_mingw:
        print("Detected MinGW. Configuring for GCC/MinGW...")
        extra_compile_args = ['-std=c++17', '-O2']
    else:
        print("Detected Windows. Configuring for MSVC...")
        extra_compile_args = ['/std:c++17', '/O2']
    
    # Assume FFmpeg is in external/ffmpeg (downloaded by script)
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    FFMPEG_DIR = os.path.join(ROOT_DIR, "external", "ffmpeg")
    
    if not os.path.exists(FFMPEG_DIR):
        print(f"WARNING: FFmpeg not found at {FFMPEG_DIR}. Compilation check may fail.")
    
    include_dirs.append(os.path.join(FFMPEG_DIR, "include"))
    library_dirs.append(os.path.join(FFMPEG_DIR, "lib"))

    
else:
    # macOS / Linux Setup
    if os.path.exists(HB_INCLUDE):
        include_dirs.append(HB_INCLUDE)
    else:
        include_dirs.append("/usr/local/include")

    if os.path.exists(HB_LIB):
        library_dirs.append(HB_LIB)
    else:
        library_dirs.append("/usr/local/lib")

    extra_compile_args = ['-O3', '-std=c++17', '-DENABLE_ACCELERATE']
    extra_link_args = ['-framework', 'Accelerate', '-framework', 'CoreFoundation']


functions_module = Extension(
    'rocky_core',
    sources=[
        'src/core/bindings.cpp',
        'src/core/media_source.cpp',
        'src/core/clip.cpp',
        'src/core/engine.cpp',
        'src/core/ofx/host.cpp', # Added to build
        # Platform & Hardware Detection
        'src/platform/common/platform_detector.cpp',
        'src/hardware/optimizer.cpp',
        # Infrastructure
        'src/infrastructure/logging/logger.cpp',
        'src/infrastructure/config/runtime_config.cpp'
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    language='c++',
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args
)

setup(
    name='rocky_core',
    version='0.1',
    author='Antigravity',
    description='C++ core for Rocky Video Editor',
    ext_modules=[functions_module],
)
