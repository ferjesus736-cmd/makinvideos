"""
ensamblar_documental.py — Modulo 3: Ensamble cinematografico
Lee clips_mapeados.json y produce un video documental con:
  - Efecto Ken Burns (zoom + paneo lento) por clip
  - Crossfade suave entre clips
  - Audio TTS sincronizado por bloque
  - Musica de fondo con ducking automatico bajo la voz
  - Lower thirds cinematograficos

Requiere:
  ffmpeg >= 5.0 en PATH

Uso:
  python ensamblar_documental.py
  python ensamblar_documental.py --sin-musica
  python ensamblar_documental.py --bloque 0 3   # solo bloques 0 al 3
  python ensamblar_documental.py --preview       # muestra filtros sin renderizar
"""

import subprocess
import json
import argparse
import random
from pathlib import Path
from config import (
    FFMPEG, FFPROBE, OUTPUT_FINAL,
    TTS_DIR, TTS_VOICE, TTS_RATE,
    LOWER_THIRDS, FONT_FILE,
    check_ffmpeg,
)

MAPEADO_FILE    = Path("clips_mapeados.json")
MUSICA_FILE     = Path("musica_fondo.mp3")   # pon aqui tu audio libre de derechos
OUTPUT_DOC      = Path("ETHOS_IA_Documental.mp4")
TMP_DIR         = Path("_doc_tmp")

# Parametros cinematograficos
CROSSFADE_DUR   = 1.0    # segundos de fundido entre clips
RESOLUTION      = "1920x1080"
FPS             = 30
CRF             = 20     # calidad video (menor = mejor, mas lento)

# Ken Burns: variantes de movimiento para que no todos sean iguales
KB_PRESETS = [
    # (zoom_inicio, zoom_fin, x_inicio, y_inicio, x_fin, y_fin)
    # zoom in centrado
    (1.0, 1.08, 0.5, 0.5, 0.5, 0.5),
    # zoom in desplazando derecha
    (1.0, 1.10, 0.5, 0.5, 0.55, 0.5),
    # zoom in desplazando izquierda
    (1.0, 1.10, 0.55, 0.5, 0.5, 0.5),
    # zoom out centrado
    (1.10, 1.0, 0.5, 0.5, 0.5, 0.5),
    # paneo horizontal suave
    (1.05, 1.05, 0.45, 0.5, 0.55, 0.5),
    # paneo diagonal
    (1.0, 1.08, 0.48, 0.48, 0.52, 0.52),
]

# Velocidad del Ken Burns segun ritmo del bloque
KB_SPEED = {
    "corte_rapido": 0.5,   # movimiento mas rapido
    "plano_largo":  1.0,   # movimiento lento y solemne
    "mixto":        0.75,
}

