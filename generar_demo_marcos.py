import subprocess
from pathlib import Path

def main():
    print("--- GENERANDO DEMO DE MARCOS ---")
    
    video_in = Path("ETHOS_IA_OpenClaw_VPS_FINAL.mp4")
    video_out = Path("demo_marcos.mp4")
    
    if not video_in.exists():
        print("El video original no se encuentra.")
        return

    # Extraemos 6 segundos (del 41 al 47)
    # y aplicamos el texto que debe aparecer entre el segundo 1 y el 5 de ese extracto.
    import shutil
    try:
        shutil.copy2("C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf")
    except:
        pass  # Si no puede, que intente usar el fallback
    
    font_path = "arialbd.ttf"
    text = "LO QUE NECESITAS\\: Dominio, IP, SSH"
    
    # Parámetros del drawtext
    # boxcolor=black@0.8 (fondo negro opacidad 80%)
    # y=h-150 (cerca de la parte inferior)
    vf_filter = (
        f"drawtext=fontfile='{font_path}':text='{text}':"
        f"fontcolor=white:fontsize=50:"
        f"box=1:boxcolor=black@0.8:boxborderw=20:"
        f"x=(w-text_w)/2:y=h-200:"
        f"enable='between(t,1,5)'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", "40",
        "-i", str(video_in),
        "-t", "7",
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy",
        str(video_out)
    ]
    
    print("Ejecutando FFmpeg en el fragmento...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"Demo generado en: {video_out.absolute()}")
    else:
        print("Error en FFmpeg:")
        print(" ".join(r.stderr.splitlines()[-15:]))

if __name__ == "__main__":
    main()
