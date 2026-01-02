# Rocky Open Source Video Editor

**Rocky Open Source Video Editor** es un motor de edición de vídeo cinematográfico y profesional desarrollado íntegramente en **Java**. Diseñado para ofrecer una arquitectura de alta fidelidad, Rocky separa los conceptos de datos brutos, composición lógica y visualización dinámica para garantizar que tu visión creativa nunca se vea comprometida por limitaciones técnicas.

Este proyecto prioriza el rendimiento en tiempo real, la edición fluida (estilo Sony Vegas) y la precisión de color mediante un motor hibridado de Java y FFmpeg.

---

## 🏗 Arquitectura de Vanguardia: El Sistema de 3 Espacios

A diferencia de editores básicos que simplemente ajustan imágenes a una ventana, Rocky implementa un sistema vectorial de transformación inspirado en software de gama alta como Premiere Pro, DaVinci Resolve y Sony Vegas.

### 1. Espacio del Asset (Local)
Maneja la resolución y el formato real del medio original.
- **Independencia Total**: Rocky no modifica tus archivos. Lee los metadatos nativos para calcular escalas correctas en los pasos siguientes.
- **Precisión de Color**: Los frames se extraen en el espacio de color nativo y se procesan internamente en formato de alta profundidad antes de cualquier conversión para visor.

### 2. Espacio del Proyecto (Lienzo Lógico)
Es el "cerebro" donde ocurre la composición. Todo se compone sobre un lienzo definido por la resolución del proyecto (ej. 4K, 1080p).
- **Transformaciones Lógicas**: Las coordenadas de posición, escala y rotación se guardan relativas al tamaño del proyecto, permitiendo que tu edición sea reproducible en cualquier resolución de salida.
- **Composición Multi-Capa**: El motor procesa todas las pistas activas, aplicando opacidades, modos de mezcla y transformaciones afines de forma jerárquica.

### 3. Espacio del Visor (Viewport)
Una capa de visualización inteligente que escala el lienzo del proyecto para que quepa en tu interfaz física de usuario.
- **Letterboxing / Pillarboxing**: Gestión automática de barras negras para preservar el aspecto cinematográfico original sin importar el tamaño de la ventana.
- **Interacción 1:1**: El sistema de coordenadas del ratón se traduce instantáneamente al espacio del proyecto, permitiendo una edición táctil y precisa sobre los elementos visuales.

---

## ⚡️ Motor de Alto Rendimiento "Vegas-Style"

Hemos rediseñado el núcleo de Rocky para ser uno de los editores más rápidos y estables escritos en Java.

### El Motor de Previsualización (FrameServer)
El `FrameServer` es el corazón de la fluidez en Rocky. Implementa técnicas avanzadas de streaming de video:
- **Background Pre-fetching**: Utiliza un `ExecutorService` con un pool de hilos dinámico que analiza la posición del cabezal de reproducción y comienza a renderizar los próximos 15-30 fotogramas antes de que llegues a ellos.
- **Caché Inteligente (LRU-style)**: Un `ConcurrentHashMap` mantiene en memoria los últimos 60 fotogramas generados. Esto permite hacer "scrubbing" (arrastrar el cabezal) hacia atrás y adelante con latencia cero en zonas ya procesadas.
- **Calidad Multinivel**:
    - **Draft / Preview**: Optimizado para velocidad. Usa interpolación *Nearest Neighbor* y reduce la carga computacional sacrificando nitidez temporal.
    - **Good / Best**: Optimizado para fidelidad. Usa interpolación *Bicubic* y activa todos los procesadores de color para una visión exacta del resultado final.

### Renderizado Paralelo y Exportación
El motor de exportación ya no es secuencial.
- **Pipeline de Paso Triple**: Mientras el hilo principal gestiona la interfaz, un grupo de hilos "productores" genera los fotogramas de la composición y un hilo "consumidor" alimenta el encoder de FFmpeg en tiempo real.
- **Aceleración Hardware Nativa**: Integración profunda con los motores de codificación del sistema operativo (VideoToolbox en macOS, NVENC/DXVA en Windows).

---

## 🎨 Características de Edición Profesional

### Línea de Tiempo de Nueva Generación
- **Miniaturas Dinámicas (Thumbnails)**: Cada clip de vídeo muestra visualmente su contenido inicial directamente en el timeline, facilitando la organización visual de proyectos complejos.
- **Zoom Infinito Vegas System**: Navega por tu proyecto con precisión quirúrgica. Usa las teclas `+` y `-` para acercarte hasta el nivel de fotograma individual o alejarte para ver horas de contenido en un solo vistazo.
- **Magnetismo Adaptativo (Smart Snapping)**: El sistema de snapping se ajusta dinámicamente según tu nivel de zoom. No más clips que se "pegan" a donde no quieres; la atracción ahora es puramente basada en píxeles visuales para una sensación orgánica.

### Herramientas de Manipulación de Clips
- **Sistema de Copiado/Pegado**: Duplica estructuras de edición completas. El comando Pegar inserta el clip exactamente en la posición del ratón en la pista seleccionada.
- **División Instantánea (Split)**: Corta clips en tiempo real sin interrumpir la reproducción.
- **Opacidad y Fades**: Curvas de fundido suaves con representación visual de *dithering* táctico en el timeline.

