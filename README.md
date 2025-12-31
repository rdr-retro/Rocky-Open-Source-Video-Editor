# Rocky Open Source Video Editor - Motor de Edicion Profesional

Este proyecto es un motor de edicion de video profesional desarrollado integramente en Java, diseñado para ofrecer un rendimiento de alto nivel en la gestion de medios, edicion en linea de tiempo y exportacion de video de alta fidelidad. Enfocado en la eficiencia y la arquitectura de software robusta, Rocky Open Source Video Editor integra tecnologias avanzadas de procesamiento de medios para proporcionar una experiencia de edicion fluida y profesional.

## Arquitectura del Sistema

El motor se fundamenta en un diseño modular y desacoplado que separa la logica de procesamiento de la interfaz de usuario, permitiendo una ejecucion multitarea eficiente:

### 1. Motor de Medios y Decodificacion (egine.media)
Responsable de la abstraccion y gestion de todos los activos multimedia.
- **VideoDecoder**: Implementa decodificacion acelerada por hardware (VideoToolbox para Apple Silicon M4) utilizando la libreria JavaCV. Incluye optimizaciones de lectura lineal para minimizar los tiempos de busqueda (seeking) en el almacenamiento.
- **AudioDecoder**: Maneja la extraccion y procesamiento de muestras de audio de forma independiente al video, permitiendo una sincronizacion precisa y un bajo overhead de CPU.
- **PeakManager**: Motor de calculo asincrono de picos de audio para la generacion de formas de onda en segundo plano, evitando bloqueos en el hilo de la interfaz de usuario (EDT).
- **MediaPool**: Sistema de cache y gestion centralizada de recursos para evitar la redundancia de datos en memoria.

### 2. Procesamiento y Sincronizacion (egine.engine)
El "cerebro" del editor que coordina la reproduccion.
- **AudioServer**: Actua como el reloj maestro del sistema. Utiliza un bufer de pre-lectura (read-ahead) para garantizar una reproduccion de audio sin interrupciones y dirige la posicion del cabezal de reproduccion.
- **FrameServer**: Motor de servidor de fotogramas que procesa y escala imagenes de forma asincrona. Implementa pre-fetching de fotogramas para asegurar que el visualizador siempre tenga listo el siguiente cuadro antes de su presentacion.

### 3. Interfaz de Usuario y Timeline (Parts A, B, C)
Diseño de alta densidad informativa y estetica premium.
- **VisualizerPanel (A)**: Visualizador de video capaz de manejar multiples resoluciones y modos de calidad, incluyendo un sistema de Proxy Preview para mejorar el rendimiento en entornos exigentes.
- **TimelinePanel (B)**: Linea de tiempo multicanal con soporte para arrastrar y soltar, gestion de pistas dinamica, escalado temporal preciso y sistema de fundidos (fades) con opacidad variable.
- **MasterSoundPanel (A)**: Monitorizacion de niveles de audio en tiempo real con vumetros de alta precision.
- **TopToolbar (C)**: Gestion de operaciones de archivo, configuracion y acceso al motor de renderizado.

### 4. Persistencia y Renderizado
- **ProjectManager**: Gestor del formato de archivo .rocky (V3), un sistema de serializacion eficiente que almacena metadatos del proyecto, configuracion de pistas y referencias a medios fuentes.
- **RenderEngine**: Motor de exportacion que utiliza un sistema de tuberias (piping) hacia FFmpeg. Convierte la composicion de la linea de tiempo en un archivo MP4 real utilizando el codec H.264 con perfiles de alta calidad, garantizando que el resultado final sea independiente de las optimizaciones de previsualizacion.

## Optimizaciones de Rendimiento

Para garantizar la fluidez en maquinas potentes como el Apple M4, se han implementado las siguientes tecnicas:
- **Proxy Preview**: Modo de visualizacion de baja resolucion (pixelado) que reduce drasticamente la carga computacional durante el proceso de edicion sin afectar la calidad final del renderizado.
- **Aceleracion por Hardware**: Integracion nativa con VideoToolbox en macOS y optimizaciones para arquitecturas x86_64.
- **Lectura Lineal Optimizada**: El decodificador detecta la reproduccion secuencial y evita operaciones de busqueda innecesarias, optimizando el rendimiento de los discos SSD.

## Soporte Multiplataforma

El sistema es totalmente portable e incluye todas las librerias nativas necesarias para ejecutarse en diferentes entornos sin instalaciones previas:
- **macOS**: Soporte nativo para Apple Silicon (M1/M2/M3/M4) e Intel (x86_64).
- **Windows**: Compatibilidad completa para versiones de 64 bits (x64) y 32 bits (x86).
- **Linux**: Soporte optimizado para distribuciones de 64 bits.

## Requisitos y Compilacion

### Requisitos del Sistema
- Java Development Kit (JDK) 17 o superior.
- FFmpeg (incluido en las librerias del proyecto).

### Instrucciones de Compilacion
Utilice el script proporcionado para compilar todos los modulos:
```bash
./compile.sh
```

### Instrucciones de Ejecucion
- **En Mac/Linux**:
  ```bash
  sh run.sh
  ```
- **En Windows**:
  ```batch
  run.bat
  ```

---
Este motor ha sido diseñado para ser la base de una estacion de trabajo de edicion de video moderna, bajo el nombre de Rocky Open Source Video Editor, priorizando la arquitectura limpia y el rendimiento extremo.
