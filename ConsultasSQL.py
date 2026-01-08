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
        datos_filtrados = []
        for registro in datos:
            fecha = registro[0]
            fecha_arreglada = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
            hora = registro[1]
            serial = registro[3]
            hostname = registro[7]
            consulta = """
                SELECT COUNT(*) AS cnt FROM Registros
                WHERE Fecha = %s AND Hora = %s AND Serial = %s AND Hostname = %s
            """
            try:
                self.cursor.execute(consulta, (fecha_arreglada, hora, serial, hostname))
                resultado = self.cursor.fetchone()
                if resultado is None:
                    existe = 0
                elif isinstance(resultado, dict):
                    existe = resultado.get('cnt')
                    if existe is None:
                        try:
                            existe = next(iter(resultado.values()))
                        except StopIteration:
                            existe = 0
                else:
                    existe = resultado[0] if len(resultado) > 0 else 0

                if not existe:
                    datos_filtrados.append(registro)
            except pymysql.MySQLError as e:
                print(f"Error al verificar duplicados: {e}")
                continue
        return datos_filtrados