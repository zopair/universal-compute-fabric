from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    environment: str
    database_url: str
    admin_api_key: str | None
    node_lease_seconds: int
    otel_exporter_otlp_endpoint: str | None

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @classmethod
    def from_env(cls) -> "Settings":
        lease = int(os.getenv("UCF_NODE_LEASE_SECONDS", "45"))
        if lease < 10 or lease > 3600:
            raise ValueError("UCF_NODE_LEASE_SECONDS must be between 10 and 3600")
        return cls(
            environment=os.getenv("UCF_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./ucf.db"),
            admin_api_key=os.getenv("UCF_ADMIN_API_KEY"),
            node_lease_seconds=lease,
            otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        )


settings = Settings.from_env()
