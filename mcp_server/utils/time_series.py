import pandas as pd
from typing import Optional


def transform_timeframe(df: pd.DataFrame, date_column: str, freq: str = "D", agg: Optional[dict] = None) -> pd.DataFrame:
    """Resample a dataframe by a time frequency.

    - `date_column` is the name of the column with datetime values.
    - `freq` is a pandas offset alias (e.g., 'D', 'W', 'M').
    - `agg` is a dict mapping column -> aggregation (e.g., {'value':'sum'}).
    """
    if date_column not in df.columns:
        raise ValueError("date_column not in dataframe")
    d = df.copy()
    d[date_column] = pd.to_datetime(d[date_column])
    d = d.set_index(date_column)
    if agg is None:
        # default: count rows
        out = d.resample(freq).size().to_frame("count")
    else:
        out = d.resample(freq).agg(agg)
    out = out.reset_index()
    return out
