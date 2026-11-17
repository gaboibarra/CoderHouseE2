"""Mini-script asíncrono para probar OpenAI, Anthropic o ambos."""

import argparse
import asyncio
import logging

from chain import process_text

EJEMPLO = (
    "Un servicio de pagos desarrollado con FastAPI usa Redis para caché y "
    "PostgreSQL para persistencia. Desde las 10:00 registra errores HTTP 500 "
    "y saturación de conexiones; algunos pagos no se procesan."
)


async def ejecutar(proveedor: str, texto: str) -> None:
    print(f"\n=== PROVEEDOR: {proveedor.upper()} ===")
    try:
        resultado = await process_text(texto, proveedor)
        # model_dump_json garantiza salida JSON serializable y legible.
        print(resultado.model_dump_json(indent=2))
    except Exception as exc:
        logging.getLogger(__name__).error("Fallo controlado (%s): %s", proveedor, exc)
        print(f"No se pudo completar la extracción con {proveedor}.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-entrega 2: pipeline técnico LCEL")
    parser.add_argument("--provider", choices=["openai", "anthropic", "both"], default="both")
    parser.add_argument("--text", default=EJEMPLO, help="Párrafo técnico de entrada")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    proveedores = ["openai", "anthropic"] if args.provider == "both" else [args.provider]
    # Secuencial para facilitar la lectura de logs; cada solicitud usa .ainvoke().
    for proveedor in proveedores:
        await ejecutar(proveedor, args.text)


if __name__ == "__main__":
    asyncio.run(main())
