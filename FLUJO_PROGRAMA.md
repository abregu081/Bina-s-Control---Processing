# Flujo del Programa - Captura de Logs

## Resumen General

El programa procesa archivos CSV de logs generados por estaciones de testing,
extrae registros y tests individuales, y los inserta en una base de datos MySQL.

---

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Orquestador: recorre directorios, coordina el flujo completo |
| `CapturarDatos.py` | Parseo de archivos CSV de logs y formateo de datos en memoria |
| `ConsultasSQL.py` | Todas las operaciones contra la base de datos |
| `ConectorDB.py` | Establecimiento de conexion MySQL via pymysql |
| `Configuraciones.py` | Lectura de archivos de configuracion (.cfg, .ini) |

---

## Flujo Paso a Paso

### 1. Inicializacion (main.py, nivel de modulo)

```
main.py se ejecuta
    |
    +--> Crea UNA instancia de ConsultasSQL (UNA conexion DB)
    +--> Lee configuracion: medio, planta, logs_path, hostnames
    +--> Obtiene medio_id de la DB (1 query)
    +--> Lee metricas del sistema (CPU, RAM, disco, red)
    |
    +--> PREFETCH: obtiene el ultimo registro de TODOS los hostnames
    |    en UNA SOLA consulta SQL con ROW_NUMBER() OVER (PARTITION BY Hostname)
    |    Resultado: dict {hostname: ultimo_registro}
    |
    +--> Muestra banner de inicio
```

**Nota sobre la conexion DB**: Antes de la optimizacion, `CapturarDatos.py`
creaba su propia instancia de `ConsultasSQL` al importarse, generando una
segunda conexion a la DB que solo se usaba para obtener `medio_id`.
Ahora `medio_id` se obtiene desde `main.py` usando la conexion principal.

### 2. Recorrido de Directorios

```
os.walk(logs_path)
    |
    +--> Para cada subdirectorio:
    |    nombre_carpeta == hostname conocido?
    |        NO --> saltar
    |        SI --> continuar
    |
    +--> Obtener fecha del ultimo registro de este hostname
    |    (desde el dict prefetcheado, sin query adicional)
    |
    +--> Para cada archivo .csv en la carpeta:
    |    Extraer fecha del nombre: XXXXX_STATION_TOPXXX_YYYYMMDD_NN.csv
    |    Si fecha_archivo >= fecha_ultimo_registro_en_DB:
    |        procesar archivo
```

### 3. Procesamiento de Archivos (CapturarDatos.py)

```
Procesar_archivo(ruta)
    |
    +--> Lee el archivo completo en memoria
    +--> Busca bloques delimitados por #INIT ... //PC_RAM_END
    |
    +--> Para cada bloque:
    |    +--> Extrae campos clave (DATE, MODEL, P/N, TIME, RESULT, etc.)
    |    +--> Extrae tests de la seccion #TEST:
    |    |    - Busca inicio "#TEST" con str.find() (no regex)
    |    |    - Busca fin "RESULT :" o "//PC_RAM_END"
    |    |    - Parsea cada linea: "NombreTest [Unidad], valor, low, high, P/F, time"
    |    |    - Extrae: test_nombre, unidad, valor, limites, resultado
    |    |
    |    +--> Devuelve dict con campos + lista de tests
    |
    +--> Retorna lista de dicts (uno por bloque/registro)
```

### 4. Formateo en Memoria (CapturarDatos.py)

```
formatear_datos_para_insercion(datos, hostname, medio, planta, medio_id)
    |
    +--> Para cada registro procesado:
    |    +--> Resuelve BOX (fallback a JIG si BOX vacio o "0")
    |    +--> Convierte fecha de yyyy/mm/dd a dd/mm/yyyy
    |    +--> Genera lista de 17 campos para tabla 'registros'
    |    +--> Genera lista de 10 campos por cada test
    |
    +--> Retorna (registros[], tests[])
```

**Nota**: Antes de la optimizacion, los datos se escribian a 2 archivos CSV
intermedios (`SeriesCapturados.csv` y `SeriesCapturados_Tests.csv`) y
luego se volvian a leer con `csv.reader`. Este round-trip de I/O fue eliminado.
Ahora los datos se mantienen en memoria durante todo el ciclo.

### 5. Deduplicacion (ConsultasSQL.py)

```
evitar_duplicados(registros)
    |
    +--> Extrae hostnames unicos y rango de fechas de los datos
    +--> UNA consulta SQL: SELECT Fecha, Hora, Serial, Hostname
    |    FROM registros WHERE Hostname IN (...) AND Fecha BETWEEN min AND max
    |
    +--> Construye set de claves existentes: (fecha, hora, serial, hostname)
    +--> Filtra en memoria: solo conserva registros cuya clave NO existe
    |
    +--> Imprime estadisticas: totales, nuevos, duplicados
    +--> Retorna registros_filtrados
```

