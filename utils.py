"""
utils.py — Funciones compartidas del pipeline makinvideos
No ejecutar directamente. Importar desde los otros módulos.
"""

import subprocess
import time
from pathlib import Path
from config import FFMPEG, FFPROBE, TTS_VOICE, TTS_RATE, TTS_DIR


# ─── FFMPEG ───────────────────────────────────────────────────────────────────

def get_duration(path: Path) -> float:
    """Retorna la duración real del video/audio en segundos."""
    r = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def run_ffmpeg(cmd: list, label: str = "") -> bool:
    """
    Ejecuta un comando ffmpeg. Muestra las últimas líneas de error si falla.
    Retorna True si exitoso.
    """
    tag = f"[{label}] " if label else ""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = [l for l in r.stderr.splitlines() if l.strip()][-8:]
        print(f"  ✗ {tag}Error ffmpeg:")
        for line in err:
            print(f"    {line}")
        return False
    return True


def cut_segment(seg_id: str, src_path: Path, start: float, duration: float,
                out_path: Path, video_encode: list, audio_encode: list) -> bool:
    """
    Corta un segmento del video fuente con re-encode a formato uniforme.
    Incluye validación de duración para no pedir más de lo que existe.
    """
    if not src_path.exists():
        print(f"  ✗ [{seg_id}] Fuente no encontrada: {src_path.name}")
        return False

    total = get_duration(src_path)
    if start >= total:
        print(f"  ✗ [{seg_id}] Inicio {start}s > duración del video {total:.0f}s")
        return False

    actual_dur = min(duration, total - start)

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", str(src_path),
        "-t", str(actual_dur),
        *video_encode,
        *audio_encode,
        "-b:v", "5000k",
        str(out_path)
    ]

    print(f"  ✂  [{seg_id}] {src_path.name} [{start}s → +{actual_dur:.0f}s]", end="", flush=True)
    ok = run_ffmpeg(cmd, seg_id)
    if ok:
        size = out_path.stat().st_size / 1024 / 1024 if out_path.exists() else 0
        print(f"  ✓  ({size:.1f} MB)")
    return ok


