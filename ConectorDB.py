import sys
import os
import pymysql
import Configuraciones as cfg

class ConectorDB:
    def __init__(self):
        self.conexion = False
        self.configuraciones = cfg.Configuraciones()
        self.datos = self.configuraciones.obtener_datos_parametros_db()
        self.host = self.datos[0]
        self.user = self.datos[1]
        self.password = self.datos[2]
        self.database = self.datos[3]
        self.conn = None
        if self.conn != None:
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        else:
            self.cursor = None

    def conectar_db(self):
        conexion = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )
        if conexion.open:
            self.conn = conexion
            self.conexion = True
        else:
            raise Exception("No se pudo conectar a la base de datos")
    
    def cerrar_conexion(self):
        if self.conn:
            self.conn.close()
            self.conexion = False
    
    def reconexion_db(self):
        self.cerrar_conexion()
        self.conectar_db()


    