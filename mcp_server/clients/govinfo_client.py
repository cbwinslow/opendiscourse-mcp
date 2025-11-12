from typing import Optional, Dict, Any
from .base_client import BaseClient
import requests


class GovInfoClient(BaseClient):
    BASE = "https://api.govinfo.gov"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    def list_collections(self):
        url = f"{self.BASE}/collections"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def bulk_download(self, collection: str, year: Optional[int] = None):
        # GovInfo exposes a bulk data repository; provide a helper that returns bulk URLs
        base_bulk = "https://www.govinfo.gov/bulkdata"
        url = f"{base_bulk}/{collection}"
        if year:
            url = f"{url}/{year}"
        # try to parse HTML listing for files
        r = self.session.get(url, timeout=self.timeout)
        if r.status_code != 200:
            return {"bulk_url": url, "status": "unavailable", "http_status": r.status_code}
        # Simple heuristic: find links to files ending with .xml, .zip, .gz
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(r.text, "lxml")
        files = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith(('.xml', '.zip', '.gz', '.json')):
                if href.startswith('http'):
                    files.append(href)
                else:
                    files.append(requests.compat.urljoin(url, href))

        return {"bulk_url": url, "files": files}

    def fetch_bulk_file(self, url: str, out_path: str, chunk_size: int = 65536, resume: bool = True):
        from mcp_server.utils.downloader import fetch_file

        return fetch_file(url, out_path, chunk_size=chunk_size, resume=resume)

    def ingest_xml_to_df(self, xml_path: str, record_xpath: str = ".//record"):
        from mcp_server.utils.xml_ingest import ingest_xml_to_df

        return ingest_xml_to_df(xml_path, record_xpath=record_xpath)
