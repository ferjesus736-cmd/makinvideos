import os
import subprocess
import time
from pathlib import Path
from google import genai
from google.genai import types

def main():
    print("--- GENERADOR DE SUBTÍTULOS CON GEMINI 1.5 FLASH ---")
    video_path = Path("ETHOS_IA_OpenClaw_VPS_FINAL.mp4")
    audio_path = Path("audio_tmp.mp3")
    srt_path = Path("subtitulos.srt")

    if not video_path.exists():
        print(f"Error: No se encontró {video_path}")
        return

    # 1. Extraer audio
    if not audio_path.exists():
        print("1. Extrayendo audio del video...")
        cmd = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-c:a", "libmp3lame", "-q:a", "4", str(audio_path)]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            print("Error extrayendo audio:", r.stderr.decode('utf-8', errors='ignore'))
            return
        print("Audio extraído exitosamente.")
    else:
        print("1. El audio ya fue extraído previamente.")

    # 2. Transcribir con Gemini
    print("2. Inicializando cliente de Gemini...")
    try:
        # El cliente tomará automáticamente GEMINI_API_KEY del entorno
        client = genai.Client()
    except Exception as e:
        print("Error inicializando el cliente Gemini. Verifica la clave API.")
        print(e)
        return

    print("Subiendo audio a Gemini...")
    audio_file = client.files.upload(file=str(audio_path))
    
    # Esperar a que se procese si es necesario
    print("Audio subido, esperando procesamiento si es necesario...")
    time.sleep(2)

    print("Generando transcripción SRT con Gemini 2.5 Flash (esto puede tomar 1 o 2 minutos)...")
    prompt = """El documento adjunto es el audio de un tutorial de tecnología (Linux, VPS, OpenClaw, Node.js).
Transcribe TODO el audio del hablante y genera los subtítulos completos.
Devuelve ÚNICA Y EXCLUSIVAMENTE un archivo en formato válido SRT.
Asegúrate de que los timestamps estén en formato HH:MM:SS,mmm y no añadas NINGÚN texto extra antes ni después del contenido SRT, ni siquiera bloques de código ```srt.
La transcripción debe estar en el mismo idioma que el hablante (español). Cuida la puntuación de las oraciones.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[audio_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        srt_content = response.text
        # Limpiar bloques markdown si todavía los devuelve
        if srt_content.startswith("```"):
            srt_content = "\n".join(srt_content.splitlines()[1:-1])

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content.strip())
        
        print(f"Subtítulos guardados exitosamente en -> {srt_path}")
        
    except Exception as e:
        print("Error durante la generación de contenido:")
        print(e)
    finally:
        # Limpiar archivo en Gemini
        try:
            client.files.delete(name=audio_file.name)
            print("Archivo de audio eliminado de la nube de Gemini.")
        except:
            pass

if __name__ == "__main__":
    main()