# Opacidad del fade de entrada (negro -> imagen) segun emocion
FADE_DUR = {
    "epico":     0.8,
    "tenso":     0.4,
    "esperanza": 1.2,
    "tecnico":   0.5,
    "intimo":    1.0,
    "accion":    0.3,
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_duration(path):
    r = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def get_video_size(path):
    """Retorna (width, height) del video."""
    r = subprocess.run(
        [FFPROBE, "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        parts = r.stdout.strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 1920, 1080


def run_ffmpeg(cmd, label=""):
    tag = f"[{label}] " if label else ""
    print(f"  {tag}Ejecutando FFmpeg...", end="", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = [l for l in r.stderr.splitlines() if l.strip()][-12:]
        print(f"\n  ERROR {tag}:")
        for line in err:
            print(f"    {line}")
        return False
    print(" OK")
    return True


def normalizar(texto):
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()


# ─── KEN BURNS FILTER ─────────────────────────────────────────────────────────

def ken_burns_filter(duracion, ritmo, emocion, seed=0):
    """
    Construye el filtro FFmpeg para efecto Ken Burns sobre un clip.
    Retorna string del filtro zoompan listo para usar en -vf.

    El zoompan de FFmpeg trabia en coordenadas de pixel del frame original.
    Formula: z=zoom, x/y = posicion del crop dentro del frame escalado.
    """
    random.seed(seed)
    preset = KB_PRESETS[seed % len(KB_PRESETS)]
    zi, zf, xi, yi, xf, yf = preset

    speed = KB_SPEED.get(normalizar(ritmo), 0.75)
    fade  = FADE_DUR.get(normalizar(emocion), 0.6)

    # Total frames del clip
    total_frames = int(duracion * FPS)
    w, h = 1920, 1080

    # Zoom lineal de zi a zf durante toda la duracion
    # x/y en coordenadas del frame escalado (iw*z = ancho del frame con zoom)
    # Centramos el crop usando las posiciones relativas del preset
    zoom_expr  = f"'zoom+({zf-zi:.4f}/{total_frames})'"
    x_expr     = f"'iw*{xi:.3f}-iw/zoom*{xi:.3f}'"
    y_expr     = f"'ih*{yi:.3f}-ih/zoom*{yi:.3f}'"

    # Fade in desde negro
    fade_frames = int(fade * FPS)
    fade_filter = f"fade=t=in:st=0:d={fade:.1f}"

    # Escala final al output
    scale_filter = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"

    # Componer filtro completo para este clip
    kb = (
        f"{scale_filter},"
        f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}"
        f":d={total_frames}:s={w}x{h}:fps={FPS},"
        f"{fade_filter}"
    )

    return kb


# ─── PREPARAR CLIPS ───────────────────────────────────────────────────────────

def preparar_clip(mapa, idx, out_path, preview=False):
    """
    Toma un clip raw y lo prepara con Ken Burns + duracion exacta.
    Si el clip es mas corto que el audio, aplica loop.
    Si no hay clip, genera un placeholder negro con texto.
    """
    clip_path       = mapa.get("clip_path")
    dur_necesaria   = mapa["duracion_necesaria"]
    ritmo           = mapa.get("ritmo", "mixto")
    emocion         = mapa.get("emocion", "tecnico")
    descripcion     = mapa.get("descripcion", "")

    if out_path.exists():
        print(f"  [CACHE] {out_path.name}")
        return True

    # ── PLACEHOLDER si no hay clip ──
    if not clip_path or not Path(clip_path).exists():
        print(f"  [PLACEHOLDER] Bloque {idx:02d} sin clip -> generando fondo negro")
        font = f"fontfile='{FONT_FILE}':" if FONT_FILE else ""
        desc_esc = descripcion.replace("'", "\\'").replace(":", "\\:")[:60]
        cmd = [
            FFMPEG, "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s=1920x1080:r={FPS}:d={dur_necesaria:.2f}",
            "-vf", (
                f"drawtext={font}text='[Sin clip disponible]':"
                f"fontcolor=gray:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2,"
                f"drawtext={font}text='{desc_esc}':"
                f"fontcolor=darkgray:fontsize=22:x=(w-text_w)/2:y=h/2+60,"
                f"fade=t=in:st=0:d=0.5"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
            "-pix_fmt", "yuv420p", "-an",
            str(out_path)
        ]
        return run_ffmpeg(cmd, f"placeholder_{idx:02d}")

    # ── CLIP REAL ──
    clip_dur = get_duration(Path(clip_path))
    print(f"  [KB] Bloque {idx:02d} | clip={clip_dur:.1f}s | necesita={dur_necesaria:.1f}s | {ritmo}")

    # Filtro Ken Burns
    kb_filter = ken_burns_filter(dur_necesaria, ritmo, emocion, seed=idx)

    # Input con loop si el clip es mas corto que lo necesario
    if clip_dur < dur_necesaria:
        loop_count = int(dur_necesaria / clip_dur) + 2
        input_args = ["-stream_loop", str(loop_count), "-i", str(clip_path)]
    else:
        input_args = ["-i", str(clip_path)]

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-t", f"{dur_necesaria:.3f}",
        "-vf", kb_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-an",
        str(out_path)
    ]

    if preview:
        print(f"    Ken Burns filter: {kb_filter[:120]}...")
        return True

    return run_ffmpeg(cmd, f"kb_{idx:02d}")


# ─── CROSSFADE ────────────────────────────────────────────────────────────────

def aplicar_crossfade(clips_preparados, output_path, preview=False):
    """
    Concatena clips con xfade (crossfade cinematografico) entre ellos.
    Usa el filtro xfade de FFmpeg para fundidos suaves.
    """
    n = len(clips_preparados)
    if n == 0:
        print("  [!] Sin clips para concatenar")
        return False

    if n == 1:
        import shutil
        shutil.copy2(str(clips_preparados[0]), str(output_path))
        return True

    print(f"\n  [XFADE] Concatenando {n} clips con crossfade de {CROSSFADE_DUR}s...")

    # Calcular offsets acumulados para xfade
    duraciones = [get_duration(p) for p in clips_preparados]

    # Construir cadena de xfade encadenada
    # xfade necesita: offset = suma de duraciones previas - crossfade_dur * numero_transicion
    cmd = [FFMPEG, "-y"]
    for p in clips_preparados:
        cmd.extend(["-i", str(p)])

    # Construir filter_complex con xfade encadenado
    filter_parts = []
    prev = "[0:v]"
    acum = 0.0

    for i in range(1, n):
        acum += duraciones[i-1] - CROSSFADE_DUR
        label_out = f"[xf{i}]" if i < n-1 else "[vout]"

        # Tipo de transicion segun emocion del clip anterior
        transition = "fade"  # siempre fade suave, es el mas cinematografico

        filter_parts.append(
            f"{prev}[{i}:v]xfade=transition={transition}"
            f":duration={CROSSFADE_DUR}:offset={acum:.3f}{label_out}"
        )
        prev = f"[xf{i}]"

    filter_complex = ";".join(filter_parts)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        str(output_path)
    ])

    if preview:
        print(f"    Filter: {filter_complex[:200]}...")
        return True

    return run_ffmpeg(cmd, "xfade")


# ─── AUDIO: TTS + MUSICA CON DUCKING ─────────────────────────────────────────

def mezclar_audio(mapas, video_sin_audio, musica_path, output_final, preview=False):
    """
    Mezcla las pistas TTS de cada bloque + musica de fondo con ducking.
    El ducking baja la musica automaticamente cuando habla la voz.

    Tecnica: sidechaincompress — la voz controla el compresor de la musica.
    """
    print(f"\n  [AUDIO] Construyendo mezcla de audio...")

    # Inputs: video base + archivos TTS + musica (si existe)
    cmd = [FFMPEG, "-y", "-i", str(video_sin_audio)]

    tts_inputs = []
    for mapa in mapas:
        idx = mapa["bloque"]
        tts_path = TTS_DIR / f"tts_{idx:02d}.mp3"
        if tts_path.exists():
            cmd.extend(["-i", str(tts_path)])
            tts_inputs.append((len(tts_inputs) + 1, mapa["tiempo_inicio"]))

    tiene_musica = musica_path and Path(musica_path).exists()
    if tiene_musica:
        cmd.extend(["-i", str(musica_path)])
        musica_input_idx = len(tts_inputs) + 1
        print(f"  [MUSICA] Usando: {musica_path}")
    else:
        print(f"  [MUSICA] No encontrada ({MUSICA_FILE}) -> solo voz")

    # ── Filtros de audio ──
    a_filters = []
    amix_inputs = ""

    # Delay + normalizar cada pista TTS
    for i, (input_idx, tiempo_inicio) in enumerate(tts_inputs):
        delay_ms = int(tiempo_inicio * 1000)
        a_filters.append(
            f"[{input_idx}:a]"
            f"adelay={delay_ms}|{delay_ms},"
            f"volume=1.8"           # voz mas fuerte
            f"[tts{i}]"
        )
        amix_inputs += f"[tts{i}]"

    n_tts = len(tts_inputs)

    if tiene_musica and n_tts > 0:
        # Mezclar todas las pistas TTS en una sola (sidechain source)
        a_filters.append(
            f"{amix_inputs}amix=inputs={n_tts}:normalize=0[voz_total]"
        )

        # Musica con loop para cubrir todo el video
        a_filters.append(
            f"[{musica_input_idx}:a]"
            f"aloop=loop=-1:size=2e+09,"
            f"volume=0.35"          # musica base suave
            f"[musica_raw]"
        )

        # Ducking: sidechaincompress
        # La voz ([voz_total]) controla el compresor de la musica ([musica_raw])
        # Cuando hay voz, la musica baja al 20% de su volumen
        a_filters.append(
            "[musica_raw][voz_total]sidechaincompress="
            "threshold=0.02:"       # sensibilidad: detecta voz suave
            "ratio=6:"              # compresion 6:1 cuando hay voz
            "attack=100:"           # sube rapido (ms)
            "release=1500:"         # baja lento al terminar la voz (ms)
            "makeup=1.0"
            "[musica_ducked]"
        )

        # Mezcla final: musica ducked + voz
        a_filters.append(
            "[musica_ducked][voz_total]amix=inputs=2:normalize=0[aout]"
        )

    elif n_tts > 0:
        # Solo voz, sin musica
        a_filters.append(
            f"{amix_inputs}amix=inputs={n_tts}:normalize=0[aout]"
        )
    else:
        print("  [!] Sin pistas de audio disponibles")
        return False

    filter_complex = ";".join(a_filters)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_final)
    ])

    if preview:
        print(f"    Audio filter: {filter_complex[:300]}...")
        return True

    return run_ffmpeg(cmd, "audio_mix")


