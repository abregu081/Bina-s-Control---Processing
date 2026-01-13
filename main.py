import os, csv
import sys
import Configuraciones as cfg
import datetime
import CapturarDatos as Captura
import ConsultasSQL as SQL
import time
import psutil as ps

tiempo_ejecucion_inicio = time.perf_counter()
tiempo_ejecucion_fin = None
consultas_sql = SQL.ConsultasSQL()
config = cfg.Configuraciones()
logs_path = config.obtenerv_datos_configuracionees()[4]
hostnames_tuplas = config.obtener_datos_hostname()
lista_hostnames = [h[1] for h in hostnames_tuplas]
medio = config.obtenerv_datos_configuracionees()[0]

if getattr(sys, 'frozen', False):
    carpeta_actual = os.path.dirname(sys.executable)
else:
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))

#estas son las variables para las estadisiticas finales (capaz las borre despues)
cpu = ps.cpu_percent(interval=1)
mem = ps.virtual_memory()
disk = ps.disk_usage(carpeta_actual)
net = ps.net_io_counters()

def lector_de_registros_stage():
    registros = []
    with open(Captura.archivo_series, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)  # le hago un skip a los nombre de las columnas :O
        for row in reader:
            registros.append(row)
    return registros


def inicio_programa():
    print("================================================")
    print(f"Mirgor {datetime.datetime.now().year} - Testing UNA/UNAE")
    print("Captura de Log - Version 2.0")
    print(f"Estacion: {medio} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("================================================")

def fin_programa():
    tiempo_ejecucion_fin = time.perf_counter()
    print("================================================")
    print(f'Tiempo de ejecucion: {tiempo_ejecucion_fin - tiempo_ejecucion_inicio:.6f} segundos')
    print(f'Memoria usada: {mem.percent}% de {mem.total / (1024 ** 3):.2f} GB')
    print(f'Espacio en disco: {disk.percent}% de {disk.total / (1024 ** 3):.2f} GB')
    print(f'Uso de CPU: {cpu}%')
    print(f'Total de datos enviados/recibidos por red: {(net.bytes_sent + net.bytes_recv) / (1024 ** 2):.2f} MB')
    print("================================================")

inicio_programa()
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
            ultimo_registo = consultas_sql.ultimo_registro_por_hostname(hostname)
            fecha_ultima = ultimo_registo['Fecha'] if ultimo_registo and 'Fecha' in ultimo_registo else None
            hora_ultima = ultimo_registo['Hora'] if ultimo_registo and 'Hora' in ultimo_registo else None
            print(f"Ultimo registro en DB para {hostname}: {fecha_ultima} {hora_ultima}")
            Captura.Guardar_datos_stage_csv(datos_a_guardar, hostname)
            datos_stage = lector_de_registros_stage()
            datos_filtrados = consultas_sql.evitar_duplicados(datos_stage)
            consultas_sql.Insertar_registros(datos_filtrados)
            print(f"Datos guardados para hostname {hostname}: {len(datos_filtrados)} registros")
            print("--------------------------------------------------")
            os.remove(Captura.archivo_series)

fin_programa()