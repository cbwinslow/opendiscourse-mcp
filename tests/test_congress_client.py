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