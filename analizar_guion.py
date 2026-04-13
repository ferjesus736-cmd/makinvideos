"""
analizar_guion.py — Módulo 1: Análisis semántico del guión con Gemini
Convierte cada bloque de texto narrativo en metadata visual estructurada.

Salida por bloque:
  {
    "bloque": 0,
    "keywords_visuales": ["hacker terminal", "server rack", "data center"],
    "emocion": "épico",          # épico | tenso | esperanza | técnico | íntimo | acción
    "ritmo": "plano_largo",      # corte_rapido | plano_largo | mixto
    "tipo_plano": "aéreo",       # aéreo | macro | personas | pantalla | naturaleza | abstracto
    "duracion_estimada": 38.5,   # segundos (calculada desde TTS)
    "descripcion_visual": "Texto breve de qué debería verse en pantalla"
  }

Uso:
  python analizar_guion.py                  # analiza GUION de config.py
  python analizar_guion.py --preview        # muestra resultado sin guardar
  python analizar_guion.py --bloque 3       # analiza solo un bloque
"""

import json
import argparse
import subprocess
from pathlib import Path
from config import GUION, TIEMPOS_TARGET, GEMINI_MODEL, TTS_DIR, TTS_VOICE, TTS_RATE

# Archivo de salida del análisis
ANALISIS_FILE = Path("guion_analizado.json")


# ─── ANÁLISIS CON GEMINI ──────────────────────────────────────────────────────

PROMPT_SISTEMA = """Eres un director de fotografía y editor de documentales.
Recibirás un bloque de narración en español para un video de YouTube estilo documental cinematográfico.
Tu tarea es devolver ÚNICAMENTE un objeto JSON con el siguiente esquema exacto, sin explicaciones ni markdown:

{
  "keywords_visuales": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "emocion": "épico",
  "ritmo": "plano_largo",
  "tipo_plano": "aéreo",
  "descripcion_visual": "Descripción breve (máx 15 palabras) de qué debe verse en pantalla"
}

Valores permitidos:
- emocion: "épico" | "tenso" | "esperanza" | "técnico" | "íntimo" | "acción"
- ritmo: "corte_rapido" | "plano_largo" | "mixto"
- tipo_plano: "aéreo" | "macro" | "personas" | "pantalla" | "naturaleza" | "abstracto" | "ciudad"

Reglas para keywords_visuales:
- Exactamente 5 keywords en inglés (para búsqueda en bancos de imágenes internacionales)
- Específicas y visuales, no abstractas ("server room blue light" mejor que "technology")
- Ordenadas de más específica a más general
- Deben describir imágenes cinematográficas reales que puedas encontrar en Pexels o Pixabay
"""


def analizar_bloque_con_gemini(texto: str, idx: int) -> dict:
    """Envía un bloque de texto a Gemini y recibe metadata visual estructurada."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("Instala: pip install google-genai")

    client = genai.Client()

    prompt_usuario = f"Analiza este bloque narrativo (bloque #{idx + 1}):\n\n{texto}"

    print(f"  [GEMINI] Analizando bloque {idx + 1}/{len(GUION)}...", end="", flush=True)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt_usuario],
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                temperature=0.3,
                max_output_tokens=512,
            )
        )

        raw = response.text.strip()

        # Limpiar markdown si Gemini lo agrega
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1])

        data = json.loads(raw)

        # Validar campos obligatorios
        required = ["keywords_visuales", "emocion", "ritmo", "tipo_plano", "descripcion_visual"]
        for campo in required:
            if campo not in data:
                raise ValueError(f"Campo faltante en respuesta: {campo}")

        print(f" ✓  [{data['emocion']} / {data['ritmo']}]")
        return data

    except json.JSONDecodeError as e:
        print(f"\n  [!] Error parseando JSON de Gemini: {e}")
        print(f"      Respuesta raw: {raw[:200]}")
        return _fallback_analisis(texto, idx)
    except Exception as e:
        print(f"\n  [!] Error Gemini bloque {idx}: {e}")
        return _fallback_analisis(texto, idx)


def _fallback_analisis(texto: str, idx: int) -> dict:
    """Análisis de fallback cuando Gemini falla — basado en heurísticas simples."""
    texto_lower = texto.lower()

    # Detectar emoción por palabras clave
    if any(w in texto_lower for w in ["poder", "épico", "increíble", "nivel", "futuro"]):
        emocion = "épico"
    elif any(w in texto_lower for w in ["atención", "cuidado", "error", "falla", "riesgo"]):
        emocion = "tenso"
    elif any(w in texto_lower for w in ["instalar", "configurar", "comando", "terminal"]):
        emocion = "técnico"
    elif any(w in texto_lower for w in ["gracias", "logrado", "éxito", "listo", "funciona"]):
        emocion = "esperanza"
    else:
        emocion = "técnico"

    return {
        "keywords_visuales": [
            "linux terminal server",
            "data center blue light",
            "programmer coding night",
            "network cables infrastructure",
            "technology abstract"
        ],
        "emocion": emocion,
        "ritmo": "mixto",
        "tipo_plano": "pantalla",
        "descripcion_visual": f"Plano técnico relacionado con el bloque {idx + 1}"
    }


# ─── DURACIÓN TTS ─────────────────────────────────────────────────────────────

def estimar_duracion_tts(texto: str, idx: int) -> float:
    """
    Genera el audio TTS (o usa caché) y devuelve su duración real en segundos.
    Esto es más preciso que cualquier fórmula de palabras/minuto.
    """
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    tts_path = TTS_DIR / f"tts_{idx:02d}.mp3"

    if not tts_path.exists():
        print(f"  [TTS] Generando audio {idx + 1}...", end="", flush=True)
        cmd = [
            "python", "-m", "edge_tts",
            "--voice", TTS_VOICE,
            "--rate", TTS_RATE,
            "--text", texto,
            "--write-media", str(tts_path)
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f" [!] Error TTS, estimando por palabras")
            # Fallback: ~150 palabras/minuto con la tasa configurada
            palabras = len(texto.split())
            return round(palabras / 2.8, 1)
        print(" ✓")

    # Medir duración real con ffprobe
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(tts_path)],
        capture_output=True, text=True
    )
    try:
        dur = float(r.stdout.strip())
        print(f"  [TTS] Bloque {idx + 1}: {dur:.1f}s")
        return dur
    except ValueError:
        palabras = len(texto.split())
        return round(palabras / 2.8, 1)


# ─── ANÁLISIS COMPLETO ────────────────────────────────────────────────────────

def analizar_guion(bloques: list = None, solo_bloque: int = None) -> list:
    """
    Analiza todos los bloques del guión (o uno específico).
    Retorna lista de dicts con metadata completa.
    """
    if bloques is None:
        bloques = GUION

    if solo_bloque is not None:
        indices = [solo_bloque]
    else:
        indices = list(range(len(bloques)))

    resultados = []

    print(f"\n{'='*55}")
    print(f"  ANÁLISIS SEMÁNTICO DEL GUIÓN")
    print(f"  {len(indices)} bloque(s) → Gemini {GEMINI_MODEL}")
    print(f"{'='*55}\n")

    for idx in indices:
        texto = bloques[idx]
        print(f"\n[BLOQUE {idx + 1}] {texto[:80]}...")

        # 1. Análisis semántico con Gemini
        meta = analizar_bloque_con_gemini(texto, idx)

        # 2. Duración real del audio TTS
        duracion = estimar_duracion_tts(texto, idx)

        # 3. Tiempo de inicio en el video (desde config)
        tiempo_inicio = TIEMPOS_TARGET[idx] if idx < len(TIEMPOS_TARGET) else sum(
            r.get("duracion_estimada", 30) for r in resultados
        )

        # 4. Ensamblar resultado final
        resultado = {
            "bloque": idx,
            "tiempo_inicio": tiempo_inicio,
            "duracion_estimada": duracion,
            "texto_preview": texto[:100] + "...",
            **meta
        }

        resultados.append(resultado)

        # Preview del análisis
        print(f"  → Descripción: {meta['descripcion_visual']}")
        print(f"  → Keywords:    {', '.join(meta['keywords_visuales'][:3])}...")
        print(f"  → Duración:    {duracion:.1f}s | Inicio: {tiempo_inicio}s")

    return resultados


# ─── GUARDAR / CARGAR ─────────────────────────────────────────────────────────

def guardar_analisis(resultados: list, path: Path = ANALISIS_FILE):
    """Guarda el análisis completo en JSON para ser consumido por otros módulos."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] Análisis guardado en: {path.absolute()}")
    print(f"       {len(resultados)} bloques procesados\n")


