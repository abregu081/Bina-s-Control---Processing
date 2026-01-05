import os

class Configuraciones:
    def __init__(self):
        self.diccionario_configuraciones = {}
        self.diccionario_parametros_db = {}
        self.diccionario_hostname = {}

    @staticmethod
    def obtener_valores(archivo):
        diccionario = {}
        carpeta_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_completa = os.path.join(carpeta_actual, archivo)
        with open(ruta_completa, 'r') as file:
            for linea in file:
                linea = linea.strip()
                if linea and not linea.startswith("//") and '=' in linea:
                    clave, valor = linea.split('=', 1)
                    diccionario[clave.strip()] = valor.strip()
            return diccionario

    # todo te devuelve tuplas :b
    def obtenerv_datos_configuracionees(self):
        self.diccionario_configuraciones = self.obtener_valores('Configuraciones.cfg')
        nombre_estacion = self.diccionario_configuraciones.get('NombreDeEstacion', '')
        TokenAcceso = self.diccionario_configuraciones.get('TokenAcceso', '')
        Planta = self.diccionario_configuraciones.get('Planta', '')
        Modo_Dev = self.diccionario_configuraciones.get('Modo_Dev', '')
        logs_path = self.diccionario_configuraciones.get('logs_path', '')
        return nombre_estacion, TokenAcceso, Planta, Modo_Dev, logs_path

    def obtener_datos_parametros_db(self):
        self.diccionario_parametros_db = self.obtener_valores('Parametros_DB.ini')
        host = self.diccionario_parametros_db.get('host', '')
        user = self.diccionario_parametros_db.get('user', '')
        password = self.diccionario_parametros_db.get('password', '')
        database = self.diccionario_parametros_db.get('database', '')
        return host, user, password, database

    def obtener_datos_hostname(self):
        self.diccionario_hostname = self.obtener_valores('hostname.ini')
        hostnames = []
        for clave, valor in self.diccionario_hostname.items():
            hostnames.append((clave, valor)) 
        return hostnames # te devuelve una lista con tuplas: LO DEJO ASI PORQUE PUEDE HABAR MAS DE UNA LINEA DE PRODUCCION

    


        