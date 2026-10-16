# Contratos de datos y API — v1

Estado: especificación de fase 0; endpoints aún no implementados. Reglas normativas en [reglas de negocio](reglas-negocio.md). JSON con nombres `snake_case`, fechas ISO `YYYY-MM-DD`, horas `HH:MM`, identificadores UUID y marcas de tiempo UTC con sufijo `Z`. Rechazar campos desconocidos en solicitudes para detectar errores del cliente.

## Entrada del análisis

`POST /api/analyses` devuelve `200` y no guarda compromisos.

```json
{
  "text": "Te envío la propuesta mañana.",
  "reference_date": "2026-10-15",
  "timezone": "America/Bogota",
  "participants": ["Jaime", "Ana"],
  "speaker": "Jaime",
  "addressee": "Ana",
  "source": {"kind": "text", "label": null, "external_id": null}
}
```

`text` y `reference_date` son obligatorios. `text`: 1 a 20 000 caracteres después de quitar espacios externos. `timezone` usa por defecto la configuración y debe ser una zona IANA válida. `participants` es una lista de nombres únicos (por defecto vacía); `speaker` y `addressee` son nombres opcionales, no identidades autenticadas. `source` por defecto es el objeto del ejemplo; `kind`: `text`, `email`, `meeting` o `other` describe procedencia de texto pegado, sin conectar cuentas. `label` y `external_id` son opcionales, máximo 500 caracteres cada uno.

## Candidato y campos editables

| Campo | Tipo y restricción |
| --- | --- |
| `title` | Texto no vacío, máximo 200 caracteres |
| `description` | Texto de hasta 2 000 caracteres o `null` |
| `responsible`, `counterparty` | Nombre de hasta 200 caracteres o `null` |
| `due_date` | Fecha real ISO o `null` |
| `due_time` | Hora de 24 horas o `null`; puede conocerse aunque falte fecha |
| `timezone` | Zona IANA válida |
| `priority` | `low`, `medium`, `high`; predeterminado `medium` |
| `condition` | Texto de hasta 1 000 caracteres o `null` |

Los campos nulos se representan explícitamente; las cadenas opcionales vacías se normalizan a `null`. Estos campos forman `values` tanto en la respuesta como al aceptar. Los candidatos agregan:

- `candidate_id`: UUID generado por el backend.
- `source_quote`: fragmento literal y continuo del texto original que sustenta la acción (máximo 20 000 caracteres).
- `confidence`: número entre 0 y 1, estimado por el modelo.
- `priority_origin`: `explicit` o `default`.
- `missing_information`: lista sin duplicados de `responsible`, `due_date`, `due_time`, recalculada por el servidor.
- `ambiguities`: lista de objetos `{field, reason, source_text}`, campos `responsible`, `due_date` o `due_time`. `reason` es una explicación legible; `source_text` es un fragmento literal.
- `status`: estado abierto calculado por el servidor, nunca `completed` o `discarded` en la extracción.

La respuesta es `{analysis_id, reference_date, timezone, source, candidates, analyzed_at}`. `candidates` puede ser `[]`; no se trata como error. `analysis_id` es UUID. El proveedor no decide IDs, marcas temporales ni estados definitivos.

## Aceptación y creación

`POST /api/commitments` recibe una cabecera obligatoria `Idempotency-Key` (UUID generado por el cliente para cada guardado) y:

```json
{
  "analysis_id": "d726f65d-1a89-4058-8392-b2957da42dc1",
  "reference_date": "2026-10-15",
  "source": {"kind": "text", "label": null, "external_id": null},
  "items": [
    {
      "candidate_id": "a0f44297-8cbe-47e5-acf1-2325b5559ac2",
      "values": {
        "title": "Enviar propuesta",
        "description": null,
        "responsible": "Jaime",
        "counterparty": "Ana",
        "due_date": "2026-10-16",
        "due_time": null,
        "timezone": "America/Bogota",
        "priority": "medium",
        "condition": null
      },
      "extraction": {
        "source_quote": "Te envío la propuesta mañana.",
        "confidence": 0.95,
        "priority_origin": "default",
        "ambiguities": []
      },
      "resolved_ambiguities": []
    }
  ]
}
```

