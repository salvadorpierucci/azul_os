"""
Parser de chats WhatsApp para Azul OS.
Envía texto de chat a Kimi K2.6 (via NVIDIA API) para extraer datos de presupuesto.
También maneja transcripción de audios (Groq Whisper) y extracción de PDFs.
"""
import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def get_nvidia_keys() -> list:
    """Obtiene las API keys de NVIDIA disponibles."""
    keys = []
    for key_name in ["NVIDIA_API_KEY_1", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY"]:
        val = os.getenv(key_name)
        if val and val.strip() and val not in keys:
            keys.append(val.strip())
    return keys


def get_groq_key() -> str:
    """Obtiene la API key de Groq para Whisper."""
    return os.getenv("GROQ_API_KEY", "")


def extract_pdf_text(pdf_path: str) -> str:
    """Extrae texto de un PDF usando pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"[Página {i+1}]\n{text.strip()}")
        return "\n\n".join(pages_text)
    except Exception as e:
        print(f"Error extracting PDF {pdf_path}: {e}")
        return ""


def extract_pdfs_from_dir(extract_dir: str) -> str:
    """Busca todos los PDFs en un directorio y devuelve su texto combinado."""
    pdf_texts = []
    for root, dirs, files in os.walk(extract_dir):
        for f in sorted(files):
            if f.lower().endswith(".pdf") and not f.startswith("__MACOSX"):
                pdf_path = os.path.join(root, f)
                print(f"Extracting text from PDF: {f}")
                text = extract_pdf_text(pdf_path)
                if text.strip():
                    pdf_texts.append(f"=== DOCUMENTO ADJUNTO: {f} ===\n{text}")
    return "\n\n".join(pdf_texts)


def transcribe_audio_groq(file_path: str) -> str:
    """Transcribe audio usando Groq Whisper."""
    groq_key = get_groq_key()
    if not groq_key:
        return ""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {groq_key}"}
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f),
                "model": (None, "whisper-large-v3"),
                "language": (None, "es"),
            }
            resp = requests.post(url, headers=headers, files=files, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("text", "").strip()
            else:
                print(f"Groq Whisper error {resp.status_code}: {resp.text}")
                return ""
    except Exception as e:
        print(f"Exception during Groq Whisper call: {e}")
        return ""


def preprocess_chat_with_audio(chat_text: str, extract_dir: str) -> str:
    """Reemplaza referencias a archivos de audio con transcripciones de Whisper."""
    audio_pattern = re.compile(r"([\w\-]+\.(?:opus|wav|mp3|m4a|ogg))", re.IGNORECASE)
    lines = chat_text.split("\n")
    processed_lines = []

    for line in lines:
        match = audio_pattern.search(line)
        if match:
            audio_filename = match.group(1)
            audio_path = os.path.join(extract_dir, audio_filename)

            if not os.path.exists(audio_path):
                for f in os.listdir(extract_dir):
                    if f.lower() == audio_filename.lower():
                        audio_path = os.path.join(extract_dir, f)
                        break

            if os.path.exists(audio_path) and os.path.isfile(audio_path):
                print(f"Transcribing audio: {audio_filename}...")
                transcript = transcribe_audio_groq(audio_path)
                if transcript:
                    line = line.replace(audio_filename, f'"{transcript}" (Mensaje de voz transcrito)')
                    print(f"Transcription OK: {transcript}")
                else:
                    line = line.replace(audio_filename, "(Mensaje de voz - falló transcripción)")
        processed_lines.append(line)

    return "\n".join(processed_lines)


def parse_whatsapp_chat(chat_text: str, catalog_data: dict, pdf_context: str = "") -> dict:
    """
    Envía texto de chat (+ PDFs) a Kimi K2.6 y extrae datos del presupuesto.
    Devuelve un dict con: cliente_nombre, fecha_evento, tipo_evento,
    cantidad_invitados, localidad, logistica_tipo, acarreo_adicional, lugares.
    """
    product_keys = list(catalog_data.get("productos", {}).keys())
    zones = list(catalog_data.get("logistica", {}).get("zonas", {}).keys())

    full_context = chat_text
    if pdf_context.strip():
        full_context += f"""

---
DOCUMENTOS Y PRESUPUESTOS ADJUNTOS EN EL CHAT:
{pdf_context}
---
"""

    system_prompt = f"""Eres un asistente experto en extracción de datos para Azul Livings Luján, un negocio de alquiler de mobiliario y decoración para eventos.

Tu tarea es analizar un chat de WhatsApp (y documentos PDF adjuntos si los hay) y extraer los datos para generar un presupuesto de alquiler de mobiliario.

DEBES responder ÚNICAMENTE con un objeto JSON válido. Sin markdown, sin explicaciones, sin texto antes o después del JSON.

**Catálogo de productos disponibles (usa estos nombres exactos en catalogo_key):**
{json.dumps(product_keys, ensure_ascii=False)}

**Zonas de entrega disponibles:**
{json.dumps(zones, ensure_ascii=False)}

---
**REGLAS IMPORTANTES:**

1. FUENTES: Prioriza SIEMPRE el contenido de los PDFs adjuntos sobre el texto del chat, porque el PDF es el presupuesto real con los productos y cantidades definitivas.

2. PROPUESTAS MÚLTIPLES (A, B, C): Si el presupuesto tiene varias propuestas (A, B, C), toma la que el cliente haya confirmado en el chat. Si no hay confirmación clara, toma la ÚLTIMA propuesta mencionada en el PDF (generalmente la B reducida o la más económica que hayan consensuado).

3. LUGARES: Los lugares son las secciones físicas del evento (ej: "Hall de ingreso", "Escenario", "Salón comedor", "Carpa", "Casa"). Cada sección tiene su propia lista de productos. Si no hay divisiones por lugar, usa un solo lugar llamado "General".

4. CANTIDADES: Extrae la cantidad EXACTA. Si dice "*15 velones led", la cantidad es 15. Si dice "*2 tochos", la cantidad es 2.

5. LOCALIDAD: Extrae solo el nombre de la ciudad/lugar (ej: "Luján", "Jáuregui", "Mercedes", "Pilar"). Si menciona "Luján centro" o "Luján, centro", extrae "Luján". Si no se menciona, pon null.

6. LOGISTICA: Si el presupuesto o chat menciona "armado", "desarme", "montaje" o "traslado y armado", usa "Armado y Desarme". Si solo dice "traslado" o "retiro", usa "Traslado Simple".

7. NO incluyas los "Otros: *Armado, desarme y traslados" como productos. Eso es la logística.

8. TIPO DE EVENTO: Extrae el tipo (ej: "Boda", "Cumpleaños 40", "XV Años", "Noche de Jazz"). null si no se menciona.

9. INVITADOS: Número entero si se menciona (ej: "150 personas" → 150). null si no se menciona.

---
**EJEMPLOS REALES (FEW-SHOT) — Aprende el formato exacto de estos ejemplos:**

EJEMPLO 1 — Presupuesto con múltiples lugares y propuesta B:
Documento PDF dice:
"CLIENTE: Karen | FECHA: 12/6/26 | LUGAR: Sushi Club, Luján | TIPO: Noche de Jazz
B) Propuesta reducida:
Hall de ingreso: *15 velones led, *2 tochos, *1 canasto con follaje
Escenario: *3 alfombras con dibujos persas, *2 cajones de luces, *2 tochos, *15 velones led
Salón comedor: *2 tochos o mesas cubos, *2 jarrones con arreglos de follaje
Otros: *Armado, desarme y traslados | Importe total B: $712000"

