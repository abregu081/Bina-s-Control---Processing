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
planta = config.obtenerv_datos_configuracionees()[2]
medio_id = consultas_sql.obtener_medio_id(medio)
medio_id = medio_id['id_medios_de_produccion'] if medio_id else None

if getattr(sys, 'frozen', False):
    carpeta_actual = os.path.dirname(sys.executable)
else:
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))

#estas son las variables para las estadisiticas finales (capaz las borre despues)
cpu = ps.cpu_percent(interval=1)
mem = ps.virtual_memory()
disk = ps.disk_usage(carpeta_actual)
net = ps.net_io_counters()

def inicio_programa():
    """Banner de inicio con estilo profesional de terminal"""
    ancho = 80
    linea = "=" * ancho

    print()
    print(linea)
    print("""
    ███╗   ███╗██╗██████╗  ██████╗  ██████╗ ██████╗
    ████╗ ████║██║██╔══██╗██╔════╝ ██╔═══██╗██╔══██╗
    ██╔████╔██║██║██████╔╝██║  ███╗██║   ██║██████╔╝
    ██║╚██╔╝██║██║██╔══██╗██║   ██║██║   ██║██╔══██╗
    ██║ ╚═╝ ██║██║██║  ██║╚██████╔╝╚██████╔╝██║  ██║
    ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
    """)
    print(f"{'Testing UNA/UNAE - Log Capture System':^{ancho}}")
    print(linea)

    # Información del sistema
    print(f"\n  INFORMACION DEL SISTEMA")
    print(f"  {'-' * (ancho - 4)}")
    print(f"  Version        : 2.0 (Optimizada)")
    print(f"  Estacion       : {medio}")
    print(f"  Planta         : {planta}")
    print(f"  Medio ID       : {medio_id if medio_id else 'N/A'}")
    print(f"  Fecha/Hora     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Año            : {datetime.datetime.now().year}")

    # Estadísticas del sistema
    print(f"\n  RECURSOS DEL SISTEMA")
    print(f"  {'-' * (ancho - 4)}")
    print(f"  CPU Usage      : {cpu}%")
    print(f"  Memoria Total  : {mem.total / (1024 ** 3):.2f} GB")
    print(f"  Memoria Usada  : {mem.percent}%")
    print(f"  Disco Total    : {disk.total / (1024 ** 3):.2f} GB")
    print(f"  Disco Libre    : {(disk.total - disk.used) / (1024 ** 3):.2f} GB ({100 - disk.percent:.1f}%)")

    # Hostnames configurados
    print(f"\n  HOSTNAMES CONFIGURADOS ({len(lista_hostnames)})")
    print(f"  {'-' * (ancho - 4)}")
    hostnames_str = ", ".join(lista_hostnames[:10])  # Mostrar máximo 10
    if len(lista_hostnames) > 10:
        hostnames_str += f", ... (+{len(lista_hostnames) - 10} mas)"
    print(f"  {hostnames_str}")

    print(f"\n{linea}")
    print(f"  >> Iniciando procesamiento de logs...")
    print(linea)
    print()

