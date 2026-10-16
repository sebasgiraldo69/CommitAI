# Respaldo y recuperación de SQLite

Esta guía corresponde a la configuración local:
`DATABASE_PATH=data/commitai.db`.

Si se configuró otra ruta, sustituirla en los comandos.

## Crear un respaldo

1. Detener el servidor con Ctrl+C y esperar su cierre.
2. Cerrar cualquier otro proceso que esté escribiendo en la base.
3. Desde la raíz de CommitAI, ejecutar:

```powershell
New-Item -ItemType Directory -Path backups -Force | Out-Null

$backupStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupFile = Join-Path backups "commitai-$backupStamp.db"

Copy-Item -LiteralPath data/commitai.db -Destination $backupFile
Write-Output "Respaldo creado: $backupFile"
```

La copia con el servidor detenido corresponde al modo de SQLite utilizado
actualmente. Si se habilita WAL u otra estrategia de acceso, revisar el
procedimiento antes de copiar únicamente el archivo principal.

El respaldo contiene compromisos, fragmentos de conversaciones, claves de
idempotencia y registro de migraciones. No contiene la clave de API de `.env`.

Agregar esta línea a `.gitignore`:

```gitignore
backups/
```

## Verificar la integridad del respaldo

En la misma terminal, donde existe `$backupFile`, ejecutar:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3,sys; from pathlib import Path; p=Path(sys.argv[1]).resolve(); c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()" $backupFile
```

El resultado esperado es:

```text
ok
```

Esta comprobación valida la integridad de SQLite; no sustituye revisar
que los compromisos esperados estén presentes.

## Probar la restauración sin sobrescribir la base original

1. Mantener detenido el servidor.
2. Elegir un respaldo existente.
3. Copiarlo a un archivo nuevo dentro de `data`.

Ejemplo: reemplazar el nombre de respaldo por el real.

```powershell
$restoreSource = "backups/commitai-REEMPLAZAR.db"
$restoreStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$restoredFile = "data/commitai-restored-$restoreStamp.db"

Copy-Item -LiteralPath $restoreSource -Destination $restoredFile
Write-Output "Base restaurada: $restoredFile"
```

4. En `.env`, cambiar `DATABASE_PATH` por la ruta mostrada:

```dotenv
DATABASE_PATH=data/commitai-restored-FECHA.db
```

5. Si `DATABASE_PATH` también está definida en la terminal, esa variable
   tiene prioridad. Abrir una terminal sin esa configuración o ajustarla.
6. Iniciar el servidor y abrir el dashboard.
7. Verificar títulos, responsables, estados y cantidad de registros.

Para volver a la base original, detener el servidor y restaurar en `.env`:

```dotenv
DATABASE_PATH=data/commitai.db
```

Después, iniciar nuevamente.

Los cambios realizados sobre la base restaurada no se incorporan
automáticamente a la original.

## Migraciones

La aplicación registra las versiones aplicadas en `schema_migrations`.
Actualmente existe la migración inicial, versión 1.

Antes de futuras actualizaciones del esquema:

- Crear y verificar un respaldo.
- Probar la actualización sobre una copia.
- No modificar manualmente la tabla de versiones.
- Documentar cualquier incompatibilidad con respaldos anteriores.

## Estado de verificación

Procedimiento documentado. La copia, comprobación de integridad y
restauración deben ejecutarse antes de afirmar que la recuperación
ha sido validada.