# CLAUDE.md

Este archivo proporciona orientación a Claude Code (claude.ai/code) al trabajar con el código en este repositorio.

# Formas de usos

Quiero que pienses este proyecto como un ingeniero de sorfware altamente calificado, tu tarea es asegurarte de que el procesamiento de los datos es 100% correcto sin perdidas o archivos saltados sin procesar. Es muy importante que ningun registro o dato se pieda porque depende la vida de una persona. 

## Resumen del proyecto

Este es un sistema de procesamiento por lotes en Python para las estaciones de prueba de manufactura de Mirgor/Motrex. Lee archivos de registro CSV desde las estaciones de prueba, analiza resultados de pruebas individuales, elimina duplicados contra una base de datos MySQL e inserta registros de forma masiva. Está diseñado para ejecutarse como tarea programada o como ejecutable de Windows.

## Ejecución de la aplicación

```bash
# Instalar dependencias (usar un virtualenv)
pip install -r requirements.txt

# Ejecutar en modo desarrollo
python main.py
```

Antes de ejecutar, configure los archivos `.ini`/`.cfg`:
- `Configuraciones.cfg` — nombre de la estación, planta, token de acceso, `logs_path` y `Modo_Dev`
- `Parametros_DB.ini` — host, usuario, contraseña y base de datos de MySQL
- `hostname.ini` — mapea nombres de estación a hostnames a monitorear
- `medios.txt` — lista de nombres válidos de estaciones de producción

## Construcción del ejecutable para Windows

```bash
python setup.py build
# Salida: build/exe.*/BinasControl.exe
```

## Arquitectura

### Flujo de datos

1. **`main.py`** — Orquestador. Recorre los directorios de `logs_path`, filtra archivos CSV por hostname y fecha, y coordina todo el flujo.
2. **`Configuraciones.py`** — Lee `Configuraciones.cfg` y `Parametros_DB.ini` usando `configparser`.
3. **`ConectorDB.py`** — Crea y devuelve una conexión PyMySQL.
4. **`CapturarDatos.py`** — Analiza archivos de registro CSV crudos; extrae campos del encabezado y bloques `#TEST...#END` en listas en memoria de diccionarios (`registros` y `tests`).
5. **`ConsultasSQL.py`** — Todas las operaciones con la base de datos: prefetch de los últimos registros por hostname, deduplicación, inserciones por lotes de `registros` (30K filas/paquete), y luego `serialtest` (50K filas/paquete) con mapeo de claves foráneas mediante `cursor.lastrowid`.

### Esquema de la base de datos (MySQL)

Dos tablas principales en `testingdb_qa`:
- **`registros`** — una fila por sesión de prueba de placa (17 campos, PK autoincremental)
- **`serialtest`** — una fila por cada paso de prueba individual, con FK hacia `registros`

Los archivos de esquema están en `SQL_DB/TestingDB_QA/`.

### Decisiones de diseño clave

- **Solo en memoria**: No se escriben archivos CSV intermedios; todos los datos residen en listas de Python hasta la inserción en la base de datos.
- **Consulta única de deduplicación**: Una consulta SQL optimizada obtiene todos los registros existentes en rango de fechas en una sola query, filtrando en memoria.
- **Inserciones por lotes**: `executemany` en fragmentos de 30K (registros) y 50K (tests) evita saturar la memoria.
- **Mapeo de IDs real**: Antes de insertar cada batch se hace `SELECT MAX(idregistros)`, luego del commit se hace `SELECT idregistros > max_id_before` para obtener los IDs reales asignados (más seguro que asumir secuencialidad con `lastrowid`).
- **`Modo_Dev = TRUE`** en `Configuraciones.cfg` habilita el comportamiento de desarrollo/pruebas.

## Notas de configuración

- Los nombres de estación en `hostname.ini` deben coincidir con las entradas en `medios.txt`.
- El directorio `logs_path` se recorre recursivamente; los archivos CSV se filtran por patrones de nombre que coinciden con el hostname configurado.
- El `TokenAcceso` en `Configuraciones.cfg` debe coincidir con un token válido en la tabla `token` de la base de datos.