def fin_programa():
    """Banner de finalización con estadísticas"""
    tiempo_ejecucion_fin = time.perf_counter()
    tiempo_total = tiempo_ejecucion_fin - tiempo_ejecucion_inicio
    ancho = 80
    linea = "=" * ancho

    print()
    print(linea)
    print(f"{'PROCESAMIENTO COMPLETADO':^{ancho}}")
    print(linea)

    # Estadísticas de ejecución
    print(f"\n  TIEMPO DE EJECUCION")
    print(f"  {'-' * (ancho - 4)}")
    horas = int(tiempo_total // 3600)
    minutos = int((tiempo_total % 3600) // 60)
    segundos = tiempo_total % 60

    if horas > 0:
        print(f"  Tiempo total   : {horas}h {minutos}m {segundos:.2f}s")
    elif minutos > 0:
        print(f"  Tiempo total   : {minutos}m {segundos:.2f}s")
    else:
        print(f"  Tiempo total   : {segundos:.6f} segundos")

    # Recursos finales
    mem_final = ps.virtual_memory()
    disk_final = ps.disk_usage(carpeta_actual)
    cpu_final = ps.cpu_percent(interval=1)
    net_final = ps.net_io_counters()

    print(f"\n  RECURSOS UTILIZADOS")
    print(f"  {'-' * (ancho - 4)}")
    print(f"  CPU Final      : {cpu_final}% (Inicio: {cpu}%)")
    print(f"  Memoria Usada  : {mem_final.percent}% de {mem_final.total / (1024 ** 3):.2f} GB")
    print(f"  Disco Usado    : {disk_final.percent}% de {disk_final.total / (1024 ** 3):.2f} GB")
    print(f"  Red (Enviado)  : {net_final.bytes_sent / (1024 ** 2):.2f} MB")
    print(f"  Red (Recibido) : {net_final.bytes_recv / (1024 ** 2):.2f} MB")

    print(f"\n{linea}")
    print(f"  {'Desarrollada por Abregu Tomas y Andres Moraldo ':^{ancho}}")
    print(f"  {'(c) ' + str(datetime.datetime.now().year) + ' Mirgor - All Rights Reserved':^{ancho}}")
    print(linea)
    print()

inicio_programa()
for root, dirs, files in os.walk(logs_path):
    hostname = os.path.basename(root)
    if hostname in lista_hostnames:
        fecha_ultima = consultas_sql.ultimo_registro_por_hostname(hostname)
        fecha_ultima_ejecucion = None
        if fecha_ultima and ('fecha' in fecha_ultima or 'Fecha' in fecha_ultima) and (fecha_ultima.get('fecha') or fecha_ultima.get('Fecha')) is not None:
            val = fecha_ultima.get('fecha', fecha_ultima.get('Fecha'))
            if hasattr(val, 'strftime'):
                fecha_ultima_ejecucion = val
            else:
                try:
                    fecha_ultima_ejecucion = datetime.datetime.strptime(str(val), "%Y-%m-%d").date()
                except Exception:
                    fecha_ultima_ejecucion = None
        datos_a_guardar = []  # Lista de tuplas (registros, tests)
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
                    registros, tests = Captura.Procesar_archivo(ruta_completa)  # Ahora retorna tupla
                    datos_a_guardar.append((registros, tests))

        if datos_a_guardar:
            ultimo_registo = consultas_sql.ultimo_registro_por_hostname(hostname)
            fecha_ultima = ultimo_registo.get('fecha', ultimo_registo.get('Fecha')) if ultimo_registo else None
            hora_ultima = ultimo_registo.get('hora', ultimo_registo.get('Hora')) if ultimo_registo else None
            print(f"Ultimo registro en DB para {hostname}: {fecha_ultima} {hora_ultima}")

            # Consolidar todos los datos
            todos_registros = []
            todos_tests = []
            for registros, tests in datos_a_guardar:
                # Formatear en memoria (sin CSV intermedio)
                registros_fmt, tests_fmt = Captura.formatear_datos_para_insercion(
                    (registros, tests), hostname, medio, planta, medio_id
                )
                todos_registros.extend(registros_fmt)
                todos_tests.extend(tests_fmt)

            # Deduplicar registros (mantener lógica existente)
            registros_no_duplicados = consultas_sql.evitar_duplicados(todos_registros)

            # Filtrar tests cuyos registros padre fueron duplicados
            claves_validas = set()
            for reg in registros_no_duplicados:
                fecha_iso = consultas_sql.normalizar_fecha(reg[0])
                hora_hms = consultas_sql.normalizar_hora(reg[1])
                serial = str(reg[3]) if reg[3] else ""
                hostname_reg = str(reg[7]) if reg[7] else ""
                claves_validas.add((fecha_iso, hora_hms, serial, hostname_reg))

            tests_no_duplicados = []
            for test in todos_tests:
                fecha_iso = consultas_sql.normalizar_fecha(test[0])
                hora_hms = consultas_sql.normalizar_hora(test[1])
                serial = str(test[2]) if test[2] else ""
                hostname_test = str(test[3]) if test[3] else ""
                clave = (fecha_iso, hora_hms, serial, hostname_test)
                if clave in claves_validas:
                    tests_no_duplicados.append(test)

            # Inserción combinada optimizada
            registros_ok, tests_ok = consultas_sql.Insertar_registros_con_tests(
                registros_no_duplicados, tests_no_duplicados
            )

            print(f"\nInsertados para hostname {hostname}:")
            print(f"  - {registros_ok} registros")
            print(f"  - {tests_ok} tests")
            print("--------------------------------------------------")

fin_programa()