"""Remote execution utilities for distributed ingestion."""
import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import subprocess
import shlex

# Optional imports with fallbacks
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    paramiko = None

try:
    from fabric import Connection, Config
    import fabric
    FABRIC_AVAILABLE = True
except ImportError:
    FABRIC_AVAILABLE = False
    Connection = None
    Config = None
    fabric = None

try:
    from scp import SCPClient
    SCP_AVAILABLE = True
except ImportError:
    SCP_AVAILABLE = False
    SCPClient = None

logger = logging.getLogger(__name__)

@dataclass
class RemoteHost:
    """Configuration for a remote host."""
    host: str
    user: str
    password: Optional[str] = None
    key_file: Optional[str] = None
    port: int = 22
    remote_path: str = "/tmp/mcp_ingestion"
    python_path: str = "python3"
    database_url: Optional[str] = None

@dataclass
class RemoteExecutionResult:
    """Result of a remote execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    host: str

class RemoteExecutor:
    """SSH-based remote execution manager."""

    def __init__(self, hosts: List[RemoteHost]):
        if not FABRIC_AVAILABLE:
            raise ImportError("Fabric not available. Install with: pip install fabric")
        self.hosts = hosts
        self.connections: Dict[str, Connection] = {}

    def connect_all(self):
        """Establish connections to all hosts."""
        for host in self.hosts:
            try:
                config = Config(
                    overrides={
                        'connect_kwargs': {
                            'key_filename': host.key_file,
                            'password': host.password
                        }
                    }
                )

                conn = Connection(
                    host=f"{host.user}@{host.host}:{host.port}",
                    config=config
                )

                # Test connection
                conn.run("echo 'Connection test'", hide=True)

                self.connections[host.host] = conn
                logger.info(f"Connected to {host.host}")

            except Exception as e:
                logger.error(f"Failed to connect to {host.host}: {e}")
                raise

    def disconnect_all(self):
        """Close all connections."""
        for host, conn in self.connections.items():
            try:
                conn.close()
                logger.info(f"Disconnected from {host}")
            except Exception as e:
                logger.error(f"Error disconnecting from {host}: {e}")

        self.connections.clear()

    async def execute_on_host(self, host: str, command: str,
                            env_vars: Optional[Dict[str, str]] = None) -> RemoteExecutionResult:
        """Execute command on specific host asynchronously."""
        if host not in self.connections:
            raise ValueError(f"No connection to host {host}")

        conn = self.connections[host]

        # Prepare environment variables
        env_prefix = ""
        if env_vars:
            env_parts = [f"{k}='{v}'" for k, v in env_vars.items()]
            env_prefix = " ".join(env_parts) + " "

        full_command = f"{env_prefix}{command}"

        start_time = asyncio.get_event_loop().time()

        try:
            # Execute command
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: conn.run(full_command, hide=True, warn=True)
            )

            execution_time = asyncio.get_event_loop().time() - start_time

            return RemoteExecutionResult(
                success=result.exited == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exited,
                execution_time=execution_time,
                host=host
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Remote execution failed on {host}: {e}")

            return RemoteExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=execution_time,
                host=host
            )

    async def execute_parallel(self, commands: Dict[str, str],
                             env_vars: Optional[Dict[str, str]] = None) -> Dict[str, RemoteExecutionResult]:
        """Execute commands on multiple hosts in parallel."""
        tasks = []

        for host, command in commands.items():
            if host in self.connections:
                task = self.execute_on_host(host, command, env_vars)
                tasks.append((host, task))

        # Execute all tasks
        results = {}
        for host, task in tasks:
            result = await task
            results[host] = result

        return results

    def upload_file(self, host: str, local_path: str, remote_path: str):
        """Upload file to remote host."""
        if host not in self.connections:
            raise ValueError(f"No connection to host {host}")

        conn = self.connections[host]

        try:
            # Create remote directory if it doesn't exist
            remote_dir = os.path.dirname(remote_path)
            conn.run(f"mkdir -p {remote_dir}", hide=True)

            # Upload file
            conn.put(local_path, remote_path)
            logger.info(f"Uploaded {local_path} to {host}:{remote_path}")

        except Exception as e:
            logger.error(f"Failed to upload file to {host}: {e}")
            raise

    def download_file(self, host: str, remote_path: str, local_path: str):
        """Download file from remote host."""
        if host not in self.connections:
            raise ValueError(f"No connection to host {host}")

        conn = self.connections[host]

        try:
            # Create local directory if it doesn't exist
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)

            # Download file
            conn.get(remote_path, local_path)
            logger.info(f"Downloaded {remote_path} from {host} to {local_path}")

        except Exception as e:
            logger.error(f"Failed to download file from {host}: {e}")
            raise

class DistributedIngestionManager:
    """Manager for distributed ingestion across multiple hosts."""

    def __init__(self, hosts: List[RemoteHost]):
        self.hosts = hosts
        self.executor = RemoteExecutor(hosts)

    async def __aenter__(self):
        """Async context manager entry."""
        self.executor.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.executor.disconnect_all()

    async def distribute_ingestion_job(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute an ingestion job across available hosts."""
        job_type = job_config.get('type')
        parameters = job_config.get('parameters', {})

        # Generate commands for each host
        commands = {}
        for host in self.hosts:
            command = self._generate_ingestion_command(host, job_type, parameters)
            commands[host.host] = command

        # Prepare environment variables
        env_vars = {
            'DATABASE_URL': job_config.get('database_url', ''),
            'PYTHONPATH': '/app'
        }

        # Execute commands in parallel
        results = await self.executor.execute_parallel(commands, env_vars)

        # Aggregate results
        aggregated_result = {
            'job_type': job_type,
            'total_hosts': len(self.hosts),
            'successful_hosts': sum(1 for r in results.values() if r.success),
            'failed_hosts': sum(1 for r in results.values() if not r.success),
            'host_results': {host: {
                'success': result.success,
                'exit_code': result.exit_code,
                'execution_time': result.execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr
            } for host, result in results.items()},
            'overall_success': all(r.success for r in results.values())
        }

        return aggregated_result

    def _generate_ingestion_command(self, host: RemoteHost, job_type: str, parameters: Dict[str, Any]) -> str:
        """Generate the appropriate ingestion command for a host."""
        base_cmd = f"cd {host.remote_path} && {host.python_path} mcp_server/scripts/"

        if job_type == 'congress':
            script = "congress_ingest.py"
            congress = parameters.get('congress', '')
            bill_type = parameters.get('bill_type', '')
            cmd = f"{script} --congress {congress}"
            if bill_type:
                cmd += f" --billType {bill_type}"

        elif job_type == 'openstates':
            script = "openstates_ingest.py"
            jurisdiction = parameters.get('jurisdiction', '')
            q = parameters.get('q', '')
            cmd = f"{script} --jurisdiction {jurisdiction}"
            if q:
                cmd += f" --q {q}"

        elif job_type == 'govinfo':
            script = "govinfo_ingest.py"
            collection = parameters.get('collection', '')
            year = parameters.get('year', '')
            cmd = f"{script} --collection {collection}"
            if year:
                cmd += f" --year {year}"

        else:
            raise ValueError(f"Unknown job type: {job_type}")

        return base_cmd + cmd

    async def sync_codebase(self, local_path: str = "."):
        """Sync codebase to all remote hosts."""
        import tarfile
        import io

        # Create tar archive of codebase
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add files, excluding common excludes
            excludes = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '*.pyc'}
            for root, dirs, files in os.walk(local_path):
                dirs[:] = [d for d in dirs if d not in excludes]
                for file in files:
                    if not any(file.endswith(ext) for ext in ['.pyc', '.pyo']):
                        tar.add(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), local_path))

        tar_buffer.seek(0)

        # Upload and extract on each host
        for host in self.hosts:
            try:
                # Save tar to temp file
                with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
                    temp_file.write(tar_buffer.getvalue())
                    temp_file_path = temp_file.name

                # Upload tar file
                remote_tar_path = f"{host.remote_path}/codebase.tar.gz"
                self.executor.upload_file(host.host, temp_file_path, remote_tar_path)

                # Extract on remote host
                extract_cmd = f"cd {host.remote_path} && rm -rf mcp_server && tar -xzf codebase.tar.gz && rm codebase.tar.gz"
                result = await self.executor.execute_on_host(host.host, extract_cmd)

                if result.success:
                    logger.info(f"Codebase synced to {host.host}")
                else:
                    logger.error(f"Failed to sync codebase to {host.host}: {result.stderr}")

                # Clean up temp file
                os.unlink(temp_file_path)

            except Exception as e:
                logger.error(f"Error syncing codebase to {host.host}: {e}")