JSON correcto:
{{
  "cliente_nombre": "Karen",
  "fecha_evento": "12/6/26",
  "tipo_evento": "Noche de Jazz",
  "cantidad_invitados": null,
  "localidad": "Luján",
  "logistica_tipo": "Armado y Desarme",
  "acarreo_adicional": false,
  "lugares": [
    {{
      "nombre": "Hall de ingreso",
      "productos": [
        {{"catalogo_key": "Velón led", "cantidad": 15, "notas": ""}},
        {{"catalogo_key": "Tocho", "cantidad": 2, "notas": ""}},
        {{"catalogo_key": "Canasto con follaje", "cantidad": 1, "notas": ""}}
      ]
    }},
    {{
      "nombre": "Escenario",
      "productos": [
        {{"catalogo_key": "Alfombra con dibujos persas", "cantidad": 3, "notas": ""}},
        {{"catalogo_key": "Cajón de luces", "cantidad": 2, "notas": ""}},
        {{"catalogo_key": "Tocho", "cantidad": 2, "notas": ""}},
        {{"catalogo_key": "Velón led", "cantidad": 15, "notas": ""}}
      ]
    }},
    {{
      "nombre": "Salón comedor",
      "productos": [
        {{"catalogo_key": "Mesa cubo", "cantidad": 2, "notas": "alternativa a tochos"}},
        {{"catalogo_key": "Jarrón con follaje", "cantidad": 2, "notas": ""}}
      ]
    }}
  ]
}}

