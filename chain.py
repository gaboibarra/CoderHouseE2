"""Pipeline LCEL con ambos proveedores, validación, logs y reintentos selectivos."""

import json
import logging
import os
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from schemas import ExtraccionTecnica

logger = logging.getLogger(__name__)


class SalidaReintentableError(ValueError):
    """Indica una salida ausente, inválida o incompleta que merece un nuevo intento."""


# El prompt es modular: {texto} se reemplaza mediante LangChain, no con f-strings.
PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Sos un analista de incidentes y arquitecturas de software.
Extraé información técnica exclusivamente del texto proporcionado.
Reglas:
- tecnologias: solo nombres de tecnologías explícitamente presentes; sin duplicados.
- nivel_de_criticidad: alta si hay indisponibilidad, pérdida de datos o servicios críticos afectados;
  media para degradación, errores aislados o riesgos moderados;
  baja para una descripción sin incidentes ni impacto significativo.
- resumen_tecnico: español, conciso, fiel a los hechos, mínimo 20 caracteres.
- No inventes tecnologías ni problemas. Si no hay ninguna tecnología identificable,
  no fabriques una para satisfacer el esquema: la validación podrá fallar.
- Ajustá la respuesta al esquema de salida solicitado."""),
    ("human", "Texto a analizar:\n<texto>\n{texto}\n</texto>"),
])


def crear_modelo(proveedor: str | None = None):
    """Fábrica: selecciona OpenAI o Anthropic sin modificar el resto de la cadena."""
    load_dotenv()
    elegido = (proveedor or os.getenv("LLM_PROVIDER", "openai")).strip().lower()
    if elegido == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Falta OPENAI_API_KEY en el archivo .env")
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            max_tokens=600,
            timeout=40,
            max_retries=1,  # Reintentos del SDK para errores de transporte.
        )
    if elegido == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Falta ANTHROPIC_API_KEY en el archivo .env")
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=600,
            timeout=40,
            max_retries=1,
        )
    raise ValueError("LLM_PROVIDER debe ser 'openai' o 'anthropic'")


def validar_salida(salida: Any) -> ExtraccionTecnica:
    """Inspecciona resultado crudo, finish_reason y Pydantic antes de aceptarlo.

    include_raw=True devuelve un dict con raw, parsed y parsing_error. Si solo
    verificáramos parsed, una respuesta truncada podría pasar inadvertida.
    """
    if not isinstance(salida, Mapping):
        raise SalidaReintentableError("La salida estructurada no tiene el formato esperado")

    raw = salida.get("raw")
    if isinstance(raw, BaseMessage):
        metadata = raw.response_metadata or {}
        # OpenAI suele usar finish_reason='length'; Anthropic stop_reason='max_tokens'.
        # Algunos adaptadores devuelven estos valores en generation_info/metadata.
        motivo = metadata.get("finish_reason") or metadata.get("stop_reason")
        if motivo in {"length", "max_tokens"}:
            logger.warning("Salida truncada detectada (motivo=%s). Se reintentará.", motivo)
            raise SalidaReintentableError(f"El modelo truncó la salida: {motivo}")

    error = salida.get("parsing_error")
    if error is not None:
        logger.warning("Error de parsing/validación: %s. Se reintentará.", error)
        raise SalidaReintentableError("No se pudo interpretar el JSON del LLM") from error

    parsed = salida.get("parsed")
    if parsed is None:
        logger.warning("El modelo no entregó un objeto válido. Se reintentará.")
        raise SalidaReintentableError("La respuesta estructurada está ausente")

    try:
        # Algunas versiones devuelven una instancia Pydantic y otras un dict.
        objeto = ExtraccionTecnica.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("Falló la validación Pydantic: %s. Se reintentará.", exc)
        raise SalidaReintentableError("El objeto no cumple el esquema") from exc

    logger.info("Validación OK: %d tecnologías, criticidad=%s",
                len(objeto.tecnologias), objeto.nivel_de_criticidad.value)
    return objeto


def construir_cadena(modelo=None):
    """LCEL: prompt | modelo estructurado | verificador, con reintento total.

    Aplicar with_retry al FINAL es crucial: repetir únicamente el modelo
    no cubriría errores detectados después por validar_salida.
    """
    modelo = modelo if modelo is not None else crear_modelo()
    estructurado = modelo.with_structured_output(ExtraccionTecnica, include_raw=True)
    cadena = PROMPT | estructurado | RunnableLambda(validar_salida)
    return cadena.with_retry(
        retry_if_exception_type=(SalidaReintentableError, OutputParserException, ValidationError, json.JSONDecodeError),
        wait_exponential_jitter=True,
        stop_after_attempt=3,  # 1 intento inicial + 2 reintentos.
    )


async def process_text(text: str, proveedor: str | None = None) -> ExtraccionTecnica:
    """Punto de entrada asíncrono: recibe texto libre y entrega un Pydantic validado."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("El texto de entrada no puede estar vacío")
    if len(text) > 20_000:
        raise ValueError("El texto de entrada no puede superar 20.000 caracteres")

    logger.info("Iniciando extracción (proveedor=%s, caracteres=%d)",
                proveedor or os.getenv("LLM_PROVIDER", "openai"), len(text))
    cadena = construir_cadena(crear_modelo(proveedor))
    try:
        resultado = await cadena.ainvoke({"texto": text.strip()})
    except (SalidaReintentableError, OutputParserException, ValidationError, json.JSONDecodeError):
        logger.error("Extracción inválida después de agotar los intentos")
        raise
    logger.info("Extracción finalizada correctamente")
    return resultado
