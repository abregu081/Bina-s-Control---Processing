import sys
from cx_Freeze import setup, Executable

# Dependencias que cx_Freeze debe incluir
build_exe_options = {
    "packages": [
        "os", 
        "csv", 
        "re",
        "datetime",
        "time",
        "psutil",
        "pymysql",
        "cryptography",
    ],
    "includes": [
        "Configuraciones",
        "ConectorDB",
        "ConsultasSQL",
        "CapturarDatos",
    ],
    "include_files": [
        ("Configuraciones.cfg", "Configuraciones.cfg"),
        ("Parametros_DB.ini", "Parametros_DB.ini"),
        ("hostname.ini", "hostname.ini"),
        ("medios.txt", "medios.txt"),
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "html",
        "http",
        "xml",
        "pydoc",
    ],
    "optimize": 2,
}

# Configuración del ejecutable
base = None
if sys.platform == "win32":
    base = "Console"  # Usa "Win32GUI" si no quieres ventana de consola

executables = [
    Executable(
        script="main.py",
        base=base,
        target_name="BinasControl.exe",
        icon=None,  # Puedes agregar un icono: icon="icono.ico"
    )
]

setup(
    name="Binas Control Processing",
    version="2.0",
    description="Captura de Log - Testing UNA/UNAE",
    author="Mirgor",
    options={"build_exe": build_exe_options},
    executables=executables,
)