EJEMPLO 2 — Presupuesto simple sin subdivisión de lugares:
Documento dice:
"CLIENTE: Jimena Benavides | FECHA: 30/4/26 | LUGAR: Luján Centro | TIPO: Cumpleaños
*2 juegos de livings caña básico (incluyen colchonería, almohadones decorativos y centros de mesa básicos)
*Armado, desarme y traslados | Importe total: $300000"

JSON correcto:
{{
  "cliente_nombre": "Jimena Benavides",
  "fecha_evento": "30/4/26",
  "tipo_evento": "Cumpleaños",
  "cantidad_invitados": null,
  "localidad": "Luján",
  "logistica_tipo": "Armado y Desarme",
  "acarreo_adicional": false,
  "lugares": [
    {{
      "nombre": "General",
      "productos": [
        {{"catalogo_key": "Living caña básico", "cantidad": 2, "notas": "incluye colchonería, almohadones decorativos y centros de mesa básicos"}}
      ]
    }}
  ]
}}

EJEMPLO 3 — Presupuesto con lugares distintos (Carpa y Casa):
Documento dice:
"CLIENTE: Anto Tilli | FECHA: 23/5/26 | LUGAR: Haras San Pablo | TIPO: Cumple nro 40 | INVITADOS: 35
C) Carpa: *3 juegos de livings estancia, *1 mesa ratona, *6 sillas jesuitas, *4 alfombras de yute, *12 velones, *4 tochos de ciprés
Livings: *2 cajones de luces, *5 alfombras con dibujos persas, *6 Puff de mimbre, *4 canastos con cortaderas, *16 velones
Otros: *Armado, desarme y traslados | Importe total C: $1704000"

JSON correcto:
{{
  "cliente_nombre": "Anto Tilli",
  "fecha_evento": "23/5/26",
  "tipo_evento": "Cumpleaños 40",
  "cantidad_invitados": 35,
  "localidad": "Haras San Pablo",
  "logistica_tipo": "Armado y Desarme",
  "acarreo_adicional": false,
  "lugares": [
    {{
      "nombre": "Carpa",
      "productos": [
        {{"catalogo_key": "Living Estancia", "cantidad": 3, "notas": ""}},
        {{"catalogo_key": "Mesa ratona", "cantidad": 1, "notas": ""}},
        {{"catalogo_key": "Silla jesuita", "cantidad": 6, "notas": ""}},
        {{"catalogo_key": "Alfombra de yute", "cantidad": 4, "notas": ""}},
        {{"catalogo_key": "Velón led", "cantidad": 12, "notas": ""}},
        {{"catalogo_key": "Tocho de ciprés", "cantidad": 4, "notas": ""}}
      ]
    }},
    {{
      "nombre": "Livings",
      "productos": [
        {{"catalogo_key": "Cajón de luces", "cantidad": 2, "notas": ""}},
        {{"catalogo_key": "Alfombra con dibujos persas", "cantidad": 5, "notas": ""}},
        {{"catalogo_key": "Puff mimbre", "cantidad": 6, "notas": ""}},
        {{"catalogo_key": "Canasto con follaje", "cantidad": 4, "notas": "con cortaderas"}},
        {{"catalogo_key": "Velón led", "cantidad": 16, "notas": ""}}
      ]
    }}
  ]
}}
---

Ahora analiza el chat y documentos que recibirás y devuelve el JSON siguiendo exactamente este formato.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analiza el siguiente chat y documentos adjuntos y extrae los datos del presupuesto:\n\n{full_context}"},
    ]

    api_keys = get_nvidia_keys()
    if not api_keys:
        return {"error": "No hay API keys de NVIDIA configuradas. Setea NVIDIA_API_KEY en .env"}

    last_error = None

    for i, api_key in enumerate(api_keys):
        print(f"Trying Nvidia API (Key {i+1}/{len(api_keys)}: {api_key[:12]}...)")
        try:
            response = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "moonshotai/kimi-k2.6",
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 4096,
                },
                timeout=90,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                # Strip markdown code fences if present
                if "```" in content:
                    parts = content.split("```")
                    for part in parts:
                        cleaned = part.strip()
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:].strip()
                        if cleaned.startswith("{"):
                            content = cleaned
                            break
                return json.loads(content.strip())
            else:
                last_error = f"Key {i+1} → HTTP {response.status_code}: {response.text[:200]}"
                print(last_error)
                continue
        except Exception as e:
            last_error = f"Exception on key {i+1}: {e}"
            print(last_error)
            continue

    return {"error": f"All API keys failed. Last error: {last_error}"}
