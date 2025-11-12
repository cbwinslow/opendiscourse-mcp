"""
Tests for the ingestion CLI tool.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from mcp_server.scripts.ingestion_cli import main, IngestionCLI


@pytest.fixture
def cli_runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_cli():
    """Mock CLI instance."""
    cli = Mock(spec=IngestionCLI)
    return cli


class TestIngestionCLI:
    """Test the ingestion CLI functionality."""

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_create_job_command(self, mock_cli_class, cli_runner):
        """Test create job command."""
        mock_cli = Mock()
        mock_cli.create_job = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'create', 'congress', 'bills',
            '--congress', '118'
        ])

        assert result.exit_code == 0
        mock_cli.create_job.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_schedule_job_command(self, mock_cli_class, cli_runner):
        """Test schedule job command."""
        mock_cli = Mock()
        mock_cli.schedule_job = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'schedule', 'congress', 'bills', 'test_job',
            '--cron', '0 2 * * *'
        ])

        assert result.exit_code == 0
        mock_cli.schedule_job.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_list_jobs_command(self, mock_cli_class, cli_runner):
        """Test list jobs command."""
        mock_cli = Mock()
        mock_cli.list_jobs = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, ['list'])

        assert result.exit_code == 0
        mock_cli.list_jobs.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_job_status_command(self, mock_cli_class, cli_runner):
        """Test job status command."""
        mock_cli = Mock()
        mock_cli.job_status = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'status', 'job_123',
            '--limit', '20'
        ])

        assert result.exit_code == 0
        mock_cli.job_status.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_remove_job_command(self, mock_cli_class, cli_runner):
        """Test remove job command."""
        mock_cli = Mock()
        mock_cli.remove_job = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, ['remove', 'job_123'])

        assert result.exit_code == 0
        mock_cli.remove_job.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_distributed_ingest_command(self, mock_cli_class, cli_runner):
        """Test distributed ingestion command."""
        mock_cli = Mock()
        mock_cli.distributed_ingest = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'distributed', 'congress',
            '--hosts', 'user1@host1', 'user2@host2'
        ])

        assert result.exit_code == 0
        mock_cli.distributed_ingest.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_ssh_setup_command(self, mock_cli_class, cli_runner):
        """Test SSH setup command."""
        mock_cli = Mock()
        mock_cli.setup_ssh_keys = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'ssh-setup',
            '--key-path', '~/.ssh/test_key',
            '--setup-host', 'testhost',
            '--setup-user', 'testuser'
        ])

        assert result.exit_code == 0
        mock_cli.setup_ssh_keys.assert_called_once()

    @patch('mcp_server.scripts.ingestion_cli.IngestionCLI')
    def test_sync_codebase_command(self, mock_cli_class, cli_runner):
        """Test sync codebase command."""
        mock_cli = Mock()
        mock_cli.sync_codebase = Mock()
        mock_cli_class.return_value = mock_cli

        result = cli_runner.invoke(main, [
            'sync',
            '--hosts', 'user@host',
            '--remote-path', '/tmp/test'
        ])

        assert result.exit_code == 0
        mock_cli.sync_codebase.assert_called_once()

    def test_invalid_command(self, cli_runner):
        """Test invalid command."""
        result = cli_runner.invoke(main, ['invalid_command'])

        assert result.exit_code == 2  # Click error code for invalid command
        assert "No such command" in result.output


class TestIngestionCLIMethods:
    """Test individual CLI methods."""

    def test_get_manager(self):
        """Test getting ingestion manager."""
        cli = IngestionCLI()

        with patch('mcp_server.scripts.ingestion_cli.get_ingestion_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            manager = cli.get_manager()

            assert manager == mock_manager
            mock_get_manager.assert_called_once()

    def test_get_scheduler(self):
        """Test getting scheduler."""
        cli = IngestionCLI()

        with patch('mcp_server.scripts.ingestion_cli.get_scheduler') as mock_get_scheduler:
            mock_scheduler = Mock()
            mock_get_scheduler.return_value = mock_scheduler

            scheduler = cli.get_scheduler()

            assert scheduler == mock_scheduler
            mock_get_scheduler.assert_called_once()

    @patch('asyncio.run')
    def test_create_job_async(self, mock_asyncio_run):
        """Test create job async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.source = 'congress'
        mock_args.collection_type = 'bills'
        mock_args.congress = 118

        cli.create_job(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_schedule_job_async(self, mock_asyncio_run):
        """Test schedule job async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.source = 'congress'
        mock_args.collection_type = 'bills'
        mock_args.name = 'test_job'
        mock_args.cron = '0 2 * * *'

        cli.schedule_job(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_list_jobs_async(self, mock_asyncio_run):
        """Test list jobs async execution."""
        cli = IngestionCLI()
        mock_args = Mock()

        cli.list_jobs(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_job_status_async(self, mock_asyncio_run):
        """Test job status async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.job_id = 'job_123'

        cli.job_status(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_remove_job_async(self, mock_asyncio_run):
        """Test remove job async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.job_id = 'job_123'

        cli.remove_job(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_distributed_ingest_async(self, mock_asyncio_run):
        """Test distributed ingest async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.source = 'congress'
        mock_args.hosts = ['user@host']

        cli.distributed_ingest(mock_args)

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_sync_codebase_async(self, mock_asyncio_run):
        """Test sync codebase async execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.hosts = ['user@host']

        cli.sync_codebase(mock_args)

        mock_asyncio_run.assert_called_once()

    def test_setup_ssh_keys_sync(self):
        """Test SSH setup sync execution."""
        cli = IngestionCLI()
        mock_args = Mock()
        mock_args.key_path = '~/.ssh/test_key'

        cli.setup_ssh_keys(mock_args)

        # Should not use asyncio.run for sync method
