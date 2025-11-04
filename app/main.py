from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import hana_sql
from app.routers import hana_sp
from app.core.config import Settings
from app.dependencies import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="TLCL Processes Hub", version="0.1.0")

    # Configuración CORS desde entorno
    settings = get_settings()

    def _to_list(value: str | None, default: list[str]) -> list[str]:
        if not value:
            return default
        v = value.strip()
        if v == "*":
            return ["*"]
        return [item.strip() for item in v.split(",") if item.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_to_list(settings.CORS_ALLOW_ORIGINS, ["*"]),
        allow_methods=_to_list(settings.CORS_ALLOW_METHODS, ["*"]),
        allow_headers=_to_list(settings.CORS_ALLOW_HEADERS, ["*"]),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    )

    # Routers
    app.include_router(hana_sql.router)
    app.include_router(hana_sp.router)

    app.summary = "API para ejecutar procesos SQL y Stored Procedures en HANA"
    # Root: información básica y enlaces útiles con el prefijo
    @app.get("/", tags=["General"], summary="Root")
    def root(settings: Settings = Depends(get_settings)):
        return {
            "name": "TLCL Processes Hub",
            "version": "0.1.0",
            "base_path": "/tlcl-hub",
            "sections": {
                "General": {"root": "/"},
                "HANA DB - SQL": {
                    "ee_site": {
                        "path": "/tlcl-hub/ee-site",
                        "description": "Lista filas de TELCEL_EE_SITE",
                        "sample": "/tlcl-hub/ee-site?limit=10",
                    }
                },
                "HANA Stored Procedures": {
                    "tlcl01": {
                        "path": "/tlcl-hub/tlcl01",
                        "description": "Ejecuta SP_TLCL_01 (p1, p2)",
                        "sample": "/tlcl-hub/tlcl01?p1=VALOR1&p2=VALOR2",
                    }
                },
            },
            "hana": {
                "host": settings.HANA_HOST,
                "port": settings.HANA_PORT,
                "schema": settings.HANA_SCHEMA,
                "encrypt": settings.HANA_ENCRYPT,
                "ssl_validate": settings.HANA_SSL_VALIDATE,
            },
            "links": {
                "docs": "/docs",
                "openapi": "/openapi.json",
            },
        }

    return app


app = create_app()