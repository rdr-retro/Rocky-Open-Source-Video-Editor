# Rocky Open Source Video Editor

Rocky Video Editor is a high-performance, open-source video editing application built in Java. It is designed to provide professional-grade features with a focus on extreme performance and fluidity ("Zero-Stutter"), utilizing hardware acceleration and advanced architectural patterns.

## 1. Introduction and Philosophy

The core philosophy of Rocky is to provide a seamless editing experience. Traditional Java applications are often criticized for performance issues, especially in media processing. Rocky overcomes this by leveraging native hardware acceleration (VideoToolbox on macOS, NVENC/AMF/QSV on Windows) and a custom-built asynchronous pipeline.

The editor supports non-linear video editing (NLE), allowing users to arrange video, audio, and image clips on multiple tracks, apply effects, transitions, and export the final result in high-quality formats.

## 2. Key Features

### 2.1 Zero-Stutter Technology
Rocky implements a sophisticated "Zero-Stutter" architecture that ensures smooth playback even with 4K footage.
- **Playback Isolation**: When the user hits play, non-essential background tasks (like waveform generation or thumbnail caching) are paused to dedicate all system resources to video decoding and rendering.
- **Asynchronous Texture Upload**: Frame data is uploaded to the GPU in a separate thread, preventing the Event Dispatch Thread (EDT) from blocking. This keeps the UI responsive at all times.

### 2.2 Hardware Acceleration
The application automatically detects the underlying hardware and selects the best available decoder and encoder.
- **macOS**: Utilizes Apple's VideoToolbox framework for hardware-accelerated H.264 and HEVC decoding/encoding. Optimized for both Intel and Apple Silicon (M1/M2/M3) chips.
- **Windows**:
    - **NVIDIA**: Detects GeForce/Quadro cards and enables NVENC/NVDEC.
    - **AMD**: Detects Radeon cards and enables AMF.
    - **Intel**: Detects Integrated Graphics (UHD/Iris) and enables QuickSync Video (QSV).

### 2.3 Professional Color Management
Rocky integrates ACES (Academy Color Encoding System) specifically via an efficient approximation (Narkowicz ACES) suitable for real-time rendering. This provides a filmic look with proper highlight roll-off and contrast handling, superior to standard sRGB rendering.

### 2.4 Smart Caching
- **Audio Peaks (.rocky_peaks)**: Similar to industry-standard software, Rocky generates and caches audio waveform data in binary files. This allows instant waveform loading on subsequent project opens, bypassing the need to re-analyze audio files.
- **Proxy System**: Users can toggle "Proxy Mode" to generate lower-resolution, lightweight copies of media files for editing, which are instantly swapped for the originals during the final render.

## 3. Technical Architecture

The project is structured around a Model-View-Controller (MVC) pattern, but heavily optimized for real-time media.

### 3.1 Core Components
- **TimelineModel**: The central data structure representing the project state. It manages a list of `TimelineClip` objects, arranged in tracks. It uses an `IntervalTree` for efficient spatial queries (finding which clips are under the playhead or mouse).
- **FrameServer**: The engine responsible for fetching and composing video frames. It handles the "Render Graph", pulling frames from `VideoDecoder` instances, applying effects chain, rendering transitions, and compositing layers.
- **VideoDecoder**: A wrapper around JavaCV/FFmpeg. It manages the native FFmpeg process, handles seeking, and frame grabbing. It implements a ring buffer to pre-fetch frames and smooth out playback.
- **RenderEngine**: Sharing logic with FrameServer, this component is dedicated to the export process, writing the composed frames to a video file using the selected hardware encoder.

### 3.2 Plugin System
Rocky features a robust plugin architecture based on Java's `ServiceLoader`.
- **Location**: Plugins are loaded from the local `plugins` folder and the user's home directory (`~/.rocky_plugins`).
- **Discovery**: The `PluginManager` scans the classpath and external JARs for implementations of the logical interfaces.
- **Types**:
    - **RockyMediaGenerator**: Creates content (e.g., Solid Color, Text, Checkerboard).
    - **RockyEffect**: Modifies existing frames (e.g., Blur, Sepia, Black & White).
    - **RockyTransition**: Blends two overlapping clips (e.g., CrossFade, Dissolve).

### 3.3 User Interface (UI)
The UI is built with Java Swing but customized heavily.
- **TimelinePanel**: A custom-painted component that renders the multi-track timeline, clips, waveforms, and playhead. It handles complex mouse interactions for trimming, moving, and selecting clips.
- **PropertiesWindow**: A dynamic panel that inspects the currently selected clip. It uses reflection or a property model to expose editable fields (Position, Opacity, Plugin Parameters).
- **TextEditorDialog**: A specialized dialog for the Text Generator plugin, offering controls for Font, Size, Color, and Text content with a modern dark theme.

