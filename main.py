import os, csv, re
import Configuraciones as cfg
import datetime
import CapturarDatos as Captura
import ConsultasSQL as SQL

consultas_sql = SQL.ConsultasSQL()
config = cfg.Configuraciones()
logs_path = config.obtenerv_datos_configuracionees()[4]
hostnames_tuplas = config.obtener_datos_hostname()
lista_hostnames = [h[1] for h in hostnames_tuplas]
medio = config.obtenerv_datos_configuracionees()[0]
carpeta_actual = os.path.dirname(os.path.abspath(__file__))



def lector_de_registros_stage():
    registros = []
    with open(Captura.archivo_series, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)  # le hago un skip a los nombre de las columnas
        for row in reader:
            registros.append(row)
    return registros


archivo_prueba = r'52245228_OQC_TOP501_20250705_01.csv'
datos = Captura.Procesar_archivo(archivo_prueba)
Captura.Guardar_datos_stage_csv(datos, "Testeos")
datos_stage = lector_de_registros_stage()
consultas_sql.Insertar_registros(datos_stage)
print("Proceso completado.")

"""
for root, dirs, files in os.walk(logs_path):
    hostname = os.path.basename(root)
    if hostname in lista_hostnames:
        for f in files:
            if f.endswith(".csv"):
                ruta = os.path.join(root, f)
                datos = CapturarDatos.Procesar_archivo(ruta)
                CapturarDatos.Guardar_datos_stage_csv(datos, hostname)
   """             