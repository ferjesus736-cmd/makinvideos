"""
buscar_imagenes.py — Módulo 2: Búsqueda y descarga de clips cinematográficos
Lee guion_analizado.json y descarga videos de Pexels que calzan con cada bloque.

Requiere:
  pip install requests
  PEXELS_API_KEY en variables de entorno (gratis en pexels.com/api)

Salida:
  _clips_descargados/bloque_00_epico_linux-server-room.mp4
  clips_mapeados.json  <- consumido por ensamblar_video.py

Uso:
  python buscar_imagenes.py
  python buscar_imagenes.py --bloque 3
  python buscar_imagenes.py --preview
  python buscar_imagenes.py --re-fetch
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from analizar_guion import cargar_analisis, ANALISIS_FILE

CLIPS_DIR       = Path("_clips_descargados")
MAPEADO_FILE    = Path("clips_mapeados.json")
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

VIDEO_ORIENTATION  = "landscape"
VIDEO_MIN_DURATION = 5
VIDEO_SIZE         = "large"
VIDEO_PER_PAGE     = 10

EMOCION_HINTS = {
    "epico":     {"extra": "cinematic dramatic",   "color": "blue"},
    "tenso":     {"extra": "dark moody close-up",  "color": "red"},
    "esperanza": {"extra": "golden hour sunrise",  "color": "orange"},
    "tecnico":   {"extra": "screen monitor code",  "color": ""},
    "intimo":    {"extra": "close up detail soft", "color": ""},
    "accion":    {"extra": "fast motion dynamic",  "color": ""},
}

TIPO_PLANO_FILTER = {
    "aereo":     "aerial drone",
    "macro":     "close up macro",
    "personas":  "people working",
    "pantalla":  "computer screen monitor",
    "naturaleza":"nature landscape",
    "abstracto": "abstract motion",
    "ciudad":    "city urban",
}


def _normalizar(texto):
    """Quita tildes y caracteres especiales para usar como clave."""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def buscar_pexels(query, duracion_necesaria):
    if not PEXELS_API_KEY:
        raise EnvironmentError(
            "PEXELS_API_KEY no encontrada.\n"
            "  Registrate gratis en https://www.pexels.com/api/\n"
            "  Windows: set PEXELS_API_KEY=tu_key\n"
            "  Linux:   export PEXELS_API_KEY=tu_key"
        )
    headers = {"Authorization": PEXELS_API_KEY}
    params  = {"query": query, "orientation": VIDEO_ORIENTATION,
                "size": VIDEO_SIZE, "per_page": VIDEO_PER_PAGE}
    try:
        resp = requests.get("https://api.pexels.com/videos/search",
                            headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"  [!] Error Pexels: {e}")
        return []

    candidatos = []
    for video in data.get("videos", []):
        dur = video.get("duration", 0)
        if dur < VIDEO_MIN_DURATION:
            continue
        best_file, best_width = None, 0
        for vf in video.get("video_files", []):
            w = vf.get("width", 0)
            if vf.get("file_type") == "video/mp4" and w >= 1280 and w > best_width:
                best_file, best_width = vf, w
        if not best_file:
            continue
        candidatos.append({
            "id": video["id"], "url": best_file["link"],
            "duracion": dur, "width": best_width,
            "height": best_file.get("height", 720), "query": query,
        })
    return candidatos


def buscar_pixabay(query, duracion_necesaria):
    if not PIXABAY_API_KEY:
        return []
    params = {"key": PIXABAY_API_KEY, "q": query,
              "video_type": "film", "orientation": "horizontal",
              "per_page": VIDEO_PER_PAGE}
    try:
        resp = requests.get("https://pixabay.com/api/videos/",
                            params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"  [!] Error Pixabay: {e}")
        return []
    candidatos = []
    for hit in data.get("hits", []):
        videos = hit.get("videos", {})
        vid = videos.get("large") or videos.get("medium") or {}
        if not vid.get("url"):
            continue
        candidatos.append({
            "id": hit["id"], "url": vid["url"],
            "duracion": 10, "width": vid.get("width", 1920),
            "height": vid.get("height", 1080), "query": query,
        })
    return candidatos


def seleccionar_mejor_clip(candidatos, duracion_necesaria):
    if not candidatos:
        return None
    suficientes = [c for c in candidatos if c["duracion"] >= duracion_necesaria]
    if suficientes:
        return min(suficientes, key=lambda c: c["duracion"])
    return max(candidatos, key=lambda c: c["duracion"])


def construir_queries(bloque):
    keywords = bloque["keywords_visuales"]
    emocion  = _normalizar(bloque["emocion"])
    tipo     = _normalizar(bloque["tipo_plano"])
    hints    = EMOCION_HINTS.get(emocion, {})
    tipo_hint = TIPO_PLANO_FILTER.get(tipo, "")
    queries = []
    if hints.get("extra"):
        queries.append(f"{keywords[0]} {hints['extra']}")
    queries.append(keywords[0])
    if tipo_hint and len(keywords) > 1:
        queries.append(f"{keywords[1]} {tipo_hint}")
    if len(keywords) > 1:
        queries.append(keywords[1])
    if len(keywords) > 2:
        queries.append(keywords[2])
    if tipo_hint:
        queries.append(tipo_hint)
    return queries


def buscar_clip_para_bloque(bloque, preview=False):
    duracion = bloque["duracion_estimada"]
    queries  = construir_queries(bloque)
    for i, query in enumerate(queries, 1):
        print(f"  [BUSCAR] Query {i}/{len(queries)}: '{query}'")
        candidatos = buscar_pexels(query, duracion)
        if not candidatos and PIXABAY_API_KEY:
            print("  [PIXABAY] Intentando fallback...")
            candidatos = buscar_pixabay(query, duracion)
        if candidatos:
            elegido = seleccionar_mejor_clip(candidatos, duracion)
            if elegido:
                print(f"  [OK] ID={elegido['id']} | {elegido['duracion']}s | {elegido['width']}x{elegido['height']}")
                elegido["query_usada"] = query
                return elegido
        time.sleep(0.3)
    print(f"  [!] Sin clip para bloque {bloque['bloque']}")
    return None


def descargar_clip(candidato, dest):
    if dest.exists():
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  [CACHE] {dest.name} ({size_mb:.1f} MB)")
        return True
    print(f"  [DL] Descargando {dest.name}...", end="", flush=True)
    try:
        resp = requests.get(candidato["url"], stream=True, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f" OK ({size_mb:.1f} MB | {candidato['duracion']}s)")
        return True
    except Exception as e:
        print(f" [!] Error: {e}")
        if dest.exists():
            dest.unlink()
        return False


def procesar_bloques(bloques, solo_bloque=None, preview=False, re_fetch=False):
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    if solo_bloque is not None:
        bloques = [b for b in bloques if b["bloque"] == solo_bloque]

    mapeados, sin_clip = [], []

    print(f"\n{'='*55}")
    print(f"  BUSQUEDA DE CLIPS CINEMATOGRAFICOS")
    print(f"  {len(bloques)} bloque(s) | Pexels API")
    print(f"{'='*55}\n")

    for bloque in bloques:
        idx     = bloque["bloque"]
        emocion = bloque["emocion"]
        print(f"\n[BLOQUE {idx:02d}] {emocion.upper()} | {bloque['duracion_estimada']:.0f}s")
        print(f"  Keywords: {', '.join(bloque['keywords_visuales'])}")

        keyword_slug = bloque["keywords_visuales"][0].replace(" ", "-")[:30]
        emocion_slug = _normalizar(emocion)
        clip_name    = f"bloque_{idx:02d}_{emocion_slug}_{keyword_slug}.mp4"
        clip_path    = CLIPS_DIR / clip_name

        if re_fetch and clip_path.exists():
            clip_path.unlink()

        candidato = buscar_clip_para_bloque(bloque, preview)

        if not candidato:
            sin_clip.append(idx)
            mapeados.append({
                "bloque": idx, "clip_path": None,
                "duracion_clip": 0,
                "duracion_necesaria": bloque["duracion_estimada"],
                "tiempo_inicio": bloque["tiempo_inicio"],
                "emocion": emocion, "ritmo": bloque["ritmo"],
                "tipo_plano": bloque["tipo_plano"],
                "descripcion": bloque["descripcion_visual"],
                "keywords": bloque["keywords_visuales"],
                "error": "sin_clip",
            })
            continue

        descargado = False
        if not preview:
            descargado = descargar_clip(candidato, clip_path)

        mapeados.append({
            "bloque":             idx,
            "clip_path":          str(clip_path) if descargado else None,
            "clip_url":           candidato["url"],
            "pexels_id":          candidato["id"],
            "query_usada":        candidato.get("query_usada", ""),
            "duracion_clip":      candidato["duracion"],
            "duracion_necesaria": bloque["duracion_estimada"],
            "tiempo_inicio":      bloque["tiempo_inicio"],
            "emocion":            emocion,
            "ritmo":              bloque["ritmo"],
            "tipo_plano":         bloque["tipo_plano"],
            "descripcion":        bloque["descripcion_visual"],
            "keywords":           bloque["keywords_visuales"],
            "necesita_loop":      candidato["duracion"] < bloque["duracion_estimada"],
        })
        time.sleep(0.5)

    return mapeados, sin_clip


def guardar_mapeado(mapeados, path=MAPEADO_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapeados, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] Mapeado guardado: {path.absolute()}")


def resumen_mapeado(mapeados, sin_clip):
    total    = len(mapeados)
    con_clip = total - len(sin_clip)
    print(f"\n{'='*55}")
    print(f"  RESUMEN")
    print(f"{'='*55}")
    print(f"  Clips encontrados: {con_clip}/{total}")
    if sin_clip:
        print(f"\n  Sin clip ({len(sin_clip)} bloques):")
        for idx in sin_clip:
            b = next(m for m in mapeados if m["bloque"] == idx)
            print(f"    Bloque {idx:02d}: {', '.join(b['keywords'][:2])}")
        print(f"\n  Opciones:")
        print(f"    1. Agrega PIXABAY_API_KEY como segunda fuente")
        print(f"    2. Pon clips manualmente en {CLIPS_DIR}/bloque_XX_*.mp4")
        print(f"    3. Ajusta keywords en guion_analizado.json y re-ejecuta")
    loops = [m for m in mapeados if m.get("necesita_loop")]
    if loops:
        print(f"\n  {len(loops)} clip(s) mas corto que el audio (se aplicara loop/slowmo):")
        for m in loops:
            print(f"    Bloque {m['bloque']:02d}: clip {m['duracion_clip']:.0f}s vs audio {m['duracion_necesaria']:.0f}s")
    print(f"\n  Siguiente paso: python ensamblar_video.py --modo documental\n")


def main():
    parser = argparse.ArgumentParser(
        description="Busca y descarga clips cinematograficos desde Pexels segun el guion analizado."
    )
    parser.add_argument("--bloque",   type=int, default=None)
    parser.add_argument("--preview",  action="store_true")
    parser.add_argument("--re-fetch", action="store_true")
    parser.add_argument("--analisis", type=str, default=str(ANALISIS_FILE))
    args = parser.parse_args()

    bloques  = cargar_analisis(Path(args.analisis))
    mapeados, sin_clip = procesar_bloques(
        bloques,
        solo_bloque=args.bloque,
        preview=args.preview,
        re_fetch=args.re_fetch,
    )
    if not args.preview:
        guardar_mapeado(mapeados)
    resumen_mapeado(mapeados, sin_clip)


if __name__ == "__main__":
    main()
