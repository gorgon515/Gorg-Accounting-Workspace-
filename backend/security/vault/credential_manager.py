from __future__ import annotations

import json
from typing import Optional

from .vault import Vault, get_vault


class CredentialManager:
    """Typed credential storage and retrieval wrapping the Vault."""

    def __init__(self, vault: Optional[Vault] = None) -> None:
        self._vault: Vault = vault if vault is not None else get_vault()

    # ------------------------------------------------------------------
    # OAuth tokens
    # ------------------------------------------------------------------

    def store_oauth_token(
        self,
        name: str,
        access_token: str,
        refresh_token: str = "",
        expires_at: str = "",
        scope: str = "",
        user: str = "system",
    ) -> dict:
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scope": scope,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="oauth_token",
            description=f"OAuth token: {name}",
            user=user,
        )
        return data

    def retrieve_oauth_token(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------

    def store_api_key(
        self,
        name: str,
        key: str,
        endpoint: str = "",
        rate_limit: int = 0,
        user: str = "system",
    ) -> dict:
        data = {
            "key": key,
            "endpoint": endpoint,
            "rate_limit": rate_limit,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="api_key",
            description=f"API key: {name}",
            user=user,
        )
        return data

    def retrieve_api_key(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # DB credentials
    # ------------------------------------------------------------------

    def store_db_credential(
        self,
        name: str,
        host: str,
        port: int,
        user_name: str,
        password: str,
        database: str,
        user: str = "system",
    ) -> dict:
        data = {
            "host": host,
            "port": port,
            "user": user_name,
            "password": password,
            "database": database,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="db_credential",
            description=f"DB credential: {name}",
            user=user,
        )
        return data

    def retrieve_db_credential(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # Broker credentials
    # ------------------------------------------------------------------

    def store_broker_credential(
        self,
        name: str,
        api_key: str,
        api_secret: str,
        account_id: str = "",
        paper_trading: bool = False,
        user: str = "system",
    ) -> dict:
        data = {
            "api_key": api_key,
            "api_secret": api_secret,
            "account_id": account_id,
            "paper_trading": paper_trading,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="broker_credential",
            description=f"Broker credential: {name}",
            user=user,
        )
        return data

    def retrieve_broker_credential(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # SMTP credentials
    # ------------------------------------------------------------------

    def store_smtp_credential(
        self,
        name: str,
        host: str,
        port: int,
        user_name: str,
        password: str,
        use_tls: bool = True,
        user: str = "system",
    ) -> dict:
        data = {
            "host": host,
            "port": port,
            "user": user_name,
            "password": password,
            "use_tls": use_tls,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="smtp_credential",
            description=f"SMTP credential: {name}",
            user=user,
        )
        return data

    def retrieve_smtp_credential(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # n8n credentials
    # ------------------------------------------------------------------

    def store_n8n_credential(
        self,
        name: str,
        url: str,
        api_key: str,
        webhook_secret: str = "",
        user: str = "system",
    ) -> dict:
        data = {
            "url": url,
            "api_key": api_key,
            "webhook_secret": webhook_secret,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="n8n_credential",
            description=f"n8n credential: {name}",
            user=user,
        )
        return data

    def retrieve_n8n_credential(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))

    # ------------------------------------------------------------------
    # Encryption keys
    # ------------------------------------------------------------------

    def store_encryption_key(
        self,
        name: str,
        key_material: str,
        algorithm: str = "AES-256-GCM",
        purpose: str = "",
        user: str = "system",
    ) -> dict:
        data = {
            "key_material": key_material,
            "algorithm": algorithm,
            "purpose": purpose,
        }
        self._vault.store(
            name=name,
            value=json.dumps(data),
            category="encryption_key",
            description=f"Encryption key: {name}",
            user=user,
        )
        return data

    def retrieve_encryption_key(self, name: str, user: str = "system") -> dict:
        return json.loads(self._vault.retrieve(name, user=user))
