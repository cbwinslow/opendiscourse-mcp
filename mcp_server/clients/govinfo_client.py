from typing import Optional, Dict, Any, List
from .base_client import BaseClient
import requests
import pandas as pd
import os
from datetime import datetime
from mcp_server.db import get_sqlalchemy_engine
from mcp_server.utils.ingest import save_dataframe


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

    def query_govinfo_documents(self, collection: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              limit: int = 100) -> Dict[str, Any]:
        """Query GovInfo documents from database"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM govinfo_documents WHERE 1=1"

        params = {}
        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection
        if start_date:
            query += " AND date >= %(start_date)s"
            params["start_date"] = start_date
        if end_date:
            query += " AND date <= %(end_date)s"
            params["end_date"] = end_date

        query += f" ORDER BY date DESC LIMIT {limit}"

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

    def analyze_document_collections(self) -> Dict[str, Any]:
        """Analyze document distribution across collections"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            collection,
            COUNT(*) as document_count,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(LENGTH(title)) as avg_title_length
        FROM govinfo_documents
        GROUP BY collection
        ORDER BY document_count DESC
        """

        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['collection', 'document_count', 'earliest_date', 'latest_date', 'avg_title_length'])

        # Calculate date ranges
        df['date_range_days'] = (df['latest_date'] - df['earliest_date']).dt.days

        return {
            "collection_analysis": df.to_dict('records'),
            "summary": {
                "total_collections": len(df),
                "total_documents": int(df['document_count'].sum()),
                "most_active_collection": df.loc[df['document_count'].idxmax()]['collection'] if len(df) > 0 else None,
                "avg_documents_per_collection": float(df['document_count'].mean())
            }
        }

    def get_document_trends(self, collection: Optional[str] = None,
                          group_by: str = "month") -> Dict[str, Any]:
        """Analyze document publication trends over time"""
        engine = get_sqlalchemy_engine()
        query = f"""
        SELECT
            DATE_TRUNC(%(group_by)s, date) as period,
            COUNT(*) as document_count,
            COUNT(DISTINCT collection) as collections_active
        FROM govinfo_documents
        WHERE 1=1
        """

        params = {"group_by": group_by}
        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        query += " GROUP BY period ORDER BY period"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['period', 'document_count', 'collections_active'])

        return {
            "trends": df.to_dict('records'),
            "summary": {
                "total_periods": len(df),
                "total_documents": int(df['document_count'].sum()),
                "avg_documents_per_period": float(df['document_count'].mean()),
                "peak_period": df.loc[df['document_count'].idxmax()]['period'].isoformat() if len(df) > 0 else None
            },
            "grouping": group_by,
            "collection_filter": collection
        }

    def search_documents_advanced(self, keywords: Optional[List[str]] = None,
                               collection: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               limit: int = 100) -> Dict[str, Any]:
        """Advanced search for GovInfo documents"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM govinfo_documents WHERE 1=1"
        params = {}

        if keywords:
            keyword_conditions = []
            for i, keyword in enumerate(keywords):
                keyword_conditions.append(f"title ILIKE %(keyword_{i})s")
                params[f"keyword_{i}"] = f"%{keyword}%"
            query += " AND (" + " OR ".join(keyword_conditions) + ")"

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        if start_date:
            query += " AND date >= %(start_date)s"
            params["start_date"] = start_date

        if end_date:
            query += " AND date <= %(end_date)s"
            params["end_date"] = end_date

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "count": len(df),
            "search_criteria": {
                "keywords": keywords,
                "collection": collection,
                "date_range": {"start": start_date, "end": end_date}
            },
            "data": df.to_dict('records'),
            "columns": list(columns)
        }

    def analyze_document_metadata(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """Analyze metadata patterns in documents"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            collection,
            COUNT(*) as total_documents,
            AVG(LENGTH(title)) as avg_title_length,
            MIN(LENGTH(title)) as min_title_length,
            MAX(LENGTH(title)) as max_title_length,
            AVG(LENGTH(metadata::text)) as avg_metadata_size
        FROM govinfo_documents
        WHERE 1=1
        """

        params = {}
        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        query += " GROUP BY collection ORDER BY total_documents DESC"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['collection', 'total_documents', 'avg_title_length', 'min_title_length', 'max_title_length', 'avg_metadata_size'])

        # Get most common words in titles (simple analysis)
        title_query = """
        SELECT title
        FROM govinfo_documents
        WHERE title IS NOT NULL
        """

        if collection:
            title_query += " AND collection = %(collection)s"

        title_query += " LIMIT 1000"

        with engine.connect() as conn:
            title_result = conn.execute(title_query, params)
            titles = [row[0] for row in title_result]

        # Simple word frequency analysis
        from collections import Counter
        import re

        all_words = []
        for title in titles:
            words = re.findall(r'\b\w+\b', title.lower())
            all_words.extend(words)

        common_words = Counter(all_words).most_common(20)

        return {
            "metadata_analysis": df.to_dict('records'),
            "title_word_frequency": dict(common_words),
            "collection_filter": collection,
            "titles_analyzed": len(titles)
        }

    def compare_collections(self, collection1: str, collection2: str) -> Dict[str, Any]:
        """Compare document characteristics between two collections"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT
            collection,
            COUNT(*) as document_count,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(LENGTH(title)) as avg_title_length,
            AVG(LENGTH(metadata::text)) as avg_metadata_size
        FROM govinfo_documents
        WHERE collection IN (%(c1)s, %(c2)s)
        GROUP BY collection
        """

        params = {"c1": collection1, "c2": collection2}

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        comparison = {}
        for row in rows:
            coll, doc_count, earliest, latest, avg_title, avg_meta = row
            comparison[coll] = {
                "document_count": doc_count,
                "date_range": {
                    "earliest": earliest.isoformat() if earliest else None,
                    "latest": latest.isoformat() if latest else None,
                    "days_span": (latest - earliest).days if earliest and latest else None
                },
                "avg_title_length": float(avg_title) if avg_title else 0,
                "avg_metadata_size": float(avg_meta) if avg_meta else 0
            }

        # Calculate differences
        if collection1 in comparison and collection2 in comparison:
            diff = {}
            for key in ['document_count', 'avg_title_length', 'avg_metadata_size']:
                if key in comparison[collection1] and key in comparison[collection2]:
                    diff[key] = comparison[collection1][key] - comparison[collection2][key]

            if comparison[collection1]['date_range']['days_span'] and comparison[collection2]['date_range']['days_span']:
                diff['date_span_difference'] = comparison[collection1]['date_range']['days_span'] - comparison[collection2]['date_range']['days_span']

            return {
                "collection_comparison": comparison,
                "differences": diff,
                "collection1": collection1,
                "collection2": collection2
            }
        else:
            return {"error": "One or both collections not found in data"}

    def export_govinfo_data(self, collection: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          format: str = "csv",
                          output_path: Optional[str] = None) -> Dict[str, Any]:
        """Export GovInfo documents data with filtering"""
        data = self.query_govinfo_documents(collection=collection,
                                          start_date=start_date,
                                          end_date=end_date,
                                          limit=50000)
        df = pd.DataFrame(data["data"])

        if not output_path:
            collection_str = f"_{collection}" if collection else ""
            date_str = f"_{start_date}_to_{end_date}" if start_date and end_date else ""
            output_path = f"govinfo_documents{collection_str}{date_str}.{format}"

        save_dataframe(df, output_path, format)

        return {
            "status": "success",
            "file": output_path,
            "format": format,
            "records": len(df),
            "filters": {
                "collection": collection,
                "start_date": start_date,
                "end_date": end_date
            }
        }

    def query_documents_by_year_range(self, start_year: int, end_year: Optional[int] = None,
                                    collection: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Query documents within a specific year range"""
        if end_year is None:
            end_year = start_year

        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM govinfo_documents
        WHERE EXTRACT(YEAR FROM date) BETWEEN %(start_year)s AND %(end_year)s
        """
        params = {"start_year": start_year, "end_year": end_year}

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "year_range": {"start": start_year, "end": end_year},
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"collection": collection}
        }

    def query_documents_by_topics(self, topics: List[str], collection: Optional[str] = None,
                                start_date: Optional[str] = None, end_date: Optional[str] = None,
                                limit: int = 100) -> Dict[str, Any]:
        """Query documents by topics in title or metadata"""
        engine = get_sqlalchemy_engine()

        query = "SELECT * FROM govinfo_documents WHERE 1=1"
        params = {}

        # Build topic conditions
        topic_conditions = []
        for i, topic in enumerate(topics):
            topic_conditions.append(f"(title ILIKE %(topic_{i})s OR metadata::text ILIKE %(topic_{i})s)")
            params[f"topic_{i}"] = f"%{topic}%"

        query += " AND (" + " OR ".join(topic_conditions) + ")"

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection
        if start_date:
            query += " AND date >= %(start_date)s"
            params["start_date"] = start_date
        if end_date:
            query += " AND date <= %(end_date)s"
            params["end_date"] = end_date

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "topics": topics,
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"collection": collection, "start_date": start_date, "end_date": end_date}
        }

    def query_documents_by_type(self, document_type: str, collection: Optional[str] = None,
                              start_date: Optional[str] = None, end_date: Optional[str] = None,
                              limit: int = 100) -> Dict[str, Any]:
        """Query documents by document type/collection"""
        engine = get_sqlalchemy_engine()

        query = "SELECT * FROM govinfo_documents WHERE collection = %(document_type)s"
        params = {"document_type": document_type}

        if collection and collection != document_type:
            # If both are specified and different, this is an error
            return {"error": "document_type and collection parameters conflict"}
        elif collection:
            params["document_type"] = collection

        if start_date:
            query += " AND date >= %(start_date)s"
            params["start_date"] = start_date
        if end_date:
            query += " AND date <= %(end_date)s"
            params["end_date"] = end_date

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "document_type": document_type,
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"start_date": start_date, "end_date": end_date}
        }

    def search_documents_by_text_content(self, search_text: str, collection: Optional[str] = None,
                                       start_date: Optional[str] = None, end_date: Optional[str] = None,
                                       limit: int = 100) -> Dict[str, Any]:
        """Search documents by text content in title or metadata"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM govinfo_documents
        WHERE (title ILIKE %(search_text)s OR metadata::text ILIKE %(search_text)s)
        """
        params = {"search_text": f"%{search_text}%"}

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection
        if start_date:
            query += " AND date >= %(start_date)s"
            params["start_date"] = start_date
        if end_date:
            query += " AND date <= %(end_date)s"
            params["end_date"] = end_date

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "search_text": search_text,
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"collection": collection, "start_date": start_date, "end_date": end_date}
        }

    def query_recent_documents(self, days: int = 30, collection: Optional[str] = None,
                             limit: int = 100) -> Dict[str, Any]:
        """Query recently published documents"""
        engine = get_sqlalchemy_engine()

        query = f"""
        SELECT * FROM govinfo_documents
        WHERE date >= CURRENT_DATE - INTERVAL '{days} days'
        """
        params = {}

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "days": days,
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"collection": collection}
        }

    def analyze_document_types(self) -> Dict[str, Any]:
        """Analyze distribution of document types/collections"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT
            collection,
            COUNT(*) as document_count,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(LENGTH(title)) as avg_title_length
        FROM govinfo_documents
        GROUP BY collection
        ORDER BY document_count DESC
        """

        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['collection', 'document_count', 'earliest_date', 'latest_date', 'avg_title_length'])

        return {
            "document_types": df.to_dict('records'),
            "summary": {
                "total_types": len(df),
                "total_documents": int(df['document_count'].sum()),
                "most_common_type": df.loc[df['document_count'].idxmax()]['collection'] if len(df) > 0 else None,
                "avg_documents_per_type": float(df['document_count'].mean())
            }
        }

    def query_documents_by_metadata_field(self, field_name: str, field_value: str,
                                        collection: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Query documents by specific metadata field values"""
        engine = get_sqlalchemy_engine()

        query = f"""
        SELECT * FROM govinfo_documents
        WHERE metadata->>%(field_name)s ILIKE %(field_value)s
        """
        params = {"field_name": field_name, "field_value": f"%{field_value}%"}

        if collection:
            query += " AND collection = %(collection)s"
            params["collection"] = collection

        query += f" ORDER BY date DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "metadata_field": field_name,
            "field_value": field_value,
            "document_count": len(df),
            "documents": df.to_dict('records'),
            "filters": {"collection": collection}
        }
