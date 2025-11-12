from typing import Optional, Dict, Any, List
from .base_client import BaseClient
import pandas as pd
import os
from mcp_server.db import get_sqlalchemy_engine
from mcp_server.utils.ingest import save_dataframe


class CongressClient(BaseClient):
    BASE = "https://api.congress.gov"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    def search_bills(self, congress: Optional[int] = None, billType: Optional[str] = None, page: int = 1):
        # Congress API uses api.data.gov API key (api_key param)
        url = f"{self.BASE}/v3/bill"
        params = {"page": page, "limit": 250}  # v3 API uses limit instead of per_page
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
        url = f"{self.BASE}/v3/bill/{congress}/{billType}/{billNumber}/actions"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_bill_text(self, congress: int, billType: str, billNumber: str):
        url = f"{self.BASE}/v3/bill/{congress}/{billType}/{billNumber}/text"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_members(self, congress: Optional[int] = None, chamber: Optional[str] = None):
        url = f"{self.BASE}/v3/member"
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
        url = f"{self.BASE}/v3/member/{bioguideId}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_committee(self, committee_code: str):
        url = f"{self.BASE}/v3/committee/{committee_code}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_committees(self, congress: Optional[int] = None, chamber: Optional[str] = None):
        url = f"{self.BASE}/v3/committee"
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

    def get_vote(self, congress: int, chamber: str, session: int, roll_number: int):
        url = f"{self.BASE}/v3/congress/{congress}/{chamber}/session/{session}/votes/{roll_number}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_votes(self, congress: Optional[int] = None, chamber: Optional[str] = None, date: Optional[str] = None):
        url = f"{self.BASE}/v3/vote"
        params = {}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        if date:
            params["date"] = date
        if self.api_key:
            params["api_key"] = self.api_key
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def query_congress_bills(self, congress: Optional[int] = None,
                           bill_type: Optional[str] = None,
                           limit: int = 100) -> Dict[str, Any]:
        """Query Congress bills from database"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM congress_bills WHERE 1=1"

        params = {}
        if congress:
            query += " AND congress = %(congress)s"
            params["congress"] = congress
        if bill_type:
            query += " AND bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY latest_action_date DESC"
        if limit:
            query += f" LIMIT {limit}"

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

    def analyze_bill_sponsors_congress(self, congress: Optional[int] = None,
                                     bill_type: Optional[str] = None) -> Dict[str, Any]:
        """Analyze bill sponsorship patterns in Congress data"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            c.congress,
            c.bill_type,
            c.bill_number,
            jsonb_array_elements(c.sponsors) as sponsor
        FROM congress_bills c
        WHERE c.sponsors IS NOT NULL
        """

        params = {}
        if congress:
            query += " AND c.congress = %(congress)s"
            params["congress"] = congress
        if bill_type:
            query += " AND c.bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY c.latest_action_date DESC LIMIT 1000"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['congress', 'bill_type', 'bill_number', 'sponsor'])

        # Analyze sponsorship patterns
        sponsor_counts = df.groupby(df['sponsor'].apply(lambda x: x.get('fullName') if isinstance(x, dict) else str(x))).size().sort_values(ascending=False)

        return {
            "total_cosponsored_bills": len(df),
            "unique_sponsors": len(sponsor_counts),
            "top_sponsors": sponsor_counts.head(10).to_dict(),
            "sample_data": df.head(5).to_dict('records')
        }

    def get_congressional_trends(self, start_congress: Optional[int] = None,
                               end_congress: Optional[int] = None) -> Dict[str, Any]:
        """Analyze congressional activity trends by congress number"""
        engine = get_sqlalchemy_engine()
        query = """
        SELECT
            congress,
            bill_type,
            COUNT(*) as bill_count,
            AVG(CASE WHEN subjects IS NOT NULL THEN array_length(subjects, 1) ELSE 0 END) as avg_subjects
        FROM congress_bills
        WHERE 1=1
        """

        params = {}
        if start_congress:
            query += " AND congress >= %(start_congress)s"
            params["start_congress"] = start_congress
        if end_congress:
            query += " AND congress <= %(end_congress)s"
            params["end_congress"] = end_congress

        query += " GROUP BY congress, bill_type ORDER BY congress, bill_type"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['congress', 'bill_type', 'bill_count', 'avg_subjects'])

        # Pivot to show bill types by congress
        pivot_df = df.pivot(index='congress', columns='bill_type', values='bill_count').fillna(0)

        return {
            "trends_by_type": pivot_df.to_dict('index'),
            "summary_stats": {
                "total_congresses": len(pivot_df),
                "total_bills": int(df['bill_count'].sum()),
                "avg_bills_per_congress": float(df.groupby('congress')['bill_count'].sum().mean())
            },
            "bill_type_breakdown": df.groupby('bill_type')['bill_count'].sum().to_dict()
        }

    def search_congress_bills_advanced(self, keywords: Optional[List[str]] = None,
                                     sponsors: Optional[List[str]] = None,
                                     congress: Optional[int] = None,
                                     bill_type: Optional[str] = None,
                                     limit: int = 100) -> Dict[str, Any]:
        """Advanced search for Congress bills"""
        engine = get_sqlalchemy_engine()
        query = "SELECT * FROM congress_bills WHERE 1=1"
        params = {}

        if keywords:
            keyword_conditions = []
            for i, keyword in enumerate(keywords):
                keyword_conditions.append(f"title ILIKE %(keyword_{i})s")
                params[f"keyword_{i}"] = f"%{keyword}%"
            query += " AND (" + " OR ".join(keyword_conditions) + ")"

        if sponsors:
            sponsor_conditions = []
            for i, sponsor in enumerate(sponsors):
                sponsor_conditions.append("sponsors::text ILIKE %(sponsor_{i})s")
                params[f"sponsor_{i}"] = f"%{sponsor}%"
            query += " AND (" + " OR ".join(sponsor_conditions) + ")"

        if congress:
            query += " AND congress = %(congress)s"
            params["congress"] = congress

        if bill_type:
            query += " AND bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY latest_action_date DESC"
        if limit:
            query += f" LIMIT {limit}"

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
                "congress": congress,
                "bill_type": bill_type
            },
            "data": df.to_dict('records'),
            "columns": list(columns)
        }

    def analyze_member_activity(self, bioguide_id: Optional[str] = None,
                              congress: Optional[int] = None) -> Dict[str, Any]:
        """Analyze legislative activity for members"""
        engine = get_sqlalchemy_engine()

        # Get member info
        member_query = "SELECT * FROM congress_members WHERE 1=1"
        member_params = {}

        if bioguide_id:
            member_query += " AND bioguide_id = %(bioguide_id)s"
            member_params["bioguide_id"] = bioguide_id

        with engine.connect() as conn:
            member_result = conn.execute(member_query, member_params)
            member_row = member_result.fetchone()

        if not member_row:
            return {"error": "Member not found"}

        member_columns = member_result.keys()
        member_data = dict(zip(member_columns, member_row))

        # Get sponsored bills
        bills_query = """
        SELECT
            congress,
            bill_type,
            bill_number,
            title,
            latest_action_date,
            latest_action_description
        FROM congress_bills
        WHERE sponsors::text ILIKE %(sponsor_pattern)s
        """

        sponsor_name = f"{member_data.get('first_name', '')} {member_data.get('last_name', '')}".strip()
        bills_params = {"sponsor_pattern": f"%{sponsor_name}%"}

        if congress:
            bills_query += " AND congress = %(congress)s"
            bills_params["congress"] = congress

        bills_query += " ORDER BY latest_action_date DESC"

        with engine.connect() as conn:
            bills_result = conn.execute(bills_query, bills_params)
            bills_rows = bills_result.fetchall()

        bills_df = pd.DataFrame(bills_rows, columns=['congress', 'bill_type', 'bill_number', 'title', 'latest_action_date', 'latest_action_description'])

        return {
            "member_info": member_data,
            "sponsored_bills_count": len(bills_df),
            "sponsored_bills": bills_df.to_dict('records'),
            "activity_summary": {
                "total_bills_sponsored": len(bills_df),
                "congresses_active": bills_df['congress'].nunique() if len(bills_df) > 0 else 0,
                "most_active_congress": bills_df['congress'].mode().iloc[0] if len(bills_df) > 0 else None
            }
        }

    def compare_congresses(self, congress1: int, congress2: int) -> Dict[str, Any]:
        """Compare legislative activity between two congresses"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT
            congress,
            COUNT(*) as total_bills,
            COUNT(DISTINCT bill_type) as bill_types,
            AVG(CASE WHEN subjects IS NOT NULL THEN array_length(subjects, 1) ELSE 0 END) as avg_subjects
        FROM congress_bills
        WHERE congress IN (%(c1)s, %(c2)s)
        GROUP BY congress
        """

        params = {"c1": congress1, "c2": congress2}

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        comparison = {}
        for row in rows:
            cong, total_bills, bill_types, avg_subjects = row
            comparison[cong] = {
                "total_bills": total_bills,
                "bill_types": bill_types,
                "avg_subjects_per_bill": float(avg_subjects) if avg_subjects else 0
            }

        # Get bill type distribution for each congress
        type_query = """
        SELECT congress, bill_type, COUNT(*) as count
        FROM congress_bills
        WHERE congress IN (%(c1)s, %(c2)s)
        GROUP BY congress, bill_type
        ORDER BY congress, count DESC
        """

        with engine.connect() as conn:
            type_result = conn.execute(type_query, params)
            type_rows = type_result.fetchall()

        type_comparison = {}
        for row in type_rows:
            cong, bill_type, count = row
            if cong not in type_comparison:
                type_comparison[cong] = {}
            type_comparison[cong][bill_type] = count

        return {
            "congress_comparison": comparison,
            "bill_type_distribution": type_comparison,
            "congress1": congress1,
            "congress2": congress2
        }

    def export_congress_data(self, congress: Optional[int] = None,
                           bill_type: Optional[str] = None,
                           format: str = "csv",
                           output_path: Optional[str] = None) -> Dict[str, Any]:
        """Export Congress bills data with filtering"""
        data = self.query_congress_bills(congress=congress, bill_type=bill_type, limit=50000)
        df = pd.DataFrame(data["data"])

        if not output_path:
            congress_str = f"_congress_{congress}" if congress else ""
            type_str = f"_{bill_type}" if bill_type else ""
            output_path = f"congress_bills{congress_str}{type_str}.{format}"

        save_dataframe(df, output_path, format)

        return {
            "status": "success",
            "file": output_path,
            "format": format,
            "records": len(df),
            "filters": {"congress": congress, "bill_type": bill_type}
        }

    def query_bills_by_party(self, party: str, congress: Optional[int] = None,
                           bill_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Query bills sponsored by members of a specific political party"""
        engine = get_sqlalchemy_engine()

        # First get members of the specified party
        member_query = """
        SELECT bioguide_id, first_name, last_name, state, district
        FROM congress_members
        WHERE party = %(party)s
        """
        member_params = {"party": party}

        with engine.connect() as conn:
            member_result = conn.execute(member_query, member_params)
            members = member_result.fetchall()

        if not members:
            return {"error": f"No members found for party {party}", "party": party}

        member_names = [f"{row[1]} {row[2]}" for row in members]

        # Query bills sponsored by these members
        bills_query = "SELECT * FROM congress_bills WHERE 1=1"
        bills_params = {}

        # Build sponsor conditions
        sponsor_conditions = []
        for i, name in enumerate(member_names):
            sponsor_conditions.append(f"sponsors::text ILIKE %(sponsor_{i})s")
            bills_params[f"sponsor_{i}"] = f"%{name}%"

        bills_query += " AND (" + " OR ".join(sponsor_conditions) + ")"

        if congress:
            bills_query += " AND congress = %(congress)s"
            bills_params["congress"] = congress
        if bill_type:
            bills_query += " AND bill_type = %(bill_type)s"
            bills_params["bill_type"] = bill_type

        bills_query += " ORDER BY latest_action_date DESC"
        if limit:
            bills_query += f" LIMIT {limit}"

        with engine.connect() as conn:
            bills_result = conn.execute(bills_query, bills_params)
            bills_rows = bills_result.fetchall()
            bills_columns = bills_result.keys()

        bills_df = pd.DataFrame(bills_rows, columns=bills_columns)

        return {
            "party": party,
            "member_count": len(members),
            "bill_count": len(bills_df),
            "members_sample": [{"name": f"{row[1]} {row[2]}", "state": row[3], "district": row[4]} for row in members[:5]],
            "bills": bills_df.to_dict('records'),
            "filters": {"congress": congress, "bill_type": bill_type}
        }

    def query_bills_by_member_name(self, member_name: str, congress: Optional[int] = None,
                                 bill_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Query bills sponsored by a specific member by name"""
        engine = get_sqlalchemy_engine()

        # Find the member
        member_query = """
        SELECT bioguide_id, first_name, last_name, party, state, district
        FROM congress_members
        WHERE CONCAT(first_name, ' ', last_name) ILIKE %(name)s
        OR first_name ILIKE %(name)s
        OR last_name ILIKE %(name)s
        """
        member_params = {"name": f"%{member_name}%"}

        with engine.connect() as conn:
            member_result = conn.execute(member_query, member_params)
            member_row = member_result.fetchone()

        if not member_row:
            return {"error": f"Member '{member_name}' not found"}

        member_data = {
            "bioguide_id": member_row[0],
            "name": f"{member_row[1]} {member_row[2]}",
            "party": member_row[3],
            "state": member_row[4],
            "district": member_row[5]
        }

        # Query bills sponsored by this member
        bills_query = """
        SELECT * FROM congress_bills
        WHERE sponsors::text ILIKE %(sponsor_pattern)s
        """

        sponsor_pattern = f"%{member_data['name']}%"
        bills_params = {"sponsor_pattern": sponsor_pattern}

        if congress:
            bills_query += " AND congress = %(congress)s"
            bills_params["congress"] = congress
        if bill_type:
            bills_query += " AND bill_type = %(bill_type)s"
            bills_params["bill_type"] = bill_type

        bills_query += " ORDER BY latest_action_date DESC"
        if limit:
            bills_query += f" LIMIT {limit}"

        with engine.connect() as conn:
            bills_result = conn.execute(bills_query, bills_params)
            bills_rows = bills_result.fetchall()
            bills_columns = bills_result.keys()

        bills_df = pd.DataFrame(bills_rows, columns=bills_columns)

        return {
            "member": member_data,
            "bill_count": len(bills_df),
            "bills": bills_df.to_dict('records'),
            "filters": {"congress": congress, "bill_type": bill_type}
        }

    def query_bills_by_year_range(self, start_year: int, end_year: Optional[int] = None,
                                bill_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Query bills within a specific year range"""
        if end_year is None:
            end_year = start_year

        engine = get_sqlalchemy_engine()

        # Convert years to congress numbers (approximate: Congress starts in odd years)
        start_congress = ((start_year - 1789) // 2) + 1
        end_congress = ((end_year - 1789) // 2) + 1

        query = "SELECT * FROM congress_bills WHERE congress BETWEEN %(start_congress)s AND %(end_congress)s"
        params = {"start_congress": start_congress, "end_congress": end_congress}

        if bill_type:
            query += " AND bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY congress DESC, latest_action_date DESC"
        if limit:
            query += f" LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "year_range": {"start": start_year, "end": end_year},
            "congress_range": {"start": start_congress, "end": end_congress},
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"bill_type": bill_type}
        }

    def query_bills_by_topics(self, topics: List[str], congress: Optional[int] = None,
                            bill_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Query bills by topics/subjects"""
        engine = get_sqlalchemy_engine()

        query = "SELECT * FROM congress_bills WHERE 1=1"
        params = {}

        # Build topic conditions
        topic_conditions = []
        for i, topic in enumerate(topics):
            topic_conditions.append(f"subjects::text ILIKE %(topic_{i})s")
            params[f"topic_{i}"] = f"%{topic}%"

        query += " AND (" + " OR ".join(topic_conditions) + ")"

        if congress:
            query += " AND congress = %(congress)s"
            params["congress"] = congress
        if bill_type:
            query += " AND bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY latest_action_date DESC"
        if limit:
            query += f" LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "topics": topics,
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"congress": congress, "bill_type": bill_type}
        }

    def query_member_voting_record(self, member_name: str, congress: Optional[int] = None,
                                 limit: int = 100) -> Dict[str, Any]:
        """Query voting record for a specific member"""
        engine = get_sqlalchemy_engine()

        # Find the member
        member_query = """
        SELECT bioguide_id, first_name, last_name, party, state, district
        FROM congress_members
        WHERE CONCAT(first_name, ' ', last_name) ILIKE %(name)s
        """
        member_params = {"name": f"%{member_name}%"}

        with engine.connect() as conn:
            member_result = conn.execute(member_query, member_params)
            member_row = member_result.fetchone()

        if not member_row:
            return {"error": f"Member '{member_name}' not found"}

        member_data = {
            "bioguide_id": member_row[0],
            "name": f"{member_row[1]} {member_row[2]}",
            "party": member_row[3],
            "state": member_row[4],
            "district": member_row[5]
        }

        # Query voting record from congress_votes table
        votes_query = """
        SELECT
            vote_id,
            congress,
            chamber,
            vote_date,
            question,
            description,
            result,
            member_votes
        FROM congress_votes
        WHERE member_votes::text ILIKE %(member_pattern)s
        """

        member_pattern = f"%{member_data['bioguide_id']}%"
        votes_params = {"member_pattern": member_pattern}

        if congress:
            votes_query += " AND congress = %(congress)s"
            votes_params["congress"] = congress

        votes_query += " ORDER BY vote_date DESC"
        if limit:
            votes_query += f" LIMIT {limit}"

        with engine.connect() as conn:
            votes_result = conn.execute(votes_query, votes_params)
            votes_rows = votes_result.fetchall()

        votes_data = []
        for row in votes_rows:
            vote_data = {
                "vote_id": row[0],
                "congress": row[1],
                "chamber": row[2],
                "vote_date": row[3],
                "question": row[4],
                "description": row[5],
                "result": row[6]
            }
            votes_data.append(vote_data)

        # Calculate voting statistics
        total_votes = len(votes_data)
        if total_votes > 0:
            # This is a simplified analysis - in practice you'd need to parse member_votes JSON
            voting_stats = {
                "total_votes": total_votes,
                "ayes": 0,  # Would need to parse member_votes JSON
                "noes": 0,  # Would need to parse member_votes JSON
                "present": 0,  # Would need to parse member_votes JSON
                "not_voting": 0  # Would need to parse member_votes JSON
            }
        else:
            voting_stats = {"total_votes": 0}

        return {
            "member": member_data,
            "voting_record": {
                "total_votes": total_votes,
                "recent_votes": votes_data[:10],  # Show 10 most recent
                "voting_statistics": voting_stats
            },
            "filters": {"congress": congress}
        }

    def query_committee_members(self, committee_code: Optional[str] = None,
                              congress: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
        """Query committee membership information"""
        engine = get_sqlalchemy_engine()

        query = "SELECT * FROM congress_committees WHERE 1=1"
        params = {}

        if committee_code:
            query += " AND committee_code = %(committee_code)s"
            params["committee_code"] = committee_code

        if congress:
            query += " AND congress = %(congress)s"
            params["congress"] = congress

        query += " ORDER BY committee_name"
        if limit:
            query += f" LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "count": len(df),
            "committees": df.to_dict('records'),
            "filters": {"committee_code": committee_code, "congress": congress}
        }

    def search_bills_by_text_content(self, search_text: str, congress: Optional[int] = None,
                                   bill_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Search bills by text content in title or description"""
        engine = get_sqlalchemy_engine()

        query = """
        SELECT * FROM congress_bills
        WHERE (title ILIKE %(search_text)s OR latest_action_description ILIKE %(search_text)s)
        """
        params = {"search_text": f"%{search_text}%"}

        if congress:
            query += " AND congress = %(congress)s"
            params["congress"] = congress
        if bill_type:
            query += " AND bill_type = %(bill_type)s"
            params["bill_type"] = bill_type

        query += " ORDER BY latest_action_date DESC"
        if limit:
            query += f" LIMIT {limit}"

        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()

        df = pd.DataFrame(rows, columns=columns)

        return {
            "search_text": search_text,
            "bill_count": len(df),
            "bills": df.to_dict('records'),
            "filters": {"congress": congress, "bill_type": bill_type}
        }
