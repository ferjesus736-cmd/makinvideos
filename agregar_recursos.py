import subprocess
from pathlib import Path

def main():
    print("--- APLICANDO RECURSOS Y SUBTÍTULOS ---")
    
    video_in = Path("ETHOS_IA_OpenClaw_VPS_FINAL.mp4")
    video_out = Path("ETHOS_IA_Tutorial_Subtitulado.mp4")
    srt_file = Path("subtitulos.srt")
    
    if not video_in.exists() or not srt_file.exists():
        print("Faltan archivos base (el video final o los subtítulos).")
        return

    # Usamos FFmpeg para aplicar el filtro de subtítulos
    # PrimaryColour en BGR (AABBGGRR o &HBBGGRR). Amarillo es &H00FFFF. Verde es &H00FF00
    style = "FontName=Space Grotesk,FontSize=22,PrimaryColour=&H0000FFFF,Outline=1,Shadow=1,MarginV=20"
    
    # IMPORTANTE: ffmpeg en Windows a veces necesita escapar los : de la ruta si se pasa absoluta
    # pero como es relativa, subtitles=subtitulos.srt debería funcionar
    # Escapamos el nombre del srt por si acaso
    srt_esc = str(srt_file.name).replace("\\", "/")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_in),
        "-vf", f"subtitles={srt_esc}:force_style='{style}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(video_out)
    ]
    
    print(f"Quemando subtítulos en el video... Esto tomará unos minutos.")
    print("Comando:", " ".join(cmd))
    
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"¡Éxito! Video guardado en: {video_out.absolute()}")
    else:
        print("Hubo un error con ffmpeg:")
        # Mostrar el final del error
        print("\n".join(r.stderr.splitlines()[-10:]))

if __name__ == "__main__":
    main()
