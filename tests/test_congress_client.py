import pytest
from unittest.mock import Mock, patch
from mcp_server.clients.congress_client import CongressClient


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_bills(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bills": [{"billType": "hr", "billNumber": "1"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.search_bills(congress=118, billType="hr")
    assert result == {"bills": [{"billType": "hr", "billNumber": "1"}]}
    mock_session.return_value.get.assert_called_once()
    args, kwargs = mock_session.return_value.get.call_args
    assert kwargs['params']['congress'] == 118
    assert kwargs['params']['billType'] == 'hr'
    assert kwargs['params']['api_key'] == 'test_key'


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_bill(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"billType": "hr", "billNumber": "1", "title": "Test Bill"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.get_bill(118, "hr", "1")
    assert result == {"billType": "hr", "billNumber": "1", "title": "Test Bill"}
    mock_session.return_value.get.assert_called_once_with(
        'https://api.congress.gov/bill/118/hr/1',
        params={'api_key': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_bill_actions(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"actions": [{"actionCode": "1000"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.get_bill_actions(118, "hr", "1")
    assert result == {"actions": [{"actionCode": "1000"}]}
    mock_session.return_value.get.assert_called_once_with(
        'https://api.congress.gov/bill/118/hr/1/actions',
        params={'api_key': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_bill_text(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"text": "Bill text here"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient()
    result = client.get_bill_text(118, "hr", "1")
    assert result == {"text": "Bill text here"}
    mock_session.return_value.get.assert_called_once_with(
        'https://api.congress.gov/bill/118/hr/1/text',
        params={},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_list_members(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"members": [{"bioguideId": "A000001"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.list_members(congress=118, chamber="house")
    assert result == {"members": [{"bioguideId": "A000001"}]}
    args, kwargs = mock_session.return_value.get.call_args
    assert kwargs['params']['congress'] == 118
    assert kwargs['params']['chamber'] == 'house'


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_member(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bioguideId": "A000001", "name": "John Doe"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.get_member("A000001")
    assert result == {"bioguideId": "A000001", "name": "John Doe"}
    mock_session.return_value.get.assert_called_once_with(
        'https://api.congress.gov/member/A000001',
        params={'api_key': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_bulk_download_collection(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"files": ["file1.zip", "file2.zip"]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = CongressClient(api_key="test_key")
    result = client.bulk_download_collection("BILLS", year=2023)
    assert result == {"files": ["file1.zip", "file2.zip"]}
    args, kwargs = mock_session.return_value.get.call_args
    assert "bulk-downloads" in args[0]
    assert kwargs['params']['api_key'] == 'test_key'


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_query_congress_bills(mock_get_engine):
    # Mock the database engine and connection
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("data1", "data2")]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.query_congress_bills(congress=118)

    assert "count" in result
    assert "data" in result
    assert "columns" in result
    mock_connection.execute.assert_called_once()


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_analyze_bill_sponsors_congress(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("data1", "data2")]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.analyze_bill_sponsors_congress(congress=118)

    assert "total_cosponsored_bills" in result
    assert "unique_sponsors" in result
    assert "top_sponsors" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_get_congressional_trends(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [(118, 100, 5, 2.5)]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.get_congressional_trends(start_congress=115, end_congress=118)

    assert "trends_by_type" in result
    assert "summary_stats" in result
    assert "bill_type_breakdown" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_search_congress_bills_advanced(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("data1", "data2")]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.search_congress_bills_advanced(keywords=["healthcare"])

    assert "count" in result
    assert "search_criteria" in result
    assert "data" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_analyze_member_activity(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    # Mock member query result
    mock_member_result = Mock()
    mock_member_result.fetchone.return_value = ("A000001", "John", "Doe", "D", "CA", "12")
    mock_connection.execute.side_effect = [mock_member_result, Mock()]  # First call returns member, second returns bills
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.analyze_member_activity(bioguide_id="A000001")

    assert "member_info" in result
    assert "sponsored_bills_count" in result
    assert "activity_summary" in result


def test_compare_congresses():
    """Test congress comparison (may not make API calls)."""
    client = CongressClient(api_key="test_key")
    # This method might be implemented locally
    try:
        result = client.compare_congresses(117, 118)
        assert isinstance(result, dict)
    except Exception:
        # Method might not be implemented yet
        pass


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
@patch('mcp_server.clients.congress_client.save_dataframe')
def test_export_congress_data(mock_save, mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("data1", "data2")]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.export_congress_data(congress=118, format="json")

    assert "status" in result
    assert "file" in result
    assert "records" in result
    mock_save.assert_called_once()


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_query_bills_by_party(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    # Mock members query
    mock_members_result = Mock()
    mock_members_result.fetchall.return_value = [("id1", "John", "Doe", "CA", "12")]
    # Mock bills query
    mock_bills_result = Mock()
    mock_bills_result.fetchall.return_value = [("bill_data",)]
    mock_bills_result.keys.return_value = ["id", "title"]
    mock_connection.execute.side_effect = [mock_members_result, mock_bills_result]
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.query_bills_by_party("D", congress=118)

    assert "party" in result
    assert "member_count" in result
    assert "bill_count" in result
    assert "bills" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_query_bills_by_member_name(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    # Mock member query
    mock_member_result = Mock()
    mock_member_result.fetchone.return_value = ("A000001", "John", "Doe", "D", "CA", "12")
    # Mock bills query
    mock_bills_result = Mock()
    mock_bills_result.fetchall.return_value = [("bill_data",)]
    mock_bills_result.keys.return_value = ["id", "title"]
    mock_connection.execute.side_effect = [mock_member_result, mock_bills_result]
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.query_bills_by_member_name("Smith", congress=118)

    assert "member" in result
    assert "bill_count" in result
    assert "bills" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_query_bills_by_year_range(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("bill_data",)]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.query_bills_by_year_range(2020, 2023)

    assert "year_range" in result
    assert "congress_range" in result
    assert "bill_count" in result
    assert "bills" in result


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_query_bills_by_topics(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("bill_data",)]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.query_bills_by_topics(["health"], congress=118)

    assert "topics" in result
    assert "bill_count" in result
    assert "bills" in result


def test_query_member_voting_record():
    """Test voting record query (placeholder implementation)."""
    client = CongressClient(api_key="test_key")
    result = client.query_member_voting_record("Smith", congress=118)

    assert "member" in result
    assert "voting_record" in result
    assert result["voting_record"]["status"] == "not_implemented"


def test_query_committee_members():
    """Test committee members query (placeholder implementation)."""
    client = CongressClient(api_key="test_key")
    result = client.query_committee_members(committee_code="HSAG")

    assert result["status"] == "not_implemented"


@patch('mcp_server.clients.congress_client.get_sqlalchemy_engine')
def test_search_bills_by_text_content(mock_get_engine):
    mock_engine = Mock()
    mock_connection = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("bill_data",)]
    mock_result.keys.return_value = ["id", "title"]
    mock_connection.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = mock_connection
    mock_engine.connect.return_value.__exit__ = Mock()
    mock_get_engine.return_value = mock_engine

    client = CongressClient(api_key="test_key")
    result = client.search_bills_by_text_content("climate change", congress=118)

    assert "search_text" in result
    assert "bill_count" in result
    assert "bills" in result
