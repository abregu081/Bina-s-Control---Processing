import os, csv, re
import sys
import Configuraciones as cfg
import datetime

# Palabras clave para extraer campos del encabezado de cada bloque
palabras_clave = [
    "DATE :", "MODEL :", "P/N :", "TIME :",
    "PROGRAM :", "INIFILE :", "FAILITEM :",
    "IMEINO :", "SKU :", "TEST-TIME :", "RESULT :", "JIG :", "BOX :", "Mode", "ModelFile :"]


def cambiar_formato_fecha(fecha):
    """
    Convierte una fecha al formato dd/mm/yyyy.
    Acepta: yyyy/mm/dd, yyyy-mm-dd, dd/mm/yyyy, dd-mm-yyyy.
    Retorna "" si el formato no es reconocido, nunca lanza excepción (BUG-03 fix).
    """
    fecha_str = str(fecha).strip()
    if not fecha_str:
        return ""
    for sep in ("/", "-"):
        if sep in fecha_str:
            partes = fecha_str.split(sep)
            if len(partes) == 3:
                if len(partes[0]) == 4:  # yyyy/mm/dd o yyyy-mm-dd → dd/mm/yyyy
                    return f"{partes[2]}/{partes[1]}/{partes[0]}"
                else:                     # dd/mm/yyyy o dd-mm-yyyy → normalizar a dd/mm/yyyy
                    return f"{partes[0]}/{partes[1]}/{partes[2]}"
    return ""


def procesar_test(bloque):
    """
    Extrae tests individuales de la sección #TEST...#END del bloque CSV.

    Formato de cada línea:
        TestName [Unit], MeasuredValue, LowerLimit, UpperLimit, P/F, Time
        Ejemplo: PWR: Measure Input Voltage [V], 13.97, 13.80, 14.20, P, 0.2884119

    Args:
        bloque: String conteniendo un bloque completo del CSV (#INIT...//PC_RAM_END)

    Returns:
        Lista de dicts con campos: TestNombre, Unidad, Valor, ValorLimit_Low,
        ValorLimit_High, Resultado para cada test encontrado
    """
    inicio = bloque.find("#TEST")
    if inicio == -1:
        return []

    # Buscar fin de la sección de tests (marcador #END)
    fin = bloque.find("#END", inicio)
    if fin == -1:
        # Fallback: buscar "RESULT :" si no hay #END
        fin = bloque.find("RESULT :", inicio)

    seccion_tests = bloque[inicio:fin] if fin != -1 else bloque[inicio:]
    lineas = seccion_tests.splitlines()

    tests = []
    for linea in lineas:
        # Saltar línea #TEST inicial
        if linea.strip().startswith("#TEST"):
            continue
        # Saltar comentarios
        if linea.strip().startswith("/*") or linea.strip().startswith("==="):
            continue
        # Saltar líneas vacías
        if not linea.strip():
            continue

        # Parsear línea: split por coma
        partes = linea.split(",")
        if len(partes) < 6:
            continue  # Línea mal formada, saltar

        # Extraer nombre del test y unidad
        nombre_completo = partes[0].strip()
        # Buscar unidad entre corchetes: "TestName [Unit]"
        if "[" in nombre_completo and "]" in nombre_completo:
            inicio_bracket = nombre_completo.find("[")
            fin_bracket = nombre_completo.find("]")
            test_nombre = nombre_completo[:inicio_bracket].strip()
            unidad = nombre_completo[inicio_bracket+1:fin_bracket].strip()
        else:
            test_nombre = nombre_completo
            unidad = ""

        # Remover # inicial si existe (tests comentados)
        if test_nombre.startswith("#"):
            test_nombre = test_nombre[1:].strip()

        try:
            valor = float(partes[1].strip()) if partes[1].strip() else None
            low = float(partes[2].strip()) if partes[2].strip() else None
            high = float(partes[3].strip()) if partes[3].strip() else None
            resultado = partes[4].strip()  # "P" o "F"
            tiempo = float(partes[5].strip()) if partes[5].strip() else None

            test_dict = {
                "TestNombre": test_nombre,
                "Unidad": unidad,
                "Valor": valor,
                "ValorLimit_Low": low,
                "ValorLimit_High": high,
                "Resultado": resultado,
                "Tiempo": tiempo  # Opcional, no se guarda en DB
            }
            tests.append(test_dict)
        except (ValueError, IndexError):
            continue

    return tests


