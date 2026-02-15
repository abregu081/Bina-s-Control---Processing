import ConectorDB as Conexion
import pymysql
from datetime import datetime, date, time, timedelta

class ConsultasSQL:
    def __init__(self):
        self.coneccion_db = Conexion.ConectorDB()
        self.coneccion_db.conectar_db()
        self.cursor = self.coneccion_db.cursor

    def ultimo_registro_por_hostname(self, hostname):
        try:
            consulta = "SELECT * FROM registros WHERE hostname = %s ORDER BY fecha DESC, hora DESC LIMIT 1"
            self.cursor.execute(consulta, (hostname,))
            resultado = self.cursor.fetchone()
            return resultado
        except pymysql.MySQLError as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        
    def obtener_medio_id(self, medio):
        try:
            consulta = "SELECT id_medios_de_produccion FROM medios_de_produccion WHERE nombre = %s"
            self.cursor.execute(consulta, (medio,))
            resultado = self.cursor.fetchone()
            return resultado
        except pymysql.MySQLError as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        
    def Insertar_registros(self, datos):
        datos_convertidos = []
        for registro in datos:
            registro = list(registro)
            if registro[0] and "/" in registro[0]:
                registro[0] = datetime.strptime(registro[0], "%d/%m/%Y").strftime("%Y-%m-%d")
            # Limpiar valores vacíos y convertir numéricos
            for i in range(len(registro)):
                if registro[i] == '':
                    registro[i] = None
            for idx in [12, 13]:
                if registro[idx] is not None:
                    try:
                        registro[idx] = float(registro[idx])
                    except Exception:
                        registro[idx] = None
            datos_convertidos.append(tuple(registro))
        if not datos_convertidos:
            return True

        consulta = """
        INSERT INTO registros
        (fecha, hora, modelo, serial, resultado, detalle, medio, hostname, planta, banda, box, imei, sku, testtime, runtime, modelfile, medio_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        total = len(datos_convertidos)
        batch_size = 30000
        inserted = 0
        def _print_progress(current, total, bar_length=40):
            percent = float(current) / total if total else 1
            filled = int(bar_length * percent)
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f"\rProgreso: |{bar}| {current}/{total} ({percent*100:.1f}%)", end='', flush=True)
            if current == total:
                print()
        try:
            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                batch = datos_convertidos[start:end]
                try:
                    self.cursor.executemany(consulta, batch)
                    self.coneccion_db.conn.commit()
                    inserted += len(batch)
                except pymysql.MySQLError as e:
                    print(f"\nError en batch {start}-{end}: {e}")
                    self.coneccion_db.conn.rollback()
                _print_progress(inserted, total)

            return True
        except Exception as e:
            print(f"Error al ejecutar la inserción por lotes: {e}")
            try:
                self.coneccion_db.conn.rollback()
            except Exception:
                pass
            return False

    def normalizar_fecha(self, fecha):
        """
        Convierte cualquier formato de fecha a yyyy-mm-dd para comparación.

        Args:
            fecha: Puede ser date object, datetime, o string en formatos:
                   - yyyy-mm-dd, yyyy/mm/dd, dd/mm/yyyy

        Returns:
            String en formato yyyy-mm-dd
        """
        if isinstance(fecha, (date, datetime)):
            return fecha.strftime("%Y-%m-%d")
        if isinstance(fecha, str):
            if "/" in fecha:
                if fecha.count("/") == 2:
                    partes = fecha.split("/")
                    if len(partes[0]) == 4:  # yyyy/mm/dd
                        return fecha.replace("/", "-")
                    else:  # dd/mm/yyyy
                        return f"{partes[2]}-{partes[1]}-{partes[0]}"
            elif "-" in fecha:
                # Ya está en formato correcto o yyyy-mm-dd
                return fecha
        return str(fecha)

    def normalizar_hora(self, hora):
        """
        Convierte cualquier formato de hora a HH:MM:SS para comparación.

        Args:
            hora: Puede ser time object, timedelta, o string

        Returns:
            String en formato HH:MM:SS
        """
        if isinstance(hora, time):
            return hora.strftime("%H:%M:%S")
        if isinstance(hora, timedelta):
            total_seconds = hora.seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        # Limpiar microsegundos si existen
        hora_str = str(hora)
        if "." in hora_str:
            hora_str = hora_str.split(".")[0]
        # Asegurar formato HH:MM:SS
        if len(hora_str.split(":")) == 2:  # HH:MM
            hora_str += ":00"
        return hora_str

    def evitar_duplicados(self, datos):
        """
        Versión optimizada: en lugar de hacer 1 query por registro,
        obtenemos todos los registros existentes del hostname en UNA sola consulta
        y filtramos en memoria (mucho más rápido).
        """
        if not datos:
            return []
        
        # Extraer hostnames únicos de los datos
        hostnames = set(registro[7] for registro in datos)
        
        # Obtener fechas mínima y máxima para acotar la consulta
        fechas = []
        for registro in datos:
            try:
                fecha = datetime.strptime(registro[0], "%d/%m/%Y").strftime("%Y-%m-%d")
                fechas.append(fecha)
            except:
                continue
        
        if not fechas:
            return datos
        
        fecha_min = min(fechas)
        fecha_max = max(fechas)
        
        # Una sola consulta para traer todos los registros existentes en ese rango
        registros_existentes = set()
        try:
            placeholders = ', '.join(['%s'] * len(hostnames))
            consulta = f"""
                SELECT fecha, hora, serial, hostname FROM registros
                WHERE hostname IN ({placeholders})
                AND fecha BETWEEN %s AND %s
            """
            params = list(hostnames) + [fecha_min, fecha_max]
            self.cursor.execute(consulta, params)
            resultados = self.cursor.fetchall()
            
            for row in resultados:
                if isinstance(row, dict):
                    fecha_db = row.get('fecha', row.get('Fecha'))
                    hora_db = row.get('hora', row.get('Hora'))
                    serial_db = row.get('serial', row.get('Serial'))
                    hostname_db = row.get('hostname', row.get('Hostname'))
                else:
                    fecha_db, hora_db, serial_db, hostname_db = row[0], row[1], row[2], row[3]
                
                # Normalizar fecha a string para comparación
                if hasattr(fecha_db, 'strftime'):
                    fecha_db = fecha_db.strftime("%Y-%m-%d")
                else:
                    fecha_db = str(fecha_db)
                
                # Normalizar hora a string
                if hasattr(hora_db, 'strftime'):
                    hora_db = hora_db.strftime("%H:%M:%S")
                elif hasattr(hora_db, 'seconds'):
                    total_seconds = hora_db.seconds
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    hora_db = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    hora_db = str(hora_db)
                
                # Crear clave única (fecha, hora, serial, hostname)
                clave = (fecha_db, hora_db, str(serial_db), str(hostname_db))
                registros_existentes.add(clave)
                
        except pymysql.MySQLError as e:
            print(f"Error al obtener registros existentes: {e}")
            return datos  # Si falla, devolvemos todos para no perder datos
        
        # Filtrar en memoria (súper rápido)
        datos_filtrados = []
        for registro in datos:
            try:
                fecha_arreglada = datetime.strptime(registro[0], "%d/%m/%Y").strftime("%Y-%m-%d")
                hora = registro[1]
                serial = registro[3]
                hostname = registro[7]
                
                clave = (fecha_arreglada, hora, str(serial), str(hostname))
                
                if clave not in registros_existentes:
                    datos_filtrados.append(registro)
            except Exception as e:
                # Si hay error parseando, lo incluimos para no perder datos
                datos_filtrados.append(registro)
                
        print(f"  -> Filtrado: {len(datos)} totales, {len(datos_filtrados)} nuevos, {len(datos) - len(datos_filtrados)} duplicados")
        return datos_filtrados

    def Insertar_registros_con_tests(self, registros, tests):
        """
        Inserta registros y tests en una transacción optimizada.

        Estrategia:
        1. Insertar registros en batches de 30,000
        2. Usar MAX(idregistros) antes/después del INSERT para calcular IDs asignados
        3. Mapear cada registro a su idregistros (max_before + 1 + i)
        4. Filtrar tests para asociarlos con su idregistros usando clave normalizada
        5. Insertar tests en batches de 50,000

        Args:
            registros: Lista de listas (17 campos cada una)
            tests: Lista de listas (10 campos: Fecha, Hora, Serial, Hostname,
                                               TestNombre, Valor, Low, High, Unidad, Resultado)

        Returns:
            tuple (registros_insertados, tests_insertados)
        """
        if not registros:
            print("No hay registros para insertar")
            return (0, 0)

        # Paso 1: Preparar datos de registros
        datos_convertidos = []
        for registro in registros:
            registro = list(registro)
            # Convertir fecha de dd/mm/yyyy a yyyy-mm-dd
            if registro[0] and "/" in registro[0]:
                registro[0] = datetime.strptime(registro[0], "%d/%m/%Y").strftime("%Y-%m-%d")
            # Limpiar valores vacíos
            for i in range(len(registro)):
                if registro[i] == '':
                    registro[i] = None
            # Convertir campos numéricos (TestTime, Runtime)
            for idx in [13, 14]:
                if registro[idx] is not None:
                    try:
                        registro[idx] = float(registro[idx])
                    except Exception:
                        registro[idx] = None
            datos_convertidos.append(tuple(registro))

        # Paso 2: Insertar registros + mapear IDs
        consulta_registros = """
        INSERT INTO registros
        (fecha, hora, modelo, serial, resultado, detalle, medio, hostname, planta, banda, box, imei, sku, testtime, runtime, modelfile, medio_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        id_mapping = {}  # {(fecha_iso, hora_hms, serial, hostname): IDRegistros}
        registros_insertados = 0
        total_registros = len(datos_convertidos)
        batch_size = 30000

        def _print_progress(current, total, bar_length=40):
            percent = float(current) / total if total else 1
            filled = int(bar_length * percent)
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f"\rProgreso Registros: |{bar}| {current}/{total} ({percent*100:.1f}%)", end='', flush=True)
            if current == total:
                print()

        try:
            for start in range(0, total_registros, batch_size):
                end = min(start + batch_size, total_registros)
                batch = datos_convertidos[start:end]

                try:
                    # Obtener MAX(id) ANTES del insert para delimitar los nuevos IDs
                    self.cursor.execute("SELECT COALESCE(MAX(idregistros), 0) AS max_id FROM registros")
                    row = self.cursor.fetchone()
                    max_id_before = row['max_id'] if isinstance(row, dict) else row[0]

                    self.cursor.executemany(consulta_registros, batch)
                    self.coneccion_db.conn.commit()

                    # Consultar los IDs reales asignados por la DB (no asumir secuencial)
                    self.cursor.execute(
                        "SELECT idregistros FROM registros WHERE idregistros > %s ORDER BY idregistros ASC",
                        (max_id_before,)
                    )
                    rows_ids = self.cursor.fetchall()
                    new_ids = []
                    for r in rows_ids:
                        if isinstance(r, dict):
                            val = r.get('idregistros', r.get('IDRegistros'))
                        else:
                            val = r[0]
                        new_ids.append(val)

                    # Mapear cada registro del batch a su ID real de la DB
                    for i, registro in enumerate(batch):
                        if i < len(new_ids):
                            fecha_iso = registro[0]  # Ya convertida a yyyy-mm-dd
                            hora_hms = self.normalizar_hora(registro[1])
                            serial = str(registro[3]) if registro[3] else ""
                            hostname = str(registro[7]) if registro[7] else ""
                            clave = (fecha_iso, hora_hms, serial, hostname)
                            id_mapping[clave] = new_ids[i]

                    registros_insertados += len(batch)
                except pymysql.MySQLError as e:
                    print(f"\nError en batch {start}-{end}: {e}")
                    self.coneccion_db.conn.rollback()

                _print_progress(registros_insertados, total_registros)

        except Exception as e:
            print(f"Error al insertar registros: {e}")
            try:
                self.coneccion_db.conn.rollback()
            except Exception:
                pass
            return (0, 0)

        # Paso 3: Mapear tests a IDRegistros
        if not tests:
            print("No hay tests para insertar")
            return (registros_insertados, 0)

        tests_con_id = []
        tests_huerfanos = 0

        for test in tests:
            # Normalizar clave del test
            fecha_iso = self.normalizar_fecha(test[0])  # dd/mm/yyyy → yyyy-mm-dd
            hora_hms = self.normalizar_hora(test[1])    # HH:MM:SS
            serial = str(test[2]) if test[2] else ""
            hostname = str(test[3]) if test[3] else ""
            clave = (fecha_iso, hora_hms, serial, hostname)

            # Buscar IDRegistros en el mapping
            if clave in id_mapping:
                id_registros = id_mapping[clave]
                # Crear tupla: (IDRegistros, TestNombre, Valor, Low, High, Unidad, Resultado)
                test_tupla = (
                    id_registros,
                    test[4],  # TestNombre
                    test[5],  # Valor
                    test[6],  # ValorLimit_Low
                    test[7],  # ValorLimit_High
                    test[8],  # Unidad
                    test[9]   # Resultado
                )
                tests_con_id.append(test_tupla)
            else:
                tests_huerfanos += 1

        if tests_huerfanos > 0:
            print(f"\nAdvertencia: {tests_huerfanos} tests no pudieron asociarse a un registro")

        if not tests_con_id:
            print("No hay tests válidos para insertar después del mapeo")
            return (registros_insertados, 0)

        # Paso 4: Insertar tests en batches
        consulta_tests = """
        INSERT INTO serialtest
        (idregistros, testnombre, valor, valorlimit_low, valorlimit_high, unidad, resultado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        tests_insertados = 0
        total_tests = len(tests_con_id)
        batch_size_tests = 50000

        def _print_progress_tests(current, total, bar_length=40):
            percent = float(current) / total if total else 1
            filled = int(bar_length * percent)
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f"\rProgreso Tests: |{bar}| {current}/{total} ({percent*100:.1f}%)", end='', flush=True)
            if current == total:
                print()

        try:
            for start in range(0, total_tests, batch_size_tests):
                end = min(start + batch_size_tests, total_tests)
                batch = tests_con_id[start:end]

                try:
                    self.cursor.executemany(consulta_tests, batch)
                    self.coneccion_db.conn.commit()
                    tests_insertados += len(batch)
                except pymysql.MySQLError as e:
                    print(f"\nError en batch tests {start}-{end}: {e}")
                    self.coneccion_db.conn.rollback()

                _print_progress_tests(tests_insertados, total_tests)

        except Exception as e:
            print(f"Error al insertar tests: {e}")
            try:
                self.coneccion_db.conn.rollback()
            except Exception:
                pass

        return (registros_insertados, tests_insertados)