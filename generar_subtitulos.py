"""
generar_subtitulos.py — Fase 2: transcripción con Gemini y quemado de subtítulos
Produce: OUTPUT_SUBTITULADO (video con subtítulos quemados en estilo pro)
"""

import subprocess
import time
from pathlib import Path
from config import (
    FFMPEG, OUTPUT_ENSAMBLADO, OUTPUT_SUBTITULADO,
    AUDIO_TMP, SRT_FILE, SUBTITLE_STYLE,
    GEMINI_MODEL, GEMINI_TRANSCRIBE_TEMP, check_ffmpeg
)


def extraer_audio(video: Path, audio: Path) -> bool:
    """Extrae el audio del video como MP3."""
    if audio.exists():
        print(f"  [EXISTE] Audio ya existe: {audio.name}")
        return True

    print("  [AUDIO] Extrayendo audio...", end="", flush=True)
    cmd = [
        FFMPEG, "-y", "-i", str(video),
        "-vn", "-c:a", "libmp3lame", "-q:a", "4",
        str(audio)
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"\n  [ERROR] {r.stderr.decode('utf-8', errors='ignore')[-200:]}")
        return False
    print("  [OK]")
    return True


def transcribir_con_gemini(audio: Path, srt_out: Path) -> bool:
    """Sube el audio a Gemini y genera el archivo SRT."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("Instala: pip install google-genai")

    print("  [IA] Inicializando Gemini...")
    client = genai.Client()  # Lee GEMINI_API_KEY del entorno automáticamente

    print(f"  [UPLOAD] Subiendo audio ({audio.stat().st_size / 1024 / 1024:.1f} MB)...", end="", flush=True)
    audio_file = client.files.upload(file=str(audio))
    print("  [OK]")

    time.sleep(2)  # Espera breve de procesamiento

    prompt = (
        "El documento adjunto es el audio de un tutorial técnico en español "
        "(Linux, VPS, OpenClaw, Node.js, Nginx, SSL).\n"
        "Transcribe COMPLETAMENTE todo lo que dice el hablante.\n"
        "Devuelve ÚNICAMENTE el contenido en formato SRT válido.\n"
        "Formato de timestamps: HH:MM:SS,mmm\n"
        "NO incluyas bloques de código ```srt, ni texto adicional antes o después.\n"
        "Cuida la puntuación y las palabras técnicas (npm, certbot, ffmpeg, etc.)."
    )

    print(f"  [DESC] Transcribiendo con {GEMINI_MODEL}... (puede tomar 1-2 min)", end="", flush=True)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[audio_file, prompt],
            config=types.GenerateContentConfig(temperature=GEMINI_TRANSCRIBE_TEMP)
        )
        srt_content = response.text

        # Limpiar bloques markdown si Gemini los incluye a pesar del prompt
        if srt_content.strip().startswith("```"):
            lines = srt_content.strip().splitlines()
            srt_content = "\n".join(lines[1:-1])

        srt_out.write_text(srt_content.strip(), encoding="utf-8")
        print(f"  [OK] ({len(srt_content.splitlines())} líneas)")
        return True

    except Exception as e:
        print(f"\n  [ERROR] Gemini: {e}")
        return False
    finally:
        try:
            client.files.delete(name=audio_file.name)
            print("  [CLEAN] Archivo de audio eliminado de Gemini Cloud.")
        except Exception:
            pass


def quemar_subtitulos(video_in: Path, srt: Path, video_out: Path) -> bool:
    """Quema los subtítulos en el video con estilo profesional."""
    # Usar ruta relativa para evitar problemas de escape en Windows con colons/slashes
    srt_relative = srt.name  # Suponiendo que el script se ejecuta en el mismo directorio

    cmd = [
        FFMPEG, "-y",
        "-i", str(video_in),
        "-vf", f"subtitles='{srt_relative}':force_style='{SUBTITLE_STYLE}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "copy",
        str(video_out)
    ]
    print("  [BURN] Quemando subtítulos (esto tarda unos minutos)...", end="", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = r.stderr.splitlines()[-10:]
        print(f"\n  [ERROR] ffmpeg:\n" + "\n".join(f"    {l}" for l in err))
        return False
    size = video_out.stat().st_size / 1024 / 1024
    print(f"  [OK] ({size:.0f} MB)")
    return True


def run():
    print("\n--- FASE 2: SUBTITULOS ------------------------------------")
    check_ffmpeg()

    if not OUTPUT_ENSAMBLADO.exists():
        raise FileNotFoundError(f"Video base no encontrado: {OUTPUT_ENSAMBLADO}")

    # Paso 1: extraer audio
    if not extraer_audio(OUTPUT_ENSAMBLADO, AUDIO_TMP):
        raise RuntimeError("Falló la extracción de audio.")

    # Paso 2: transcribir (reutiliza SRT si ya existe)
    if SRT_FILE.exists():
        print(f"  [EXISTE] SRT ya existe: {SRT_FILE.name} — omitiendo transcripción.")
        print("     (Borra el archivo para regenerar.)")
    else:
        if not transcribir_con_gemini(AUDIO_TMP, SRT_FILE):
            raise RuntimeError("Falló la transcripción con Gemini.")

    # Paso 3: quemar subtítulos
    if not quemar_subtitulos(OUTPUT_ENSAMBLADO, SRT_FILE, OUTPUT_SUBTITULADO):
        raise RuntimeError("Falló el quemado de subtítulos.")

    print(f"\n  [FIN] Video subtitulado: {OUTPUT_SUBTITULADO}")
    return OUTPUT_SUBTITULADO


if __name__ == "__main__":
    run()