# ─── LOWER THIRDS CINEMATOGRAFICOS ───────────────────────────────────────────

def agregar_lower_thirds(video_in, video_out, mapas, preview=False):
    """
    Agrega lower thirds cinematograficos al video.
    Aparecen al inicio de cada bloque con fade in/out suave.
    Estilo: barra lateral izquierda + texto en dos lineas.
    """
    if not LOWER_THIRDS:
        import shutil
        shutil.copy2(str(video_in), str(video_out))
        return True

    print(f"\n  [LT] Aplicando {len(LOWER_THIRDS)} lower thirds...")

    font = f"fontfile='{FONT_FILE}':" if FONT_FILE else ""
    filters = []
    nodo = "0:v"

    for i, (t_s, dur, titulo, subtitulo) in enumerate(LOWER_THIRDS, 1):
        t_e = t_s + dur
        fade_d = 0.3
        new_node = f"lt{i}"

        titulo_esc    = titulo.replace("'", "\\'").replace(":", "\\:")
        subtitulo_esc = subtitulo.replace("'", "\\'").replace(":", "\\:")

        # Barra de acento (linea vertical color)
        f_accent = (
            f"[{nodo}]drawbox="
            f"x=60:y=ih-105:w=4:h=55:"
            f"color=0x00BFFF@0.9:t=fill:"
            f"enable='between(t,{t_s},{t_e})'[lt_acc{i}]"
        )
        filters.append(f_accent)

        # Fondo semitransparente
        f_bg = (
            f"[lt_acc{i}]drawbox="
            f"x=70:y=ih-108:w=480:h=62:"
            f"color=black@0.55:t=fill:"
            f"enable='between(t,{t_s},{t_e})'[lt_bg{i}]"
        )
        filters.append(f_bg)

        # Titulo (blanco)
        f_titulo = (
            f"[lt_bg{i}]drawtext={font}"
            f"text='{titulo_esc}':"
            f"fontcolor=white:fontsize=26:x=82:y=h-100:"
            f"enable='between(t,{t_s},{t_e})'[lt_t{i}]"
        )
        filters.append(f_titulo)

        # Subtitulo (gris claro)
        f_sub = (
            f"[lt_t{i}]drawtext={font}"
            f"text='{subtitulo_esc}':"
            f"fontcolor=0xCCCCCC:fontsize=17:x=82:y=h-70:"
            f"enable='between(t,{t_s},{t_e})'[{new_node}]"
        )
        filters.append(f_sub)
        nodo = new_node

    filter_complex = ";".join(filters)

    cmd = [
        FFMPEG, "-y",
        "-i", str(video_in),
        "-vf", filter_complex.replace(f"[0:v]", "").lstrip(";"),
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-c:a", "copy",
        str(video_out)
    ]

    # Forma mas robusta: usar filter_complex en vez de -vf cuando hay muchos filtros
    cmd = [
        FFMPEG, "-y",
        "-i", str(video_in),
        "-filter_complex", f"[0:v]{';['.join(f.split('[', 1)[1] if f.startswith('[') else f for f in filters)}",
        "-map", f"[{nodo}]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-c:a", "copy",
        str(video_out)
    ]

    # Rebuild correcto
    cmd = [FFMPEG, "-y", "-i", str(video_in)]
    vf_chain = ";".join(filters)
    cmd.extend([
        "-filter_complex", vf_chain,
        "-map", f"[{nodo}]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-c:a", "copy",
        str(video_out)
    ])

    if preview:
        print(f"    Lower thirds filter preview ({len(filters)} filtros)")
        return True

    return run_ffmpeg(cmd, "lower_thirds")


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def run(bloques_rango=None, sin_musica=False, preview=False):
    print(f"\n{'='*55}")
    print(f"  ENSAMBLE CINEMATOGRAFICO DOCUMENTAL")
    print(f"  Ken Burns + Crossfade + Ducking")
    print(f"{'='*55}\n")

    check_ffmpeg()
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Cargar mapeado
    if not MAPEADO_FILE.exists():
        raise FileNotFoundError(
            f"No se encontro {MAPEADO_FILE}.\n"
            "Ejecuta primero: python buscar_imagenes.py"
        )
    with open(MAPEADO_FILE, "r", encoding="utf-8") as f:
        mapas = json.load(f)

    # Filtrar bloques si se especifico rango
    if bloques_rango:
        mapas = [m for m in mapas if m["bloque"] in range(bloques_rango[0], bloques_rango[1]+1)]

    print(f"  Procesando {len(mapas)} bloques\n")

    # ── FASE 1: Ken Burns en cada clip ──
    print(f"[FASE 1] Aplicando Ken Burns a {len(mapas)} clips...")
    clips_kb = []
    for mapa in mapas:
        idx      = mapa["bloque"]
        out_clip = TMP_DIR / f"kb_{idx:02d}.mp4"
        ok = preparar_clip(mapa, idx, out_clip, preview)
        if ok:
            clips_kb.append(out_clip)
        else:
            print(f"  [!] Bloque {idx:02d} fallo, saltando")

    if not clips_kb:
        raise RuntimeError("Ningun clip preparado exitosamente")

    # ── FASE 2: Crossfade entre clips ──
    print(f"\n[FASE 2] Crossfade entre {len(clips_kb)} clips...")
    video_xfade = TMP_DIR / "video_xfade.mp4"
    ok = aplicar_crossfade(clips_kb, video_xfade, preview)
    if not ok and not preview:
        raise RuntimeError("Fallo el crossfade")

    # ── FASE 3: Mezcla de audio (TTS + musica con ducking) ──
    print(f"\n[FASE 3] Mezcla de audio con ducking...")
    video_con_audio = TMP_DIR / "video_con_audio.mp4"
    musica = None if sin_musica else MUSICA_FILE
    ok = mezclar_audio(mapas, video_xfade, musica, video_con_audio, preview)
    if not ok and not preview:
        raise RuntimeError("Fallo la mezcla de audio")

    # ── FASE 4: Lower thirds ──
    print(f"\n[FASE 4] Lower thirds cinematograficos...")
    video_final = OUTPUT_DOC
    ok = agregar_lower_thirds(video_con_audio, video_final, mapas, preview)
    if not ok and not preview:
        raise RuntimeError("Fallo la adicion de lower thirds")

    # ── RESULTADO ──
    if not preview and video_final.exists():
        size_mb = video_final.stat().st_size / 1024 / 1024
        dur     = get_duration(video_final)
        m, s    = int(dur // 60), int(dur % 60)
        print(f"\n{'='*55}")
        print(f"  VIDEO DOCUMENTAL LISTO")
        print(f"  {video_final.absolute()}")
        print(f"  {size_mb:.0f} MB | {m}:{s:02d} min")
        print(f"{'='*55}\n")
    elif preview:
        print(f"\n  [PREVIEW] Pipeline completo. Sin archivos generados.")
        print(f"  Quita --preview para renderizar.\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ensambla el video documental con Ken Burns, crossfade y audio ducking."
    )
    parser.add_argument(
        "--bloque", nargs=2, type=int, metavar=("DESDE", "HASTA"),
        help="Procesa solo bloques en rango, ej: --bloque 0 4"
    )
    parser.add_argument(
        "--sin-musica", action="store_true",
        help="Genera el video sin musica de fondo"
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Muestra los filtros sin renderizar"
    )
    args = parser.parse_args()

    run(
        bloques_rango=args.bloque,
        sin_musica=args.sin_musica,
        preview=args.preview,
    )


if __name__ == "__main__":
    main()
