"""Enhanced Congress.gov ingestion script with GPU, parallel, and async capabilities.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/enhanced_congress_ingest.py --congress 118 --use-gpu --use-parallel
"""
import os
import argparse
import asyncio
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
# from tqdm.asyncio import tqdm  # Optional dependency
try:
    from tqdm.asyncio import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    tqdm = None
    TQDM_AVAILABLE = False

from mcp_server.clients.congress_client import CongressClient
from mcp_server.utils.enhanced_ingestion import (
    IngestionConfig,
    EnhancedIngestionManager,
    get_ingestion_manager,
    retry,
    cache,
    rate_limit,
    monitor_performance
)
from mcp_server.utils.monitoring import monitor
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.db import get_raw_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedCongressIngestor:
    """Enhanced Congress data ingestor with GPU and parallel processing."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.manager = get_ingestion_manager(config)
        self.client = None

    def initialize_client(self, api_key: str):
        """Initialize Congress API client."""
        self.client = CongressClient(api_key)

    async def ingest_congress_data(self, congress: int, bill_type: Optional[str] = None,
                                 max_pages: int = 100) -> Dict[str, Any]:
        """Ingest Congress data with enhanced processing."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        logger.info(f"Starting enhanced Congress ingestion for congress {congress}")

        total_processed = 0
        all_data = []

        # Create progress tracking
        page = 1
        if TQDM_AVAILABLE and tqdm:
            pbar = tqdm(total=999999, desc="Processing Congress pages")
        
        try:
            while True:
                try:
                    # Fetch data from API
                    response = await self._fetch_congress_page(congress, bill_type, page)

                    if not response or not response.get('bills'):
                        logger.info(f"No more data at page {page}")
                        break

                    # Process batch with GPU/parallel processing
                    processed_batch = await self._process_batch(response['bills'])

                    # Store data
                    await self._store_batch(processed_batch)

                    total_processed += len(processed_batch)
                    all_data.extend(processed_batch)

                    if TQDM_AVAILABLE and tqdm:
                        pbar.update(1)
                        pbar.set_postfix({"processed": total_processed})
                    page += 1

                    # Rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error processing page {page}: {e}")
                    break
        except Exception as e:
            logger.error(f"Enhanced ingestion failed: {e}")
            raise
        finally:
            if TQDM_AVAILABLE and tqdm:
                pbar.close()

        # Final deduplication and optimization
        await self._finalize_ingestion(all_data)

        result = {
            "status": "completed",
            "congress": congress,
            "bill_type": bill_type,
            "total_processed": total_processed,
            "pages_processed": page - 1
        }

        logger.info(f"Congress ingestion completed: {result}")
        return result

    @retry(max_attempts=3, delay=2.0)
    @rate_limit(calls_per_second=10.0)
    @cache(ttl_seconds=300)  # 5 minute cache for API responses
    async def _fetch_congress_page(self, congress: int, bill_type: Optional[str],
                                 page: int) -> Optional[Dict[str, Any]]:
        """Fetch a page of Congress data asynchronously."""
        loop = asyncio.get_event_loop()

        def fetch_sync():
            return self.client.search_bills(
                congress=congress,
                billType=bill_type,
                page=page
            )

        try:
            response = await loop.run_in_executor(None, fetch_sync)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch page {page}: {e}")
            return None

    @monitor_performance
    async def _process_batch(self, bills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of bills with enhanced processing."""
        if not bills:
            return []

        # Convert to DataFrame for processing
        df = pd.DataFrame(bills)

        # GPU processing disabled - use CPU processing instead
        from mcp_server.utils.enhanced_ingestion import CPUDataProcessor
        cpu_processor = CPUDataProcessor()
        df = cpu_processor.process_dataframe(df)

        # Normalize data
        normalized_data = []
        for _, bill in df.iterrows():
            normalized = self._normalize_congress_bill(dict(bill))
            normalized_data.append(normalized)

        # Deduplication
        if self.config.enable_deduplication:
            deduplicated = await self._deduplicate_batch(normalized_data)
        else:
            deduplicated = normalized_data

        return deduplicated

    def _normalize_congress_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Congress bill data."""
        bill_id = f"{bill.get('congress')}:{bill.get('billType')}:{bill.get('billNumber')}"

        return {
            'id': bill_id,
            'congress': bill.get('congress'),
            'bill_type': bill.get('billType'),
            'bill_number': bill.get('billNumber'),
            'title': bill.get('title'),
            'latest_action_date': bill.get('latestActionDate'),
            'latest_action_description': bill.get('latestActionDescription'),
            'subjects': bill.get('subjects') or [],
            'sponsors': bill.get('sponsors') or {},
            'raw': bill
        }

    async def _deduplicate_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates from batch."""
        deduplicated = []
        for item in batch:
            if not self.manager.deduplication_manager.is_duplicate(item, 'congress_bills'):
                deduplicated.append(item)
                self.manager.deduplication_manager.mark_processed(item, 'congress_bills')

        return deduplicated

    async def _store_batch(self, batch: List[Dict[str, Any]]):
        """Store batch of processed data."""
        if not batch:
            return

        # Convert to DataFrame for efficient storage
        df = pd.DataFrame(batch)

        # Use copy method for bulk insert
        raw_conn = get_raw_connection()
        try:
            copy_dataframe_to_table(raw_conn, df, 'congress_bills', {
                'id': 'id',
                'congress': 'congress',
                'bill_type': 'bill_type',
                'bill_number': 'bill_number',
                'title': 'title',
                'latest_action_date': 'latest_action_date',
                'latest_action_description': 'latest_action_description'
            })
        finally:
            raw_conn.close()

    async def _finalize_ingestion(self, all_data: List[Dict[str, Any]]):
        """Finalize ingestion with optimizations."""
        # Create indexes if needed
        # Update statistics
        # Clean up temporary data
        pass

async def main():
    """Main entry point for enhanced Congress ingestion."""
    parser = argparse.ArgumentParser(description="Enhanced Congress.gov ingestion")
    parser.add_argument('--congress', type=int, required=True, help='Congress number')
    parser.add_argument('--bill-type', help='Bill type filter')
    parser.add_argument('--api-key', default=os.getenv('CONGRESS_API_KEY'), help='Congress API key')
    parser.add_argument('--max-pages', type=int, default=999999, help='Maximum pages to process')
    # parser.add_argument('--use-gpu', action='store_true', help='Enable GPU processing (DISABLED - not useful for web ingestion)')
    parser.add_argument('--use-parallel', action='store_true', help='Enable parallel processing')
    parser.add_argument('--use-async', action='store_true', help='Enable async processing')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    parser.add_argument('--redis-url', help='Redis URL for progress tracking')
    parser.add_argument('--enable-progress', action='store_true', help='Enable progress tracking')
    parser.add_argument('--enable-compression', action='store_true', help='Enable data compression')

    args = parser.parse_args()

    # Validate environment
    if not os.getenv('DATABASE_URL'):
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    # Create configuration
    config = IngestionConfig(
        use_gpu=False,  # GPU processing disabled - not beneficial for web ingestion
        use_parallel=args.use_parallel,
        use_async=args.use_async,
        batch_size=args.batch_size,
        enable_progress_tracking=args.enable_progress,
        enable_compression=args.enable_compression,
        redis_url=args.redis_url
    )

    # Create ingestor
    ingestor = EnhancedCongressIngestor(config)
    ingestor.initialize_client(args.api_key)

    # Run ingestion
    try:
        result = await ingestor.ingest_congress_data(
            congress=args.congress,
            bill_type=args.bill_type,
            max_pages=args.max_pages
        )

        print(f"Ingestion completed: {result}")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise

if __name__ == '__main__':
    # Run async main
    asyncio.run(main())