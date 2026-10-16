# CommitAI: análisis inicial

Fecha: 2026-10-15. Estado: requisitos documentados; implementación no iniciada. Las propuestas de este documento no sustituyen el prompt original ni representan decisiones ya aprobadas.

## Objetivo y alcance

Transformar texto en compromisos revisables y seguir los aprobados hasta su cierre. El flujo del MVP es: ingresar texto → extraer candidatos con un LLM → validar → revisar y corregir → aceptar o descartar → guardar los aprobados → consultar y actualizar el dashboard.

La entrada inicial es texto pegado, incluso si procede de un correo o reunión. La conexión automática a Gmail, Calendar, WhatsApp, transcripciones, recordatorios y cuentas de múltiples usuarios corresponde a una etapa posterior. Detectar “agéndame” no implica crear un evento externo en el MVP.

## Referencia arquitectónica verificada

Se encontró SpendWiseAI en `../Proyecto`. Se revisaron el README, las dependencias y fragmentos de `main.py`, `models.py`, `database.py`, `ai_provider.py` y `docs/arquitectura.md`, además del listado de archivos. No se ejecutó el proyecto ni sus pruebas.

| Evidencia local | Patrón aprovechable |
| --- | --- |
| `main.py`: FastAPI, rutas `/api`, archivos estáticos y tratamiento de errores | API REST con errores consistentes; separar las rutas del arranque |
| `web/`: HTML, CSS y JavaScript | Interfaz separada del código del servidor |
| `models.py`: esquemas Pydantic | Contratos explícitos y validación de entradas y salidas |
| `database.py`: SQLite, conexión por operación, claves foráneas | Persistencia local detrás de repositorios |
| `ai_provider.py`: adaptador del proveedor, salida estructurada y tiempos de espera | Transporte de IA aislado de las reglas de negocio |
| `main.py` y `ai_provider.py`: variables de entorno y errores de proveedor | Configuración centralizada y diagnósticos sin contenido sensible |
| `tests/`, `evals/`, `docs/` y README | Pruebas, evaluación de extracción y documentación |

El README y el código consultado utilizan un adaptador OpenAI; `docs/arquitectura.md` describe Gemini y archivos que no aparecen en el listado actual. Esa documentación es histórica y no demuestra que su cola asíncrona, perfiles o estructura sigan implementados. La configuración actual está distribuida entre módulos: centralizarla sería una mejora. No se encontró configuración Docker en la exploración realizada.

Se propone reutilizar estos patrones mediante una implementación propia para compromisos. No copiar modelos, prompts, cálculos, categorías, presupuestos ni datos financieros. No se ha copiado código del proyecto anterior.

## Organización propuesta

Mantener una aplicación modular, sin exigir microservicios. Como punto de partida, FastAPI, Pydantic, SQLite y una interfaz sencilla siguen el enfoque observado; la selección definitiva del stack y del proveedor queda pendiente.

```text
CommitAI/
  backend/
    app/
      main.py
      api/routes/          # análisis y compromisos
      core/                # configuración, errores y logging
      schemas/             # contratos de API y extracción
      domain/              # reglas de fechas, completitud y estados
      services/            # casos de uso y coordinación
      ai/                  # proveedor, prompts y validación de salida
      repositories/        # acceso a datos
      db/                  # conexión, esquema y migraciones
    tests/
  frontend/                # ingreso, revisión y dashboard
  evals/                   # ejemplos etiquetados y calidad de extracción
  docs/
  .env.example
  .gitignore
  README.md
```

Este árbol es una propuesta; únicamente se han creado documentos. Docker/Compose se evaluará según las necesidades de ejecución. Los módulos de integración futuros deben consumir los mismos casos de uso, sin introducir dependencias de Gmail o WhatsApp en las reglas del dominio.

## Contrato de datos propuesto

Cada extracción devuelve una lista, que puede estar vacía si no hay compromisos. Cada candidato incluye `title`, `description`, `responsible`, `counterparty`, `due_date`, `due_time`, `priority`, `status`, `confidence`, `missing_information` y contexto/origen. Se propone agregar `source_quote` para justificar lo extraído, zona horaria y una condición de activación opcional para compromisos como “cuando llegue el producto”. Los registros persistidos necesitan además identificador y fechas de creación y actualización.

