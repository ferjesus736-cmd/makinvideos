"""
config.py — Configuración central de makinvideos
Edita SOLO este archivo para adaptar el pipeline a cualquier proyecto.
"""

from pathlib import Path
import shutil

# ─── DIRECTORIOS ──────────────────────────────────────────────────────────────
# Carpeta raíz donde están los videos fuente
VIDEOS_DIR = Path(r"c:\Users\madhu\Desktop\GAMES\videos")

# Carpeta temporal para segmentos cortados (se crea automáticamente)
TMP_DIR = VIDEOS_DIR / "_segmentos_tmp"

# Archivos de salida
OUTPUT_ENSAMBLADO   = VIDEOS_DIR / "ETHOS_IA_OpenClaw_VPS_FINAL.mp4"
OUTPUT_SUBTITULADO  = VIDEOS_DIR / "ETHOS_IA_Tutorial_Subtitulado.mp4"
OUTPUT_NARRADO      = VIDEOS_DIR / "ETHOS_IA_Master_Narrado.mp4"
OUTPUT_FINAL        = VIDEOS_DIR / "ETHOS_IA_Completo_Final.mp4"
AUDIO_TMP           = VIDEOS_DIR / "audio_tmp.mp3"
SRT_FILE            = VIDEOS_DIR / "subtitulos.srt"

# ─── FFMPEG ───────────────────────────────────────────────────────────────────
FFMPEG  = "ffmpeg"
FFPROBE = "ffprobe"

# Parámetros de codificación estándar (aplicados a todos los segmentos)
VIDEO_ENCODE = [
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-r", "30", "-s", "1920x1080", "-pix_fmt", "yuv420p",
    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
]
AUDIO_ENCODE = ["-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k"]

# ─── TTS ──────────────────────────────────────────────────────────────────────
TTS_VOICE      = "es-MX-JorgeNeural"   # Voz edge-tts
TTS_RATE       = "+10%"                 # Velocidad (+10% suena más dinámico)
TTS_DIR        = VIDEOS_DIR / "_tts_cache"  # Cache para no regenerar si ya existe

# ─── GEMINI ───────────────────────────────────────────────────────────────────
GEMINI_MODEL            = "gemini-2.5-flash"
GEMINI_TRANSCRIBE_TEMP  = 0.1  # Temperatura baja = transcripción más fiel

# ─── FUENTE / TIPOGRAFÍA ─────────────────────────────────────────────────────
# Busca fuente automáticamente en orden de prioridad
def _find_font():
    candidates = [
        Path("SpaceGrotesk-Bold.ttf"),          # Si la copiaste al proyecto
        Path("C:/Windows/Fonts/arialbd.ttf"),   # Windows
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),  # Linux
        Path("/System/Library/Fonts/Helvetica.ttc"),  # macOS
    ]
    for f in candidates:
        if f.exists():
            return str(f)
    return ""  # ffmpeg usará fuente interna como fallback

FONT_FILE = _find_font()

# ─── ESTILO VISUAL (calidad YouTuber pro) ────────────────────────────────────
SUBTITLE_STYLE = (
    f"FontName=Arial,FontSize=22,"
    f"PrimaryColour=&H00FFFFFF,"   # Blanco puro
    f"OutlineColour=&H00000000,"   # Contorno negro
    f"BackColour=&H80000000,"      # Fondo semitransparente
    f"Outline=2,Shadow=1,"
    f"MarginV=30,Alignment=2"      # Centrado abajo
)

# Lower thirds: (segundo_inicio, duracion, texto_principal, texto_secundario)
LOWER_THIRDS = [
    (4,   5,  "ETHOS I.A.",                  "Tutorial OpenClaw en VPS"),
    (44,  6,  "REQUISITOS",                  "Dominio · IP · SSH · API Key"),
    (59,  5,  "PASO 1",                      "Conexión SSH al servidor"),
    (84,  5,  "PASO 2",                      "Actualización y configuración"),
    (154, 5,  "PASO 3",                      "Instalación Node.js + OpenClaw"),
    (183, 6,  "PASO 4",                      "Configuración del asistente IA"),
    (270, 5,  "PASO 5",                      "Conexión con Telegram"),
    (281, 8,  "PASO 6",                      "Dominio gratuito + Nginx + SSL"),
    (395, 6,  "PASO 7",                      "Auditoría y verificación final"),
]

# Alertas visuales emergentes: (segundo, duracion, texto, color_fondo)
ALERTAS = [
    (65,  6,  "⚠  Cambia la contraseña root PRIMERO",          "red@0.85"),
    (159, 5,  "ℹ  Los warnings amarillos de npm son normales",  "darkorange@0.85"),
    (193, 6,  "✓  Gemini 2.5 Flash — recomendado",             "green@0.80"),
    (275, 6,  "🤖  ¡El Bot de Telegram responde!",              "green@0.80"),
    (495, 8,  "🔒  SSL activo — dominio seguro",                "black@0.85"),
]

