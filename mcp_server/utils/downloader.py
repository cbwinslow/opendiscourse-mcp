import os
import requests
from typing import Dict, Any

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


def fetch_file(url: str, out_path: str, chunk_size: int = 65536, resume: bool = True, timeout: int = 60) -> Dict[str, Any]:
    """Download `url` to `out_path` streaming in chunks.

    - If `resume` is True and a partial file exists, attempt HTTP Range resume.
    - Returns a dict with status and path.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    headers = {}
    mode = "wb"
    existing = 0
    if resume and os.path.exists(out_path):
        existing = os.path.getsize(out_path)
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"
            mode = "ab"

    with requests.get(url, stream=True, headers=headers, timeout=timeout) as r:
        r.raise_for_status()
        total = None
        if "Content-Length" in r.headers:
            try:
                total = int(r.headers["Content-Length"]) + existing
            except Exception:
                total = None

        if tqdm and total:
            pbar = tqdm(total=total, unit="B", unit_scale=True, desc=os.path.basename(out_path))
            pbar.update(existing)
        else:
            pbar = None

        with open(out_path, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                if pbar:
                    pbar.update(len(chunk))

        if pbar:
            pbar.close()

    return {"status": "ok", "path": out_path, "size": os.path.getsize(out_path)}
