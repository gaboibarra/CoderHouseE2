"""Pruebas unitarias sin API keys: ejecutarlas no consume tokens."""
import pytest
from pydantic import ValidationError
from schemas import Criticidad, ExtraccionTecnica


def valido():
    return {
        "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
        "nivel_de_criticidad": "alta",
        "resumen_tecnico": "El servicio de pagos registra fallos de conectividad.",
    }


def test_valido():
    dato = ExtraccionTecnica.model_validate(valido())
    assert dato.nivel_de_criticidad == Criticidad.ALTA


def test_lista_vacia():
    dato = valido(); dato["tecnologias"] = []
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_tecnologia_sin_nombre():
    dato = valido(); dato["tecnologias"] = [" "]
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_duplicados():
    dato = valido(); dato["tecnologias"] = ["Redis", "redis"]
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_criticidad_invalida():
    dato = valido(); dato["nivel_de_criticidad"] = "urgente"
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_resumen_corto():
    dato = valido(); dato["resumen_tecnico"] = "Error"
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_campo_faltante():
    dato = valido(); del dato["resumen_tecnico"]
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)


def test_campo_extra():
    dato = valido(); dato["inventado"] = "no"
    with pytest.raises(ValidationError):
        ExtraccionTecnica.model_validate(dato)
