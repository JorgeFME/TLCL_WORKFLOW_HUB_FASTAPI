import json
import os
import tempfile
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación y conexión a SAP HANA.

    - Lee variables de entorno y .env para desarrollo local.
    - Si existe VCAP_SERVICES (Cloud Foundry), sobreescribe con credenciales del servicio HANA.
    """

    # HANA base
    HANA_HOST: Optional[str] = Field(default=None)
    HANA_PORT: Optional[int] = Field(default=443)
    HANA_USER: Optional[str] = Field(default=None)
    HANA_PASSWORD: Optional[str] = Field(default=None)
    HANA_SCHEMA: Optional[str] = Field(default=None)

    # SSL/TLS
    HANA_ENCRYPT: bool = Field(default=True)
    HANA_SSL_VALIDATE: bool = Field(default=False)
    HANA_SSL_TRUST_STORE: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def _load_from_vcap(self) -> None:
        """Intenta cargar credenciales desde VCAP_SERVICES en Cloud Foundry."""
        vcap = os.environ.get("VCAP_SERVICES")
        if not vcap:
            return

        try:
            data = json.loads(vcap)
        except Exception:
            return

        # Buscar servicios con etiqueta relacionada a HANA
        for label, services in data.items():
            if "hana" in label.lower():
                for srv in services:
                    creds = srv.get("credentials", {})
                    host = creds.get("host") or creds.get("hostname")
                    port_raw = creds.get("port")
                    port = int(port_raw) if port_raw else (self.HANA_PORT or 443)
                    user = creds.get("user") or creds.get("username")
                    password = creds.get("password")
                    schema = creds.get("schema") or creds.get("schemaName") or creds.get("currentSchema")
                    certificate = creds.get("certificate") or creds.get("certificates")

                    if host and user and password:
                        self.HANA_HOST = host
                        self.HANA_PORT = port
                        self.HANA_USER = user
                        self.HANA_PASSWORD = password
                        if schema:
                            self.HANA_SCHEMA = schema

                        if certificate:
                            # Escribir certificado en archivo temporal para trust store
                            try:
                                fd, path = tempfile.mkstemp(prefix="hana-trust-", suffix=".pem")
                                with os.fdopen(fd, "w", encoding="utf-8") as f:
                                    if isinstance(certificate, list):
                                        f.write("\n".join(certificate))
                                    else:
                                        f.write(certificate)
                                self.HANA_SSL_TRUST_STORE = path
                                self.HANA_SSL_VALIDATE = True
                            except Exception:
                                # Si falla, no validar certificado en esta instancia
                                self.HANA_SSL_VALIDATE = False
                        else:
                            # Sin certificado, mejor no validar en runtime
                            self.HANA_SSL_VALIDATE = False

                        # Una coincidencia es suficiente
                        return

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # En CF, sobreescribe desde VCAP_SERVICES si está presente
        self._load_from_vcap()