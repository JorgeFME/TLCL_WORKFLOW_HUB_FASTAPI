import logging
from typing import Generator, Optional

from fastapi import Depends

from app.core.config import Settings
from app.dependencies import get_settings


# Logger seguro: no depende de uvicorn y configura un handler por defecto
logger = logging.getLogger("tlcl-hub")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("tlcl-hub")

try:
    from hdbcli import dbapi
except Exception as e:
    dbapi = None
    logger.warning("hdbcli no está disponible: %s", e)


def connect_hana(settings: Settings):
    """Crea una conexión a SAP HANA usando hdbcli."""
    if dbapi is None:
        raise RuntimeError("El cliente hdbcli no está instalado. Instale 'hdbcli'.")

    params = {
        "address": settings.HANA_HOST,
        "port": settings.HANA_PORT or 443,
        "user": settings.HANA_USER,
        "password": settings.HANA_PASSWORD,
        "encrypt": settings.HANA_ENCRYPT,
        "sslValidateCertificate": settings.HANA_SSL_VALIDATE,
    }

    if settings.HANA_SSL_TRUST_STORE:
        params["sslTrustStore"] = settings.HANA_SSL_TRUST_STORE

    conn = dbapi.connect(**params)

    if settings.HANA_SCHEMA:
        try:
            cursor = conn.cursor()
            cursor.execute(f'SET SCHEMA "{settings.HANA_SCHEMA}"')
            cursor.close()
        except Exception as e:
            logger.warning("No se pudo establecer SCHEMA: %s", e)

    return conn


def get_hana_connection(settings: Settings = Depends(get_settings)) -> Generator:
    """Dependencia de FastAPI que entrega una conexión y la cierra al finalizar."""
    conn = connect_hana(settings)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute_query(conn, sql: str, params: Optional[tuple] = None):
    """Ejecuta una consulta y devuelve una lista de dicts (filas)."""
    cur = conn.cursor()
    try:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        # Algunas consultas/procedimientos pueden no retornar result set.
        try:
            rows = cur.fetchall()
        except Exception:
            rows = []
        # Obtener nombres de columnas desde cursor.description
        columns = [desc[0] for desc in (cur.description or [])]
        if not columns:
            # Si no hay metadata, devolver filas crudas
            return rows
        return [dict(zip(columns, row)) for row in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def call_procedure_with_outputs(conn, proc_name: str, params: Optional[tuple] = None):
    """
    Llama un stored procedure y captura tanto result sets como parámetros OUT.
    
    Retorna un dict con:
    - 'output_params': valores de parámetros OUT (si existen)
    - 'result_sets': lista de result sets (si existen)
    """
    cur = conn.cursor()
    try:
        args = list(params) if params else []
        
        # callproc puede modificar args si hay parámetros OUT
        result = cur.callproc(proc_name, args)
        
        output_data = {
            'output_params': result if result != args else None,
            'result_sets': []
        }

        # Intentar capturar result sets
        def get_rows():
            try:
                if not cur.description:
                    return []
                rows_local = cur.fetchall()
                columns_local = [desc[0] for desc in cur.description]
                return [dict(zip(columns_local, row)) for row in rows_local]
            except Exception:
                return []

        # Primera result set
        first_set = get_rows()
        if first_set:
            output_data['result_sets'].append(first_set)
        
        # Result sets adicionales
        if hasattr(cur, "nextset"):
            while True:
                try:
                    has_more = cur.nextset()
                    if not has_more:
                        break
                    next_set = get_rows()
                    if next_set:
                        output_data['result_sets'].append(next_set)
                except Exception:
                    break
        
        return output_data
        
    finally:
        try:
            cur.close()
        except Exception:
            pass