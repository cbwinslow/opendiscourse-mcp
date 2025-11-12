from typing import Optional, Dict, Any, List
from .base_client import BaseClient
import requests
import pandas as pd
import os
from mcp_server.db import get_sqlalchemy_engine
from mcp_server.utils.ingest import save_dataframe


class OpenStatesClient(BaseClient):
    BASE = "https://v3.openstates.org"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    def get_openapi_schema(self) -> Dict[str, Any]:
        url = self.BASE + "/openapi.json"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def search_bills(self, jurisdiction: Optional[str] = None, q: Optional[str] = None, page: int = 1, per_page: int = 50):
        url = self.BASE + "/bills"
        params = {"page": page, "per_page": per_page}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if q:
            params["q"] = q
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_bill(self, openstates_bill_id: str):
        url = f"{self.BASE}/bills/ocd-bill/{openstates_bill_id}"
        params = {}
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def search_people(self, jurisdiction: Optional[str] = None, name: Optional[str] = None, page: int = 1, per_page: int = 50):
        url = self.BASE + "/people"
        params = {"page": page, "per_page": per_page}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if name:
            params["name"] = name
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_person(self, person_id: str):
        url = f"{self.BASE}/people/{person_id}"
        params = {}
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def search_events(self, jurisdiction: Optional[str] = None, before: Optional[str] = None, after: Optional[str] = None, page: int = 1, per_page: int = 20):
        url = self.BASE + "/events"
        params = {"page": page, "per_page": per_page}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_event(self, event_id: str):
        url = f"{self.BASE}/events/{event_id}"
        params = {}
        if self.api_key:
            params["apikey"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def query_bills(self, jurisdiction: Optional[str] = None, session: Optional[str] = None,
                   classification: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Query bills from the database"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM openstates_bills WHERE 1=1"

        params = {}
        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
        if session:
            query += " AND session = %(session)s"
            params["session"] = session
        if classification:
            query += " AND classification && %(classification)s"
            params["classification"] = classification

        query += f" ORDER BY updated_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)
        return {
            "count": len(df),
            "data": df.to_dict('records'),
            "columns": list(columns)
        }

    def export_bills(self, jurisdiction: Optional[str] = None, format: str = "csv",
                    output_path: Optional[str] = None) -> Dict[str, Any]:
        """Export bills data to file"""
        if not output_path:
            output_path = f"openstates_bills_{jurisdiction or 'all'}.{format}"

        data = self.query_bills(jurisdiction=jurisdiction, limit=10000)  # Large limit for export
        df = pd.DataFrame(data["data"])

        save_dataframe(df, output_path, format)

        return {
            "status": "success",
            "file": output_path,
            "format": format,
            "records": len(df)
        }

    def ingest_bills(self, jurisdiction: Optional[str] = None, q: Optional[str] = None,
                    max_pages: int = 10) -> Dict[str, Any]:
        """Ingest bills data from API to database"""
        # This would trigger the ingestion script
        # For now, return a placeholder
        return {
            "status": "not_implemented",
            "message": "Use /mcp/ingest_data endpoint instead"
        }
