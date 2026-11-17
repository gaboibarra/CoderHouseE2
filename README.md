# Pre-entrega 2 — Pipeline de extracción de entidades técnicas

Proyecto en **Python 3.12** que recibe texto libre de arquitectura o incidentes, extrae tecnologías, clasifica la criticidad y genera un resumen técnico **validado con Pydantic**. Usa **LangChain Expression Language (LCEL)** y permite cambiar entre **OpenAI** y **Anthropic** mediante la misma función `process_text()`.

## Arquitectura

```text
Texto libre
   ↓
ChatPromptTemplate ({texto})
   ↓
ChatOpenAI / ChatAnthropic
   ↓
.with_structured_output(ExtraccionTecnica, include_raw=True)
   ↓
validar_salida(): parsing_error + finish_reason/stop_reason + Pydantic
   ↓
ExtraccionTecnica (objeto Pydantic) → JSON

[LCEL completo].with_retry(stop_after_attempt=3)
```

**Nota:** `.with_retry()` rodea la cadena completa, incluido el validador. Si el modelo devuelve datos incompletos, un JSON imposible de parsear o un motivo de parada `length` / `max_tokens`, se vuelve a pedir una respuesta (hasta **tres intentos totales**). El `max_retries=1` adicional del SDK atiende fallas transitorias de transporte, por separado. No se reintentan por defecto errores de autenticación ni se garantiza que cualquier salida incorrecta pueda recuperarse.

## Estructura

- `schemas.py`: `ExtraccionTecnica` y enumeración `Criticidad`; validaciones Pydantic.
- `chain.py`: prompt, fábrica de modelos, cadena LCEL, verificación de salida, `.with_retry()` y `process_text()`.
- `main.py`: mini-script asíncrono para OpenAI, Anthropic o ambos.
- `tests/test_schemas.py`: validaciones correctas e incorrectas.
- `tests/test_chain.py`: salidas truncadas, JSON inválido y reintentos con modelos simulados.
- `.env.example`: plantilla de variables. **No subir `.env`.**
- `requirements.txt`: dependencias;

## Requisitos e instalación (Windows PowerShell)

1. Instalar Python 3.12 y entrar en la carpeta del proyecto.
2. Crear y activar un entorno virtual:

```powershell
py -3.12 -m venv .venv
```
<img width="695" height="28" alt="image" src="https://github.com/user-attachments/assets/123aef4d-d3dd-43ce-9bd2-7816862cbc94" />

```powershell
.\.venv\Scripts\Activate.ps1
```
<img width="700" height="17" alt="image" src="https://github.com/user-attachments/assets/edcee656-3655-41e0-9e3b-a56876b14a76" />

```powershell
python -m pip install -r requirements.txt
```
```powershell
python --version
```
<img width="697" height="27" alt="image" src="https://github.com/user-attachments/assets/051d6637-a196-4a0f-8ef7-8f30be3048ca" />

3. Crear `.env` desde `.env.example`:

```powershell
Copy-Item .env.example .env
```

4. Completar **las claves propias**, sin comillas, en `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=TU_CLAVE_OPENAI
ANTHROPIC_API_KEY=TU_CLAVE_ANTHROPIC
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-haiku-4-5
```

Los modelos deben estar habilitados en tus respectivas cuentas. Las llamadas reales a las APIs pueden generar cargos. Una cuenta de ChatGPT no equivale a crédito API.

## Ejecución

Probar **ambos** proveedores en modo asíncrono (secuencial para mostrar logs legibles):

```powershell
python main.py
```
<img width="642" height="257" alt="image" src="https://github.com/user-attachments/assets/62ae1344-97fa-47cc-9e8c-6a80f83b022c" />

Solo OpenAI o Anthropic:

```powershell
python main.py --provider openai
```
<img width="641" height="145" alt="image" src="https://github.com/user-attachments/assets/c79eb33e-1cd9-488d-a088-b3c10d375867" />


```powershell
python main.py --provider anthropic
```
<img width="641" height="158" alt="image" src="https://github.com/user-attachments/assets/25d051a3-5217-45b7-88a4-d8140b8e1aab" />

