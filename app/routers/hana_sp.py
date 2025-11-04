import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Body
from pydantic import BaseModel

from app.db.hana import get_hana_connection, call_procedure_with_outputs

# Agregar esta línea para el logger
logger = logging.getLogger("uvicorn.error")


router = APIRouter(prefix="/tlcl-hub", tags=["HANA Stored Procedures"])

class TLCL01Payload(BaseModel):
    p1: str
    p2: str


@router.post("/tlcl01", summary="TLCL01")
def call_tlcl01(
    payload: TLCL01Payload = Body(..., description="Parámetros para SP_TLCL_01"),
    conn=Depends(get_hana_connection),
):
    """Ejecuta el stored procedure SP_TLCL_01 y devuelve su resultado."""
    proc_name = '"B4B85072923A44789F391B1E8CB24202"."SP_TLCL_01"'
    
    try:
        # Llamar al procedimiento con la nueva función
        result = call_procedure_with_outputs(conn, proc_name, (payload.p1, payload.p2))
        
        # Extraer datos de salida
        output_params = result.get('output_params')
        result_sets = result.get('result_sets', [])
        
        # Preparar respuesta
        response = {
            "success": False,
            "success_flag": None,
            "message": "No se recibieron datos del procedimiento",
            "output_params": output_params,
            "result_sets_count": len(result_sets),
        }
        
        # Si hay result sets, usar el primero
        if result_sets and len(result_sets) > 0:
            first_set = result_sets[0]
            if first_set:
                first_row = first_set[0]
                response.update({
                    "success": True,
                    "success_flag": first_row.get("SUCCESS_FLAG"),
                    "message": first_row.get("MESSAGE"),
                    "rows": first_set,
                    "count": len(first_set)
                })
        
        # Si hay parámetros OUT, también incluirlos
        if output_params:
            response["output_params"] = output_params
            # Si los parámetros OUT son SUCCESS_FLAG y MESSAGE
            if len(output_params) >= 2:
                response.update({
                    "success": True,
                    "success_flag": output_params[0],
                    "message": output_params[1]
                })
        
        return response
        
    except Exception as e:
        logger.error(f"Error ejecutando procedimiento {proc_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando procedimiento: {str(e)}"
        )