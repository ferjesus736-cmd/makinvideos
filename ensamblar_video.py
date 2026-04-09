#!/usr/bin/env python3
"""
Ensamblador de video — Tutorial OpenClaw en VPS Hostinger
Canal: Ethos I.A. | Duración objetivo: ~9 minutos

Mapeo de material disponible:
  toma1  = 0:04   (b-roll corto)
  toma2  = 1:17   (cámara frontal - INTRO)
  toma3  = 0:25   (pantalla - requisitos)
  toma4  = 1:33   (terminal SSH + preparación)
  toma5  = 1:04   (instalación node + openclaw)
  toma6  = 1:29   (configuración wizard)
  toma7  = 1:24   (nginx + certbot + cierre)
  setup  = 1:24   (setup general + afraid.org)
  tutorial = 0:25 (verificación final)
"""

import subprocess
import sys
import os
from pathlib import Path

# ─── RECARGAR PATH (para detectar ffmpeg de winget) ───────────────────────────
machine_path = subprocess.run(
    ["powershell", "-command",
     "[System.Environment]::GetEnvironmentVariable('Path', 'Machine')"],
    capture_output=True, text=True).stdout.strip()
user_path = subprocess.run(
    ["powershell", "-command",
     "[System.Environment]::GetEnvironmentVariable('Path', 'User')"],
    capture_output=True, text=True).stdout.strip()
os.environ['PATH'] = machine_path + ";" + user_path + ";" + os.environ.get('PATH', '')

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
VIDEOS_DIR = Path(r"c:\Users\madhu\Desktop\GAMES\videos")
TMP_DIR    = VIDEOS_DIR / "_segmentos_tmp"
OUTPUT     = VIDEOS_DIR / "ETHOS_IA_OpenClaw_VPS_FINAL.mp4"
FFMPEG     = "ffmpeg"

SOURCES = {
    "toma1":    VIDEOS_DIR / "video toma 1.mp4",
    "toma2":    VIDEOS_DIR / "video toma 2.mp4",
    "toma3":    VIDEOS_DIR / "video toma 3.mp4",
    "toma4":    VIDEOS_DIR / "video toma 4.mp4",
    "toma5":    VIDEOS_DIR / "video toma 5.mp4",
    "toma6":    VIDEOS_DIR / "video toma 6.mp4",
    "toma7":    VIDEOS_DIR / "video toma 7.mp4",
    "setup":    VIDEOS_DIR / "setup openclaw.mp4",
    "tutorial": VIDEOS_DIR / "OpenClaw_ Self-Hosted AI on VPS Tutorial.mp4",
    "cover1":   VIDEOS_DIR / "coverr-coding-on-a-laptop-2116-1080p.mp4",
    "cover2":   VIDEOS_DIR / "coverr-coding-sequences-9906-1080p.mp4",
    "cover3":   VIDEOS_DIR / "coverr-coding-technology-5974-1080p.mp4",
    "cover4":   VIDEOS_DIR / "coverr-woman-coding-8692-1080p.mp4",
}

# Segmentos: (id_unico, fuente, inicio_seg, duracion_seg)
SEGMENTS = [
    # ESCENA 0: HOOK (0:00-0:04)
    ("00_hook",        "cover1",   0,    4),
    # ESCENA 1: INTRO (0:04-0:44)
    ("01_intro",       "toma2",    0,   40),
    # ESCENA 2: REQUISITOS (0:44-0:59)
    ("02_requisitos",  "toma3",    0,   15),
    # ESCENA 3: SSH AL VPS (0:59-1:24)
    ("03_ssh",         "toma4",    0,   25),
    # ESCENA 4A: apt update (1:24-2:01)
    ("04a_update",     "toma2",   40,   37),
    # ESCENA 4B: swap (2:01-2:34)
    ("04b_swap",       "toma4",   25,   33),
    # ESCENA 5A: instalar node+openclaw (2:34-2:59)
    ("05a_install",    "toma5",    0,   25),
    # ESCENA 5B: B-ROLL PROGRESO (2:59-3:03)
    ("05b_broll",      "cover2",   0,    4),
    # ESCENA 6: configurar wizard (3:03-4:26)
    ("06_config",      "toma6",    0,   83),
    # ESCENA 7A: B-ROLL TECNOLOGÍA (4:26-4:30)
    ("07a_broll",      "cover3",   0,    4),
    # ESCENA 7B: gateway + pairing (4:30-4:41)
    ("07b_prueba",     "toma3",   15,   11),
    # ESCENA 8A: afraid.org / setup (4:41-5:41)
    ("08a_dns",        "setup",    0,   60),
    # ESCENA 8A2: B-ROLL REDES (5:41-5:45)
    ("08a2_broll",     "cover4",   0,    4),
    # ESCENA 8B: nginx + certbot (5:45-6:35)
    ("08b_nginx",      "toma7",    0,   50),
    # ESCENA 9A: audit + doctor (6:35-7:00)
    ("09a_audit",      "tutorial", 0,   25),
    # ESCENA 9B: cierre (7:00-7:34)
    ("09b_cierre",     "toma7",   50,   34),
]

# ─── FUNCIONES ────────────────────────────────────────────────────────────────

