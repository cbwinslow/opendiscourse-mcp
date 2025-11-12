import requests
from typing import Optional


class BaseClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        return {"status": "ok"}