La entrada debería permitir fecha de referencia de la conversación, zona horaria y participantes. Los campos desconocidos deben ser `null`; no se deben inventar responsables, fechas ni horas. La confianza del modelo es orientativa y debe evaluarse con ejemplos etiquetados; no garantiza exactitud.

El ejemplo de “Te envío la propuesta mañana” no permite deducir por sí solo “Jaime”, “actualizada” ni “15:00”. La salida ilustrativa necesita contexto adicional para justificar esos valores. “Mañana” solo corresponde a 2026-10-16 si la fecha local de referencia es 2026-10-15.

## Reglas y decisiones pendientes

- **Fechas relativas:** resolverlas usando la fecha del mensaje o una referencia proporcionada, no siempre la fecha de ejecución. Proponer `America/Bogota` como valor local configurable.
- **Ambigüedad temporal:** “el 15” no especifica mes y “a las 4” puede requerir aclarar mañana o tarde. Conservar la expresión original y señalar la duda.
- **Responsables:** “yo”, “te” y “tenemos” requieren identificar hablante y destinatario. Separar responsable de contraparte.
- **Completitud:** proponer título, responsable y fecha como mínimos para compromisos con vencimiento. La hora no debería ser obligatoria para tareas de día completo. Definir cómo se tratan compromisos condicionados a un evento sin fecha conocida.
- **Estados:** distinguir revisión previa de estado del compromiso. Los candidatos descartados antes de aceptar no se guardarían como compromisos; `discarded` puede aplicarse a un compromiso previamente guardado. Confirmar si se necesita historial de descartes de la revisión.
- **Vencimiento:** calcularlo de forma determinista; definir la hora de corte cuando solo existe fecha y la precedencia entre `incomplete` y `overdue`. No reclasificar automáticamente registros `completed` o `discarded` como vencidos.
- **Cambios manuales:** establecer transiciones y validaciones para compatibilizar la edición manual con el cálculo automático de completitud y vencimiento.
- **Prioridad:** definir valores permitidos y si `medium` es un valor por defecto explícito cuando el texto no indica urgencia.
- **Persistencia:** evitar duplicados por reenvío de una aceptación y conservar el registro tras reiniciar. Decidir cuánto contexto original se almacena.

## API inicial propuesta

| Operación | Propósito |
| --- | --- |
| `POST /api/analyses` | Analizar texto y devolver candidatos sin guardarlos como compromisos |
| `POST /api/commitments` | Validar y guardar los candidatos aceptados y editados |
| `GET /api/commitments` | Listar y filtrar el dashboard |
| `GET /api/commitments/{id}` | Consultar un compromiso |
| `PATCH /api/commitments/{id}` | Editar campos o cambiar estado con validación |

El proveedor propone información; el backend valida estructura y reglas. La persistencia ocurre después de la aceptación del usuario. Los errores del proveedor deben permitir reintentar conservando el texto y sin guardar resultados parciales. Los logs deberían registrar identificadores, duración y códigos de error, evitando claves y conversaciones completas.

## Criterios de aceptación y desarrollo

1. Un texto con varios compromisos genera candidatos separados; un texto sin compromisos devuelve una lista vacía.
2. La interfaz permite editar, aceptar y descartar antes de persistir; solo se guardan los aprobados, incluidos los incompletos que el usuario acepte.
3. El ejemplo “Tenemos que revisar el contrato” conserva responsable y fecha como `null` y los señala como faltantes.
4. Las fechas relativas se prueban con una referencia fija y una zona horaria; las ambiguas no se resuelven inventando datos.
5. El dashboard muestra los cinco estados, permite actualizaciones válidas y conserva los datos después de reiniciar.
6. Las pruebas cubren reglas temporales y estados, persistencia y API; las evaluaciones de IA incluyen negaciones, citas, duplicados, varios participantes y compromisos condicionales. Las pruebas con proveedor simulado se distinguen de las evaluaciones reales.
7. El README final explica configuración, instalación, ejecución y validación; `.env.example` contiene solo valores de ejemplo.

Orden sugerido: acordar contrato y reglas → preparar estructura y configuración → implementar extracción y revisión → persistencia y dashboard → validar casos y documentar ejecución. Las integraciones automáticas permanecen fuera de esta primera entrega.
