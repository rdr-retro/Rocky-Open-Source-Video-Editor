# Rocky Video Editor

## English Version

Rocky Video Editor is a high-performance, non-linear video editing software designed to bridge the gap between ease of use and professional computational power. The architecture is a hybrid masterpiece: a low-level C++ rendering core (Rocky Core) paired with a modern, high-contrast Python/PyQt5 user interface.

### Core Philosophy

The project was born from the need for a video editor that maximizes hardware potential, specifically targeting modern multi-core processors and specialized multimedia instruction sets like Apple's Accelerate framework. Unlike many script-based editors, Rocky leverages C++ for every pixel manipulation and audio mix, ensuring that the interface remains fluid while the engine performs heavy lifting in background threads.

### Key Features

1.  Rocky Core C++ Engine: A high-performance library built on C++17 that handles video decoding via FFmpeg, real-time compositing, and audio processing.
2.  Master Clock Synchronization: Implemented using high-precision wall-clock timing to ensure zero audio-video drift, even under high system load.
3.  Multi-Format Support: Native support for aspect ratios including 16:9 (Wide), 9:16 (Vertical), 21:9 (Cinematic), 4:3 (Classic), and 1:1 (Square).
4.  Advanced Timeline: A custom-built timeline component supporting ripple edits, rolling edits, snapping, and precision clip splitting.
5.  Audio Mastering: Real-time VU meters, master gain controls, and soft-limiters to prevent digital clipping.
6.  Proxy Workflow: Automatic background proxy generation to enable smooth editing of high-bitrate 4K footage on standard hardware.
7.  Visual Context: Professional workstation aesthetic using a neutral gray canvas and charcoal-toned UI elements to minimize eye strain.

### Technical Architecture

The application is divided into three distinct layers:

1.  The Rendering Core (C++):
    -   IntervalTree: A data structure used to manage timeline clips with O(log N) search complexity.
    -   MediaSource: Abstraction layer for FFmpeg decoders, supporting VideoToolbox and hardware acceleration.
    -   Engine: The orchestrator that receives time requests and produces RGBA frame buffers and Float32 audio chunks.

2.  The Bridge (Pybind11):
    -   Seamlessly maps C++ classes to Python objects.
    -   Efficient memory handling using shared pointers and GIL-aware execution to prevent UI blocking.

3.  The GUI (Python/PyQt5):
    -   Standardized NLE workflow with Project Assets, Viewer, and Timeline.
    -   Dynamic styling system for premium workstation aesthetics.

### Minimum Requirements

To build and run Rocky Video Editor, your system must meet these specifications:

-   Operating System: macOS 11+, Windows 10/11, or Modern Linux Distro.
-   CPU: 4-core processor (8-core recommended).
-   RAM: 8GB (16GB recommended for 4K editing).
-   Python: Version 3.12 or higher.
-   FFmpeg: Header files and dynamic libraries (avcodec, avformat, swscale).
-   Compiler: C++17 compliant (Clang, GCC, or MSVC).

### Installation and Compilation

The project uses a unified shell script to handle environment setup and compilation. Ensure you have the FFmpeg development libraries installed on your system.

On macOS (Brew):
brew install ffmpeg

On Ubuntu:
sudo apt install libavcodec-dev libavformat-dev libswscale-dev

Then, run the one-line command:
chmod +x run.sh && ./run.sh

### Usage Instructions

1.  Import Media: Drag and drop video or audio files from your file explorer into the Assets panel or directly onto the timeline tracks.
2.  Editing:
    -   Split: Right-click on a clip and select Split to cut it at the playhead position.
    -   Copy/Paste: Use the context menu to duplicate clips across tracks.
    -   Fades: Drag the top-corner handles of a clip to create opacity or volume fades.
3.  Settings: Click the Gear icon to adjust resolution (up to 8K) and target frame rates (Hz).
4.  Render: Click Export to generate the final MP4 file using the high-quality H264 encoder.

### Development Roadmap

-   GPU Compositing: Transitioning the CPU-based blending engine to Fragment Shaders (Metal/Vulkan).
-   Color Grading: Adding LUT support and real-time primary color correction tools.
-   Keyframe Automation: Enabling precise control over every parameter over time.

---

## Versión en Castellano

Rocky Video Editor es un software de edición de vídeo no lineal de alto rendimiento diseñado para cerrar la brecha entre la facilidad de uso y la potencia computacional profesional. La arquitectura es una obra maestra híbrida: un núcleo de renderizado de bajo nivel en C++ (Rocky Core) emparejado con una interfaz de usuario moderna de alto contraste en Python/PyQt5.

### Filosofía del Proyecto

El proyecto nació de la necesidad de un editor de vídeo que maximice el potencial del hardware, apuntando específicamente a procesadores multinúcleo modernos y conjuntos de instrucciones multimedia especializados como el framework Accelerate de Apple. A diferencia de muchos editores basados en scripts, Rocky utiliza C++ para cada manipulación de píxeles y mezcla de audio, asegurando que la interfaz permanezca fluida mientras el motor realiza el trabajo pesado en hilos de fondo.