# ─── GUIÓN DE NARRACIÓN (9 bloques alineados al video) ───────────────────────
GUION = [
    # 0. Intro
    "¡Qué onda, gente! Bienvenidos a Ethos I.A. Hoy vamos a subir de nivel. "
    "Muchos me han preguntado cómo tener un agente de IA que sea realmente suyo, "
    "sin pagar suscripciones mensuales ni tener límites absurdos. La respuesta es OpenClaw. "
    "Vamos a instalarlo desde cero en un VPS de Hostinger, configurar un dominio, "
    "ponerle SSL con el candadito verde, conectarlo con Gemini 2.5 Flash y dejarlo "
    "viviendo en un bot de Telegram que te responde al instante. ¡Vamos directo al grano!",

    # 1. Requisitos
    "Antes de meter las manos en la terminal, necesitamos el kit básico. "
    "Primero: un VPS con mínimo 2 gigas de RAM — con 1 giga OpenClaw se queda corto. "
    "Segundo: tu API Key de Gemini, gratis en AI Studio de Google. "
    "Tercero: un bot de Telegram vacío — créalo con BotFather y guarda el token. "
    "Y por último, tu computadora. Yo usaré PowerShell en Windows, "
    "pero en Mac o Linux la terminal funciona exactamente igual.",

    # 2. SSH
    "Vamos a entrar al servidor. Consejo de oro: antes de conectar, "
    "cambia la contraseña root en tu hPanel de Hostinger. "
    "Hostinger genera contraseñas con símbolos raros que se corrompen en PowerShell. "
    "Pon algo seguro pero simple. Luego escribe ssh root arroba y tu IP. "
    "Al escribir la contraseña el cursor no se mueve — es por seguridad de Linux. "
    "Escríbela a ciegas y dale Enter. ¡Ya estamos dentro!",

    # 3. Actualización y swap
    "Antes de instalar la IA, limpiamos la casa. "
    "Actualizamos los paquetes del sistema. Si aparece pantalla azul sobre versiones, "
    "dejen la opción por defecto y denle Enter. "
    "Ahora un truco clave: creamos una SWAP de 2 gigas. "
    "Es usar el disco como RAM de emergencia para que Node.js no derribe el servidor "
    "cuando el bot procesa tareas pesadas.",

    # 4. Node + OpenClaw
    "Instalamos el motor. OpenClaw corre sobre Node.js y usamos NVM para manejarlo. "
    "Instalamos la versión 22, la más estable. Con Node listo, instalamos OpenClaw global. "
    "Verán texto pasando rápido y warnings amarillos — ignórenlos, son normales. "
    "Para verificar, escriban openclaw guion guion version. "
    "Si responde con un número, ya tienen el poder en sus manos.",

    # 5. Configurar wizard
    "Damos cerebro al bot con el comando de onboard. "
    "Elegimos configuración rápida, proveedor Google Gemini, "
    "pegamos la API Key y seleccionamos el modelo. "
    "Yo recomiendo gemini-2.5-flash: velocidad y costo imbatibles. "
    "Luego pegamos el token de Telegram y le damos Enter a todo lo demás. "
    "El asistente configura los archivos base y deja el servicio listo.",

    # 6. Gateway y Telegram
    "Conectamos los cables. Lanzamos el gateway en el puerto 18789. "
    "En una segunda pestaña de PowerShell nos volvemos a conectar por SSH. "
    "Listamos los emparejamientos de Telegram — nos da un código numérico. "
    "Vamos al bot en Telegram, mandamos ese código, "
    "regresamos y escribimos approve seguido del código. "
    "¡Boom! El bot cobra vida y ya responde con todo el poder de Gemini.",

    # 7. DNS, Nginx, SSL
    "Lo ponemos realmente profesional. Usamos afraid.org para un dominio gratuito "
    "apuntando a la IP de nuestro VPS. Instalamos Nginx como escudo y puente. "
    "Creamos la configuración para que todo lo que llegue a nuestro dominio "
    "se pase internamente al puerto de OpenClaw. "
    "Luego instalamos Certbot para el certificado SSL gratuito — "
    "el famoso candadito verde de HTTPS. "
    "Finalmente activamos el firewall para cerrar puertos no usados.",

    # 8. Auditoría y cierre
    "Corremos una auditoría de seguridad de OpenClaw y el comando doctor "
    "para verificar que todos los servicios funcionen. "
    "El bot responde por HTTPS, la conexión es segura y el retraso es casi nulo. "
    "Ya tienen su propio agente de IA corriendo en su propio hardware. "
    "Sin límites, sin censura innecesaria, con total control de sus datos. "
    "Si les gustó, denle like, suscríbanse a Ethos I.A. "
    "y cuéntenme en los comentarios qué automatización quieren ver. "
    "La guía con todos los comandos está abajo en la descripción. ¡Nos vemos en el futuro!",
]

# Segundo del video en que empieza cada bloque de narración
TIEMPOS_TARGET = [4, 44, 59, 84, 154, 183, 270, 281, 395]

# ─── VERIFICACIONES ───────────────────────────────────────────────────────────
def check_ffmpeg():
    """Verifica que ffmpeg esté disponible en el PATH."""
    path = shutil.which(FFMPEG)
    if not path:
        raise EnvironmentError(
            "ffmpeg no encontrado en el PATH.\n"
            "  Windows: winget install Gyan.FFmpeg\n"
            "  Linux:   sudo apt install ffmpeg\n"
            "  macOS:   brew install ffmpeg"
        )
    return path

def check_dirs():
    """Crea directorios necesarios si no existen."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    TTS_DIR.mkdir(parents=True, exist_ok=True)

def check_sources(sources: dict) -> bool:
    """Verifica que todos los archivos fuente existan. Retorna True si todos OK."""
    all_ok = True
    for key, path in sources.items():
        exists = path.exists()
        size = f"{path.stat().st_size/1024/1024:.0f} MB" if exists else "---"
        icon = "✓" if exists else "✗"
        print(f"  {icon} {key:12s}  {path.name}  ({size})")
        if not exists:
            all_ok = False
    return all_ok
