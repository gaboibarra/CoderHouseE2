# Guía de estudio — Pre-entrega 2

## Orden de lectura

1. **schemas.py:** contrato. `Enum` evita criticidades arbitrarias; `BaseModel` valida; `Field` define restricciones; `field_validator` normaliza y rechaza duplicados.
2. **chain.py / PROMPT:** `ChatPromptTemplate.from_messages` genera mensajes system/human con la variable `{texto}`. No interpolamos f-strings. El texto se trata como datos, no como órdenes.
3. **crear_modelo:** la fábrica selecciona un adaptador LangChain oficial (OpenAI o Anthropic) y configura parámetros.
4. **construir_cadena:** LCEL encadena `PROMPT | modelo.with_structured_output(...) | RunnableLambda(validar_salida)`. El operador `|` combina Runnables; no es un OR lógico.
5. **validar_salida:** revisa los metadatos del mensaje crudo para detectar truncamiento; rechaza `parsing_error` y `parsed=None`; revalida los campos mediante Pydantic.
6. **with_retry:** envolver TODA la cadena es crucial, pues repetir solo el LLM no reintenta errores de validación posteriores.
7. **process_text:** valida texto de entrada y ejecuta `await cadena.ainvoke({"texto": text})`. La función devuelve un objeto Pydantic, no un diccionario anidado sin validar.
8. **main.py:** `asyncio.run(main())` administra el event loop. Se prueban ambos proveedores, uno a la vez, y se convierte el objeto a JSON con `model_dump_json()`.
9. **tests:** pruebas sin red con respuestas simuladas. Conviene romper datos a propósito y mirar por qué falla cada prueba.

## Preguntas para defender el código

- ¿Por qué `with_structured_output` es preferible a pedir “devolveme JSON” sin validación?
- ¿Para qué sirve `include_raw=True` si el resultado final es Pydantic?
- ¿Qué diferencia hay entre `async def` y `await`?
- ¿Qué hace `stop_after_attempt=3` exactamente?
- ¿Por qué un texto sin tecnologías no puede producir un resultado válido con nuestro esquema?
- ¿Qué riesgos tienen los reintentos: latencia, costo, respuestas no deterministas?
- ¿Por qué un sistema puede producir JSON válido y aun así describir hechos incorrectos?

## Extensión opcional

Crear una política que permita lista vacía cuando el texto no menciona tecnologías, en lugar de reintentar inevitablemente. También se puede agregar un `request_id` para correlacionar logs sin registrar el contenido sensible.
