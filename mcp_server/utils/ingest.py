from typing import Any, Dict, List
import pandas as pd


def json_results_to_dataframe(results: List[Dict[str, Any]], normalize: bool = True) -> pd.DataFrame:
    """Convert a list of JSON/dict results into a pandas DataFrame.

    If `normalize` is True, try to flatten nested dicts using json_normalize.
    """
    if not results:
        return pd.DataFrame()
    if normalize:
        try:
            df = pd.json_normalize(results)
        except Exception:
            df = pd.DataFrame(results)
    else:
        df = pd.DataFrame(results)
    return df


def save_dataframe(df: pd.DataFrame, path: str, fmt: str = "parquet") -> Dict[str, str]:
    fmt = fmt.lower()
    if fmt == "parquet":
        df.to_parquet(path)
    elif fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records", lines=False)
    else:
        raise ValueError("Unsupported format")
    return {"status": "ok", "path": path, "format": fmt}
