from typing import Optional, Dict, Any
from .base_client import BaseClient


class CongressClient(BaseClient):
    BASE = "https://api.congress.gov"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    def search_bills(self, congress: Optional[int] = None, billType: Optional[str] = None, page: int = 1):
        # Congress API uses api.data.gov API key (api_key param)
        url = f"{self.BASE}/bill"
        params = {"page": page}
        if congress:
            params["congress"] = congress
        if billType:
            params["billType"] = billType
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_bill(self, congress: int, billType: str, billNumber: str):
        url = f"{self.BASE}/bill/{congress}/{billType}/{billNumber}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def bulk_download_collection(self, collection: str, year: Optional[int] = None):
        # Not all endpoints support bulk; provide a helper that uses govinfo bulk paths when possible
        return {"status": "not_implemented", "collection": collection, "year": year}

    def get_bill_actions(self, congress: int, billType: str, billNumber: str):
        url = f"{self.BASE}/bill/{congress}/{billType}/{billNumber}/actions"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_bill_text(self, congress: int, billType: str, billNumber: str):
        url = f"{self.BASE}/bill/{congress}/{billType}/{billNumber}/text"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_members(self, congress: Optional[int] = None, chamber: Optional[str] = None):
        url = f"{self.BASE}/member"
        params = {}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_member(self, bioguideId: str):
        url = f"{self.BASE}/member/{bioguideId}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
