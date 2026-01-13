import ConectorDB as Conexion
import pymysql
from datetime import datetime

class ConsultasSQL:
    def __init__(self):
        self.coneccion_db = Conexion.ConectorDB()
        self.coneccion_db.conectar_db()
        self.cursor = self.coneccion_db.cursor

    def ultimo_registro_por_hostname(self, hostname):
        try:
            consulta = "SELECT * FROM Registros WHERE Hostname = %s ORDER BY Fecha DESC, Hora DESC LIMIT 1"
            self.cursor.execute(consulta, (hostname,))
            resultado = self.cursor.fetchone()
            return resultado
        except pymysql.MySQLError as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        
    def obtener_medio_id(self, medio):
        try:
            consulta = "SELECT ID_Medios_de_produccion FROM Medios_de_produccion WHERE Nombre = %s"
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
        INSERT INTO Registros
        (Fecha, Hora, Modelo,Serial, Resultado, Detalle, Medio, Hostname, Planta, Banda, Box, IMEI, SKU, TestTime, Runtime, ModelFile, Medio_id)
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
                SELECT Fecha, Hora, Serial, Hostname FROM Registros
                WHERE Hostname IN ({placeholders})
                AND Fecha BETWEEN %s AND %s
            """
            params = list(hostnames) + [fecha_min, fecha_max]
            self.cursor.execute(consulta, params)
            resultados = self.cursor.fetchall()
            
            for row in resultados:
                if isinstance(row, dict):
                    fecha_db = row['Fecha']
                    hora_db = row['Hora']
                    serial_db = row['Serial']
                    hostname_db = row['Hostname']
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