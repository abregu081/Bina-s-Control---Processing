import sys
import os
from cx_Freeze import setup, Executable

# Obtener el directorio actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

build_exe_options = {
    "packages": ["os", "csv", "re", "psutil", "pymysql", "datetime", "time"],
    "include_files": [
        "Configuraciones.cfg", 
        "Parametros_DB.ini", 
        "hostname.ini",
        "requirements.txt",
        "medios.txt",
    ],
    "excludes": ["tkinter", "unittest", "email","http", "xmlrpc", "pydoc"],
    "build_exe": os.path.join(BASE_DIR, "build")
}
setup(
    name="CapturaLog",
    version="2.0",
    description="Aplicacion para capturar logs de testing y almacenarlos en una base de datos MySQL",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=None)],
)
