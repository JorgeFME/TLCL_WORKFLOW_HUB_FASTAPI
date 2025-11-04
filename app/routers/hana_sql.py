from fastapi import APIRouter, Depends, Query

from app.db.hana import get_hana_connection, execute_query
from app.dependencies import get_settings
from app.core.config import Settings


router = APIRouter(prefix="/tlcl-hub", tags=["HANA DB - SQL"])


@router.get("/ee-site")
def list_ee_site(
    limit: int = Query(10, ge=1, le=1000),
    conn=Depends(get_hana_connection),
    settings: Settings = Depends(get_settings),
):
    """Devuelve hasta 'limit' filas de TELCEL_EE_SITE."""
    # Construir tabla calificada con el schema si está disponible
    if settings.HANA_SCHEMA:
        table_name = f'"{settings.HANA_SCHEMA}".TELCEL_EE_SITE'
    else:
        table_name = "TELCEL_EE_SITE"

    # LIMIT no siempre admite bind param; validamos entero y lo interpolamos
    sql = f"SELECT * FROM {table_name} LIMIT {int(limit)}"
    rows = execute_query(conn, sql)
    return {"count": len(rows), "rows": rows}