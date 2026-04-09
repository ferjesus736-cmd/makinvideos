import os
import subprocess
import shutil
import json
from pathlib import Path

# GUION EN 9 BLOQUES (Alineados a los 9 capítulos del video)
GUION = [
    # 1. Intro (0:00+)
    "¡Qué onda, gente! Bienvenidos a Ethos I.A. Hoy vamos a subir de nivel. Muchos me han preguntado cómo tener un agente de IA que sea realmente suyo, sin tener que pagar suscripciones mensuales a plataformas intermediarias que te cobran por cada mensaje o te ponen límites absurdos. La respuesta es OpenClaw. En este video vamos a instalarlo desde cero en un VPS de Hostinger. Vamos a configurar un dominio, ponerle seguridad SSL con el candadito verde, conectarlo con la API de Gemini 2.5 Flash, que vuela, y dejarlo viviendo en un bot de Telegram que te va a responder al instante. Miren esto... así es como va a quedar vuestro servidor al final de este tutorial. No perdamos más tiempo, ¡vamos directo al grano!",
    # 2. Requisitos (0:40+)
    "Antes de meter las manos en la terminal, necesitamos el kit básico de herramientas. Primero: un VPS. Yo recomiendo Hostinger, pero ojo aquí: asegúrense de que tenga mínimo 2 gigas de RAM. He probado con el de 1 giga y OpenClaw se queda corto cuando la IA empieza a procesar tareas pesadas, así que no se arriesguen. Segundo: su API Key de Gemini. La consiguen en AI Studio de Google, es gratis y el modelo Flash es increíblemente rápido. Tercero: un bot de Telegram vacío. Vayan con el padre de los bots, BotFather, y creen uno nuevo para obtener el Token. Y por último, su computadora. Yo usaré PowerShell en Windows, pero si estás en Mac o Linux, la terminal te sirve exactamente igual.",
    # 3. SSH (1:00+)
    "Vamos a entrar a las entrañas del servidor. Un consejo de oro antes de conectar: entren a su hPanel de Hostinger y cambien la contraseña de root. Hostinger a veces genera unas con símbolos muy raros que, cuando las pegas en PowerShell, se corrompen y te dan error de acceso. Pongan algo seguro pero simple, tipo OpenClaw2026. Total, después la pueden volver a cambiar. Ahora abrimos PowerShell y escribimos: ssh root arroba y su dirección IP. Si les pregunta si confían en el host, escriban yes con ganas. Al poner la contraseña, van a notar que no se mueve el cursor ni aparecen asteriscos. No entren en pánico, es por pura seguridad de Linux. Escríbanla a ciegas y denle Enter. ¡Ya estamos dentro!",
    # 4. Servidor y Swap (2:00+)
    "Antes de instalar la IA, hay que limpiar la casa. Corremos el comando para actualizar los paquetes del sistema. Si les sale una pantalla azul o morada preguntando sobre versiones de archivos, simplemente dejen la opción por defecto, que suele ser keep local version, y denle Enter a todo. Ahora, un truco de optimización clave. Aunque tengamos 2 gigas de RAM, Node.js a veces tiene picos de consumo. Vamos a crear una SWAP, que es básicamente usar un pedacito del disco duro como si fuera memoria RAM de emergencia. Vamos a crear un archivo de 2 gigas, le damos los permisos correctos para que solo el sistema lo use y lo activamos. Con esto nos aseguramos de que el servidor no se caiga si el bot se pone muy exigente con las tareas.",
    # 5. Instalar Node y Openclaw (3:30+)
    "Es hora de instalar el motor. OpenClaw corre sobre Node.js, y para no tener problemas de compatibilidad, vamos a usar NVM, que es un manejador de versiones. Pegamos el comando de instalación, refrescamos la terminal con el comando source y procedemos a instalar la versión 22 de Node, que es la más estable ahora mismo. Con Node listo, instalamos OpenClaw de forma global. Verán un montón de texto pasando rápido y quizás algunos avisos amarillos. Mientras no vean nada en rojo brillante que diga ERROR, pueden ignorarlos. Para verificar que todo está bien, escriban openclaw guion guion version. Si les responde con un número de versión, ya tienen el poder en sus manos.",
    # 6. Configurar Openclaw (4:30+)
    "Ahora vamos a darle cerebro al bot con el comando de onboard. Este comando es genial porque es un asistente que te lleva de la mano. Aceptamos el aviso de seguridad y elegimos la configuración rápida para no complicarnos la vida. Cuando nos pregunte por el proveedor, elegimos Google Gemini. Aquí pegan su API Key de Google y seleccionan el modelo. Yo les recomiendo el gemini-2.5-flash porque la relación entre velocidad y costo es imbatible. Luego, el asistente les pedirá el Token de Telegram; lo pegan y a todo lo demás le dan Enter o Skip. Esto configurará los archivos base y dejará el servicio listo para ejecutarse en segundo plano como un profesional.",
    # 7. Gateway y Telegram (6:00+)
    "Vamos a conectar los cables. Lanzamos el gateway en el puerto 18789. Ahora necesitamos emparejar el bot de Telegram con nuestra instancia. Para esto, abran una segunda pestaña de PowerShell y conéctense de nuevo por SSH. Escriban el comando para listar los emparejamientos de Telegram y les va a dar un código numérico. Vayan a su aplicación de Telegram, busquen su bot y mándenle ese código. Regresen a la terminal y escriban approve seguido del código. ¡Boom! En ese momento su bot de Telegram cobra vida. Ya pueden escribirle cualquier cosa y les va a responder usando toda la potencia de Gemini desde su propio servidor.",
    # 8. DNS, Nginx, SSL (6:40+)
    "Pero no lo vamos a dejar así, vamos a ponerlo realmente profesional. Tener una IP pública está bien para pruebas, pero para que sea estable y seguro necesitamos un dominio. Yo uso afraid.org porque es gratis y muy rápido de configurar. Solo tienen que apuntar un subdominio a la IP de su VPS. Ahora instalamos Nginx, que va a funcionar como un escudo y un puente entre internet y su bot. Vamos a crear un archivo de configuración donde le decimos a Nginx: Oye, todo lo que llegue a mi-dominio.com, pásalo internamente al puerto de OpenClaw. Guardamos, activamos la configuración y lo más importante: instalamos Certbot. Con Certbot vamos a sacar un certificado SSL gratuito. Solo siguen los pasos, ponen su correo y listo: ya tienen el candadito verde de HTTPS. Finalmente, activamos el firewall para cerrar todos los puertos que no usemos y proteger el servidor de ataques externos.",
    # 9. Auditoría y Cierre (8:30+)
    "Ya casi terminamos, solo queda asegurar que todo esté sólido. Corremos una auditoría de seguridad de OpenClaw para que el sistema revise que no dejamos puertas abiertas y luego usamos el comando doctor para ver que todos los servicios estén funcionando correctamente. Miren el resultado: el bot responde por HTTPS, la conexión es segura y el retraso es casi nulo. Y eso es todo por hoy. Ya tienen su propio agente de IA corriendo en su propio hardware virtual. Sin límites, sin censura innecesaria y con total control de sus datos. Si les gustó este tutorial express, denle un buen like, suscríbanse a Ethos I.A. y cuéntenme en los comentarios qué otra automatización quieren ver. La guía con todos los comandos detallados está aquí abajo en la descripción. ¡Nos vemos en el futuro!"
]

