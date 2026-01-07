import ConsultasSQL as sql
import os
import Configuraciones as cfg
import datetime
import csv
import threading as th
import re

config = cfg.Configuraciones()
nombre_estacion = config.obtenerv_datos_configuracionees()[0]
logs_path = config.obtenerv_datos_configuracionees()[4]
hostnames = config.obtener_datos_hostname() # lista con tupla
lista_hostnames = [hostname[1] for hostname in hostnames] # lista normal
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
palabras_clave=[
            "DATE :", "MODEL :", "P/N :", "TIME :",
            "PROGRAM :", "INIFILE :", "FAILITEM :",
            "IMEINO :", "SKU :", "TEST-TIME :", "RESULT :", "JIG :","BOX :"]

#Carpetas para este invento que quiero hacer
carpeta_escenario = os.path.join(carpeta_actual, 'Escenario')
archivo_series = os.path.join(carpeta_escenario, 'SeriesCapturadas.csv')
archivo_tests =  os.path.join(carpeta_escenario, 'TestsCapturados.csv')
if not os.path.exists(carpeta_escenario):
    os.mkdir(carpeta_escenario)


#archivo_para_practicar = r"52245228_OQC_TOP501_20250705_01.csv"

def cambiar_formato_fecha(fecha):
    año, mes, dia = fecha.split("/")
    return f"{dia}/{mes}/{año}"

def Procesar_archivo(archivo):
    inicio_registro = "#INIT"
    final_registro = "//PC_RAM_END"
    resultados = []
    registro = re.compile(rf"{re.escape(inicio_registro)}.*?{re.escape(final_registro)}.*?$",re.DOTALL | re.MULTILINE)
    with open(archivo,"r",encoding="utf-8",errors="ignore") as file:
        contenido = file.read()
        bloques = registro.findall(contenido)
        #print(f"Se encontraron {len(bloques)} bloques de registros en el archivo.")
        for bloque in bloques:
            lineas = bloque.splitlines()
            datos_registro = {}
            for linea in lineas:
                for palabra in palabras_clave:
                    if linea.startswith(palabra):
                        clave = palabra.replace(" :", "").strip()
                        valor = linea.replace(palabra, "").strip()
                        datos_registro[clave] = valor
            resultados.append(datos_registro)
    return resultados

def Guardar_datos_stage_csv(lista_datos):
    datos = lista_datos
    nombre = "Archivo_prueba.csv"
    ruta_completa = os.path.join(carpeta_escenario, nombre)
    with open(ruta_completa, mode='w', newline='', encoding='utf-8') as file:
        campos = ["Fecha","Hora","Serial","Resultado","Detalle",
                  "Medio","Hostname","Planta","Banda","Box","IMEI","SKU","TestTime","Runtime",
                  "ModelFile","Medio_id"]
        writer = csv.DictWriter(file, fieldnames=campos)
        writer.writeheader()
        for dato in datos:
            fecha_original = dato.get("DATE", "")
            fecha_formateada = cambiar_formato_fecha(fecha_original) if fecha_original else ""
            hora = dato.get("TIME", "")
            serial = dato.get("P/N", "")
            resultado = dato.get("RESULT", "")
            detalle = dato.get("FAILITEM", "")
            medio = ""
            hostname = ""
            planta = ""
            banda = ""
            box = dato.get("BOX", "")
            imei = dato.get("IMEINO", "")
            sku = dato.get("SKU", "")
            test_time = dato.get("TEST-TIME", "")
            runtime = ""  
            modelfile = dato.get("MODEL", "")
            medio_id = ""

            fila = {
                "Fecha": fecha_formateada,
                "Hora": hora,
                "Serial": serial,
                "Resultado": resultado,
                "Detalle": detalle,
                "Medio": medio,
                "Hostname": hostname,
                "Planta": planta,
                "Banda": banda,
                "Box": box,
                "IMEI": imei,
                "SKU": sku,
                "TestTime": test_time,
                "Runtime": runtime,
                "ModelFile": modelfile,
                "Medio_id": medio_id
            }
            writer.writerow(fila)
    print(f"Datos guardados en {ruta_completa}")


print(nombre_estacion)
print(hostnames)

