"""Command-line interface for enhanced ingestion management."""
import argparse
import asyncio
import json
import sys
from typing import Dict, Any, Optional
import logging

from mcp_server.utils.enhanced_ingestion import (
    IngestionConfig,
    get_ingestion_manager
)
from mcp_server.utils.scheduler import (
    get_scheduler,
    ScheduledJob
)
from mcp_server.utils.remote_execution import (
    RemoteHost,
    DistributedIngestionManager,
    generate_ssh_key_pair,
    setup_passwordless_ssh
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionCLI:
    """Command-line interface for ingestion management."""

    def __init__(self):
        self.manager = None
        self.scheduler = None

    def get_manager(self):
        """Get or create ingestion manager."""
        if self.manager is None:
            config = IngestionConfig()
            self.manager = get_ingestion_manager(config)
        return self.manager

    def get_scheduler(self):
        """Get or create scheduler."""
        if self.scheduler is None:
            self.scheduler = get_scheduler()
        return self.scheduler

    async def create_job(self, args):
        """Create and execute an ingestion job."""
        manager = self.get_manager()

        # Create job parameters
        params = {}
        if hasattr(args, 'congress') and args.congress:
            params['congress'] = args.congress
        if hasattr(args, 'jurisdiction') and args.jurisdiction:
            params['jurisdiction'] = args.jurisdiction
        if hasattr(args, 'collection') and args.collection:
            params['collection'] = args.collection
        if hasattr(args, 'year') and args.year:
            params['year'] = args.year

        # Create job
        job_id = manager.create_job(args.source, args.collection_type, params)

        print(f"Created job: {job_id}")

        # Execute if not scheduled
        if not getattr(args, 'schedule', None):
            result = await manager.execute_job_async(job_id)
            print(f"Job result: {json.dumps(result, indent=2)}")
        else:
            print(f"Job {job_id} created for scheduling")

    async def schedule_job(self, args):
        """Schedule a recurring ingestion job."""
        scheduler = self.get_scheduler()

        # Parse schedule
        if args.cron:
            schedule_type = 'cron'
            schedule_config = {'expression': args.cron}
        elif args.interval:
            schedule_type = 'interval'
            schedule_config = {'seconds': args.interval}
        else:
            print("Error: Must specify --cron or --interval")
            return

        # Create job parameters
        params = {}
        if hasattr(args, 'congress') and args.congress:
            params['congress'] = args.congress
        if hasattr(args, 'jurisdiction') and args.jurisdiction:
            params['jurisdiction'] = args.jurisdiction
        if hasattr(args, 'collection') and args.collection:
            params['collection'] = args.collection

        # Create scheduled job
        job = ScheduledJob(
            job_id=f"{args.source}_{args.collection_type}_{args.name}",
            name=args.name,
            source=args.source,
            collection=args.collection_type,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            parameters=params
        )

        job_id = scheduler.add_scheduled_job(job)
        print(f"Scheduled job: {job_id}")

    async def list_jobs(self, args):
        """List scheduled jobs."""
        scheduler = self.get_scheduler()
        jobs = scheduler.get_scheduled_jobs()

        if not jobs:
            print("No scheduled jobs found")
            return

        print("Scheduled Jobs:")
        print("-" * 80)
        for job in jobs:
            print(f"ID: {job.job_id}")
            print(f"Name: {job.name}")
            print(f"Source: {job.source}")
            print(f"Collection: {job.collection}")
            print(f"Schedule: {job.schedule_type} - {job.schedule_config}")
            print(f"Enabled: {job.enabled}")
            print(f"Last Run: {job.last_run}")
            print(f"Next Run: {job.next_run}")
            print(f"Run Count: {job.run_count}")
            print(f"Success Rate: {job.success_count}/{job.run_count}")
            print("-" * 80)

    async def job_status(self, args):
        """Get status of a specific job."""
        scheduler = self.get_scheduler()
        executions = scheduler.get_job_executions(args.job_id, limit=getattr(args, 'limit', 10))

        if not executions:
            print(f"No executions found for job {args.job_id}")
            return

        print(f"Recent executions for job {args.job_id}:")
        print("-" * 100)
        for exec in executions:
            print(f"Execution ID: {exec.execution_id}")
            print(f"Status: {exec.status}")
            print(f"Start: {exec.start_time}")
            print(f"Duration: {exec.duration:.2f}s" if exec.duration else "Duration: N/A")
            print(f"Records: {exec.records_processed}")
            if exec.errors:
                print(f"Errors: {len(exec.errors)}")
                for error in exec.errors[:3]:  # Show first 3 errors
                    print(f"  - {error}")
            print("-" * 100)

    async def remove_job(self, args):
        """Remove a scheduled job."""
        scheduler = self.get_scheduler()
        scheduler.remove_scheduled_job(args.job_id)
        print(f"Removed job: {args.job_id}")

    async def distributed_ingest(self, args):
        """Run distributed ingestion across multiple hosts."""
        # Parse host configurations
        hosts = []
        for host_spec in args.hosts:
            # Format: user@host:port or user@host
            if ':' in host_spec:
                user_host, port = host_spec.split(':')
                port = int(port)
            else:
                user_host = host_spec
                port = 22

            user, host = user_host.split('@')

            hosts.append(RemoteHost(
                host=host,
                user=user,
                port=port,
                remote_path=getattr(args, 'remote_path', '/tmp/mcp_ingestion'),
                database_url=getattr(args, 'database_url', None)
            ))

        # Create job configuration
        job_config = {
            'type': args.source,
            'parameters': {},
            'database_url': getattr(args, 'database_url', None)
        }

        if hasattr(args, 'congress') and args.congress:
            job_config['parameters']['congress'] = args.congress
        if hasattr(args, 'jurisdiction') and args.jurisdiction:
            job_config['parameters']['jurisdiction'] = args.jurisdiction
        if hasattr(args, 'collection') and args.collection:
            job_config['parameters']['collection'] = args.collection

        # Run distributed ingestion
        async with DistributedIngestionManager(hosts) as manager:
            result = await manager.distribute_ingestion_job(job_config)

        print("Distributed ingestion result:")
        print(json.dumps(result, indent=2))

    def setup_ssh_keys(self, args):
        """Setup SSH keys for passwordless authentication."""
        key_path = generate_ssh_key_pair(getattr(args, 'key_path', '~/.ssh/id_rsa_mcp'))

        if args.setup_host:
            success = setup_passwordless_ssh(args.setup_host, args.setup_user, key_path)
            if success:
                print(f"SSH setup successful for {args.setup_user}@{args.setup_host}")
            else:
                print(f"SSH setup failed for {args.setup_user}@{args.setup_host}")
                sys.exit(1)
        else:
            print(f"Generated SSH key pair at {key_path}")

    async def sync_codebase(self, args):
        """Sync codebase to remote hosts."""
        hosts = []
        for host_spec in args.hosts:
            if ':' in host_spec:
                user_host, port = host_spec.split(':')
                port = int(port)
            else:
                user_host = host_spec
                port = 22

            user, host = user_host.split('@')

            hosts.append(RemoteHost(
                host=host,
                user=user,
                port=port,
                remote_path=getattr(args, 'remote_path', '/tmp/mcp_ingestion')
            ))

        async with DistributedIngestionManager(hosts) as manager:
            await manager.sync_codebase(getattr(args, 'local_path', '.'))

        print("Codebase sync completed")

def main():
    """Main CLI entry point."""
    cli = IngestionCLI()

    parser = argparse.ArgumentParser(description="Enhanced MCP Ingestion CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create job command
    create_parser = subparsers.add_parser('create', help='Create and execute ingestion job')
    create_parser.add_argument('source', choices=['congress', 'openstates', 'govinfo'],
                              help='Data source')
    create_parser.add_argument('collection_type', help='Collection or table type')
    create_parser.add_argument('--congress', type=int, help='Congress number')
    create_parser.add_argument('--jurisdiction', help='Jurisdiction code')
    create_parser.add_argument('--collection', help='Collection name')
    create_parser.add_argument('--year', type=int, help='Year')
    create_parser.add_argument('--schedule', action='store_true', help='Create for scheduling only')

    # Schedule job command
    schedule_parser = subparsers.add_parser('schedule', help='Schedule recurring ingestion job')
    schedule_parser.add_argument('source', choices=['congress', 'openstates', 'govinfo'])
    schedule_parser.add_argument('collection_type')
    schedule_parser.add_argument('name', help='Job name')
    schedule_parser.add_argument('--cron', help='Cron expression (e.g., "0 2 * * *")')
    schedule_parser.add_argument('--interval', type=int, help='Interval in seconds')
    schedule_parser.add_argument('--congress', type=int)
    schedule_parser.add_argument('--jurisdiction')
    schedule_parser.add_argument('--collection')

    # List jobs command
    list_parser = subparsers.add_parser('list', help='List scheduled jobs')

    # Status command
    status_parser = subparsers.add_parser('status', help='Get job status')
    status_parser.add_argument('job_id', help='Job ID')
    status_parser.add_argument('--limit', type=int, default=10, help='Number of executions to show')

    # Remove job command
    remove_parser = subparsers.add_parser('remove', help='Remove scheduled job')
    remove_parser.add_argument('job_id', help='Job ID to remove')

    # Distributed ingestion command
    distributed_parser = subparsers.add_parser('distributed', help='Run distributed ingestion')
    distributed_parser.add_argument('source', choices=['congress', 'openstates', 'govinfo'])
    distributed_parser.add_argument('--hosts', nargs='+', required=True,
                                   help='Host specifications (user@host:port)')
    distributed_parser.add_argument('--congress', type=int)
    distributed_parser.add_argument('--jurisdiction')
    distributed_parser.add_argument('--collection')
    distributed_parser.add_argument('--remote-path', default='/tmp/mcp_ingestion')
    distributed_parser.add_argument('--database-url')

    # SSH setup command
    ssh_parser = subparsers.add_parser('ssh-setup', help='Setup SSH keys')
    ssh_parser.add_argument('--key-path', default='~/.ssh/id_rsa_mcp', help='SSH key path')
    ssh_parser.add_argument('--setup-host', help='Setup passwordless SSH to this host')
    ssh_parser.add_argument('--setup-user', help='Username for SSH setup')

    # Sync codebase command
    sync_parser = subparsers.add_parser('sync', help='Sync codebase to remote hosts')
    sync_parser.add_argument('--hosts', nargs='+', required=True,
                            help='Host specifications (user@host:port)')
    sync_parser.add_argument('--remote-path', default='/tmp/mcp_ingestion')
    sync_parser.add_argument('--local-path', default='.')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Run async commands
    async def run_async():
        try:
            if args.command == 'create':
                await cli.create_job(args)
            elif args.command == 'schedule':
                await cli.schedule_job(args)
            elif args.command == 'list':
                await cli.list_jobs(args)
            elif args.command == 'status':
                await cli.job_status(args)
            elif args.command == 'remove':
                await cli.remove_job(args)
            elif args.command == 'distributed':
                await cli.distributed_ingest(args)
            elif args.command == 'sync':
                await cli.sync_codebase(args)
        except Exception as e:
            logger.error(f"Command failed: {e}")
            sys.exit(1)

    # Run sync commands
    if args.command == 'ssh-setup':
        cli.setup_ssh_keys(args)
    else:
        asyncio.run(run_async())

if __name__ == '__main__':
    main()