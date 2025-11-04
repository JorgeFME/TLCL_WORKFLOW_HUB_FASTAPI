# TLCL Processes Hub (FastAPI + SAP HANA)

Aplicación FastAPI para exponer endpoints de consulta SQL y ejecución de Stored Procedures sobre SAP HANA. Incluye configuración por entorno, soporte para `VCAP_SERVICES` (Cloud Foundry), y documentación interactiva.

## Características

- Endpoints para consultas SQL simples y ejecución de Stored Procedures en HANA.
- Configuración con `Pydantic Settings` y soporte para `VCAP_SERVICES` (SAP BTP).
- Conexión segura a HANA con `encrypt` y validación opcional de certificado.
- Documentación interactiva en `http://localhost:8000/docs`.

## Estructura del proyecto

```
TLCL Processes Hub/
├─ app/
│  ├─ core/
│  │  └─ config.py          # Configuración (env/VCAP_SERVICES)
│  ├─ db/
│  │  └─ hana.py            # Conexión y helpers HANA (query y SP)
│  ├─ routers/
│  │  ├─ hana_sql.py        # Endpoints de SQL (ej. TELCEL_EE_SITE)
│  │  └─ hana_sp.py         # Endpoints de Stored Procedures (ej. TLCL01)
│  ├─ dependencies.py       # Settings cacheado (FastAPI Depends)
│  └─ main.py               # FastAPI app y endpoint raíz
├─ .env.example             # Variables de entorno para dev local
├─ requirements.txt         # Dependencias
├─ Procfile                 # Arranque de app en CF
├─ manifest.yml             # Manifiesto CF (opcional)
└─ README.md
```

## Requisitos

- Python 3.10+
- Paquetes de `requirements.txt`
- Acceso a SAP HANA (Cloud) para pruebas

## Configuración

- Variables de entorno principales:
  - `HANA_HOST`, `HANA_PORT`, `HANA_USER`, `HANA_PASSWORD`, `HANA_SCHEMA`
  - `HANA_ENCRYPT` (por defecto `true`), `HANA_SSL_VALIDATE` (en local puede ser `false`)
  - `HANA_SSL_TRUST_STORE` (ruta a certificado, opcional)

- Soporte `VCAP_SERVICES` (Cloud Foundry):
  - Detecta servicios con etiqueta que contenga `hana` y usa sus `credentials`.
  - Si `VCAP_SERVICES` incluye certificado, se escribe temporalmente y se activa la validación de certificado.

## Instalación y ejecución local

- Entorno virtual (Windows PowerShell):
  ```powershell
  py -3 -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

- Ejecutar la API:
  ```powershell
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

- Enlaces útiles:
  - Home JSON: `http://localhost:8000/`
  - Documentación: `http://localhost:8000/docs`
  - OpenAPI JSON: `http://localhost:8000/openapi.json`

## Endpoints

- General
  - `GET /` — Resumen de la API, secciones y configuración no sensible.

- HANA DB - SQL
  - `GET /tlcl-hub/ee-site?limit={n}`
    - Devuelve hasta `n` filas de `TELCEL_EE_SITE`.
    - Respuesta: `{ "count": number, "rows": [ { ... } ] }`.

- HANA Stored Procedures
  - `POST /tlcl-hub/tlcl01`
    - Ejecuta el SP `"<SCHEMA>"."SP_TLCL_01"` con parámetros en el cuerpo JSON:
      ```json
      {"p1": "VALOR1", "p2": "VALOR2"}
      ```
    - Respuesta típica:
      ```json
      {
        "success": true,
        "success_flag": "Y",
        "message": "Proceso ejecutado",
        "output_params": ["Y", "Proceso ejecutado"],
        "result_sets_count": 1,
        "rows": [{"SUCCESS_FLAG": "Y", "MESSAGE": "Proceso ejecutado"}],
        "count": 1
      }
      ```
    - Notas: se capturan tanto parámetros OUT como el primer result set no vacío.

## Ejemplos de uso

- `curl` (Windows PowerShell):
  ```powershell
  curl "http://localhost:8000/tlcl-hub/ee-site?limit=10"
  curl -X POST "http://localhost:8000/tlcl-hub/tlcl01" ^
    -H "Content-Type: application/json" ^
    -d "{\"p1\": \"VALOR1\", \"p2\": \"VALOR2\"}"
  ```

- Swagger UI: visitar `http://localhost:8000/docs` y probar los endpoints.

## Conexión y seguridad HANA

- Se usa `hdbcli` (cliente oficial SAP HANA).
- Conexión con `encrypt=true`; la validación de certificado puede activarse con `HANA_SSL_VALIDATE` y `HANA_SSL_TRUST_STORE`.
- Si se proporciona `HANA_SCHEMA`, se emplea para calificar tablas y procedimientos.

## Despliegue en SAP BTP - Cloud Foundry

1. Preparar dependencias:
   - Asegúrate de tener `requirements.txt` actualizado.
   - Revisar `manifest.yml` (nombre de app, memoria, buildpack).

2. Crear servicio HANA y bindear a la app (ejemplos):
   ```bash
   cf create-service hanacloud hana-shared my-hana
   cf bind-service tlcl-processes-hub my-hana
   ```

3. Desplegar la app:
   ```bash
   cf push tlcl-processes-hub -f manifest.yml
   ```

4. Ver registros si algo falla:
   ```bash
   cf logs tlcl-processes-hub --recent
   ```

## Logging

- Logger principal: `tlcl-hub`.
- Cuando la app corre fuera de `uvicorn`, se configura un `basicConfig` para evitar errores de logging.

## Solución de problemas

- Falta `hdbcli`:
  - Instalar con `pip install hdbcli` (incluido en `requirements.txt`).

- Certificado HANA:
  - En local, puedes desactivar validación (`HANA_SSL_VALIDATE=false`). En producción, habilitar y usar `HANA_SSL_TRUST_STORE`.

- Stored Procedure devuelve vacío:
  - El SP puede entregar parámetros OUT en lugar de result set. El helper `call_procedure_with_outputs` captura ambos. Verifica `output_params`.
  - Asegúrate de usar nombre totalmente calificado y entrecomillado: `"<SCHEMA>"."SP_TLCL_01"`.

- Esquema incorrecto:
  - Revisa `HANA_SCHEMA` y que el usuario tenga permisos sobre el esquema/configurado.

## Próximos pasos sugeridos

- Añadir controladores de errores y mapeo estandarizado.
- Integrar logging estructurado y métricas.
- Añadir pruebas unitarias y contract tests.
- Extender endpoints para más SPs y consultas.

---

Si necesitas autenticación, versionado de API o pruebas automatizadas, indícalo y lo implementamos paso a paso.