### 6. Filtrado de Tests

```
(en main.py)
    |
    +--> Construye set de claves de registros no-duplicados
    |    Clave = (fecha_iso, hora_hms, serial, hostname)
    |
    +--> Normaliza fechas y horas de los tests con las mismas funciones
    +--> Filtra: conserva solo tests cuya clave coincide con un registro valido
```

### 7. Insercion Combinada (ConsultasSQL.py)

```
Insertar_registros_con_tests(registros, tests)
    |
    +--> PASO 1: Preparar datos
    |    Convierte fechas dd/mm/yyyy a yyyy-mm-dd
    |    Limpia valores vacios ('' -> None)
    |    Convierte campos numericos a float
    |
    +--> PASO 2: Insertar registros + mapear IDs
    |    Para cada batch de 30.000:
    |        executemany(INSERT INTO registros ...)
    |        commit()
    |        first_id = cursor.lastrowid  <-- primer auto_increment del batch
    |        Para cada registro i en el batch:
    |            id_mapping[clave_normalizada] = first_id + i
    |        Muestra barra de progreso
    |
    +--> PASO 3: Mapear tests a IDRegistros
    |    Para cada test:
    |        Normaliza fecha/hora/serial/hostname
    |        Busca IDRegistros en id_mapping
    |        Prepara tupla (IDRegistros, TestNombre, Valor, Low, High, Unidad, Resultado)
    |
    +--> PASO 4: Insertar tests
    |    Para cada batch de 50.000:
    |        executemany(INSERT INTO serialtest ...)
    |        commit()
    |        Muestra barra de progreso
    |
    +--> Retorna (registros_insertados, tests_insertados)
```

**Nota sobre lastrowid**: Antes de la optimizacion, despues de insertar los
registros se ejecutaban queries SELECT adicionales (en chunks de 5.000) para
recuperar los IDRegistros generados. Esto requeria N/5000 consultas extra.
Ahora se usa `cursor.lastrowid` que devuelve el primer auto_increment del
batch, y como los IDs son secuenciales, se calculan todos sin queries extras.

### 8. Finalizacion

```
fin_programa()
    |
    +--> Calcula tiempo de ejecucion total
    +--> Muestra estadisticas: tiempo, memoria, disco, CPU, red
```

---

## Consultas SQL por ejecucion (resumen)

| Etapa | Consultas | Descripcion |
|---|---|---|
| Inicializacion | 1 | obtener_medio_id |
| Prefetch | 1 | ultimos_registros_por_hostnames (todos los hostnames) |
| Por hostname con datos | 1 | evitar_duplicados (SELECT rango de fechas) |
| Por hostname con datos | N batches | INSERT registros (30K por batch) |
| Por hostname con datos | M batches | INSERT tests (50K por batch) |

**Total minimo por hostname**: 1 (dedup) + 1 (insert reg) + 1 (insert tests) = 3 queries

**Comparacion con version anterior**:
- Antes: 2 queries individuales de ultimo_registro por hostname + 1 dedup + N insert + N/5000 recovery + M insert tests
- Ahora: 0 queries individuales (prefetch) + 1 dedup + N insert + 0 recovery + M insert tests

---

## Normalizacion de Fechas y Horas

Tanto `main.py` como `ConsultasSQL.py` usan funciones de normalizacion para
asegurar que las claves de comparacion siempre tengan el mismo formato:

- **Fechas**: siempre se comparan como `yyyy-mm-dd` (ISO)
  - Acepta: `yyyy-mm-dd`, `dd/mm/yyyy`, `yyyy/mm/dd`, objetos date/datetime
- **Horas**: siempre se comparan como `HH:MM:SS`
  - Acepta: `HH:MM:SS`, `HH:MM`, objetos time, timedelta con `.seconds`
  - Descarta microsegundos si los hay

Esto previene que tests se pierdan por diferencias de formato entre lo que
viene del log CSV y lo que devuelve MySQL.

---

## Estructura de Tablas (referencia)

### registros
17 campos: Fecha, Hora, Modelo, Serial, Resultado, Detalle, Medio, Hostname,
Planta, Banda, Box, IMEI, SKU, TestTime, Runtime, ModelFile, Medio_id
- IDRegistros: auto_increment (PK)

### serialtest
Campos: IDRegistros (FK), TestNombre, Valor, ValorLimit_Low, ValorLimit_High,
Unidad, Resultado
