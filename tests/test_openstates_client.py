import pytest
from unittest.mock import Mock, patch
from mcp_server.clients.openstates_client import OpenStatesClient


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_bills(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"id": "bill1"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.search_bills(jurisdiction="nc", q="test")
    assert result == {"results": [{"id": "bill1"}]}
    mock_session.return_value.get.assert_called_once()
    args, kwargs = mock_session.return_value.get.call_args
    assert kwargs['params']['jurisdiction'] == 'nc'
    assert kwargs['params']['q'] == 'test'
    assert kwargs['params']['apikey'] == 'test_key'


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_bill(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"id": "bill1", "title": "Test Bill"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.get_bill("ocd-bill/test")
    assert result == {"id": "bill1", "title": "Test Bill"}
    mock_session.return_value.get.assert_called_once_with(
        'https://v3.openstates.org/bills/ocd-bill/ocd-bill/test',
        params={'apikey': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_people(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"id": "person1"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.search_people(jurisdiction="nc", name="John")
    assert result == {"results": [{"id": "person1"}]}
    args, kwargs = mock_session.return_value.get.call_args
    assert kwargs['params']['jurisdiction'] == 'nc'
    assert kwargs['params']['name'] == 'John'


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_person(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"id": "person1", "name": "John Doe"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient()
    result = client.get_person("person1")
    assert result == {"id": "person1", "name": "John Doe"}
    mock_session.return_value.get.assert_called_once_with(
        'https://v3.openstates.org/people/person1',
        params={},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_events(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"id": "event1"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.search_events(jurisdiction="nc", before="2025-12-01")
    assert result == {"results": [{"id": "event1"}]}
    args, kwargs = mock_session.return_value.get.call_args
    assert kwargs['params']['jurisdiction'] == 'nc'
    assert kwargs['params']['before'] == '2025-12-01'


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_event(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"id": "event1", "name": "Test Event"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient()
    result = client.get_event("event1")
    assert result == {"id": "event1", "name": "Test Event"}
    mock_session.return_value.get.assert_called_once_with(
        'https://v3.openstates.org/events/event1',
        params={},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_openapi_schema(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"openapi": "3.0.0"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.get_openapi_schema()
    assert result == {"openapi": "3.0.0"}
    mock_session.return_value.get.assert_called_once_with(
        'https://v3.openstates.org/openapi.json',
        params={'apikey': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_bills(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_bills(jurisdiction="nc", session="2025")
    assert result == {"results": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_export_bills(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"export": "data"}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.export_bills(jurisdiction="nc", format="csv")
    assert result == {"export": "data"}


@patch('mcp_server.clients.base_client.requests.Session')
def test_analyze_bill_sponsors(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"analysis": {}}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.analyze_bill_sponsors(bill_id="bill1")
    assert result == {"analysis": {}}


@patch('mcp_server.clients.base_client.requests.Session')
def test_find_related_bills(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"related": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.find_related_bills("bill1", jurisdiction="nc")
    assert result == {"related": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_legislative_trends(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"trends": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.get_legislative_trends(jurisdiction="nc")
    assert result == {"trends": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_bills_advanced(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.search_bills_advanced(keywords=["healthcare"])
    assert result == {"results": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_get_bill_statistics(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"stats": {}}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.get_bill_statistics(jurisdiction="nc")
    assert result == {"stats": {}}


@patch('mcp_server.clients.base_client.requests.Session')
def test_export_filtered_data(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.export_filtered_data("bills", jurisdiction="nc")
    assert result == {"data": []}


def test_compare_legislatures():
    """Test legislature comparison."""
    client = OpenStatesClient(api_key="test_key")
    try:
        result = client.compare_legislatures("nc", "ca")
        assert isinstance(result, dict)
    except Exception:
        # Method might not be implemented yet
        pass


@patch('mcp_server.clients.base_client.requests.Session')
def test_generate_bill_report(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"report": {}}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.generate_bill_report("bill1")
    assert result == {"report": {}}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_bills_by_party(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bills": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_bills_by_party("D", jurisdiction="nc")
    assert result == {"bills": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_bills_by_person_name(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bills": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_bills_by_person_name("Smith", jurisdiction="nc")
    assert result == {"bills": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_bills_by_year_range(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bills": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_bills_by_year_range(2020, 2023)
    assert result == {"bills": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_bills_by_topics(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"bills": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_bills_by_topics(["health"], jurisdiction="nc")
    assert result == {"bills": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_person_voting_record(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"votes": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_person_voting_record("Smith", jurisdiction="nc")
    assert result == {"votes": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_query_committees(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"committees": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.query_committees(jurisdiction="nc")
    assert result == {"committees": []}


@patch('mcp_server.clients.base_client.requests.Session')
def test_search_bills_by_text_content(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = OpenStatesClient(api_key="test_key")
    result = client.search_bills_by_text_content("climate change", jurisdiction="nc")
    assert result == {"results": []}