# Tiempos base deseados de las escenas (desplazados por hook, b-rolls y duraciones reales)
TIEMPOS_TARGET = [4, 44, 59, 84, 154, 183, 270, 281, 395]

def get_audio_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return float(r.stdout.strip())

def generate_tts(idx, text):
    filename = f"narracion_{idx+1}.mp3"
    print(f"Generando TTS {idx+1}/{len(GUION)}...")
    # Aumentamos sutilmente la velocidad para que suene dinámico y encaje mejor (+10%)
    cmd = ["python", "-m", "edge_tts", "--voice", "es-MX-JorgeNeural", "--rate", "+10%", "--text", text, "--write-media", filename]
    subprocess.run(cmd, check=True)
    return filename

def main():
    print("--- GENERADOR DE NARRACION EN OFF MASTER ---")
    video_in = "ETHOS_IA_OpenClaw_VPS_FINAL.mp4" # Usamos el master limpio original
    if not Path(video_in).exists():
        print(f"No se encuentra el master {video_in}")
        return
        
    video_out = "ETHOS_IA_Master_Narrado.mp4"
    
    # 1. Copiar fuente local
    font_file = "arialbd.ttf"
    if not Path(font_file).exists():
        try: shutil.copy2("C:/Windows/Fonts/arialbd.ttf", font_file)
        except: pass

    # 2. Generar todos los audios y calcular solapamientos dinámicos
    tts_tracks = []
    current_end_time = 0.0
    print("1. Creando canales de voz e interpolando tiempos...")
    
    for i in range(len(GUION)):
        f_name = generate_tts(i, GUION[i])
        dur = get_audio_duration(f_name)
        
        # El audio no puede empezar antes de que termine el audio anterior (con un respiro de 0.8s)
        # Empieza en el mayor valor entre: el target de la escena, o el final del audio previo.
        start_time = max(float(TIEMPOS_TARGET[i]), current_end_time + 0.8)
        
        tts_tracks.append({"file": f_name, "start": start_time})
        current_end_time = start_time + dur
        
        m_s = int(start_time // 60)
        s_s = int(start_time % 60)
        dur_s = int(dur)
        print(f"     -> Pista {i+1}: Inicia {m_s}:{s_s:02d} | Dura {dur_s}s")

    # 3. Marcos Visuales (Desplazados para coincidir con nuevo montaje rápido)
    marcos = [
        (45, 5, "LO QUE NECESITAS\\: Dominio, IP, SSH", "black@0.9"),
        (60, 6, "⚠️ Cambia la contrasena root PRIMERO", "red@0.9"),
        (159, 6, "INFO\\: Los warnings amarillos de npm son normales", "darkorange@0.9"),
        (193, 6, "CONFIG\\: Escoge Gemini 2.5 Flash y la API key", "green@0.8"),
        (275, 6, "🤖 ¡El Bot de Telegram responde!", "green@0.8"),
        (371, 8, "SSL Activo\\: Tu IP ahora es un dominio seguro", "black@0.9")
    ]
        
    print("2. Construyendo MEGA-Renderizado FFmpeg...")
    cmd = ["ffmpeg", "-y", "-i", video_in]
    for tr in tts_tracks:
        cmd.extend(["-i", tr["file"]])
        
    v_filters = []
    prev_node = "0:v"
    font_str = font_file if Path(font_file).exists() else "Arial"
    
    # Textos dibujados
    for i, m in enumerate(marcos, 1):
        t_s = m[0]
        t_e = m[0] + m[1]
        vf = (
            f"[{prev_node}]drawtext=fontfile='{font_str}':text='{m[2]}':"
            f"fontcolor=white:fontsize=50:box=1:boxcolor={m[3]}:boxborderw=20:"
            f"x=(w-text_w)/2:y=h-200:enable='between(t,{t_s},{t_e})'[v{i}]"
        )
        v_filters.append(vf)
        prev_node = f"v{i}"
        
    # Mezcla de los nuevos 9 audios TTS
    a_filters = []
    amix_inputs = ""
    # NO incluimos [0:a] para que la pista original de voz en el video quede en SILENCIO ABSOLUTO.
    for i, tr in enumerate(tts_tracks, 1):
        delay_ms = int(tr["start"] * 1000)
        a_filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        amix_inputs += f"[a{i}]"
        
    n_inputs = len(tts_tracks)
    # Amix mezcla los 9 inputs TTS. Normalize=0 previene reducciones fuertes de volumen si la version FFmpeg lo soporta,
    # pero como fallback estándar multiplicaremos por N.
    a_filters.append(f"{amix_inputs}amix=inputs={n_inputs}:duration=longest:dropout_transition=2[aout_raw];[aout_raw]volume={n_inputs}.0[aout]")
    
    filter_complex = ";".join(v_filters) + ";" + ";".join(a_filters)
    
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{prev_node}]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "24",
        "-c:a", "aac", "-b:a", "192k",
        video_out
    ])

    print(f"3. Renderizando el video maestro final sin la voz original...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"[OK] Video final compilado perfectamente!\nRuta: {os.path.abspath(video_out)}")
    else:
        print("[X] Error compilando el master final.")
        print("\n".join(r.stderr.splitlines()[-25:]))

if __name__ == "__main__":
    main()
