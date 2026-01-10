from setuptools import setup, Extension
import pybind11
import os

# Force arm64 for Apple Silicon Homebrew compatibility
os.environ["ARCHFLAGS"] = "-arch arm64"

# Homebrew paths for Apple Silicon
HB_INCLUDE = "/opt/homebrew/include"
HB_LIB = "/opt/homebrew/lib"

functions_module = Extension(
    'rocky_core',
    sources=[
        'src/core/bindings.cpp',
        'src/core/media_source.cpp',
        'src/core/clip.cpp',
        'src/core/engine.cpp',
        # Platform & Hardware Detection
        'src/platform/common/platform_detector.cpp',
        'src/hardware/optimizer.cpp',
        # Infrastructure
        'src/infrastructure/logging/logger.cpp',
        'src/infrastructure/config/runtime_config.cpp'
    ],
    include_dirs=[
        pybind11.get_include(),
        HB_INCLUDE if os.path.exists(HB_INCLUDE) else "/usr/local/include"
    ],
    library_dirs=[
        HB_LIB if os.path.exists(HB_LIB) else "/usr/local/lib"
    ],
    libraries=['avformat', 'avcodec', 'swscale', 'avutil', 'swresample'],
    language='c++',
    extra_compile_args=['-O3', '-std=c++17', '-DENABLE_ACCELERATE'],
    extra_link_args=['-framework', 'Accelerate', '-framework', 'CoreFoundation']
)

setup(
    name='rocky_core',
    version='0.1',
    author='Antigravity',
    description='C++ core for Rocky Video Editor',
    ext_modules=[functions_module],
)
