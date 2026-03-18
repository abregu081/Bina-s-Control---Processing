import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class MedioConfig:
    """Configuración de un medio de producción (una sección del cfg)."""
    nombre: str
    token: str
    planta: str
    logs_path: str
    hostnames: List[str]
    medio_id: Optional[int] = None


class Configuraciones:
    def __init__(self):
        self.diccionario_configuraciones = {}
        self.diccionario_parametros_db = {}
        self.diccionario_hostname = {}

    @staticmethod
    def obtener_valores(archivo):
        diccionario = {}
        if getattr(sys, 'frozen', False):
            carpeta_actual = os.path.dirname(sys.executable)
        else:
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))

        ruta_completa = os.path.join(carpeta_actual, archivo)
        with open(ruta_completa, 'r') as file:
            for linea in file:
                linea = linea.strip()
                if linea and not linea.startswith("//") and '=' in linea:
                    clave, valor = linea.split('=', 1)
                    diccionario[clave.strip()] = valor.strip()
            return diccionario

    @staticmethod
    def cargar_config_medios(archivo):
        """
        Lee un archivo .cfg con secciones [NOMBRE] y devuelve
        un dict {section_name: {key: value}}.
        Ignora líneas que empiezan con // y líneas en blanco.
        """
        if getattr(sys, 'frozen', False):
            carpeta_actual = os.path.dirname(sys.executable)
        else:
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))

        ruta_completa = os.path.join(carpeta_actual, archivo)
        secciones = {}
        seccion_actual = None

        with open(ruta_completa, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("//"):
                    continue
                if linea.startswith("[") and linea.endswith("]"):
                    seccion_actual = linea[1:-1].strip()
                    secciones[seccion_actual] = {}
                elif '=' in linea and seccion_actual is not None:
                    clave, valor = linea.split('=', 1)
                    secciones[seccion_actual][clave.strip()] = valor.strip()

        return secciones

    @staticmethod
    def obtener_config_todos_medios():
        """
        Lee Configuraciones.cfg y devuelve una lista de MedioConfig,
        uno por cada sección que no sea [GLOBAL].
        Los valores de [GLOBAL] actúan como defaults para cualquier sección.
        """
        secciones = Configuraciones.cargar_config_medios('Configuraciones.cfg')
        global_vals = secciones.get('GLOBAL', {})

        medios = []
        for nombre, vals in secciones.items():
            if nombre == 'GLOBAL':
                continue
            planta = vals.get('Planta', global_vals.get('Planta', '01'))
            token = vals.get('TokenAcceso', global_vals.get('TokenAcceso', ''))
            logs_path = vals.get('logs_path', '')
            hostnames_str = vals.get('hostnames', '')
            hostnames = [h.strip() for h in hostnames_str.split(',') if h.strip()]

            medios.append(MedioConfig(
                nombre=nombre,
                token=token,
                planta=planta,
                logs_path=logs_path,
                hostnames=hostnames,
            ))

        return medios

    # --- Métodos de compatibilidad hacia atrás (sin cambios) ---

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
        return hostnames
