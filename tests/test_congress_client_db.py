"""
Tests for CongressClient database query methods.
"""
import pytest
from unittest.mock import Mock, patch
import pandas as pd
from mcp_server.clients.congress_client import CongressClient


class TestCongressClientDatabaseQueries:
    """Test CongressClient database query methods."""

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_query_congress_bills(self, mock_get_engine):
        """Test querying Congress bills from database."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill", "2025-01-01", "Introduced", ["subject1"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.query_congress_bills(congress=118, limit=10)

        assert result["count"] == 1
        assert len(result["data"]) == 1
        assert result["data"][0]["congress"] == 118
        assert result["data"][0]["bill_type"] == "hr"

        # Verify query construction
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        assert "WHERE congress = %(congress)s" in query
        assert "LIMIT 10" in query

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_analyze_bill_sponsors_congress(self, mock_get_engine):
        """Test analyzing bill sponsorship patterns."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("Test Bill 1", {"fullName": "John Doe"}, "Test Jurisdiction", "2025-01-01"),
            ("Test Bill 2", {"fullName": "Jane Smith"}, "Test Jurisdiction", "2025-01-02")
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.analyze_bill_sponsors_congress(congress=118)

        assert result["total_cosponsored_bills"] == 2
        assert result["unique_sponsors"] == 2
        assert "John Doe" in result["top_sponsors"]
        assert "Jane Smith" in result["top_sponsors"]

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_get_congressional_trends(self, mock_get_engine):
        """Test getting congressional activity trends."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 100, 2.5),
            (118, "s", 50, 1.8)
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.get_congressional_trends(start_congress=118, end_congress=118)

        assert result["summary_stats"]["total_bills"] == 150
        assert 118 in result["trends_by_type"]
        assert "hr" in result["trends_by_type"][118]
        assert "s" in result["trends_by_type"][118]

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_search_congress_bills_advanced(self, mock_get_engine):
        """Test advanced bill search."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill", "2025-01-01", "Introduced", ["subject1"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.search_congress_bills_advanced(
            keywords=["test", "bill"],
            congress=118,
            limit=50
        )

        assert result["count"] == 1
        assert result["search_criteria"]["keywords"] == ["test", "bill"]
        assert result["search_criteria"]["congress"] == 118

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_analyze_member_activity(self, mock_get_engine):
        """Test analyzing member legislative activity."""
        # Mock member lookup
        mock_engine = Mock()
        mock_conn = Mock()

        # First call - member lookup
        mock_member_result = Mock()
        mock_member_result.fetchone.return_value = ("A000001", "John", "Doe", "Republican", "CA", "12")
        mock_conn.execute.side_effect = [mock_member_result, Mock()]  # Two calls

        # Second call - bills lookup
        mock_bills_result = Mock()
        mock_bills_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill 1", "2025-01-01", "Introduced"),
            (118, "hr", 5678, "Test Bill 2", "2025-01-02", "Passed")
        ]
        mock_conn.execute.side_effect = [mock_member_result, mock_bills_result]

        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.analyze_member_activity(bioguide_id="A000001")

        assert result["member_info"]["bioguide_id"] == "A000001"
        assert result["member_info"]["name"] == "John Doe"
        assert result["sponsored_bills_count"] == 2
        assert len(result["sponsored_bills"]) == 2

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_compare_congresses(self, mock_get_engine):
        """Test comparing legislative activity between congresses."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, 100, 5, 2.3, 80),
            (119, 120, 6, 2.8, 95)
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.compare_congresses(118, 119)

        assert 118 in result["congress_comparison"]
        assert 119 in result["congress_comparison"]
        assert result["congress_comparison"][118]["bill_count"] == 100
        assert result["congress_comparison"][119]["bill_count"] == 120

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    @patch('mcp_server.clients.congress_client.save_dataframe')
    def test_export_congress_data(self, mock_save, mock_get_engine):
        """Test exporting Congress data."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill", "2025-01-01", "Introduced", ["subject1"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.export_congress_data(congress=118, format="csv")

        assert result["status"] == "success"
        assert result["format"] == "csv"
        assert result["records"] == 1
        assert "congress_118" in result["file"]
        mock_save.assert_called_once()

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_query_bills_by_party(self, mock_get_engine):
        """Test querying bills by political party."""
        mock_engine = Mock()
        mock_conn = Mock()

        # Mock members query
        mock_members_result = Mock()
        mock_members_result.fetchall.return_value = [
            ("A000001", "John Doe", "Republican", "CA", "12"),
            ("B000002", "Jane Smith", "Republican", "NY", "1")
        ]

        # Mock bills query
        mock_bills_result = Mock()
        mock_bills_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill 1", "2025-01-01", "Introduced", ["subject1"], None, None),
            (118, "hr", 5678, "Test Bill 2", "2025-01-02", "Passed", ["subject2"], None, None)
        ]
        mock_bills_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]

        mock_conn.execute.side_effect = [mock_members_result, mock_bills_result]
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.query_bills_by_party(party="Republican", congress=118)

        assert result["party"] == "Republican"
        assert result["member_count"] == 2
        assert result["bill_count"] == 2
        assert len(result["members_sample"]) == 2

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_query_bills_by_member_name(self, mock_get_engine):
        """Test querying bills by member name."""
        mock_engine = Mock()
        mock_conn = Mock()

        # Mock member lookup
        mock_member_result = Mock()
        mock_member_result.fetchone.return_value = ("A000001", "John", "Doe", "Republican", "CA", "12")

        # Mock bills query
        mock_bills_result = Mock()
        mock_bills_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill", "2025-01-01", "Introduced", ["subject1"], None, None)
        ]
        mock_bills_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]

        mock_conn.execute.side_effect = [mock_member_result, mock_bills_result]
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.query_bills_by_member_name(member_name="John Doe")

        assert result["person"]["name"] == "John Doe"
        assert result["bill_count"] == 1
        assert len(result["bills"]) == 1

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_query_bills_by_year_range(self, mock_get_engine):
        """Test querying bills by year range."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill 1", "2025-01-01", "Introduced", ["subject1"], None, None),
            (119, "s", 5678, "Test Bill 2", "2026-01-01", "Introduced", ["subject2"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.query_bills_by_year_range(start_year=2025, end_year=2026)

        assert result["year_range"]["start"] == 2025
        assert result["year_range"]["end"] == 2026
        assert result["bill_count"] == 2

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_query_bills_by_topics(self, mock_get_engine):
        """Test querying bills by topics."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Test Bill", "2025-01-01", "Introduced", ["healthcare", "medicare"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.query_bills_by_topics(topics=["healthcare", "medicare"])

        assert result["topics"] == ["healthcare", "medicare"]
        assert result["bill_count"] == 1

    @patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
    def test_search_bills_by_text_content(self, mock_get_engine):
        """Test searching bills by text content."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (118, "hr", 1234, "Healthcare Reform Bill", "2025-01-01", "Introduced for healthcare reform", ["healthcare"], None, None)
        ]
        mock_result.keys.return_value = ["congress", "bill_type", "bill_number", "title", "latest_action_date", "latest_action_description", "subjects", "sponsors", "raw"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = mock_conn
        mock_engine.connect.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        client = CongressClient()
        result = client.search_bills_by_text_content(search_text="healthcare")

        assert result["search_text"] == "healthcare"
        assert result["bill_count"] == 1
        assert "healthcare" in result["bills"][0]["title"].lower()

    def test_bulk_download_collection_not_implemented(self):
        """Test bulk download collection returns not implemented."""
        client = CongressClient()
        result = client.bulk_download_collection("BILLS", year=2025)

        assert result["status"] == "not_implemented"
        assert result["collection"] == "BILLS"
        assert result["year"] == 2025

    def test_query_member_voting_record_placeholder(self):
        """Test member voting record query returns placeholder."""
        client = CongressClient()
        result = client.query_member_voting_record("John Doe")

        assert result["voting_record"]["status"] == "not_implemented"

    def test_query_committee_members_placeholder(self):
        """Test committee members query returns placeholder."""
        client = CongressClient()
        result = client.query_committee_members(committee_code="TEST")

        assert result["status"] == "not_implemented"