---

## ANÁLISIS DE INTEGRIDAD DE DATOS — BUGS CRÍTICOS ENCONTRADOS

> Esta sección documenta todos los riesgos de pérdida de datos identificados en el código. Deben ser resueltos antes de operar en producción en un contexto de seguridad crítica.

### BUG-01 — CRÍTICO: Sin transacción atómica entre `registros` y `serialtest`

**Archivo**: `ConsultasSQL.py`, líneas 311-419
**Riesgo**: Pérdida permanente e irrecuperable de tests.

`registros` se inserta y hace `COMMIT` en un lote. Luego, en otra transacción separada, se insertan los `serialtest`. Si el programa se interrumpe (crash, pérdida de red, fallo de DB) entre los dos commits:

- Los `registros` quedan guardados en la DB.
- En la siguiente ejecución, la deduplicación los identifica como ya existentes y los **descarta**.
- Los `serialtest` asociados a esos registros se convierten en **huérfanos y se pierden para siempre**, ya que nunca volverán a pasar la deduplicación.

**La única solución correcta** es envolver AMBAS inserciones (registros + tests del mismo batch) en una sola transacción que no se commitea hasta que ambas hayan sido exitosas.

---

### BUG-02 — CRÍTICO: Error en un batch de registros descarta silenciosamente sus tests

**Archivo**: `ConsultasSQL.py`, líneas 339-341
**Riesgo**: Pérdida de datos sin notificación efectiva.

```python
except pymysql.MySQLError as e:
    print(f"\nError en batch {start}-{end}: {e}")
    self.coneccion_db.conn.rollback()
    # <-- el código continúa al siguiente batch. id_mapping no se llena para este batch.
```

Cuando un batch de registros falla: el rollback es correcto, pero la función continúa hacia el siguiente batch sin registrar cuáles registros se perdieron. Los tests de ese batch tienen su clave de mapeo ausente en `id_mapping` → se cuentan como `tests_huerfanos` → se descartan silenciosamente. No hay retry, no hay log a archivo, no hay modo de recuperación.

---

### BUG-03 — CRÍTICO: `cambiar_formato_fecha` sin manejo de errores pierde un archivo entero

**Archivo**: `CapturarDatos.py`, línea 33 y llamadas en líneas 188 y 219
**Riesgo**: Si el formato de fecha en el log no es exactamente `yyyy/mm/dd`, se lanza `ValueError` sin capturar, y **todos los registros del archivo se pierden**.

```python
def cambiar_formato_fecha(fecha):
    año, mes, dia = fecha.split("/")  # Sin try-except. Falla con "2026-03-16" o ""
    return f"{dia}/{mes}/{año}"
```

Si un log tiene `DATE : 2026-03-16` (con guiones en lugar de barras) o cualquier otro formato inesperado, la función falla. La llamada en `formatear_datos_para_insercion` no está dentro de un try-except, por lo que el error sube y **el archivo completo es descartado** sin ningún mensaje de advertencia.

---

### BUG-04 — CRÍTICO: Tests huérfanos se descartan con solo un `print`

**Archivo**: `ConsultasSQL.py`, líneas 384-391
**Riesgo**: Pérdida silenciosa de resultados de tests.

```python
if tests_huerfanos > 0:
    print(f"\nAdvertencia: {tests_huerfanos} tests no pudieron asociarse a un registro")
# Los tests huérfanos se descartan aquí. No se guardan, no se reintentan.
```

Un `print` a consola NO es logging en un sistema de producción. Si el proceso corre desatendido (como tarea programada), esta advertencia se pierde. Además, no hay forma de saber qué tests específicos se perdieron.

---

### BUG-05 — ALTO: Comparación de hora inconsistente en deduplicación puede generar duplicados

