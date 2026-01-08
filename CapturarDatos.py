import os, csv, re
import Configuraciones as cfg
import datetime
import ConsultasSQL as SQL

consultas_sql = SQL.ConsultasSQL()
config = cfg.Configuraciones()
logs_path = config.obtenerv_datos_configuracionees()[4]
hostnames_tuplas = config.obtener_datos_hostname()
lista_hostnames = [h[1] for h in hostnames_tuplas]
medio = config.obtenerv_datos_configuracionees()[0]
planta = config.obtenerv_datos_configuracionees()[2]
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
carpeta_escenario = os.path.join(carpeta_actual, "Escenario")
os.makedirs(carpeta_escenario, exist_ok=True)
archivo_series = os.path.join(carpeta_escenario, "SeriesCapturados.csv")
medio_id = consultas_sql.obtener_medio_id(medio)
medio_id = medio_id['ID_Medios_de_produccion'] if medio_id else None

# mas que nada son para armar el registro en la tabla Registros 
palabras_clave = [
    "DATE :", "MODEL :", "P/N :", "TIME :",
    "PROGRAM :", "INIFILE :", "FAILITEM :",
    "IMEINO :", "SKU :", "TEST-TIME :", "RESULT :", "JIG :", "BOX :"]

def cambiar_formato_fecha(fecha):
    año, mes, dia = fecha.split("/")
    return f"{dia}/{mes}/{año}"

def Procesar_archivo(archivo):
    inicio_registro = "#INIT"
    final_registro = "//PC_RAM_END"
    patron = re.compile(
        rf"{re.escape(inicio_registro)}.*?{re.escape(final_registro)}.*?$",
        re.DOTALL | re.MULTILINE
    )
    resultados = []
    with open(archivo, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
        bloques = patron.findall(contenido)
    for bloque in bloques:
        datos_registro = {}
        for linea in bloque.splitlines():
            for palabra in palabras_clave:
                if linea.startswith(palabra):
                    clave = palabra.replace(" :", "").strip()
                    valor = linea.replace(palabra, "").strip()
                    datos_registro[clave] = valor
        resultados.append(datos_registro)
    return resultados

def Guardar_datos_stage_csv(lista_datos, hostname_path):
    campos = ["Fecha","Hora","Modelo","Serial","Resultado","Detalle",
              "Medio","Hostname","Planta","Banda","Box","IMEI","SKU","TestTime","Runtime",
              "ModelFile","Medio_id"]
    # si no existe, escribo header. Si existe, solo append
    existe = os.path.exists(archivo_series)
    with open(archivo_series, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=campos)
        if not existe:
            writer.writeheader()

        for dato in lista_datos:
            fecha_original = dato.get("DATE", "")
            writer.writerow({
                "Fecha": cambiar_formato_fecha(fecha_original) if fecha_original else "",
                "Hora": dato.get("TIME", ""),
                "Serial": dato.get("P/N", ""),
                "Resultado": dato.get("RESULT", ""),
                "Detalle": dato.get("FAILITEM", ""),
                "Medio": medio,
                "Modelo": dato.get("MODEL", ""),
                "Hostname": hostname_path,
                "Planta": planta,
                "Banda": "",
                "Box": f"0{dato.get("BOX", "")}",
                "IMEI": dato.get("IMEINO", ""),
                "SKU": dato.get("SKU", ""),
                "TestTime": dato.get("TEST-TIME", ""),
                "Runtime": "",
                "ModelFile": "",
                "Medio_id": medio_id
            })