`items` contiene exclusivamente candidatos aceptados (1 a 100, IDs únicos). El número de confianza del ejemplo es ilustrativo. La interfaz preserva `extraction`; `resolved_ambiguities` enumera campos que la persona aclaró explícitamente al revisar. El servidor recalcula faltantes y estado sobre los valores aprobados, excluyendo ambigüedades resueltas. Solo se puede resolver una ambigüedad presente; resolver una fecha con `null` no elimina el faltante de fecha.

El MVP local es sin sesión de análisis persistida: el cliente devuelve valores revisados y metadatos. El servidor valida el contrato, pero los IDs y citas reenviados no son evidencia autenticada de una respuesta del proveedor. No se usa la confianza ni la procedencia reenviada para autorizar acciones. La validación de cita contra el texto se hace durante el análisis; no se conserva toda la conversación para comprobarla después.

Crear todo el lote en una transacción o no crear nada. Respuesta inicial `201`: `{items: [Commitment]}`. Misma clave y mismo cuerpo normalizado: devolver `200` con la respuesta original y mismos IDs; misma clave con contenido diferente: `409 idempotency_conflict`. Persistir clave y resultado con la transacción. La idempotencia no elimina tareas similares creadas en guardados distintos.

## Compromiso persistido y lectura

`Commitment` contiene los campos de `values` y añade `id`, `analysis_id`, `candidate_id`, `reference_date`, `source`, `extraction`, `resolved_ambiguities`, `missing_information`, `status`, `is_past_due`, `created_at` y `updated_at`. El estado efectivo puede variar con el reloj sin modificar `updated_at`, que registra una edición explícita. El almacenamiento conserva el ciclo interno `open`/`completed`/`discarded`.

- `GET /api/commitments/{id}`: `200 Commitment` o `404`.
- `GET /api/commitments`: `200 {items, total, limit, offset, counts}`.
- Filtros opcionales: `status` (uno de los cinco estados) y `responsible` (coincidencia exacta ignorando mayúsculas).
- `limit`: 1–100, predeterminado 20; `offset`: entero no negativo, predeterminado 0.
- `sort`: `due_asc` (predeterminado), `due_desc`, `created_desc`. Fechas desconocidas al final; empates por ID. Orden temporal considerando zona y cierre del día si falta hora.
- `total` respeta todos los filtros. `counts` incluye los cinco estados con ceros cuando corresponda; respeta responsable, pero omite el filtro de estado y la paginación para alimentar las pestañas del dashboard. Calcular listado, total y contadores con el mismo instante de referencia.

## Edición y transiciones

`PATCH /api/commitments/{id}` recibe `{changes: {...}, action: ...}`. Ambos son opcionales, pero se requiere al menos uno no vacío.

`changes` admite los campos de `values` y `resolved_ambiguities`. Campo omitido conserva su valor; `null` elimina únicamente campos anulables. No permite modificar IDs, cita, confianza, origen ni marcas de tiempo.

`action` admite `complete`, `discard`, `reopen`, `set_pending`, `set_incomplete` y `set_overdue`. Aplicar primero cambios, luego acción, dentro de una única transacción. Sin acción, conservar el cierre o recalcular si está abierto. `set_*` solo procede cuando el estado abierto calculado coincide; si no, devolver `409 invalid_transition` sin aplicar cambios. Devolver `200 Commitment` al terminar.

## Errores comunes

Formato: `{error: {code, message, details}, request_id}`. `details` es una lista de `{field, message}` sin volcar el texto original ni secretos.

| HTTP | Códigos iniciales |
| --- | --- |
| 404 | `commitment_not_found` |
| 409 | `invalid_transition`, `idempotency_conflict` |
| 422 | `validation_error` (incluye fecha, zona o tamaño inválidos) |
| 502 | `provider_invalid_response`, `provider_refusal` |
| 503 | `ai_not_configured`, `provider_auth`, `provider_quota`, `provider_unavailable` |
| 504 | `provider_timeout` |

`GET /api/health` devuelve `200 {status: "ok"}` si el proceso responde; no llama al LLM ni certifica su disponibilidad. No exponer credenciales en ninguna respuesta.
