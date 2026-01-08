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
        try:
            consulta = """
            INSERT INTO Registros
            (Fecha, Hora, Modelo,Serial, Resultado, Detalle, Medio, Hostname, Planta, Banda, Box, IMEI, SKU, TestTime, Runtime, ModelFile, Medio_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.executemany(consulta, datos_convertidos)
            self.coneccion_db.conn.commit()
            self.coneccion_db.cerrar_conexion()
            return True
        except pymysql.MySQLError as e:
            print(f"Error al ejecutar la consulta: {e}")
            self.coneccion_db.conn.rollback()
            return False
        
    def evitar_duplicados(self, datos):
        datos_filtrados = []
        for registro in datos:
            fecha = registro[0]
            hora = registro[1]
            serial = registro[2]
            hostname = registro[6]
            consulta = """
                SELECT COUNT(*) FROM Registros
                WHERE Fecha = %s AND Hora = %s AND Serial = %s AND Hostname = %s
            """
            try:
                self.cursor.execute(consulta, (fecha, hora, serial, hostname))
                existe = self.cursor.fetchone()[0]
                if existe == 0:
                    datos_filtrados.append(registro)
            except pymysql.MySQLError as e:
                print(f"Error al verificar duplicados: {e}")
                continue
        return datos_filtrados
        
            