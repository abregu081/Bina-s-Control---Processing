# ConectorDB.py
import pymysql
import Configuraciones as cfg

class ConectorDB:
    def __init__(self):
        self.configuraciones = cfg.Configuraciones()
        self.datos = self.configuraciones.obtener_datos_parametros_db()
        self.host, self.user, self.password, self.database = self.datos[:4]

        self.conn = None
        self.cursor = None
        self.conexion = False

    def conectar_db(self):
        self.conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        self.cursor = self.conn.cursor()
        self.conexion = True

    def cerrar_conexion(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.cursor = None
        self.conn = None
        self.conexion = False
