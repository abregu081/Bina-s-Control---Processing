"""
BinasControl Service — Servicio persistente de captura de logs de testing.

Reemplaza los 8 ejecutables separados (uno por medio) con un único proceso
que monitorea todos los directorios simultáneamente usando watchdog (file events),
procesa archivos CSV en tiempo real con debounce, y serializa las inserciones
a MySQL a través de un único hilo de DB para evitar conflictos de concurrencia.

Arquitectura:
  - WatchdogObserver (1 por medio): detecta archivos CSV nuevos/modificados.
  - CSVEventHandler: aplica debounce de 2 segundos por archivo (espera fin de escritura).
  - FileProcessor: parsea CSV y encola DBTask.
  - DBWorker (único): consume la cola, deduplica e inserta en MySQL.
  - BinasControlService: orquesta todo; boot scan al inicio; shutdown graceful.
"""

import os
import sys
import threading
import queue
import logging
import signal
import time
from datetime import datetime
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import Configuraciones as cfg
import CapturarDatos as Captura
import ConsultasSQL as SQL


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging():
    """Configura logging: archivo rotativo (WARNING+) y consola (INFO+)."""
    if getattr(sys, 'frozen', False):
        carpeta = os.path.dirname(sys.executable)
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))

    log_file = os.path.join(carpeta, "errores_procesamiento.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(threadName)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class DBTask:
    """Unidad de trabajo que viaja de FileProcessor → DBWorker."""
    medio_nombre: str
    hostname: str
    registros: list
    tests: list
    source_file: str


# ---------------------------------------------------------------------------
# Watchdog handler con debounce por archivo
# ---------------------------------------------------------------------------

class CSVEventHandler(FileSystemEventHandler):
    """
    Detecta CSVs creados o modificados y aplica debounce de 2 segundos.
    El timer se reinicia con cada evento nuevo sobre el mismo archivo,
    garantizando que el archivo esté completamente escrito antes de procesarlo.
    """

    DEBOUNCE_SECONDS = 2.0

    def __init__(self, file_processor):
        super().__init__()
        self.file_processor = file_processor
        self._pending: dict = {}   # path → threading.Timer
        self._lock = threading.Lock()

    def _schedule(self, path: str):
        with self._lock:
            existing = self._pending.pop(path, None)
            if existing:
                existing.cancel()
            t = threading.Timer(self.DEBOUNCE_SECONDS, self._fire, args=[path])
            self._pending[path] = t
            t.start()

    def _fire(self, path: str):
        with self._lock:
            self._pending.pop(path, None)
        try:
            self.file_processor.process_file(path)
        except Exception as e:
            logging.error(f"Error procesando {path}: {e}", exc_info=True)

    def flush_all(self):
        """
        En shutdown: cancela todos los timers pendientes y los procesa
        de inmediato para no perder archivos que estaban en debounce.
        """
        with self._lock:
            pending = dict(self._pending)
            self._pending.clear()
        for path, timer in pending.items():
            timer.cancel()
            try:
                self.file_processor.process_file(path)
            except Exception as e:
                logging.error(f"Error en flush de {path}: {e}", exc_info=True)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            self._schedule(event.src_path)


# ---------------------------------------------------------------------------
# Procesador de archivos (parseo + encolado)
# ---------------------------------------------------------------------------

class FileProcessor:
    """Parsea un archivo CSV y encola un DBTask para el DBWorker."""

    def __init__(self, medio_config, db_queue):
        self.medio_config = medio_config
        self.db_queue = db_queue

    def process_file(self, path: str):
        # Determinar hostname a partir del directorio padre del archivo
        hostname = os.path.basename(os.path.dirname(path))
        if hostname not in self.medio_config.hostnames:
            return  # Archivo en subdirectorio que no corresponde a un hostname configurado

        try:
            registros_raw, tests_raw = Captura.Procesar_archivo(path)
        except Exception as e:
            logging.error(
                f"[{self.medio_config.nombre}] Error leyendo {os.path.basename(path)}: {e}",
                exc_info=True
            )
            return

        if not registros_raw:
            return

        try:
            registros_fmt, tests_fmt = Captura.formatear_datos_para_insercion(
                (registros_raw, tests_raw),
                hostname,
                self.medio_config.nombre,
                self.medio_config.planta,
                self.medio_config.medio_id,
            )
        except Exception as e:
            logging.error(
                f"[{self.medio_config.nombre}] Error formateando {os.path.basename(path)}: {e}",
                exc_info=True
            )
            return

        if not registros_fmt:
            return

        task = DBTask(
            medio_nombre=self.medio_config.nombre,
            hostname=hostname,
            registros=registros_fmt,
            tests=tests_fmt,
            source_file=path,
        )
        self.db_queue.put(task)
        logging.info(
            f"[{self.medio_config.nombre}/{hostname}] Encolado: "
            f"{os.path.basename(path)} ({len(registros_fmt)} registros, {len(tests_fmt)} tests)"
        )


# ---------------------------------------------------------------------------
# Worker de base de datos (único hilo — evita concurrencia en PyMySQL)
# ---------------------------------------------------------------------------

class DBWorker(threading.Thread):
    """
    Único hilo que serializa todas las inserciones a MySQL.
    Dueño exclusivo de la conexión DB (PyMySQL no es thread-safe).
    """

    def __init__(self, db_queue: queue.Queue):
        super().__init__(name="DBWorker", daemon=False)
        self.db_queue = db_queue
        self._sql = None
        self._stop_event = threading.Event()

    def run(self):
        logging.info("DBWorker iniciado.")
        self._sql = SQL.ConsultasSQL()

        while True:
            try:
                task = self.db_queue.get(timeout=1.0)
            except queue.Empty:
                if self._stop_event.is_set():
                    break
                continue

            if task is None:  # poison pill
                self.db_queue.task_done()
                break

            try:
                self._process_task(task)
            except Exception as e:
                logging.error(
                    f"Error fatal procesando {task.source_file}: {e}", exc_info=True
                )
            finally:
                self.db_queue.task_done()

        logging.info("DBWorker detenido.")

    def _process_task(self, task: DBTask):
        # Reconectar si la conexión se perdió (BUG-06)
        self._sql.coneccion_db.reconectar_si_necesario()
        self._sql.cursor = self._sql.coneccion_db.cursor

        registros_dedup = self._sql.evitar_duplicados(task.registros)
        if not registros_dedup:
            logging.info(
                f"[{task.medio_nombre}/{task.hostname}] "
                f"{os.path.basename(task.source_file)}: todos duplicados, nada que insertar"
            )
            return

        # Filtrar tests cuyos registros padre fueron descartados por deduplicación
        claves_validas = set()
        for reg in registros_dedup:
            fecha_iso = self._sql.normalizar_fecha(reg[0])
            hora_hms = self._sql.normalizar_hora(reg[1])
            serial = str(reg[3]) if reg[3] else ""
            hostname = str(reg[7]) if reg[7] else ""
            claves_validas.add((fecha_iso, hora_hms, serial, hostname))

        tests_dedup = []
        for test in task.tests:
            fecha_iso = self._sql.normalizar_fecha(test[0])
            hora_hms = self._sql.normalizar_hora(test[1])
            serial = str(test[2]) if test[2] else ""
            hostname = str(test[3]) if test[3] else ""
            if (fecha_iso, hora_hms, serial, hostname) in claves_validas:
                tests_dedup.append(test)

        reg_ok, test_ok = self._sql.Insertar_registros_con_tests(registros_dedup, tests_dedup)
        logging.info(
            f"[{task.medio_nombre}/{task.hostname}] "
            f"{os.path.basename(task.source_file)}: "
            f"{reg_ok} registros + {test_ok} tests insertados"
        )

    def stop(self):
        self._stop_event.set()
        self.db_queue.put(None)  # desbloquea el get() con poison pill


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------

class BinasControlService:
    """
    Orquesta todos los componentes:
    - Carga configuración unificada (todos los medios).
    - Obtiene medio_id de DB para cada medio.
    - Ejecuta boot scan (archivos llegados mientras el servicio estaba detenido).
    - Inicia WatchdogObservers para cada medio.
    - Maneja SIGTERM/SIGINT con shutdown graceful que drena la cola antes de salir.
    """

    def __init__(self):
        self._medios = cfg.Configuraciones.obtener_config_todos_medios()
        self._db_queue: queue.Queue = queue.Queue()
        self._db_worker = DBWorker(self._db_queue)
        self._observers = []
        self._handlers: list[CSVEventHandler] = []
        self._shutdown_event = threading.Event()

    def _resolve_medio_ids(self):
        """Consulta DB una vez al inicio para obtener el medio_id de cada medio."""
        sql_tmp = SQL.ConsultasSQL()
        for mc in self._medios:
            row = sql_tmp.obtener_medio_id(mc.nombre)
            mc.medio_id = row['id_medios_de_produccion'] if row else None
            if mc.medio_id is None:
                logging.error(
                    f"Medio '{mc.nombre}' no encontrado en DB — "
                    "verificar que el nombre en Configuraciones.cfg coincida exactamente con medios_de_produccion.nombre"
                )
        sql_tmp.coneccion_db.cerrar_conexion()

    def _boot_scan(self, medio_config, file_processor: FileProcessor):
        """
        Procesa archivos CSV que llegaron mientras el servicio estaba detenido.

        Estrategia de lotes diarios: en lugar de encolar un DBTask por archivo
        (lento para backlogs grandes), agrupa todos los archivos del mismo día
        y hostname en un único DBTask. Esto reduce las queries de dedup de
        N_archivos a N_dias, y las inserciones aprovechan al máximo los batch
        sizes de 30K/50K.

        Ejemplo: 1 año de backlog para 1 hostname = 365 DBTasks en vez de
        potencialmente cientos de miles de archivos individuales.
        """
        logging.info(f"[{medio_config.nombre}] Boot scan en {medio_config.logs_path} ...")
        sql_tmp = SQL.ConsultasSQL()

        hostname_last_date = {}
        for hostname in medio_config.hostnames:
            row = sql_tmp.ultimo_registro_por_hostname(hostname)
            if row:
                val = row.get('fecha', row.get('Fecha'))
                if hasattr(val, 'strftime'):
                    hostname_last_date[hostname] = val
                elif val:
                    try:
                        hostname_last_date[hostname] = datetime.strptime(str(val), "%Y-%m-%d").date()
                    except Exception:
                        hostname_last_date[hostname] = None

        sql_tmp.coneccion_db.cerrar_conexion()

        lotes_encolados = 0
        for root, dirs, files in os.walk(medio_config.logs_path):
            hostname = os.path.basename(root)
            if hostname not in medio_config.hostnames:
                continue

            last_date = hostname_last_date.get(hostname)

            # Agrupar archivos por fecha del nombre (YYYYMMDD en posición [3])
            archivos_por_dia: dict = {}
            for f in files:
                if not f.endswith('.csv'):
                    continue
                partes = f.split('_')
                if len(partes) < 4:
                    continue
                try:
                    file_date = datetime.strptime(partes[3], "%Y%m%d").date()
                except ValueError:
                    continue
                if last_date is None or file_date >= last_date:
                    archivos_por_dia.setdefault(file_date, []).append(f)

            # Procesar día a día en orden cronológico
            for dia in sorted(archivos_por_dia):
                todos_registros = []
                todos_tests = []

                for f in sorted(archivos_por_dia[dia]):
                    ruta = os.path.join(root, f)
                    try:
                        registros_raw, tests_raw = Captura.Procesar_archivo(ruta)
                    except Exception as e:
                        logging.error(f"[{medio_config.nombre}] Boot scan — error leyendo {f}: {e}")
                        continue

                    if not registros_raw:
                        continue

                    try:
                        registros_fmt, tests_fmt = Captura.formatear_datos_para_insercion(
                            (registros_raw, tests_raw),
                            hostname,
                            medio_config.nombre,
                            medio_config.planta,
                            medio_config.medio_id,
                        )
                    except Exception as e:
                        logging.error(f"[{medio_config.nombre}] Boot scan — error formateando {f}: {e}")
                        continue

                    todos_registros.extend(registros_fmt)
                    todos_tests.extend(tests_fmt)

                if todos_registros:
                    task = DBTask(
                        medio_nombre=medio_config.nombre,
                        hostname=hostname,
                        registros=todos_registros,
                        tests=todos_tests,
                        source_file=f"boot_scan:{hostname}:{dia}",
                    )
                    self._db_queue.put(task)
                    lotes_encolados += 1
                    logging.info(
                        f"[{medio_config.nombre}/{hostname}] "
                        f"Boot scan {dia}: {len(todos_registros)} registros, "
                        f"{len(todos_tests)} tests encolados"
                    )

        logging.info(f"[{medio_config.nombre}] Boot scan completo: {lotes_encolados} lotes encolados")

    def start(self):
        setup_logging()
        logging.info("=" * 60)
        logging.info(f"BinasControl Service iniciando — {len(self._medios)} medios configurados")
        for mc in self._medios:
            logging.info(f"  {mc.nombre}: {mc.logs_path} ({len(mc.hostnames)} hostnames)")
        logging.info("=" * 60)

        # Obtener medio_ids antes de arrancar cualquier cosa
        self._resolve_medio_ids()

        # Registrar manejadores de señales
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Arrancar worker de DB
        self._db_worker.start()

        for mc in self._medios:
            if mc.medio_id is None:
                logging.error(
                    f"[{mc.nombre}] Nombre de medio no encontrado en la DB "
                    f"(¿está mal escrito en Configuraciones.cfg?) — saltando este medio"
                )
                continue
            if not mc.logs_path or not os.path.isdir(mc.logs_path):
                logging.error(
                    f"[{mc.nombre}] logs_path '{mc.logs_path}' "
                    "no existe o no es un directorio — saltando este medio"
                )
                continue

            fp = FileProcessor(mc, self._db_queue)
            handler = CSVEventHandler(fp)
            observer = Observer()
            observer.schedule(handler, mc.logs_path, recursive=True)

            self._handlers.append(handler)
            self._observers.append(observer)

            # Boot scan ANTES de iniciar el observer: evita events duplicados
            self._boot_scan(mc, fp)

            observer.start()
            logging.info(f"[{mc.nombre}] Observando {mc.logs_path}")

        logging.info("Servicio activo. Esperando archivos... (Ctrl+C o SIGTERM para detener)")
        self._shutdown_event.wait()
        self._stop()

    def _handle_signal(self, signum, frame):
        logging.info(f"Señal {signum} recibida — iniciando shutdown graceful...")
        self._shutdown_event.set()

    def _stop(self):
        logging.info("Deteniendo observers...")
        for obs in self._observers:
            obs.stop()
        for obs in self._observers:
            obs.join()

        # Forzar procesamiento de archivos que estaban en debounce
        logging.info("Flushing timers pendientes...")
        for handler in self._handlers:
            handler.flush_all()

        # Esperar que la cola de DB quede completamente vacía (cero pérdida de datos)
        logging.info("Esperando que la cola de DB quede vacía...")
        self._db_queue.join()

        # Detener el worker
        self._db_worker.stop()
        self._db_worker.join(timeout=30)

        logging.info("BinasControl Service detenido limpiamente.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    BinasControlService().start()
