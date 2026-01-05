# Rocky Open Source Video Editor

Rocky Video Editor es un editor de video gratuito y de código abierto diseñado para ofrecer un rendimiento de nivel profesional con una interfaz intuitiva.

##  Arquitectura "Zero-Stutter" (Multi-Plataforma)

Rocky ha sido rediseñado para ofrecer la fluidez más extrema del mercado en Java, detectando automáticamente tu sistema operativo y hardware para optimizar el rendimiento:

### Aceleración por Hardware Automática
Rocky detecta tu tarjeta gráfica y utiliza el codificador nativo más rápido disponible:
- **macOS (Apple Silicon/Intel)**: Usa **VideoToolbox** (nativo de Apple) para una renderización ultra-rápida y eficiente.
- **Windows (NVIDIA)**: Detecta tarjetas GeForce/Quadro y activa **NVENC**.
- **Windows (AMD)**: Detecta tarjetas Radeon y activa **AMF**.
- **Windows (Intel)**: Detecta gráficos integrados (UHD/Iris) y activa **QuickSync (QSV)**.

### Optimizaciones del Motor
- **Playback Isolation Mode**: Sistema inteligente que pausa procesos secundarios (miniaturas, ondas de audio) al dar a "Play" para dedicar toda la potencia del equipo a la fluidez del video.
- **Ondas de Audio Persistentes (.rocky_peaks)**: Inspirado en Sony Vegas (.sfk), Rocky guarda un caché binario de las ondas de audio para que se carguen instantáneamente sin volver a analizar el video.
- **Async Texture Pipeline**: Subida de fotogramas a VRAM en hilos secundarios, eliminando por completo los bloqueos o avisos de `EDT BLOCKED`.
- **Async History Engine**: El sistema de Undo/Redo (historial) funciona en segundo plano, permitiendo mover clips o soltar archivos sin micro-parones.

## Características Principales

- **Edición Multiuso**: Soporta múltiples pistas de video y audio simultáneas.
- **Formatos Profesionales**: Soporte para MP4, MOV (HEVC/H264), MP3, WAV y archivos de audio CAF.
- **Línea de Tiempo Intuitiva**: Arrastra y suelta (Drag & Drop) para empezar a editar al instante.
- **Control Creativo**: Ajusta opacidad, realiza cortes precisos, aplica ACES Color Management y usa Keyframes para animar.
- **Gestión de Proxies**: Genera versiones ligeras de tus clips (botón "px") para una respuesta táctil instantánea en proyectos masivos.

## Como Descargar e Instalar

Sigue estos pasos sencillos para empezar a usar Rocky Video Editor en tu ordenador:

### Requisitos Previos
Necesitas tener **Java** instalado en tu ordenador. Es probable que ya lo tengas, pero si no, puedes descargarlo gratis desde la pagina oficial de Java u OpenJDK.

### Paso 1: Descargar
1. Ve al boton verde que dice "Code" en la parte superior de esta pagina.
2. Selecciona la opcion "Download ZIP".
3. Guarda el archivo en tu escritorio o carpeta de descargas.

### Paso 2: Preparar
1. Busca el archivo ZIP que acabas de descargar.
2. Haz clic derecho sobre el y selecciona "Extraer aqui" o "Descomprimir".
3. Entra en la carpeta que se ha creado.

### Paso 3: Abrir el Programa

**En Windows:**
1. Dentro de la carpeta, busca un archivo llamado `run.bat` (o simplemente `run`).
2. Haz doble clic sobre el para iniciar el editor.

**En Mac o Linux:**
1. Abre la carpeta del programa.
2. Haz doble clic en el archivo `run.sh` (o `run`).
3. Nota: Si no se abre al hacer doble clic, es posible que necesites abrir la "Terminal", arrastrar el archivo `run.sh` dentro y pulsar Enter.

¡Y listo! El editor deberia abrirse y estar listo para usarse.
