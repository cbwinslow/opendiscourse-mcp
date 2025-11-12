import pytest
from unittest.mock import Mock, patch, mock_open
from mcp_server.clients.govinfo_client import GovInfoClient


@patch('mcp_server.clients.base_client.requests.Session')
def test_list_collections(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {"collections": ["BILLS", "STATUTES"]}
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    client = GovInfoClient(api_key="test_key")
    result = client.list_collections()
    assert result == {"collections": ["BILLS", "STATUTES"]}
    mock_session.return_value.get.assert_called_once_with(
        'https://api.govinfo.gov/collections',
        params={'api_key': 'test_key'},
        timeout=30
    )


@patch('mcp_server.clients.base_client.requests.Session')
@patch('bs4.BeautifulSoup')
def test_bulk_download(mock_bs, mock_session):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '<html><a href="file1.xml">file1</a><a href="file2.zip">file2</a></html>'
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response

    mock_soup = Mock()
    mock_a1 = Mock()
    mock_a1.__getitem__ = Mock(return_value='file1.xml')
    mock_a1.get = Mock(return_value='file1.xml')
    mock_a2 = Mock()
    mock_a2.__getitem__ = Mock(return_value='file2.zip')
    mock_a2.get = Mock(return_value='file2.zip')
    mock_soup.find_all.return_value = [mock_a1, mock_a2]
    mock_bs.return_value = mock_soup

    client = GovInfoClient()
    result = client.bulk_download("BILLS", year=2025)
    assert "bulk_url" in result
    assert result["bulk_url"] == "https://www.govinfo.gov/bulkdata/BILLS/2025"
    assert "files" in result
    assert len(result["files"]) == 2
    assert "file1.xml" in result["files"][0]


@patch('mcp_server.utils.downloader.fetch_file')
def test_fetch_bulk_file(mock_fetch):
    mock_fetch.return_value = "downloaded"

    client = GovInfoClient()
    result = client.fetch_bulk_file("http://example.com/file.xml", "/tmp/file.xml")
    assert result == "downloaded"
    mock_fetch.assert_called_once_with("http://example.com/file.xml", "/tmp/file.xml", chunk_size=65536, resume=True)


@patch('mcp_server.utils.xml_ingest.ingest_xml_to_df')
def test_ingest_xml_to_df(mock_ingest):
    mock_ingest.return_value = "dataframe"

    client = GovInfoClient()
    result = client.ingest_xml_to_df("/tmp/file.xml")
    assert result == "dataframe"
    mock_ingest.assert_called_once_with("/tmp/file.xml", record_xpath=".//record")