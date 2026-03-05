import json
import re
from io import BytesIO

from google import genai
from PIL import Image

PROMPT = """Analiza esta imagen de una página de directorio empresarial de una revista española.

EXTRAE SOLO los bloques de directorio empresarial: listados estructurados que contienen
datos de contacto como dirección, teléfono, email, web o actividad.

NO EXTRAIGAS:
- Perfiles narrativos (secciones con foto grande, nombre destacado y citas textuales largas)
- Títulos de sección, números de página o publicidad

Para cada empresa/organización encontrada, devuelve un objeto JSON.
Si una entrada lista múltiples personas con cargos distintos, crea UNA FILA POR PERSONA
repitiendo los datos de la empresa en cada fila.

Formato de respuesta — un array JSON:
[
  {
    "empresa": "Nombre de la empresa u organización",
    "cargo": "Cargo (Presidente, Director general, CEO, etc.)",
    "nombre": "Nombre completo de la persona",
    "direccion": "Dirección postal completa",
    "codigo_postal": "Código postal",
    "ciudad": "Ciudad",
    "telefono": "Teléfono(s) de contacto",
    "email": "Dirección de email",
    "web": "Página web",
    "actividad": "Descripción de la actividad empresarial",
    "seccion": "Sección del directorio visible en la página (ej: Transporte y logística)"
  }
]

REGLAS:
- Si un dato no aparece en la imagen, usa cadena vacía ""
- Extrae TODOS los bloques de directorio visibles en la página
- No inventes datos que no estén en la imagen
- Responde ÚNICAMENTE con el array JSON, sin texto adicional ni marcadores de código"""


def extract_directory(
    image: Image.Image,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> list[dict]:
    """Envía la imagen a Gemini y devuelve una lista de diccionarios con los datos extraídos."""
    client = genai.Client(api_key=api_key)

    buf = BytesIO()
    image.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    response = client.models.generate_content(
        model=model_name,
        contents=[
            PROMPT,
            genai.types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ],
        config=genai.types.GenerateContentConfig(temperature=0.1),
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)
    if not isinstance(data, list):
        data = [data]

    return data
