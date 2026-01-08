from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "CapturarDatos", "ConsultasSQL", "Configuraciones", "pymysql", "csv", "re", "psutil"],
    "include_files": ["Configuraciones.cfg", "Parametros_DB.ini", "hostname.ini","requirements.txt","medios.txt"],
    "excludes": ["tkinter", "unittest", "email","http", "xmlrpc", "pydoc"],   
}
setup(
    name="CapturaLog",
    version="2.0",
    description="Aplicacion para capturar logs de testing y almacenarlos en una base de datos MySQL",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=None)],
)

