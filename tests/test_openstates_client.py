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