def cargar_analisis(path: Path = ANALISIS_FILE) -> list:
    """
    Carga el análisis desde JSON.
    Usar desde buscar_imagenes.py y ensamblar_video.py.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Ejecuta primero: python analizar_guion.py"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resumen_analisis(resultados: list):
    """Imprime un resumen visual del análisis completo."""
    print(f"\n{'='*55}")
    print(f"  RESUMEN DEL ANÁLISIS")
    print(f"{'='*55}")

    duracion_total = sum(r["duracion_estimada"] for r in resultados)
    m, s = int(duracion_total // 60), int(duracion_total % 60)

    print(f"\n  Total bloques:  {len(resultados)}")
    print(f"  Duración total: {m}:{s:02d} min (estimada)")

    emociones = {}
    ritmos = {}
    for r in resultados:
        emociones[r["emocion"]] = emociones.get(r["emocion"], 0) + 1
        ritmos[r["ritmo"]] = ritmos.get(r["ritmo"], 0) + 1

    print(f"\n  Emociones:")
    for k, v in sorted(emociones.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k:15s} {bar} ({v})")

    print(f"\n  Ritmos:")
    for k, v in sorted(ritmos.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k:20s} {bar} ({v})")

    print(f"\n  Bloques detallados:")
    for r in resultados:
        dur = r["duracion_estimada"]
        print(f"    [{r['bloque']:02d}] {r['emocion']:10s} | {r['ritmo']:15s} | {dur:.0f}s | {r['keywords_visuales'][0]}")

    print()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analiza el guión con Gemini y genera metadata visual para cada bloque."
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Muestra el análisis sin guardar el archivo JSON"
    )
    parser.add_argument(
        "--bloque", type=int, default=None,
        help="Analiza solo un bloque específico (índice 0-based)"
    )
    parser.add_argument(
        "--output", type=str, default=str(ANALISIS_FILE),
        help=f"Ruta del archivo de salida (default: {ANALISIS_FILE})"
    )
    parser.add_argument(
        "--force-tts", action="store_true",
        help="Regenera los audios TTS aunque ya existan en caché"
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    # Ejecutar análisis
    resultados = analizar_guion(solo_bloque=args.bloque)

    # Mostrar resumen
    resumen_analisis(resultados)

    # Guardar o preview
    if args.preview:
        print("  [PREVIEW] No se guarda el archivo (--preview activo)")
        print("\n  JSON que se generaría:")
        print(json.dumps(resultados[:2], ensure_ascii=False, indent=2))
        print("  ... (primeros 2 bloques)")
    else:
        guardar_analisis(resultados, output_path)
        print(f"  Siguiente paso: python buscar_imagenes.py")


if __name__ == "__main__":
    main()
