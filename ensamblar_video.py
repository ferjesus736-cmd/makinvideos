"""
ensamblar_video.py — Fase 1: cortar y ensamblar segmentos
Produce: OUTPUT_ENSAMBLADO (video limpio sin overlays ni narración)
"""

from pathlib import Path
from config import (
    VIDEOS_DIR, TMP_DIR, OUTPUT_ENSAMBLADO,
    VIDEO_ENCODE, AUDIO_ENCODE, check_ffmpeg, check_dirs, check_sources
)
from utils import cut_segment, concat_segments

# ─── FUENTES ──────────────────────────────────────────────────────────────────
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

# ─── SEGMENTOS ────────────────────────────────────────────────────────────────
# (id, fuente, inicio_seg, duracion_seg)
SEGMENTS = [
    ("00_hook",       "cover1",    0,  4),
    ("01_intro",      "toma2",     0, 40),
    ("02_requisitos", "toma3",     0, 15),
    ("03_ssh",        "toma4",     0, 25),
    ("04a_update",    "toma2",    40, 37),
    ("04b_swap",      "toma4",    25, 33),
    ("05a_install",   "toma5",     0, 25),
    ("05b_broll",     "cover2",    0,  4),
    ("06_config",     "toma6",     0, 83),
    ("07a_broll",     "cover3",    0,  4),
    ("07b_prueba",    "toma3",    15, 11),
    ("08a_dns",       "setup",     0, 60),
    ("08a2_broll",    "cover4",    0,  4),
    ("08b_nginx",     "toma7",     0, 50),
    ("09a_audit",     "tutorial",  0, 25),
    ("09b_cierre",    "toma7",    50, 34),
]


def run():
    print("\n--- FASE 1: ENSAMBLADO ------------------------------------")
    check_ffmpeg()
    check_dirs()

    print("\nVerificando archivos fuente:")
    check_sources(SOURCES)

    OUTPUT_ENSAMBLADO.unlink(missing_ok=True)

    # Cortar segmentos
    print(f"\nCortando {len(SEGMENTS)} segmentos...")
    good = []
    for seg_id, src_key, start, duration in SEGMENTS:
        out = TMP_DIR / f"{seg_id}.mp4"
        ok = cut_segment(
            seg_id, SOURCES[src_key], start, duration, out,
            VIDEO_ENCODE, AUDIO_ENCODE
        )
        if ok:
            good.append(out)
        else:
            print(f"  [!] Segmento '{seg_id}' omitido.")

    print(f"\n  {len(good)}/{len(SEGMENTS)} segmentos listos.")

    if not good:
        raise RuntimeError("No hay segmentos válidos para ensamblar.")

    # Concatenar
    print("\nEnsamblando video final...")
    ok = concat_segments(good, OUTPUT_ENSAMBLADO)
    if not ok:
        raise RuntimeError("Falló la concatenación.")

    print(f"\n  [FIN] Video base guardado en: {OUTPUT_ENSAMBLADO}")
    return OUTPUT_ENSAMBLADO


if __name__ == "__main__":
    run()
