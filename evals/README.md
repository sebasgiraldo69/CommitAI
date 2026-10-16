# Evaluación de fase 0

`casos-fase-0.json` contiene 30 entradas sintéticas etiquetadas y resultados esperados; todavía no se ha ejecutado ningún proveedor. C01–C20 son desarrollo; C21–C30 quedan reservados para evaluación y no deben usarse como ejemplos dentro del prompt. Si se ajusta el prompt tras revisar errores del conjunto reservado, crear nuevos casos independientes para la evaluación final.

## Cómo interpretar las etiquetas

- Cada caso define texto, contexto, fecha de referencia y `evaluated_at` UTC. Inyectar este reloj al comprobar estados; no usar el día real de ejecución.
- `expected.count` es el número de acciones distintas esperadas. Emparejar candidatos por acción y responsable, no por posición en la lista.
- `title` y `condition` admiten paráfrasis fieles. Nombres, fechas, horas, prioridad, estado y faltantes se comparan exactamente; el orden de las listas de faltantes no importa.
- `ambiguous_fields` resume los campos esperados en `ambiguities`; no exige una frase exacta de explicación.
- `source_quote` debe ser un fragmento literal del texto y respaldar la acción. No se etiqueta una única cita porque hay varios fragmentos válidos.
- La descripción puede ser `null` o una paráfrasis sustentada. Se revisa que no añada información. La confianza solo se valida como número entre 0 y 1; no se exige un decimal específico.
- `priority_origin` debe ser `default` excepto en C27 y C28, donde es `explicit`. IDs y marcas de generación no se comparan literalmente.
- `is_past_due` se verifica en dominio/persistencia; no es un campo obligatorio del candidato de análisis.

## Casos complementarios de estado y validación

Usar zona `America/Bogota` y reloj `2026-10-15T17:00:00Z` salvo que se indique otro. Estos escenarios son especificaciones para pruebas de fase 2, no pruebas ya ejecutadas.

| ID | Preparación y acción | Resultado esperado |
| --- | --- | --- |
| S01 | Título válido, sin responsable ni fecha | `incomplete`; faltan ambos |
| S02 | Sin responsable, fecha 2026-10-14 | `incomplete`, `is_past_due=true` |
| S03 | Completo, fecha 2026-10-15, sin hora; reloj 2026-10-16T04:59:59Z | `pending` |
| S04 | Mismo registro; reloj 2026-10-16T05:00:00Z | `overdue` |
| S05 | Completo, fecha 2026-10-15, hora 12:00 | `overdue` al alcanzar el límite |
| S06 | Completar registro incompleto | `completed`; faltantes conservados |
| S07 | Registro completado con fecha pasada; editar título | Sigue `completed` |
| S08 | Descartar registro pendiente y avanzar reloj | Sigue `discarded` |
| S09 | Reabrir completado con datos completos y fecha pasada | `overdue` |
| S10 | Reabrir descartado sin fecha | `incomplete` |
| S11 | Completar responsable y fecha futura de un incompleto | `pending` |
| S12 | Solicitar `set_pending` sin responsable | `409 invalid_transition`; ningún cambio persistido |
| S13 | Título vacío al crear o editar | `422 validation_error`; ningún cambio persistido |
| S14 | Responsable y fecha conocidos, hora ambigua | `pending` si fecha futura; `due_time` señalado en faltantes |
| S15 | Repetir aceptación con misma clave y cuerpo | Mismos IDs, sin duplicados |
| S16 | Reutilizar clave con cuerpo distinto | `409 idempotency_conflict` |
| S17 | Cambiar datos de registro cerrado y reabrir en la misma solicitud | Estado calculado sobre datos nuevos |
| S18 | `completed` con fecha pasada y sin responsable | Sigue `completed`, faltante visible, `is_past_due=true` |

## Reporte futuro

Registrar versión del conjunto, proveedor, modelo, prompt, fecha, número de casos, aciertos, falsos positivos, omisiones y valores inventados. Medir precisión y cobertura por compromiso y exactitud de campos conocidos por separado. Revisar especialmente C01, C04, C05, C16, C25 y C30 para detectar invenciones.

Las métricas semánticas requieren ejecutar el proveedor y revisar correspondencias; que este JSON sea válido no certifica extracción correcta. No hay runner de evaluación implementado en fase 0.
