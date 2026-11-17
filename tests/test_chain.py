"""Pruebas del parser y del retry con modelo falso: sin llamadas a las APIs."""
import asyncio
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from chain import SalidaReintentableError, construir_cadena, validar_salida
from schemas import ExtraccionTecnica


def datos():
    return {
        "tecnologias": ["FastAPI", "Redis"],
        "nivel_de_criticidad": "alta",
        "resumen_tecnico": "Hay errores HTTP 500 que afectan las transacciones.",
    }


def salida(parsed=None, reason="stop", error=None):
    return {
        "raw": AIMessage(content="", response_metadata={"finish_reason": reason}),
        "parsed": parsed,
        "parsing_error": error,
    }


def test_valida_resultado_correcto():
    assert isinstance(validar_salida(salida(datos())), ExtraccionTecnica)


def test_detecta_truncamiento_openai():
    with pytest.raises(SalidaReintentableError, match="truncó"):
        validar_salida(salida(datos(), reason="length"))


def test_detecta_truncamiento_anthropic():
    respuesta = salida(datos())
    respuesta["raw"] = AIMessage(content="", response_metadata={"stop_reason": "max_tokens"})
    with pytest.raises(SalidaReintentableError, match="truncó"):
        validar_salida(respuesta)


def test_detecta_json_invalido():
    with pytest.raises(SalidaReintentableError):
        validar_salida(salida(error=ValueError("JSON inválido")))


def test_reintenta_ante_salida_invalida_y_luego_valida():
    llamadas = {"n": 0}

    async def simular_modelo(_):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return salida(error=ValueError("JSON incompleto"))
        return salida(datos())

    modelo = Mock()
    modelo.with_structured_output.return_value = RunnableLambda(simular_modelo)
    cadena = construir_cadena(modelo)
    resultado = asyncio.run(cadena.ainvoke({"texto": "FastAPI y Redis fallan"}))
    assert resultado.nivel_de_criticidad.value == "alta"
    assert llamadas["n"] == 2


def test_agota_tres_intentos():
    llamadas = {"n": 0}

    async def simular_modelo(_):
        llamadas["n"] += 1
        return salida(error=ValueError("JSON inválido"))

    modelo = Mock()
    modelo.with_structured_output.return_value = RunnableLambda(simular_modelo)
    cadena = construir_cadena(modelo)
    with pytest.raises(SalidaReintentableError):
        asyncio.run(cadena.ainvoke({"texto": "Redis falló"}))
    assert llamadas["n"] == 3