def check_ffmpeg():
    try:
        r = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True)
        print(f"[OK] {r.stdout.splitlines()[0]}")
        return True
    except FileNotFoundError:
        print("[X] ffmpeg no encontrado. Instala con: winget install Gyan.FFmpeg")
        return False


def check_sources():
    print("\n[ ] Verificando archivos fuente:")
    ok = True
    for key, path in SOURCES.items():
        exists = path.exists()
        size = f"{path.stat().st_size/1024/1024:.0f} MB" if exists else "---"
        icon = "[OK]" if exists else "[X]"
        print(f"  {icon} {key:10s}: {path.name} ({size})")
        if not exists:
            ok = False
    return ok


def get_duration(path):
    """Obtener duración real del video en segundos."""
    r = subprocess.run([
        FFMPEG.replace("ffmpeg", "ffprobe"),
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path)
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 0


def cut_segment(seg_id, src_key, start, duration, out_path):
    """Cortar segmento con re-encode a formato común."""
    src = SOURCES[src_key]
    if not src.exists():
        print(f"  [!] Fuente no existe: {src}")
        return False

    # Verificar que el segmento pedido existe dentro del video
    total = get_duration(src)
    if start >= total:
        print(f"  [!] {seg_id}: inicio {start}s > duración {total:.0f}s del video")
        return False
    actual_dur = min(duration, total - start)

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(actual_dur),
        # Re-encode con parámetros consistentes para concat sin problemas
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-b:v", "5000k", "-b:a", "192k",
        "-r", "30",
        "-s", "1920x1080",
        "-pix_fmt", "yuv420p",
        # Forzar aspect ratio si el video original es distinto
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        str(out_path)
    ]

    print(f"  [CUT] [{seg_id}] {src.name} [{start}s -> +{actual_dur:.0f}s] -> {out_path.name}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Mostrar solo últimas líneas del error
        err_lines = [l for l in r.stderr.splitlines() if l.strip()][-5:]
        print(f"  [X] Error en {seg_id}:\n     " + "\n     ".join(err_lines))
        return False

    size = out_path.stat().st_size / 1024 / 1024 if out_path.exists() else 0
    print(f"     -> OK ({size:.1f} MB)")
    return True


def concat_segments(segment_paths, output):
    """Concatenar todos los segmentos usando el demuxer concat."""
    list_file = TMP_DIR / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in segment_paths:
            # Usar forward slash y escapar apóstrofes para el formato concat
            safe = str(p).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe}'\n")

    print(f"\n  [CONCAT] Concatenando {len(segment_paths)} segmentos...")
    cmd = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        # Copy: no re-encode, ya que todos los segmentos tienen el mismo codec
        "-c", "copy",
        str(output)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err_lines = [l for l in r.stderr.splitlines() if l.strip()][-10:]
        print("  [X] Error concatenando:\n     " + "\n     ".join(err_lines))
        return False
    return True


def main():
    print("[==========================================================]")
    print("[  ENSAMBLADOR --- ETHOS I.A. --- OpenClaw en VPS Hostinger   ]")
    print("[==========================================================]\n")

    # 1. Verificar ffmpeg
    if not check_ffmpeg():
        sys.exit(1)

    # 2. Verificar fuentes
    if not check_sources():
        print("\n[!] Algunos archivos no existen. Verifica las rutas en SOURCES.")

    # 3. Crear directorio temporal
    TMP_DIR.mkdir(exist_ok=True)
    OUTPUT.unlink(missing_ok=True)   # borrar salida previa si existe

    # 4. Cortar segmentos
    print(f"\n[FASE 1] Cortando {len(SEGMENTS)} segmentos...")
    good_segments = []
    for seg_id, src_key, start, duration in SEGMENTS:
        out = TMP_DIR / f"{seg_id}.mp4"
        ok = cut_segment(seg_id, src_key, start, duration, out)
        if ok:
            good_segments.append(out)
        else:
            print(f"  [!] Segmento '{seg_id}' omitido del video final.")

    print(f"\n  [OK] {len(good_segments)}/{len(SEGMENTS)} segmentos cortados correctamente.")

    if not good_segments:
        print("\n[X] No hay segmentos para concatenar. Revisa los errores.")
        sys.exit(1)

    # 5. Concatenar
    print(f"\n[FASE 2] Ensamblaje final...")
    ok = concat_segments(good_segments, OUTPUT)

    # 6. Resultado
    if ok and OUTPUT.exists():
        size_mb = OUTPUT.stat().st_size / 1024 / 1024
        # Duración real del video final
        dur_sec = get_duration(OUTPUT)
        mins = int(dur_sec // 60)
        secs = int(dur_sec % 60)
        print(f"\n[==================================================]")
        print(f"[  *  VIDEO FINAL LISTO                           ]")
        print(f"[  *  {OUTPUT.name:<42}  ]")
        print(f"[  *  {size_mb:.1f} MB   *  {mins}:{secs:02d} minutos           ]")
        print(f"[  *  Listo para revisar y subir a YouTube        ]")
        print(f"[==================================================]")
    else:
        print("\n[X] El ensamblaje final falló.")
        sys.exit(1)


if __name__ == "__main__":
    main()