class RemoteDatabaseManager:
    """Manager for remote database operations."""

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    async def execute_query(self, host: str, query: str, database_url: str) -> RemoteExecutionResult:
        """Execute a SQL query on remote database."""
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(query)
            sql_file = f.name

        try:
            # Upload SQL file
            remote_sql_path = f"/tmp/query_{int(asyncio.get_event_loop().time())}.sql"
            self.executor.upload_file(host, sql_file, remote_sql_path)

            # Execute query using psql or similar
            command = f"psql {database_url} -f {remote_sql_path}"

            # Execute command
            result = await self.executor.execute_on_host(host, command, {
                'DATABASE_URL': database_url
            })

            # Clean up remote file
            await self.executor.execute_on_host(host, f"rm {remote_sql_path}")

            return result

        finally:
            # Clean up local file
            os.unlink(sql_file)

    async def check_database_health(self, host: str, database_url: str) -> Dict[str, Any]:
        """Check database health on remote host."""
        query = "SELECT version(), current_database(), current_user, pg_postmaster_start_time();"

        result = await self.execute_query(host, query, database_url)

        if result.success:
            # Parse the result (simplified)
            health_info = {
                'status': 'healthy',
                'host': host,
                'response_time': result.execution_time,
                'raw_output': result.stdout
            }
        else:
            health_info = {
                'status': 'unhealthy',
                'host': host,
                'error': result.stderr,
                'response_time': result.execution_time
            }

        return health_info

    async def get_table_stats(self, host: str, database_url: str, table_name: str) -> Dict[str, Any]:
        """Get statistics for a remote table."""
        query = f"""
        SELECT
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_rows,
            n_dead_tup as dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE tablename = '{table_name}';
        """

        result = await self.execute_query(host, query, database_url)

        if result.success:
            # Parse result (simplified)
            return {
                'table': table_name,
                'host': host,
                'stats': result.stdout.strip()
            }
        else:
            return {
                'table': table_name,
                'host': host,
                'error': result.stderr
            }

