# Reglas de negocio — fase 0

Estado: reglas aceptadas por el usuario en la conversación. Este documento resuelve las decisiones pendientes del análisis inicial. Los detalles operativos precisan esas reglas para su implementación.

## Extracción y revisión

- Extraer cero, uno o varios compromisos. Una intención de acción pendiente o una solicitud explícita puede ser candidata; una negación, tarea ya realizada o hipótesis aislada no crea una tarea nueva.
- Cada candidato debe representar una acción independiente. Repeticiones explícitas de la misma acción dentro del texto se unifican; no unir acciones diferentes por compartir responsable o fecha.
- Nunca inventar responsables, contrapartes, fechas, horas o detalles del título. Lo desconocido es `null`.
- Identificar al hablante mediante contexto explícito o etiquetas del texto. Una lista de participantes por sí sola no identifica quién dice “yo”. La contraparte es el destinatario de la acción, no necesariamente su responsable.
- El título es obligatorio y resume fielmente la acción. La descripción añade contexto sustentado; puede ser `null`.
- Prioridad permitida: `low`, `medium`, `high`. Usar `medium` si no hay indicación; marcar que es un valor predeterminado. Una fecha cercana no implica automáticamente prioridad alta.
- La confianza está entre 0 y 1 y es una estimación de extracción, no una probabilidad validada ni autorización para guardar.
- Mostrar siempre los candidatos antes de guardar. Permitir editar, aceptar o descartar cada uno. Se pueden aceptar incompletos.
- Descartar un candidato no crea un registro. Descartar un compromiso ya guardado conserva su registro con estado `discarded`.
- Guardar la cita original y metadatos del origen, no la conversación completa por defecto. La edición humana no altera la cita original ni convierte la confianza original en una nueva puntuación.

## Fechas y faltantes

- La solicitud de análisis incluye fecha local de referencia; la interfaz propone una fecha y permite corregirla para conversaciones antiguas. La zona horaria inicial es `America/Bogota`, configurable.
- “Mañana” se resuelve respecto a esa referencia. Para un día de semana sin otra indicación se usa la siguiente ocurrencia estrictamente posterior; si coincide con el día de referencia, se deja ambiguo para revisión. Esta convención debe mostrarse en la ayuda de la interfaz.
- “El 15” sin mes o “a las 4” sin franja se dejan sin resolver. Una hora explícita como `16:00` o “4 de la tarde” sí se convierte a formato de 24 horas.
- Una fecha explícita pasada se conserva; no se mueve al siguiente mes o año para que parezca futura. Una fecha imposible queda sin resolver y se señala para revisión.
- Una fecha sin hora es válida. Vence al comenzar el día siguiente en su zona local; hasta ese instante no está vencida. Con hora explícita vence cuando el reloj alcanza esa hora.
- Los estados usan el instante actual del servidor; la extracción de fechas relativas usa la referencia de la conversación. Son relojes conceptualmente distintos.
- `missing_information` contiene campos obligatorios ausentes (`responsible`, `due_date`) y campos explícitamente solicitados pero ambiguos (`due_time` si el texto menciona una hora irresoluble). La ausencia de una hora no mencionada no es faltante.
- Para completitud se requieren título, responsable y fecha. Una hora ambigua se señala para revisión pero no convierte por sí sola un compromiso en `incomplete`, porque la hora es opcional.
- “Cuando llegue el producto” se conserva en `condition`; sin fecha el compromiso queda `incomplete`. El MVP no detecta automáticamente que esa condición se cumplió.

## Estados

El ciclo persistido es `open`, `completed` o `discarded`, como detalle interno. El estado público se calcula con estas reglas, en este orden:

1. Si está cerrado, devolver `completed` o `discarded` sin reclasificar por tiempo o faltantes.
2. Si falta responsable o fecha, devolver `incomplete`.
3. Si su límite temporal se alcanzó, devolver `overdue`.
4. En otro caso, devolver `pending`.

El título vacío impide guardar. `is_past_due` informa por separado si una fecha conocida venció, incluso para un registro incompleto o cerrado; no significa por sí solo que su estado sea `overdue`.

| Acción | Origen permitido | Resultado |
| --- | --- | --- |
| Completar | Cualquier estado | `completed`, incluso si faltan datos |
| Descartar | Cualquier estado | `discarded` |
| Reabrir | Cualquier estado | Recalcular `incomplete`, `overdue` o `pending` |
| Editar campos | Cualquier estado | Recalcular si está abierto; conservar cierre si está cerrado |
| Solicitar un estado abierto concreto | Cualquier estado | Reabrir solo si el estado calculado coincide; de lo contrario, rechazar toda la operación |

Repetir completar o descartar el mismo estado es una operación válida. Completar un descartado o descartar un completado cambia el cierre por acción explícita del usuario. Un cierre no exige inventar los datos que faltaban.

## Casos de referencia

Los seis ejemplos originales están representados en `evals/casos-fase-0.json`. La propuesta sin hablante no recibe el nombre “Jaime”, la palabra “actualizada” ni una hora inventada. Los casos de estado usan reloj fijo para evitar que el resultado cambie según el día de ejecución.

## Decisiones técnicas iniciales

Para implementar se adopta la base prevista: FastAPI y Pydantic; SQLite con repositorios y migraciones; frontend HTML/CSS/JavaScript modular; configuración central por entorno. Son elecciones de implementación revisables y no implican que ya exista código ejecutable. El proveedor y modelo se seleccionarán en fase 3. No se requiere Docker ni microservicios para empezar.
