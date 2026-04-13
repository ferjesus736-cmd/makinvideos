"""
producir_final.py - Fase 3: narracion TTS + lower thirds + alertas visuales
Unifica lo que antes era narracion_total.py + procesador_final.py.
Produce: OUTPUT_FINAL (video completo listo para YouTube)
"""

import subprocess
from pathlib import Path
from config import (
    FFMPEG, OUTPUT_SUBTITULADO, OUTPUT_ENSAMBLADO, OUTPUT_FINAL,
    TTS_VOICE, TTS_RATE, FONT_FILE,
    LOWER_THIRDS, ALERTAS, GUION, TIEMPOS_TARGET,
    check_ffmpeg, check_dirs
)
from utils import (
    generate_tts, get_duration,
    build_lower_third_filter, build_alert_filter,
    build_tts_audio_mix, run_ffmpeg
)


def calcular_pistas_tts() -> list:
    """
    Genera todos los audios TTS y calcula sus tiempos de inicio.
    Respeta que cada pista no empiece antes de que termine la anterior.
    Retorna lista de dicts: [{"file": Path, "start": float}]
    """
    pistas = []
    fin_anterior = 0.0

    for i, (texto, target) in enumerate(zip(GUION, TIEMPOS_TARGET)):
        audio_path = generate_tts(i, texto, TTS_VOICE, TTS_RATE)
        dur = get_duration(audio_path)

        # El inicio es el mayor entre el target del guion y el fin del audio anterior
        inicio = max(float(target), fin_anterior + 0.8)
        pistas.append({"file": audio_path, "start": inicio})
        fin_anterior = inicio + dur

        m, s = int(inicio // 60), int(inicio % 60)
        print(f"    Pista {i:02d}: inicia {m}:{s:02d} - duracion {dur:.1f}s")

    return pistas


def renderizar(video_in: Path, pistas: list, video_out: Path) -> bool:
    """
    Renderiza el video final aplicando:
    - Lower thirds sincronizados
    - Alertas visuales emergentes
    - Narracion TTS sincronizada (reemplaza audio original)
    """
    # Construir inputs: video + archivos TTS
    cmd = [FFMPEG, "-y", "-i", str(video_in)]
    for p in pistas:
        cmd.extend(["-i", str(p["file"])])

    # -- Filtros de video ------------------------------------------------------
    v_filters = []
    nodo_actual = "0:v"

    # Lower thirds (estilo Ethos I.A.)
    lf, nodo_actual = build_lower_third_filter(LOWER_THIRDS, FONT_FILE, nodo_actual)
    v_filters.extend(lf)

    # Alertas emergentes
    af, nodo_actual = build_alert_filter(ALERTAS, FONT_FILE, nodo_actual)
    v_filters.extend(af)

    # -- Filtros de audio (TTS - sin audio original) ---------------------------
    a_filters, audio_out_label = build_tts_audio_mix(pistas)

    # -- Ensamblar filter_complex ----------------------------------------------
    filter_complex = ";".join(v_filters + a_filters)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{nodo_actual}]",
        "-map", audio_out_label,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        str(video_out)
    ])

    return run_ffmpeg(cmd, "render_final")


def run():
    print("\n=== FASE 3: PRODUCCION FINAL ===")
    check_ffmpeg()
    check_dirs()

    # Usar video subtitulado si existe, si no el ensamblado limpio
    if OUTPUT_SUBTITULADO.exists():
        video_base = OUTPUT_SUBTITULADO
        print(f"  Base: {video_base.name} (con subtitulos)")
    elif OUTPUT_ENSAMBLADO.exists():
        video_base = OUTPUT_ENSAMBLADO
        print(f"  Base: {video_base.name} (sin subtitulos - ejecuta generar_subtitulos.py primero)")
    else:
        raise FileNotFoundError(
            "No se encontro ningun video base. Ejecuta primero ensamblar_video.py"
        )

    # Generar audios TTS y calcular tiempos
    print("\n  Generando narracion TTS...")
    pistas = calcular_pistas_tts()

    # Renderizar
    print(f"\n  Renderizando video final ({len(pistas)} pistas de voz + overlays)...")
    ok = renderizar(video_base, pistas, OUTPUT_FINAL)

    if ok and OUTPUT_FINAL.exists():
        size = OUTPUT_FINAL.stat().st_size / 1024 / 1024
        dur = get_duration(OUTPUT_FINAL)
        m, s = int(dur // 60), int(dur % 60)
        print(f"\n  [OK] Video final: {OUTPUT_FINAL}")
        print(f"    {size:.0f} MB - {m}:{s:02d} min")
    else:
        raise RuntimeError("Fallo el renderizado final.")

    return OUTPUT_FINAL


if __name__ == "__main__":
    run()