def concat_segments(segment_paths: list, output: Path) -> bool:
    """Concatena segmentos usando el demuxer concat (copia sin re-encode)."""
    list_file = output.parent / "_concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in segment_paths:
            safe = str(p).replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")

    print(f"  ⛓  Concatenando {len(segment_paths)} segmentos...", end="", flush=True)
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output)
    ]
    ok = run_ffmpeg(cmd, "concat")
    if ok:
        size = output.stat().st_size / 1024 / 1024
        dur = get_duration(output)
        m, s = int(dur // 60), int(dur % 60)
        print(f"  ✓  {size:.0f} MB · {m}:{s:02d} min")
    return ok


# ─── TTS ──────────────────────────────────────────────────────────────────────

def generate_tts(idx: int, text: str, voice: str = TTS_VOICE,
                 rate: str = TTS_RATE, force: bool = False) -> Path:
    """
    Genera audio TTS con edge-tts.
    Usa caché: si el archivo ya existe y force=False, no lo regenera.
    Retorna el Path del archivo generado.
    """
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    out = TTS_DIR / f"tts_{idx:02d}.mp3"

    if out.exists() and not force:
        dur = get_duration(out)
        print(f"  ♻  [TTS {idx:02d}] Cache hit ({dur:.1f}s)")
        return out

    print(f"  🎙  [TTS {idx:02d}] Generando voz...", end="", flush=True)
    cmd = [
        "python", "-m", "edge_tts",
        "--voice", voice,
        "--rate", rate,
        "--text", text,
        "--write-media", str(out)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"\n  ✗ Error TTS: {r.stderr[-200:]}")
        raise RuntimeError(f"TTS falló para el bloque {idx}")

    dur = get_duration(out)
    print(f"  ✓  ({dur:.1f}s)")
    return out


# ─── OVERLAYS FFMPEG (lower thirds + alertas) ────────────────────────────────

def build_lower_third_filter(lower_thirds: list, font_file: str,
                              prev_node: str) -> tuple:
    """
    Construye los filtros drawtext para lower thirds estilo profesional.
    Retorna (lista_de_filtros, nombre_del_ultimo_nodo).

    Formato lower_thirds: [(t_start, duracion, texto_principal, texto_secundario)]
    """
    filters = []
    node = prev_node

    font = f"fontfile='{font_file}':" if font_file else ""

    for i, (t_s, dur, titulo, subtitulo) in enumerate(lower_thirds, 1):
        t_e = t_s + dur
        new_node = f"lt{i}"

        # Barra de fondo (rectángulo semitransparente)
        # Se logra con un drawbox encadenado al drawtext
        # Línea superior (acento de color)
        vf_accent = (
            f"[{node}]drawbox="
            f"x=60:y=ih-110:w=6:h=60:"
            f"color=0x00D4FF@0.95:t=fill:"
            f"enable='between(t,{t_s},{t_e})'[lt_accent{i}]"
        )
        filters.append(vf_accent)

        # Fondo semitransparente
        vf_bg = (
            f"[lt_accent{i}]drawbox="
            f"x=72:y=ih-112:w=520:h=64:"
            f"color=black@0.65:t=fill:"
            f"enable='between(t,{t_s},{t_e})'[lt_bg{i}]"
        )
        filters.append(vf_bg)

        # Texto principal (título)
        titulo_esc = titulo.replace("'", "\\'").replace(":", "\\:")
        vf_title = (
            f"[lt_bg{i}]drawtext={font}"
            f"text='{titulo_esc}':"
            f"fontcolor=white:fontsize=28:x=82:y=h-103:"
            f"enable='between(t,{t_s},{t_e})'[lt_t{i}]"
        )
        filters.append(vf_title)

        # Texto secundario (subtítulo)
        sub_esc = subtitulo.replace("'", "\\'").replace(":", "\\:")
        vf_sub = (
            f"[lt_t{i}]drawtext={font}"
            f"text='{sub_esc}':"
            f"fontcolor=0xCCCCCC:fontsize=18:x=82:y=h-73:"
            f"enable='between(t,{t_s},{t_e})'[{new_node}]"
        )
        filters.append(vf_sub)
        node = new_node

    return filters, node


def build_alert_filter(alertas: list, font_file: str, prev_node: str) -> tuple:
    """
    Construye filtros para alertas visuales emergentes centradas.
    Retorna (lista_de_filtros, nombre_del_ultimo_nodo).

    Formato alertas: [(t_start, duracion, texto, color_fondo)]
    """
    filters = []
    node = prev_node
    font = f"fontfile='{font_file}':" if font_file else ""

    for i, (t_s, dur, texto, color) in enumerate(alertas, 1):
        t_e = t_s + dur
        new_node = f"al{i}"

        texto_esc = texto.replace("'", "\\'").replace(":", "\\:")

        # Fondo de la alerta
        vf_bg = (
            f"[{node}]drawbox="
            f"x=(iw-860)/2:y=ih-200:w=860:h=60:"
            f"color={color}:t=fill:"
            f"enable='between(t,{t_s},{t_e})'[al_bg{i}]"
        )
        filters.append(vf_bg)

        # Texto centrado
        vf_text = (
            f"[al_bg{i}]drawtext={font}"
            f"text='{texto_esc}':"
            f"fontcolor=white:fontsize=24:"
            f"x=(w-text_w)/2:y=h-185:"
            f"enable='between(t,{t_s},{t_e})'[{new_node}]"
        )
        filters.append(vf_text)
        node = new_node

    return filters, node


def build_tts_audio_mix(tts_tracks: list) -> tuple:
    """
    Construye los filtros de audio para mezclar N pistas TTS con adelay.
    tts_tracks: [{"file": path, "start": float}]
    Retorna (lista_inputs_adicionales, lista_filtros_audio, etiqueta_salida)
    """
    a_filters = []
    amix_inputs = ""
    n = len(tts_tracks)

    for i, tr in enumerate(tts_tracks, 1):
        delay_ms = int(tr["start"] * 1000)
        a_filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        amix_inputs += f"[a{i}]"

    # normalize=0 evita que amix reduzca el volumen automáticamente
    a_filters.append(
        f"{amix_inputs}amix=inputs={n}:duration=longest:"
        f"normalize=0:dropout_transition=2[aout]"
    )

    return a_filters, "[aout]"