Texto personalizado (PowerShell):

```powershell
python main.py --provider openai --text "Servicio FastAPI con Redis y PostgreSQL: errores HTTP 500 afectan los pagos."
```

Uso desde otro programa:

```python
import asyncio
from chain import process_text

async def main():
    resultado = await process_text("Una API FastAPI con Redis presenta errores HTTP 500.", "openai")
    print(resultado.model_dump_json(indent=2))

asyncio.run(main())
```

### Ejemplo de JSON esperado

**Entrada:** `Un servicio de pagos desarrollado con FastAPI usa Redis y PostgreSQL. Hay errores HTTP 500 y pagos sin procesar.`

**Salida de ejemplo** (puede variar; no es una ejecución verificada de la API):

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "El servicio de pagos registra errores HTTP 500 que afectan el procesamiento de transacciones."
}
```
<img width="641" height="155" alt="image" src="https://github.com/user-attachments/assets/5262fbf1-82cf-4c31-b09b-5892d285b4dd" />



## Pruebas unitarias

```powershell
python -m pytest -q
```
<img width="644" height="44" alt="image" src="https://github.com/user-attachments/assets/71f797bb-dc2b-43fd-8cb9-7413eb80c78a" />




```powershell
python -m pytest -v
```
<img width="640" height="224" alt="image" src="https://github.com/user-attachments/assets/0925f2d5-de0b-438b-9373-1cbca2d75be2" />

Estas pruebas **no requieren claves API ni generan consumo**. Se usan respuestas simuladas para probar tres situaciones: (a) validación correcta, (b) respuesta inválida que se recupera al segundo intento y (c) fallas persistentes hasta agotar tres intentos.

### Prueba de estrés / texto ambiguo

```powershell
python main.py --provider openai --text "El sistema funciona raro desde ayer y hay problemas."
```

El esquema exige por lo menos una tecnología explícita. Este texto no indica ninguna. La instrucción prohíbe inventar, así que el resultado correcto puede ser un **error controlado tras agotar los reintentos**. No se debe interpretar como falla del programa. Podría diseñarse otro contrato que permita `tecnologias=[]`, pero aquí se aplica la restricción pedida como ejercicio.

## Resiliencia y logs

- `include_raw=True` permite inspeccionar tanto `parsed` como `parsing_error` y metadatos crudos.
- Se detectan `finish_reason="length"` (OpenAI) y `stop_reason="max_tokens"` (Anthropic) antes de aceptar el objeto.
- `Pydantic` valida tipos, campos faltantes, enum, duplicados y longitud mínima del resumen.
- Excepciones del parser/validador se reintentan mediante `.with_retry(stop_after_attempt=3)`.
- `logging` registra inicio, validación, problemas y resultado final, sin imprimir claves API.
- Fallos no recuperables (p. ej. credenciales inválidas) se muestran como errores controlados en `main.py`.

**Limitación:** los metadatos de finalización dependen del proveedor/versión del adaptador; si no están disponibles, la validación estructural sigue funcionando, pero no puede determinarse el truncamiento solo por esos metadatos. Structured output no garantiza exactitud semántica. Los reintentos pueden generar costos.

## Cómo encaja con la Pre-entrega 1

Se conserva el criterio de **selección de proveedor y asincronía**, pero en vez de llamar directamente a `AsyncOpenAI`/`AsyncAnthropic`, esta entrega utiliza `ChatOpenAI`/`ChatAnthropic`, las integraciones LangChain oficiales para LCEL. Es una **reutilización de arquitectura y configuración**, no una importación directa del código del primer proyecto.

## Referencias

- [LangChain OpenAI — structured output](https://reference.langchain.com/python/langchain-openai/langchain_openai/chat_models/base/ChatOpenAI/with_structured_output)
- [LangChain Anthropic — structured output](https://reference.langchain.com/python/langchain-anthropic/chat_models/ChatAnthropic/with_structured_output)
- [LCEL y Runnables](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable)
- [Pydantic](https://docs.pydantic.dev/latest/)
=======
# CoderHouseE2
>>>>>>> origin/main
