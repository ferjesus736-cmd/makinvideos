import os
import subprocess
import shutil
from pathlib import Path

def generate_tts(text_id, tts_text):
    filename = f"tts_{text_id}.mp3"
    print(f"Generando TTS {text_id}...")
    # Usamos JorgeNeural, una voz en español muy clara y natural
    cmd = ["python", "-m", "edge_tts", "--voice", "es-MX-JorgeNeural", "--text", tts_text, "--write-media", filename]
    subprocess.run(cmd, check=True)
    return filename

def main():
    print("--- 🎬 PROCESADOR FINAL DE VIDEO ---")
    video_in = "ETHOS_IA_Tutorial_Subtitulado.mp4"
    if not Path(video_in).exists():
        video_in = "ETHOS_IA_OpenClaw_VPS_FINAL.mp4" # fallback si el anterior no existe
    
    video_out = "ETHOS_IA_Completo_Voces_Marcos.mp4"
    
    # Intentar copiar fuente a la carpeta actual si no está
    font_file = "arialbd.ttf"
    if not Path(font_file).exists():
        try:
            shutil.copy2("C:/Windows/Fonts/arialbd.ttf", font_file)
        except:
            pass
            
    font_str = font_file if Path(font_file).exists() else "Arial"

    marcos = [
        # (id, t_start_sec, dur_sec, drawtext, bbox color, tts_text)
        (1, 41, 5, "LO QUE NECESITAS\\: Dominio, IP, SSH", "black@0.9", "LO QUE NECESITAS: Dominio, IP y acceso SSH."),
        (2, 65, 6, "⚠️ Cambia la contrasena root PRIMERO", "red@0.9", "Atención. Cambia la contraseña root PRIMERO."),
        (3, 220, 6, "INFO\\: Los warnings amarillos de npm son normales", "darkorange@0.9", "Nota importante: Los warnings amarillos de ene pe eme son normales, ignóralos."),
        (4, 280, 6, "CONFIG\\: Escoge Gemini 2.5 Flash y la API key", "green@0.8", "Configurando OpenClaw. Escoge el modelo Gemini dos punto cinco Flash."),
        (5, 390, 6, "🤖 ¡El Bot de Telegram responde!", "green@0.8", "Y listo, ¡El bot de Telegram responde correctamente!"),
        (6, 495, 8, "SSL Activo\\: Tu IP ahora es un dominio seguro", "black@0.9", "Finalmente, tu ese ese ele está activo. Tu servidor ahora responde en un dominio seguro.")
    ]

    tts_files = []
    
    # 1. Generar Audios TTS
    print("1. Generando archivos de voz...")
    for m in marcos:
        tts_filename = generate_tts(m[0], m[5])
        tts_files.append(tts_filename)
        
    # 2. Construir el grafo de filtros FFmpeg
    print("2. Construyendo comando de ensamble final...")
    
    cmd = ["ffmpeg", "-y", "-i", video_in]
    for tf in tts_files:
        cmd.extend(["-i", tf])
        
    # Filtros de Video (Encadenados)
    v_filters = []
    prev_node = "0:v"
    
    for i, m in enumerate(marcos, 1):
        # Escapado para FFmpeg: comillas dobles y textos sin ñ complicadas 
        # (usamos "contrasena" y sacamos warning para evitar glitches visuales en unicode terminales a veces,
        # pero ffmpeg lo suele leer bien si lo ponemos directo en el filter_complex)
        
        t_s = m[1]
        t_e = m[1] + m[2]
        
        vf = (
            f"[{prev_node}]drawtext=fontfile='{font_str}':text='{m[3]}':"
            f"fontcolor=white:fontsize=50:box=1:boxcolor={m[4]}:boxborderw=20:"
            f"x=(w-text_w)/2:y=h-200:enable='between(t,{t_s},{t_e})'[v{i}]"
        )
        v_filters.append(vf)
        prev_node = f"v{i}"
        
    # Filtros de Audio (Retrasos y Mezcla)
    a_filters = []
    amix_inputs = "[0:a]"
    
    for i, m in enumerate(marcos, 1):
        delay_ms = m[1] * 1000
        a_filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        amix_inputs += f"[a{i}]"
        
    # Mezclamos el audio original + 6 voces
    # amix divide el volumen entre N. Aplicamos volume=N para restaurarlo.
    n_inputs = len(marcos) + 1
    a_filters.append(f"{amix_inputs}amix=inputs={n_inputs}:duration=first:dropout_transition=2[aout_raw];[aout_raw]volume={n_inputs}.0[aout]")
    
    # Unir todo el graph
    filter_complex = ";".join(v_filters) + ";" + ";".join(a_filters)
    
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{prev_node}]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        video_out
    ])

    print(f"3. Renderizando el video final con FFmpeg... (Tomará unos minutos)")
    # print("comando debug:", "\\\n  ".join(cmd))
    
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✅ ¡Video final compilado perfectamente!\nRuta: {os.path.abspath(video_out)}")
    else:
        print("❌ Error compilando el video.")
        print("\n".join(r.stderr.splitlines()[-20:]))

if __name__ == "__main__":
    main()