### Gestión de Audio de Alta Fidelidad
- **Visualización de Ondas (Waveforms)**: El `PeakManager` procesa el audio de forma asíncrona, extrayendo los picos de intensidad sin congelar la interfaz de usuario.
- **Sincronía Maestro-Reloj**: Rocky usa el stream de audio como el reloj maestro del sistema. Si el vídeo se retrasa, el `FrameServer` realiza saltos inteligentes de fotogramas (frame-drop controlado) para mantener la sincronía labial perfecta.

---

## 🎞 Compatibilidad y Formatos

Rocky aprovecha la potencia de FFmpeg integrado a través de JavaCV para ofrecer una compatibilidad sin precedentes:

- **Formatos de Vídeo**: MP4 (H.264/H.265), MOV (ProRes), MKV, AVI, WebM, FLV.
- **Formatos de Imagen**: WebP (Soporte total estático/animado), PNG (con Alpha), JPG, GIF (con bucle automático).
- **Formatos de Audio**: MP3, WAV (PCM), AAC, M4A, OGG, FLAC.
- **Transparencia Nativa**: Soporte completo para canales Alpha en WebP y PNG, permitiendo superposiciones gráficas complejas y títulos.

---

## 🛠 Especificaciones Técnicas y Desarrollo

### Requisitos Técnicos
- **Java**: JDK 17 o 21 (Recomendado para optimizaciones de ZGC).
- **OS**: macOS (Universal/Apple Silicon), Windows 10/11, Linux (Ubuntu/Fedora).
- **Hardware**: Se recomienda GPU con soporte para OpenGL para el renderizado del visor.

### Estructura del Código Source
- `rocky.core.media`: Gestión de decodificadores y fuentes de medios originales.
- `rocky.core.engine`: El motor de composición, pre-fetching y renderizado final.
- `rocky.ui.timeline`: Implementación Swing de la línea de tiempo, interacción de ratón y renderizado de clips.
- `rocky.ui.viewer`: Panel de visualización con escalado afín y lógica de previsualización.

### Compilación para Desarrolladores (Linux / macOS)
El proyecto incluye scripts optimizados para una compilación rápida. Si usas Linux o macOS, asegúrate de otorgar permisos de ejecución por única vez:

```bash
# Otorgar permisos de ejecución
chmod +x compile.sh
chmod +x run.sh

# Compilar proyecto completo
./compile.sh

# Ejecutar el editor
./run.sh
```

### Compilación en Windows
Simplemente ejecuta los archivos `.bat`:
```cmd
compile.bat
run.bat
```

---

## 🚀 Hoja de Ruta (Roadmap)

### Fase Actualmente en Desarrollo: "The Creative Update"
- [x] **Vegas Engine**: Sistema de pre-fetching y caché de 60 frames.
- [x] **Multi-threaded Rendering**: Exportación paralela Java-to-FFmpeg.
- [x] **Clip Thumbnails**: Miniaturas visuales en el timeline.
- [x] **Precision Snapping**: Magnetismo basado en píxeles.
- [x] **WebP & Color Fix**: Soporte total de WebP con precisión de color BGRA en Mac.
- [/] **Efectos de Capa**: Implementación de Blur Gaussiano y Corrección Gamma.
- [ ] **Multi-Select**: Selección de múltiples clips con la tecla Shift/Ctrl.

### Fase Futura: "Professional Mastering"
- [ ] **Generador de Títulos**: Sistema de texto enriquecido con sombras y bordes.
- [ ] **Modos de Fusión**: Screen, Multiply, Overlay por cada clip.
- [ ] **Audio Mixer**: Mezclador de canales con EQ y soporte para plugins de efectos.
- [ ] **Proxy System**: Creación automática de archivos de baja resolución para edición en máquinas menos potentes.

---

## ❓ Preguntas Frecuentes (FAQ)

**¿Por qué elegir Rocky frente a otros editores open source?**
Rocky está diseñado para ser ligero y predecible. Al estar escrito en Java, ofrece una seguridad de memoria superior y una portabilidad real entre Windows, Mac y Linux sin las pesadillas de dependencias de C++.

**¿Puedo editar video 4K en un portátil normal?**
Sí, gracias al sistema de "Calidad de Previsualización". Puedes poner el visor en modo "Draft" para editar fluídamente y solo subir a "Best" cuando necesites revisar detalles finos o exportar.

**¿Cómo gestiona Rocky los colores en Mac M1/M2/M3/M4?**
Hemos implementado un pipeline específico para Little Endian que mapea los canales de color directamente a los formatos nativos de macOS (BGRA), evitando los típicos problemas de "colores lavados" o amarillos que se ven rosáceos.

---

## 🤝 Contribución y Comunidad

Rocky es un esfuerzo comunitario para democratizar la edición de vídeo de alta calidad. Si deseas contribuir:
1. Revisa las tareas pendientes en el Roadmap.
2. Asegúrate de seguir las guías de estilo de código (Java Standard).
3. Envía tus Pull Requests enfocadas en el rendimiento del `FrameServer` o nuevos filtros en `MediaDecoder`.

---

**Rocky Open Source Video Editor** - *Simplificando la complejidad del cine digital.*

Desarrollado con ❤️ para la comunidad creativa mundial. 
© 2026 Rocky Project Team.