def Procesar_archivo(archivo):
    inicio_registro = "#INIT"
    final_registro = "//PC_RAM_END"
    patron = re.compile(
        rf"{re.escape(inicio_registro)}.*?{re.escape(final_registro)}.*?$",
        re.DOTALL | re.MULTILINE
    )
    resultados = []
    todos_los_tests = []

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

        # Extraer tests de este bloque
        test_resultados = procesar_test(bloque)

        # Agregar campos identificadores a cada test
        fecha = datos_registro.get("DATE", "")
        hora = datos_registro.get("TIME", "")
        serial = datos_registro.get("P/N", "")

        for test in test_resultados:
            test["Fecha"] = fecha
            test["Hora"] = hora
            test["Serial"] = serial
            todos_los_tests.append(test)

        resultados.append(datos_registro)

    return (resultados, todos_los_tests)


def formatear_datos_para_insercion(datos_procesados, hostname, medio_param, planta_param, medio_id_param):
    """
    Formatea registros y tests en memoria sin archivos intermedios.

    Args:
        datos_procesados: tuple (registros, tests) desde Procesar_archivo()
        hostname: nombre del hostname/estación
        medio_param: nombre del medio de producción
        planta_param: código de planta
        medio_id_param: ID del medio en la tabla Medios_de_produccion

    Returns:
        tuple (registros_formateados, tests_formateados)
    """
    registros, tests = datos_procesados

    registros_formateados = []
    for dato in registros:
        # Aplicar lógica de BOX fallback (si BOX vacío o "0", usar JIG)
        box_crudo = dato.get("BOX", "").strip()
        if not box_crudo or box_crudo == "0":
            box_crudo = dato.get("JIG", "").strip()
        box_value = f"{box_crudo}" if box_crudo else ""

        # Convertir fecha de yyyy/mm/dd a dd/mm/yyyy
        fecha_original = dato.get("DATE", "")
        fecha_formateada = cambiar_formato_fecha(fecha_original) if fecha_original else ""

        # Crear lista de 17 campos en orden correcto
        # Formato: [Fecha, Hora, Modelo, Serial, Resultado, Detalle, Medio,
        #           Hostname, Planta, Banda, Box, IMEI, SKU, TestTime, Runtime,
        #           ModelFile, Medio_id]
        registro_lista = [
            fecha_formateada,
            dato.get("TIME", ""),
            dato.get("MODEL", ""),
            dato.get("P/N", ""),
            dato.get("RESULT", ""),
            dato.get("FAILITEM", ""),
            medio_param,
            hostname,
            planta_param,
            "",  # Banda (vacío)
            box_value,
            dato.get("IMEINO", ""),
            dato.get("SKU", ""),
            dato.get("TEST-TIME", ""),
            "",  # Runtime (vacío)
            dato.get("ModelFile", ""),
            medio_id_param
        ]
        registros_formateados.append(registro_lista)

    tests_formateados = []
    for test in tests:
        # Normalizar fecha a dd/mm/yyyy
        fecha_test = test.get("Fecha", "")
        fecha_formateada_test = cambiar_formato_fecha(fecha_test) if fecha_test else ""

        # Crear lista de 10 campos: [Fecha, Hora, Serial, Hostname,
        #                             TestNombre, Valor, ValorLimit_Low,
        #                             ValorLimit_High, Unidad, Resultado]
        test_lista = [
            fecha_formateada_test,
            test.get("Hora", ""),
            test.get("Serial", ""),
            hostname,
            test.get("TestNombre", ""),
            test.get("Valor"),
            test.get("ValorLimit_Low"),
            test.get("ValorLimit_High"),
            test.get("Unidad", ""),
            test.get("Resultado", "")
        ]
        tests_formateados.append(test_lista)

    return (registros_formateados, tests_formateados)