# Utility functions for SSH key management
def generate_ssh_key_pair(key_path: str = "~/.ssh/id_rsa_mcp"):
    """Generate SSH key pair for MCP operations."""
    key_path = os.path.expanduser(key_path)

    if os.path.exists(key_path):
        logger.info(f"SSH key already exists at {key_path}")
        return key_path

    # Generate key pair
    key = paramiko.RSAKey.generate(2048)

    # Save private key
    key.write_private_key_file(key_path)

    # Save public key
    with open(f"{key_path}.pub", 'w') as f:
        f.write(f"ssh-rsa {key.get_base64()} mcp-ingestion-key\n")

    # Set proper permissions
    os.chmod(key_path, 0o600)
    os.chmod(f"{key_path}.pub", 0o644)

    logger.info(f"Generated SSH key pair at {key_path}")
    return key_path

def setup_passwordless_ssh(host: str, user: str, key_path: str = "~/.ssh/id_rsa_mcp"):
    """Setup passwordless SSH to a host."""
    key_path = os.path.expanduser(key_path)
    pub_key_path = f"{key_path}.pub"

    if not os.path.exists(pub_key_path):
        raise FileNotFoundError(f"Public key not found at {pub_key_path}")

    # Read public key
    with open(pub_key_path, 'r') as f:
        pub_key_content = f.read().strip()

    # Copy public key to remote host
    ssh_copy_cmd = f"ssh-copy-id -i {key_path} {user}@{host}"

    try:
        result = subprocess.run(shlex.split(ssh_copy_cmd), capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"Passwordless SSH setup successful for {user}@{host}")
            return True
        else:
            logger.error(f"Failed to setup passwordless SSH: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"SSH setup timed out for {user}@{host}")
        return False
    except Exception as e:
        logger.error(f"Error setting up passwordless SSH: {e}")
        return False