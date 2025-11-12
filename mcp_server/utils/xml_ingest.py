from typing import Dict, Any, Optional
import pandas as pd
import os


def ingest_xml_to_df(xml_path: str, record_xpath: str = ".//record", namespaces: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Parse an XML file and return a DataFrame of records.

    - `record_xpath` is the XPath to each record element (default is `.//record`).
    - `namespaces` is an optional dict of XML namespaces.

    This function tries `pandas.read_xml` when available for convenience; if it fails,
    it falls back to a simple ElementTree-based extractor that flattens child elements.
    """
    if not os.path.exists(xml_path):
        raise FileNotFoundError(xml_path)

    try:
        df = pd.read_xml(xml_path, xpath=record_xpath, namespaces=namespaces)
        return df
    except Exception:
        # Fallback: simple parse and flatten
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_path)
        root = tree.getroot()
        records = []
        for elem in root.findall(record_xpath, namespaces=namespaces or {}):
            row = {}
            for child in list(elem):
                # use tag without namespace
                tag = child.tag
                if '}' in tag:
                    tag = tag.split('}', 1)[1]
                row[tag] = child.text
            records.append(row)
        return pd.DataFrame(records)
