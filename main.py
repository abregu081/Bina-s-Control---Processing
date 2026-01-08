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

for root, dirs, files in os.walk(logs_path):
    hostname = os.path.basename(root)
    if hostname in lista_hostnames:
        fecha_ultima = consultas_sql.ultimo_registro_por_hostname(hostname)
        fecha_ultima_ejecucion = None
        if fecha_ultima and 'Fecha' in fecha_ultima and fecha_ultima['Fecha'] is not None:
            val = fecha_ultima['Fecha']
            if hasattr(val, 'strftime'):
                fecha_ultima_ejecucion = val
            else:
                try:
                    fecha_ultima_ejecucion = datetime.datetime.strptime(str(val), "%Y-%m-%d").date()
                except Exception:
                    fecha_ultima_ejecucion = None
        datos_a_guardar = []
        for f in files:
            if f.endswith(".csv"):
                partes_archivo = f.split("_")
                if len(partes_archivo) < 4:
                    continue
                fecha_archivo_str = partes_archivo[3]
                try:
                    fecha_archivo_date = datetime.datetime.strptime(fecha_archivo_str, "%Y%m%d").date()
                except Exception:
                    continue
                # procesar si no hay fecha en BD (None) o si el archivo es de la fecha o posterior
                if (fecha_ultima_ejecucion is None) or (fecha_archivo_date >= fecha_ultima_ejecucion):
                    ruta_completa = os.path.join(root, f)
                    datos_procesados = Captura.Procesar_archivo(ruta_completa)
                    datos_a_guardar.extend(datos_procesados)

        if datos_a_guardar:
            Captura.Guardar_datos_stage_csv(datos_a_guardar, hostname)
            datos_stage = lector_de_registros_stage()
            datos_filtrados = consultas_sql.evitar_duplicados(datos_stage)
            consultas_sql.Insertar_registros(datos_filtrados)
            print(f"Datos guardados para hostname {hostname}: {len(datos_a_guardar)} registros")
            os.remove(Captura.archivo_series)
            