"""Contrato de salida del pipeline. Se valida ANTES de entregar datos al consumidor."""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Criticidad(str, Enum):
    """Solo se permiten estos tres niveles, escritos en minúsculas."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class ExtraccionTecnica(BaseModel):
    """Salida obligatoria de la extracción. No se admiten campos adicionales."""

    model_config = ConfigDict(extra="forbid")

    tecnologias: list[str] = Field(
    default_factory=list,
    description=(
        "Lista de tecnologías explícitamente mencionadas. "
        "Si no se identifica ninguna, devolver una lista vacía."
        )
    )

    nivel_de_criticidad: Criticidad = Field(
        ..., description="baja, media o alta de acuerdo con el impacto descrito."
    )
    resumen_tecnico: str = Field(
        ..., min_length=20,
        description="Resumen técnico en español, fiel al texto y de al menos 20 caracteres."
    )

    @field_validator("tecnologias")
    @classmethod
    def validar_tecnologias(cls, valores: list[str]) -> list[str]:
        """Evita nombres vacíos, valores sin texto y duplicados (sin distinguir mayúsculas)."""
        resultado: list[str] = []
        vistos: set[str] = set()
        for tecnologia in valores:
            if not isinstance(tecnologia, str) or not tecnologia.strip():
                raise ValueError("Cada tecnología debe ser un texto no vacío")
            nombre = tecnologia.strip()
            if nombre.casefold() in vistos:
                raise ValueError(f"Tecnología duplicada: {nombre}")
            vistos.add(nombre.casefold())
            resultado.append(nombre)
        return resultado

    @field_validator("resumen_tecnico")
    @classmethod
    def validar_resumen(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < 20:
            raise ValueError("El resumen debe tener al menos 20 caracteres útiles")
        return limpio