**Archivo**: `ConsultasSQL.py`, líneas 191-228
**Riesgo**: Inserción de registros duplicados en la DB.

Para los registros existentes en DB, la hora se normaliza a `HH:MM:SS` (usando conversión de objeto `time`/`timedelta`). Para los registros nuevos del CSV, la hora se usa **tal cual** (`hora = registro[1]`), sin pasar por `normalizar_hora()`.

Si el CSV contiene `"14:30"` (sin segundos) pero la DB almacena `"14:30:00"`, las claves son distintas → el registro NO se detecta como duplicado → **se inserta dos veces**.

---

### BUG-06 — ALTO: Sin reconexión a DB — pérdida de datos si cae la conexión MySQL

**Archivo**: `ConectorDB.py`
**Riesgo**: Si la conexión MySQL se pierde durante un batch (por `wait_timeout`, reinicio de red, etc.), el programa falla sin reintentar. Los batches en vuelo se pierden.

No hay lógica de reconexión ni de retry. Una ejecución larga con miles de archivos puede perder horas de trabajo si la conexión cae una sola vez.

---

### BUG-07 — MEDIO: `evitar_duplicados` retorna TODOS los datos si la query SQL falla

**Archivo**: `ConsultasSQL.py`, líneas 213-215
**Riesgo**: Si la consulta de deduplicación falla, todos los registros del lote se marcan como "nuevos" y se insertan. Esto es intencionalmente conservador (para no perder datos), pero puede causar **duplicación masiva** silenciosa. La condición falla con solo un `print`.

---

### BUG-08 — MEDIO: `ultimo_registro_por_hostname` se llama dos veces por hostname

**Archivo**: `main.py`, líneas 133 y 162
**Riesgo**: Ninguno para datos, pero es una query extra innecesaria por hostname. La segunda llamada (línea 162) solo se usa para imprimir un log.

---

### Tabla resumen de bugs y estado

| ID | Severidad | Archivo | Descripción | Estado |
|----|-----------|---------|-------------|--------|
| BUG-01 | **CRÍTICO** | `ConsultasSQL.py` | Sin transacción atómica registros+tests | **CORREGIDO** — cada batch hace un único COMMIT con registros+tests |
| BUG-02 | **CRÍTICO** | `ConsultasSQL.py` | Error en batch continuaba silenciosamente | **CORREGIDO** — rollback completo + log a archivo; reintento en próxima ejecución |
| BUG-03 | **CRÍTICO** | `CapturarDatos.py` | `cambiar_formato_fecha` sin manejo de errores | **CORREGIDO** — acepta múltiples formatos, retorna "" si no parsea |
| BUG-04 | **CRÍTICO** | `ConsultasSQL.py` | Tests huérfanos solo se imprimían | **CORREGIDO** — se loguean con detalle en `errores_procesamiento.log` |
| BUG-05 | **ALTO** | `ConsultasSQL.py` | Hora sin normalizar en dedup (causaba duplicados) | **CORREGIDO** — usa `normalizar_hora()` en ambos lados de la comparación |
| BUG-06 | **ALTO** | `ConectorDB.py` | Sin reconexión automática a MySQL | **CORREGIDO** — `reconectar_si_necesario()` con `ping(reconnect=True)` |
| BUG-07 | **MEDIO** | `ConsultasSQL.py` | Falla de dedup retorna todos los datos sin aviso claro | Pendiente — comportamiento conservador intencional, falta log |
| BUG-08 | **MEDIO** | `main.py` | `ultimo_registro_por_hostname` llamada dos veces por hostname | Pendiente — sin pérdida de datos, query redundante |

### Archivo de log de errores

El sistema escribe en `errores_procesamiento.log` (mismo directorio que el ejecutable) todos los eventos de:
- Batches que fallaron (con rollback)
- Tests huérfanos (sin registro padre)
- Cualquier error fatal

Este archivo **debe monitorearse** en producción. Su existencia o crecimiento indica problemas activos.
