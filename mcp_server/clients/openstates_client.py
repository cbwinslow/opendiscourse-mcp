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

    def analyze_bill_sponsors(self, bill_id: Optional[str] = None, jurisdiction: Optional[str] = None,
                            limit: int = 50) -> Dict[str, Any]:
        """Analyze bill sponsorship patterns"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            b.id,
            b.title,
            jsonb_array_elements(b.sponsors) as sponsor,
            b.jurisdiction,
            b.session
        FROM openstates_bills b
        WHERE b.sponsors IS NOT NULL
        """

        params = {}
        conditions = []
        if bill_id:
            conditions.append("b.id = %(bill_id)s")
            params["bill_id"] = bill_id
        if jurisdiction:
            conditions.append("b.jurisdiction = %(jurisdiction)s")
            params["jurisdiction"] = jurisdiction

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += f" ORDER BY b.updated_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['bill_id', 'title', 'sponsor', 'jurisdiction', 'session'])

        # Analyze sponsorship patterns
        sponsor_counts = df.groupby(df['sponsor'].apply(lambda x: x.get('name') if isinstance(x, dict) else str(x))).size().sort_values(ascending=False)

        return {
            "total_bills": len(df),
            "unique_sponsors": len(sponsor_counts),
            "top_sponsors": sponsor_counts.head(10).to_dict(),
            "sample_data": df.head(5).to_dict('records')
        }

    def find_related_bills(self, bill_id: str, jurisdiction: Optional[str] = None,
                          similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """Find bills related by sponsors, subjects, or keywords"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            b.id,
            b.title,
            b.subjects,
            b.sponsors,
            b.classification,
            b.jurisdiction,
            b.session,
            b.updated_at
        FROM openstates_bills b
        WHERE b.id != %(bill_id)s
        """

        params = {"bill_id": bill_id}
        if jurisdiction:
            query += " AND b.jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction

        # Find bills with same sponsors
        sponsor_query = """
        SELECT jsonb_array_elements(sponsors) as sponsor
        FROM openstates_bills
        WHERE id = %(bill_id)s AND sponsors IS NOT NULL
        """
        with engine.connect() as conn:
            sponsor_result = conn.execute(sponsor_query, {"bill_id": bill_id})
            sponsors = [row[0] for row in sponsor_result]

        if sponsors:
            sponsor_names = [s.get('name') if isinstance(s, dict) else str(s) for s in sponsors]
            query += " AND (" + " OR ".join([f"b.sponsors::text LIKE %(sponsor_{i})s" for i in range(len(sponsor_names))]) + ")"
            for i, name in enumerate(sponsor_names):
                params[f"sponsor_{i}"] = f"%{name}%"

        query += " ORDER BY b.updated_at DESC LIMIT 20"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['id', 'title', 'subjects', 'sponsors', 'classification', 'jurisdiction', 'session', 'updated_at'])

        return {
            "related_bills_count": len(df),
            "related_bills": df.to_dict('records'),
            "search_criteria": {
                "original_bill": bill_id,
                "sponsors_used": sponsor_names if sponsors else []
            }
        }

    def get_legislative_trends(self, jurisdiction: Optional[str] = None,
                              start_date: Optional[str] = None, end_date: Optional[str] = None,
                              group_by: str = "month") -> Dict[str, Any]:
        """Analyze legislative trends over time"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            DATE_TRUNC(%(group_by)s, created_at) as period,
            COUNT(*) as bill_count,
            COUNT(DISTINCT classification) as unique_classifications,
            AVG(CASE WHEN subjects IS NOT NULL THEN jsonb_array_length(subjects) ELSE 0 END) as avg_subjects
        FROM openstates_bills
        WHERE 1=1
        """

        params = {"group_by": group_by}
        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
        if start_date:
            query += " AND created_at >= %(start_date)s"
            params["start_date"] = start_date
        if end_date:
            query += " AND created_at <= %(end_date)s"
            params["end_date"] = end_date

        query += " GROUP BY period ORDER BY period"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['period', 'bill_count', 'unique_classifications', 'avg_subjects'])

        return {
            "trends": df.to_dict('records'),
            "summary": {
                "total_periods": len(df),
                "total_bills": int(df['bill_count'].sum()),
                "avg_bills_per_period": float(df['bill_count'].mean()),
                "peak_period": df.loc[df['bill_count'].idxmax()]['period'].isoformat() if len(df) > 0 else None
            },
            "grouping": group_by
        }

    def search_bills_advanced(self, keywords: Optional[List[str]] = None,
                            sponsors: Optional[List[str]] = None,
                            classification: Optional[List[str]] = None,
                            status: Optional[str] = None,
                            jurisdiction: Optional[str] = None,
                            date_from: Optional[str] = None,
                            date_to: Optional[str] = None,
                            limit: int = 100) -> Dict[str, Any]:
        """Advanced bill search with multiple criteria"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM openstates_bills WHERE 1=1"
        params = {}

        if keywords:
            keyword_conditions = []
            for i, keyword in enumerate(keywords):
                keyword_conditions.append(f"(title ILIKE %(keyword_{i})s OR subjects::text ILIKE %(keyword_{i})s)")
                params[f"keyword_{i}"] = f"%{keyword}%"
            query += " AND (" + " OR ".join(keyword_conditions) + ")"

        if sponsors:
            sponsor_conditions = []
            for i, sponsor in enumerate(sponsors):
                sponsor_conditions.append("sponsors::text ILIKE %(sponsor_{i})s")
                params[f"sponsor_{i}"] = f"%{sponsor}%"
            query += " AND (" + " OR ".join(sponsor_conditions) + ")"

        if classification:
            query += " AND classification && %(classification)s"
            params["classification"] = classification

        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction

        if date_from:
            query += " AND created_at >= %(date_from)s"
            params["date_from"] = date_from

        if date_to:
            query += " AND created_at <= %(date_to)s"
            params["date_to"] = date_to

        query += f" ORDER BY updated_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "count": len(df),
            "search_criteria": {
                "keywords": keywords,
                "sponsors": sponsors,
                "classification": classification,
                "jurisdiction": jurisdiction,
                "date_range": {"from": date_from, "to": date_to}
            },
            "data": df.to_dict('records'),
            "columns": list(columns)
        }

    def get_bill_statistics(self, jurisdiction: Optional[str] = None,
                          classification: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get statistical overview of bills"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            COUNT(*) as total_bills,
            COUNT(DISTINCT jurisdiction) as jurisdictions,
            COUNT(DISTINCT session) as sessions,
            AVG(CASE WHEN subjects IS NOT NULL THEN jsonb_array_length(subjects) ELSE 0 END) as avg_subjects_per_bill,
            COUNT(CASE WHEN sponsors IS NOT NULL THEN 1 END) as bills_with_sponsors,
            COUNT(DISTINCT CASE WHEN classification IS NOT NULL THEN unnest(classification) END) as unique_classifications
        FROM openstates_bills
        WHERE 1=1
        """

        params = {}
        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
        if classification:
            query += " AND classification && %(classification)s"
            params["classification"] = classification

        with engine.connect() as conn:
            result = conn.execute(query, params)
            row = result.fetchone()

        # Get classification distribution
        class_query = """
        SELECT classification, COUNT(*) as count
        FROM (
            SELECT unnest(classification) as classification
            FROM openstates_bills
            WHERE classification IS NOT NULL
        ) t
        GROUP BY classification
        ORDER BY count DESC
        LIMIT 10
        """

        with engine.connect() as conn:
            class_result = conn.execute(class_query)
            class_rows = class_result.fetchall()

        classification_dist = {row[0]: row[1] for row in class_rows}

        return {
            "summary": {
                "total_bills": row[0],
                "jurisdictions": row[1],
                "sessions": row[2],
                "avg_subjects_per_bill": float(row[3]) if row[3] else 0,
                "bills_with_sponsors": row[4],
                "unique_classifications": row[5]
            },
            "top_classifications": classification_dist
        }

    def export_filtered_data(self, table: str = "openstates_bills",
                           filters: Optional[Dict[str, Any]] = None,
                           format: str = "csv",
                           output_path: Optional[str] = None) -> Dict[str, Any]:
        """Export filtered data with advanced options"""
        if table not in ["openstates_bills", "openstates_people", "openstates_events"]:
            raise ValueError(f"Unsupported table: {table}")

        engine = get_sqlalchemy_engine()
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = {}

        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    query += f" AND {key} = ANY(%({key})s)"
                    params[key] = value
                elif isinstance(value, str):
                    query += f" AND {key} ILIKE %({key})s"
                    params[key] = f"%{value}%"
                else:
                    query += f" AND {key} = %({key})s"
                    params[key] = value

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        if not output_path:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{table}_filtered_{timestamp}.{format}"

        save_dataframe(df, output_path, format)

        return {
            "status": "success",
            "table": table,
            "filters_applied": filters or {},
            "records_exported": len(df),
            "file": output_path,
            "format": format,
            "columns": list(columns)
        }

    def compare_legislatures(self, jurisdiction1: str, jurisdiction2: str,
                           metric: str = "bill_count") -> Dict[str, Any]:
        """Compare legislative activity between jurisdictions"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT
            jurisdiction,
            COUNT(*) as bill_count,
            COUNT(DISTINCT session) as sessions,
            AVG(CASE WHEN subjects IS NOT NULL THEN jsonb_array_length(subjects) ELSE 0 END) as avg_subjects,
            COUNT(CASE WHEN sponsors IS NOT NULL THEN 1 END) as bills_with_sponsors
        FROM openstates_bills
        WHERE jurisdiction IN (%(jur1)s, %(jur2)s)
        GROUP BY jurisdiction
        """

        params = {"jur1": jurisdiction1, "jur2": jurisdiction2}

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        comparison = {}
        for row in rows:
            jur, bill_count, sessions, avg_subjects, bills_with_sponsors = row
            comparison[jur] = {
                "bill_count": bill_count,
                "sessions": sessions,
                "avg_subjects_per_bill": float(avg_subjects) if avg_subjects else 0,
                "bills_with_sponsors": bills_with_sponsors,
                "sponsor_ratio": bills_with_sponsors / bill_count if bill_count > 0 else 0
            }

        # Calculate differences
        if jurisdiction1 in comparison and jurisdiction2 in comparison:
            diff = {}
            for key in comparison[jurisdiction1]:
                if isinstance(comparison[jurisdiction1][key], (int, float)):
                    diff[key] = comparison[jurisdiction1][key] - comparison[jurisdiction2][key]

            return {
                "comparison": comparison,
                "differences": diff,
                "jurisdiction1": jurisdiction1,
                "jurisdiction2": jurisdiction2
            }
        else:
            return {"error": "One or both jurisdictions not found in data"}

    def generate_bill_report(self, bill_id: str) -> Dict[str, Any]:
        """Generate a comprehensive report for a specific bill"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM openstates_bills WHERE id = %(bill_id)s
        """
        params = {"bill_id": bill_id}

        with engine.connect() as conn:
            result = conn.execute(query, params)
            row = result.fetchone()

        if not row:
            return {"error": f"Bill {bill_id} not found"}

        columns = result.keys()
        bill_data = dict(zip(columns, row))

        # Analyze sponsors
        sponsors = bill_data.get('sponsors', [])
        sponsor_info = []
        if sponsors:
            for sponsor in sponsors:
                if isinstance(sponsor, dict):
                    sponsor_info.append({
                        "name": sponsor.get('name'),
                        "type": sponsor.get('type'),
                        "district": sponsor.get('district')
                    })

        # Analyze subjects
        subjects = bill_data.get('subjects', [])
        subject_analysis = {
            "count": len(subjects),
            "subjects": subjects
        }

        # Generate summary
        summary = f"""
Bill ID: {bill_data.get('id')}
Title: {bill_data.get('title')}
Jurisdiction: {bill_data.get('jurisdiction')}
Session: {bill_data.get('session')}
Classification: {', '.join(bill_data.get('classification', []))}
Created: {bill_data.get('created_at')}
Updated: {bill_data.get('updated_at')}

Sponsors ({len(sponsor_info)}):
{chr(10).join([f"- {s['name']} ({s.get('type', 'Unknown')})" for s in sponsor_info])}

Subjects ({subject_analysis['count']}):
{', '.join(subjects) if subjects else 'None'}

Latest Action: {bill_data.get('latest_action_description', 'Unknown')}
        """.strip()

        return {
            "bill_id": bill_id,
            "bill_data": bill_data,
            "sponsor_analysis": {
                "count": len(sponsor_info),
                "sponsors": sponsor_info
            },
            "subject_analysis": subject_analysis,
            "summary_report": summary
        }

    def query_bills_by_party(self, party: str, jurisdiction: Optional[str] = None,
                           classification: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Query bills sponsored by members of a specific political party"""
        engine = get_sqlalchemy_engine()

        # First get people of the specified party
        people_query = """
        SELECT id, name, party, jurisdiction
        FROM openstates_people
        WHERE party = %(party)s
        """
        people_params = {"party": party}

        if jurisdiction:
            people_query += " AND jurisdiction = %(jurisdiction)s"
            people_params["jurisdiction"] = jurisdiction

        with engine.connect() as conn:
            people_result = conn.execute(people_query, people_params)
            people = people_result.fetchall()

        if not people:
            return {"error": f"No people found for party {party}", "party": party}

        person_names = [row[1] for row in people]

        # Query bills sponsored by these people
        bills_query = "SELECT * FROM openstates_bills WHERE 1=1"
        bills_params = {}

        # Build sponsor conditions
        sponsor_conditions = []
        for i, name in enumerate(person_names):
            sponsor_conditions.append(f"sponsors::text ILIKE %(sponsor_{i})s")
            bills_params[f"sponsor_{i}"] = f"%{name}%"

        bills_query += " AND (" + " OR ".join(sponsor_conditions) + ")"

        if jurisdiction:
            bills_query += " AND jurisdiction = %(jurisdiction)s"
            bills_params["jurisdiction"] = jurisdiction
        if classification:
            bills_query += " AND classification && %(classification)s"
            bills_params["classification"] = classification

        bills_query += f" ORDER BY updated_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            bills_result = conn.execute(bills_query, bills_params)
            bills_rows = bills_result.fetchall()
            bills_columns = bills_result.keys()

        bills_df = pd.DataFrame(bills_rows, columns=bills_columns)

        return {
            "party": party,
            "member_count": len(people),
            "bill_count": len(bills_df),
            "members_sample": [{"name": row[1], "jurisdiction": row[3]} for row in people[:5]],
            "bills": bills_df.to_dict('records'),
            "filters": {"jurisdiction": jurisdiction, "classification": classification}
        }

    def query_bills_by_person_name(self, person_name: str, jurisdiction: Optional[str] = None,
                                 classification: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Query bills sponsored by a specific person by name"""
        engine = get_sqlalchemy_engine()

        # Find the person
        person_query = """
        SELECT id, name, party, jurisdiction, district
        FROM openstates_people
        WHERE name ILIKE %(name)s
        """
        person_params = {"name": f"%{person_name}%"}

        if jurisdiction:
            person_query += " AND jurisdiction = %(jurisdiction)s"
            person_params["jurisdiction"] = jurisdiction

        with engine.connect() as conn:
            person_result = conn.execute(person_query, person_params)
            person_row = person_result.fetchone()

        if not person_row:
            return {"error": f"Person '{person_name}' not found"}

        person_data = {
            "id": person_row[0],
            "name": person_row[1],
            "party": person_row[2],
            "jurisdiction": person_row[3],
            "district": person_row[4]
        }

        # Query bills sponsored by this person
        bills_query = """
        SELECT * FROM openstates_bills
        WHERE sponsors::text ILIKE %(sponsor_pattern)s
        """

        sponsor_pattern = f"%{person_data['name']}%"
        bills_params = {"sponsor_pattern": sponsor_pattern}

        if jurisdiction:
            bills_query += " AND jurisdiction = %(jurisdiction)s"
            bills_params["jurisdiction"] = jurisdiction
        if classification:
            bills_query += " AND classification && %(classification)s"
            bills_params["classification"] = classification

        bills_query += f" ORDER BY updated_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            bills_result = conn.execute(bills_query, bills_params)
            bills_rows = bills_result.fetchall()
            bills_columns = bills_result.keys()

        bills_df = pd.DataFrame(bills_rows, columns=bills_columns)

        return {
            "person": person_data,
            "bill_count": len(bills_df),
            "bills": bills_df.to_dict('records'),
            "filters": {"jurisdiction": jurisdiction, "classification": classification}
        }

    def query_bills_by_year_range(self, start_year: int, end_year: Optional[int] = None,
                                jurisdiction: Optional[str] = None, classification: Optional[List[str]] = None,
                                limit: int = 100) -> Dict[str, Any]:
        """Query bills within a specific year range"""
        if end_year is None:
            end_year = start_year

        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM openstates_bills
        WHERE EXTRACT(YEAR FROM created_at) BETWEEN %(start_year)s AND %(end_year)s
        """
        params = {"start_year": start_year, "end_year": end_year}

        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
        if classification:
            query += " AND classification && %(classification)s"
            params["classification"] = classification

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "year_range": {"start": start_year, "end": end_year},
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"jurisdiction": jurisdiction, "classification": classification}
        }

    def query_bills_by_topics(self, topics: List[str], jurisdiction: Optional[str] = None,
                            classification: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Query bills by topics/subjects"""
        engine = get_sqlalchemy_engine()

        query = "SELECT * FROM openstates_bills WHERE 1=1"
        params = {}

        # Build topic conditions
        topic_conditions = []
        for i, topic in enumerate(topics):
            topic_conditions.append(f"subjects::text ILIKE %(topic_{i})s")
            params[f"topic_{i}"] = f"%{topic}%"

        query += " AND (" + " OR ".join(topic_conditions) + ")"

        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
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
            "topics": topics,
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"jurisdiction": jurisdiction, "classification": classification}
        }

    def query_person_voting_record(self, person_name: str, jurisdiction: Optional[str] = None,
                                 limit: int = 100) -> Dict[str, Any]:
        """Query voting record for a specific person"""
        engine = get_sqlalchemy_engine()

        # Find the person
        person_query = """
        SELECT id, name, party, jurisdiction, district
        FROM openstates_people
        WHERE name ILIKE %(name)s
        """
        person_params = {"name": f"%{person_name}%"}

        if jurisdiction:
            person_query += " AND jurisdiction = %(jurisdiction)s"
            person_params["jurisdiction"] = jurisdiction

        with engine.connect() as conn:
            person_result = conn.execute(person_query, person_params)
            person_row = person_result.fetchone()

        if not person_row:
            return {"error": f"Person '{person_name}' not found"}

        person_data = {
            "id": person_row[0],
            "name": person_row[1],
            "party": person_row[2],
            "jurisdiction": person_row[3],
            "district": person_row[4]
        }

        # Placeholder - voting data structure needs to be defined
        return {
            "person": person_data,
            "voting_record": {"status": "not_implemented", "message": "Voting data structure needs to be defined"},
            "filters": {"jurisdiction": jurisdiction}
        }

    def query_committees(self, jurisdiction: Optional[str] = None, committee_name: Optional[str] = None,
                        limit: int = 100) -> Dict[str, Any]:
        """Query committee information"""
        # Placeholder - committee data structure needs to be defined
        return {
            "status": "not_implemented",
            "message": "Committee data structure needs to be defined in database schema",
            "filters": {"jurisdiction": jurisdiction, "committee_name": committee_name}
        }

    def search_bills_by_text_content(self, search_text: str, jurisdiction: Optional[str] = None,
                                   classification: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Search bills by text content in title or description"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM openstates_bills
        WHERE (title ILIKE %(search_text)s OR latest_action_description ILIKE %(search_text)s)
        """
        params = {"search_text": f"%{search_text}%"}

        if jurisdiction:
            query += " AND jurisdiction = %(jurisdiction)s"
            params["jurisdiction"] = jurisdiction
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
            "search_text": search_text,
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"jurisdiction": jurisdiction, "classification": classification}
        }