### Características Clave

1.  Motor Rocky Core C++: Una librería de alto rendimiento construida en C++17 que maneja la decodificación de vídeo a través de FFmpeg, composición en tiempo real y procesamiento de audio.
2.  Sincronización de Reloj Maestro: Implementada mediante temporización de reloj de pared de alta precisión para asegurar una deriva de audio-vídeo de cero, incluso bajo alta carga del sistema.
3.  Soporte para Múltiples Formatos: Soporte nativo para relaciones de aspecto que incluyen 16:9 (Panorámico), 9:16 (Vertical), 21:9 (Cinemático), 4:3 (Clásico) y 1:1 (Cuadrado).
4.  Timeline Avanzada: Un componente de línea de tiempo personalizado que soporta ediciones tipo ripple, rolling, imantado (snapping) y división de clips de precisión.
5.  Masterización de Audio: Medidores VU en tiempo real, controles de ganancia maestra y limitadores suaves para prevenir el clipping digital.
6.  Flujo de Trabajo de Proxies: Generación automática de proxies en segundo plano para permitir la edición fluida de material 4K de alto bitrate en hardware estándar.
7.  Contexto Visual: Estética de estación de trabajo profesional utilizando un lienzo gris neutro y elementos de interfaz en tonos carbón para minimizar la fatiga visual.

### Arquitectura Técnica

La aplicación se divide en tres capas distintas:

1.  El Núcleo de Renderizado (C++):
    -   IntervalTree: Una estructura de datos utilizada para gestionar clips en la línea de tiempo con una complejidad de búsqueda O(log N).
    -   MediaSource: Capa de abstracción para los decodificadores FFmpeg, con soporte para VideoToolbox y aceleración de hardware.
    -   Engine: El orquestador que recibe peticiones de tiempo y produce buffers de fotogramas RGBA y fragmentos de audio Float32.

2.  El Puente (Pybind11):
    -   Mapea sin fisuras las clases de C++ a objetos de Python.
    -   Gestión eficiente de la memoria mediante punteros compartidos y ejecución consciente del GIL para prevenir el bloqueo de la UI.

3.  El GUI (Python/PyQt5):
    -   Flujo de trabajo estándar de NLE con activos del proyecto, visor y línea de tiempo.
    -   Sistema de estilos dinámicos para una estética de estación de trabajo premium.

### Requisitos Mínimos

Para compilar y ejecutar Rocky Video Editor, su sistema debe cumplir con estas especificaciones:

-   Sistema Operativo: macOS 11+, Windows 10/11, o Distribución de Linux Moderna.
-   CPU: Procesador de 4 núcleos (se recomiendan 8 núcleos).
-   RAM: 8GB (se recomiendan 16GB para edición 4K).
-   Python: Versión 3.12 o superior.
-   FFmpeg: Archivos de cabecera y librerías dinámicas (avcodec, avformat, swscale).
-   Compilador: Compatible con C++17 (Clang, GCC o MSVC).

### Instalación y Compilación

El proyecto utiliza un script de shell unificado para manejar la configuración del entorno y la compilación. Asegúrese de tener instaladas las librerías de desarrollo de FFmpeg en su sistema.

En macOS (Brew):
brew install ffmpeg

En Ubuntu:
sudo apt install libavcodec-dev libavformat-dev libswscale-dev

Después, ejecute el comando de una sola línea:
chmod +x run.sh && ./run.sh

### Instrucciones de Uso

1.  Importar Medios: Arrastre y suelte archivos de vídeo o audio desde su explorador de archivos al panel de Activos o directamente a las pistas del timeline.
2.  Edición:
    -   Dividir: Haga clic derecho en un clip y seleccione Dividir para cortarlo en la posición del cabezal.
    -   Copiar/Pegar: Use el menú contextual para duplicar clips entre pistas.
    -   Fades: Arrastre los tiradores de las esquinas superiores de un clip para crear fundidos de opacidad o volumen.
3.  Ajustes: Haga clic en el icono del Engranaje para ajustar la resolución (hasta 8K) y las frecuencias de cuadro (Hz).
4.  Renderizar: Haga clic en Exportar para generar el archivo MP4 final usando el codificador H264 de alta calidad.

### Hoja de Ruta del Desarrollo

-   Composición por GPU: Transición del motor de mezcla basado en CPU a Fragment Shaders (Metal/Vulkan).
-   Corrección de Color: Añadir soporte para LUTs y herramientas de corrección de color primaria en tiempo real.
-   Automatización por Keyframes: Permitir el control preciso de cada parámetro a lo largo del tiempo.

---
*Copyright 2026 Rocky Video Editor. Todos los derechos reservados.*