## 4. Project Structure

- **src/**: Contains the main application source code.
    - `rocky.app`: Entry point (`RockyMain.java`).
    - `rocky.core`: Core logic, data models, and media processing.
        - `model`: `TimelineClip`, `TimelineModel`, `ProjectProperties`.
        - `media`: `VideoDecoder`, `AudioDecoder`, `FrameServer`.
        - `plugins`: Plugin interfaces and `PluginManager`.
    - `rocky.ui`: UI components.
        - `timeline`: `TimelinePanel`, `TimelineRuler`.
        - `viewer`: `ViewerPanel`, `GLCanvas` integration.
- **plugins_src/**: Source code for built-in plugins (Standard Library).
    - `rocky.core.plugins.samples`: Implementations like `TextGenerator`, `SolidColorGenerator`.
    - `META-INF/services`: Configuration files for `ServiceLoader`.
- **lib/**: External dependencies (JARs). Populated automatically by the build script.
- **bin_user/**: Output directory for compiled main application classes.
- **bin_plugins/**: Temporary output directory for compiling plugins.
- **plugins/**: Final destination for packaged plugin JARs (`samples.jar`).

## 5. Development Guide

### 5.1 Dependencies
The project relies on **JavaCV** (Java Wrapper for OpenCV and FFmpeg) handling all low-level media operations.
- `ffmpeg.jar`: The core media library.
- `javacv.jar`: The Java bridge.
- `javacpp.jar`: Native memory management.
The build scripts automatically download the correct versions of these libraries from Maven Central into the `lib/` folder.

### 5.2 Compiling the Project
We provide custom build scripts that handle dependency downloading, compilation, and plugin packaging.

#### Windows
1.  Navigate to the project root directory.
2.  Run `compile.bat`.
    - This script checks for `lib/` dependencies and downloads them if missing.
    - It compiles `src/` into `bin_user/`.
    - It compiles `plugins_src/` into `plugins/samples.jar`.
    - It configures a portable FFmpeg if necessary.

#### macOS and Linux
1.  Open a terminal in the project root.
2.  Make the script executable: `chmod +x compile.sh`.
3.  Run `./compile.sh`.
    - Similar to the Windows script, it handles dependencies, main compilation, and plugin packaging.

### 5.3 Running the Application

#### Windows
Run `run.bat`.
- This sets up the classpath including `lib/*`, `bin_user`, and `plugins/samples.jar`.
- It launches `rocky.app.RockyMain`.

#### macOS and Linux
Run `./run.sh`.
- Ensure it is executable (`chmod +x run.sh`).
- Checks OS type to set the correct classpath separator (`:` vs `;`).
- Launches the application.

## 6. Creating Creating Custom Plugins

To create a new plugin for Rocky:

1.  **Create a Class**: Create a new Java class in `plugins_src` (or your own project) that implements one of the interfaces:
    - `rocky.core.plugins.RockyEffect`
    - `rocky.core.plugins.RockyTransition`
    - `rocky.core.plugins.RockyMediaGenerator`

2.  **Implement Methods**:
    - `getName()`, `getDescription()`, `getCategory()`: Metadata.
    - `getParameters()`: Return a list of `PluginParameter` objects (Sliders, Colors, Text, Dropdowns).
    - `render()` / `generate()`: The core logic. You receive a `BufferedImage` or `Graphics2D` context to draw your effect.

3.  **Register the Service**:
    - Create a file in `META-INF/services/` named exactly after the interface (e.g., `rocky.core.plugins.RockyEffect`).
    - Add the fully qualified name of your class (e.g., `com.myuser.MyCoolEffect`) on a new line.

4.  **Compile**: Re-run the compilation script to package your new plugin into the JAR.

## 7. Troubleshooting

### 7.1 "Command not found" on macOS/Linux
Ensure the scripts have execution permissions:
`chmod +x compile.sh run.sh`

### 7.2 Missing Dependencies / Download Errors
If the download fails, check your internet connection. You can manually place the required JARs (JavaCV, FFmpeg 6.0 components) in the `lib/` folder. The script skips download if files exist.

### 7.3 Performance Issues
- Ensure you are running on the High Performance power plan/profile.
- Rocky tries to use GPU decoding. Check console logs for "VideoToolbox" (Mac) or "NVENC" (Windows) to verify hardware acceleration is active.
- For extremely large files (8K), consider using the Proxy workflow.

### 7.4 Plugins Not Showing
- Verify `plugins/samples.jar` exists.
- Check the `META-INF/services` files for typos.
- Ensure the build script output says "Compilando y empaquetando plugins...".

## 8. License

Rocky Video Editor is open source software. Feel free to modify, fork, and contribute back to the project.
