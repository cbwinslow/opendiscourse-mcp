#!/usr/bin/env python3
"""
Unified Legislative Data Ingestion Script

This monoscript consolidates all ingestion functionality for Congress.gov, GovInfo, and OpenStates.
It provides a single interface for ingesting all types of legislative data with comprehensive
parameter handling, monitoring, and error recovery.

Usage Examples:
  # Ingest specific Congress data
  python unified_ingestion.py --source congress --data-type bills --congress 118

  # Ingest all Congress data for multiple congresses
  python unified_ingestion.py --source congress --data-type all --congress 116 117 118

  # Ingest GovInfo collection
  python unified_ingestion.py --source govinfo --collection BILLS --year 2023

  # Ingest OpenStates data
  python unified_ingestion.py --source openstates --jurisdiction nc --per-page 100

  # Comprehensive ingestion of all sources
  python unified_ingestion.py --source all --comprehensive
"""

import os
import sys
import argparse
import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing clients and utilities
from mcp_server.clients.congress_client import CongressClient
from mcp_server.clients.govinfo_client import GovInfoClient
from mcp_server.clients.openstates_client import OpenStatesClient
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
from mcp_server.utils.progress_tracker import IngestionProgressTracker, create_congress_progress_tracker
from mcp_server.utils.async_client import AsyncCongressClient, extract_successful_data
from mcp_server.utils.parallel_processor import ParallelCongressProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Enumeration of supported data sources."""
    CONGRESS = "congress"
    GOVINFO = "govinfo"
    OPENSTATES = "openstates"
    ALL = "all"


class CongressDataType(Enum):
    """Enumeration of Congress.gov data types."""
    BILLS = "bills"
    MEMBERS = "members"
    COMMITTEES = "committees"
    VOTES = "votes"
    BILL_ACTIONS = "bill_actions"
    BILL_TEXT = "bill_text"
    SUMMARIES = "summaries"
    TREATIES = "treaties"
    NOMINATIONS = "nominations"
    HEARINGS = "hearings"
    CONGRESS = "congress"
    ALL = "all"


class GovInfoCollection(Enum):
    """Enumeration of GovInfo collections."""
    BILLS = "BILLS"
    STATUTES = "STATUTES"
    CRR = "CRR"
    CRPT = "CRPT"
    CREC = "CREC"
    FR = "FR"
    GPO = "GPO"


@dataclass
class IngestionConfig:
    """Configuration for ingestion operations."""
    # Database configuration
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    
    # API keys
    congress_api_key: str = field(default_factory=lambda: os.getenv("CONGRESS_API_KEY"))
    govinfo_api_key: str = field(default_factory=lambda: os.getenv("GOVINFO_API_KEY"))
    openstates_api_key: str = field(default_factory=lambda: os.getenv("OPENSTATES_API_KEY"))
    
    # Processing options
    use_copy: bool = field(default_factory=lambda: bool(os.getenv("USE_COPY", "")))
    use_sqlalchemy: bool = field(default_factory=lambda: bool(os.getenv("USE_SQLALCHEMY", "")))
    use_async: bool = True
    max_concurrent: int = 5
    batch_size: int = 1000
    
    # Pagination and limits
    max_pages: int = 999999
    per_page: int = 999999
    timeout: int = 300
    
    # Output options
    download_dir: str = "./data"
    log_dir: str = "./logs"
    dry_run: bool = False
    
    # Monitoring
    enable_monitoring: bool = True
    enable_deduplication: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    source: str
    data_type: str
    success: bool
    records_processed: int = 0
    duplicates_found: int = 0
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0
    api_calls: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)


class UnifiedIngester:
    """Unified ingestion class for all data sources."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.progress_tracker = None
        self.results: List[IngestionResult] = []
        
        # Initialize database connections
        self.engine = None
        if config.use_sqlalchemy:
            self.engine = get_sqlalchemy_engine()
    
    def ingest(self, source: DataSource, **kwargs) -> List[IngestionResult]:
        """Main ingestion method that routes to appropriate source handlers."""
        logger.info(f"Starting ingestion for source: {source.value}")
        
        if source == DataSource.ALL:
            return self._ingest_all_sources(**kwargs)
        elif source == DataSource.CONGRESS:
            return self._ingest_congress(**kwargs)
        elif source == DataSource.GOVINFO:
            return self._ingest_govinfo(**kwargs)
        elif source == DataSource.OPENSTATES:
            return self._ingest_openstates(**kwargs)
        else:
            raise ValueError(f"Unsupported data source: {source}")
    
    def _ingest_all_sources(self, **kwargs) -> List[IngestionResult]:
        """Ingest data from all sources."""
        all_results = []
        
        # Ingest Congress data
        if kwargs.get('congress') or kwargs.get('comprehensive'):
            congress_results = self._ingest_congress(**kwargs)
            all_results.extend(congress_results)
        
        # Ingest GovInfo data
        if kwargs.get('collection') or kwargs.get('comprehensive'):
            govinfo_results = self._ingest_govinfo(**kwargs)
            all_results.extend(govinfo_results)
        
        # Ingest OpenStates data
        if kwargs.get('jurisdiction') or kwargs.get('comprehensive'):
            openstates_results = self._ingest_openstates(**kwargs)
            all_results.extend(openstates_results)
        
        return all_results
    
    def _ingest_congress(self, **kwargs) -> List[IngestionResult]:
        """Ingest Congress.gov data."""
        data_types = kwargs.get('data_type', ['bills'])
        congresses = kwargs.get('congress', [118])
        
        if isinstance(data_types, str):
            data_types = [data_types]
        
        if isinstance(congresses, int):
            congresses = [congresses]
        
        results = []
        
        for congress in congresses:
            for data_type in data_types:
                if data_type == 'all':
                    # Ingest all data types for this congress
                    for dt in CongressDataType:
                        if dt != CongressDataType.ALL:
                            result = self._ingest_congress_data_type(congress, dt.value)
                            results.append(result)
                else:
                    result = self._ingest_congress_data_type(congress, data_type)
                    results.append(result)
        
        return results
    
    def _ingest_congress_data_type(self, congress: int, data_type: str, **kwargs) -> IngestionResult:
        """Ingest a specific Congress data type."""
        start_time = time.time()
        result = IngestionResult(
            source="congress",
            data_type=f"{data_type}_{congress}",
            success=False,
            parameters={'congress': congress, 'data_type': data_type}
        )
        
        try:
            if self.config.use_async and data_type in ['bills', 'members', 'committees', 'votes']:
                # Use async ingestion for supported data types
                result = asyncio.run(self._ingest_congress_async(congress, data_type, **kwargs))
            else:
                # Use synchronous ingestion
                result = self._ingest_congress_sync(congress, data_type, **kwargs)
                
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Error ingesting {data_type} for Congress {congress}: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return result
    
    async def _ingest_congress_async(self, congress: int, data_type: str, **kwargs) -> IngestionResult:
        """Async ingestion for Congress data."""
        result = IngestionResult(
            source="congress",
            data_type=f"{data_type}_{congress}",
            success=False,
            parameters={'congress': congress, 'data_type': data_type}
        )
        
        # Initialize progress tracker
        self.progress_tracker = create_congress_progress_tracker(congress, data_type)
        self.progress_tracker.initialize(description=f"🏛️ Congress {congress} - {data_type}")
        
        try:
            async with AsyncCongressClient(self.config.congress_api_key, max_concurrent=self.config.max_concurrent) as client:
                endpoint = self._get_congress_endpoint(data_type, congress)
                if not endpoint:
                    raise ValueError(f"No endpoint configured for {data_type}")
                
                responses = await client.fetch_all_pages(
                    f"https://api.congress.gov/v3{endpoint}",
                    max_pages=self.config.max_pages
                )
                
                successful_data = extract_successful_data(responses)
                result.api_calls = len(responses)
                
                # Store data
                records_stored = await self._store_congress_data_async(data_type, congress, successful_data)
                result.records_processed = records_stored
                result.success = True
                
                self.progress_tracker.update_progress(records_stored, f"✓ {data_type}: {records_stored} records")
                
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Async ingestion error for {data_type}: {e}")
        finally:
            if self.progress_tracker:
                self.progress_tracker.finish()
        
        return result
    
    def _ingest_congress_sync(self, congress: int, data_type: str, **kwargs) -> IngestionResult:
        """Synchronous ingestion for Congress data."""
        result = IngestionResult(
            source="congress",
            data_type=f"{data_type}_{congress}",
            success=False,
            parameters={'congress': congress, 'data_type': data_type}
        )
        
        try:
            client = CongressClient(api_key=self.config.congress_api_key)
            endpoint = self._get_congress_endpoint(data_type, congress)
            
            if not endpoint:
                raise ValueError(f"No endpoint configured for {data_type}")
            
            # Fetch data
            all_data = []
            page = 1
            while True:
                data = client.get(endpoint, params={'offset': (page - 1) * self.config.per_page})
                page += 1
                if not data or not data.get(data.get('pagination', {}).get('next', {}).get('count', 0)):
                    break
                
                records = self._extract_records_from_response(data, data_type)
                all_data.extend(records)
                result.api_calls += 1
                
                if len(records) < self.config.per_page:
                    break
            
            # Store data
            records_stored = self._store_congress_data_sync(data_type, congress, all_data)
            result.records_processed = records_stored
            result.success = True
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Sync ingestion error for {data_type}: {e}")
        
        return result
    
    def _ingest_govinfo(self, **kwargs) -> List[IngestionResult]:
        """Ingest GovInfo data."""
        collection = kwargs.get('collection', 'BILLS')
        year = kwargs.get('year')
        
        results = []
        result = IngestionResult(
            source="govinfo",
            data_type=f"{collection}_{year or 'all'}",
            success=False,
            parameters={'collection': collection, 'year': year}
        )
        
        start_time = time.time()
        
        try:
            client = GovInfoClient(api_key=self.config.govinfo_api_key)
            listing = client.bulk_download(collection, year=year)
            files = listing.get('files') or []
            
            total_ingested = 0
            duplicates_found = 0
            
            for file_path in files:
                filename = os.path.basename(file_path)
                output_path = os.path.join(self.config.download_dir, filename)
                
                # Download file
                client.fetch_bulk_file(file_path, output_path)
                
                # Process XML
                try:
                    df = client.ingest_xml_to_df(output_path)
                    if df.empty:
                        continue
                    
                    # Store data
                    stored, duplicates = self._store_govinfo_data(df, collection, file_path)
                    total_ingested += stored
                    duplicates_found += duplicates
                    
                except Exception as e:
                    result.errors.append(f"Failed to process {filename}: {e}")
                    continue
            
            result.records_processed = total_ingested
            result.duplicates_found = duplicates_found
            result.success = True
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"GovInfo ingestion error: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return [result]
    
    def _ingest_openstates(self, **kwargs) -> List[IngestionResult]:
        """Ingest OpenStates data."""
        jurisdiction = kwargs.get('jurisdiction')
        query = kwargs.get('query')
        per_page = kwargs.get('per_page', self.config.per_page)
        
        results = []
        result = IngestionResult(
            source="openstates",
            data_type=f"bills_{jurisdiction or 'all'}_{query or 'all'}",
            success=False,
            parameters={'jurisdiction': jurisdiction, 'query': query}
        )
        
        start_time = time.time()
        
        try:
            client = OpenStatesClient(api_key=self.config.openstates_api_key)
            
            total_ingested = 0
            duplicates_found = 0
            page = 1
            
            while True:
                response = client.search_bills(
                    jurisdiction=jurisdiction,
                    q=query,
                    page=page,
                    per_page=per_page
                )
                
                bills = response.get('results') or response.get('data') or []
                if not bills:
                    break
                
                # Store data
                stored, duplicates = self._store_openstates_data(bills)
                total_ingested += stored
                duplicates_found += duplicates
                
                if len(bills) < per_page:
                    break
                
                page += 1
            
            result.records_processed = total_ingested
            result.duplicates_found = duplicates_found
            result.success = True
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"OpenStates ingestion error: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return [result]
    
    def _get_congress_endpoint(self, data_type: str, congress: int) -> Optional[str]:
        """Get API endpoint for Congress data type."""
        endpoints = {
            'bills': f'/bill/{congress}',
            'members': f'/member/congress/{congress}',
            'committees': f'/committee',
            'votes': f'/house-vote/{congress}',
            'bill_actions': f'/bill/{congress}',
            'bill_text': f'/bill/{congress}',
            'hearings': f'/hearing/{congress}',
            'nominations': f'/nomination/{congress}',
            'treaties': f'/treaty/{congress}',
            'congress': f'/congress/{congress}',
            'summaries': f'/bill/{congress}'
        }
        return endpoints.get(data_type)
    
    def _extract_records_from_response(self, data: Dict, data_type: str) -> List[Dict]:
        """Extract records from API response based on data type."""
        if data_type in ['bills', 'bill_actions', 'bill_text', 'summaries']:
            return data.get('bills', [])
        elif data_type == 'members':
            return data.get('members', [])
        elif data_type == 'committees':
            return data.get('committees', [])
        elif data_type == 'votes':
            return data.get('votes', [])
        elif data_type == 'hearings':
            return data.get('hearings', [])
        elif data_type == 'nominations':
            return data.get('nominations', [])
        elif data_type == 'treaties':
            return data.get('treaties', [])
        elif data_type == 'congress':
            return [data]  # Single record for congress info
        else:
            return []
    
    async def _store_congress_data_async(self, data_type: str, congress: int, data: List[Dict]) -> int:
        """Store Congress data asynchronously."""
        if not data:
            return 0
        
        loop = asyncio.get_event_loop()
        total_stored = 0
        
        for i in range(0, len(data), self.config.batch_size):
            batch = data[i:i + self.config.batch_size]
            stored = await loop.run_in_executor(
                None,
                self._store_congress_batch_sync,
                data_type,
                congress,
                batch
            )
            total_stored += stored
        
        return total_stored
    
    def _store_congress_data_sync(self, data_type: str, congress: int, data: List[Dict]) -> int:
        """Store Congress data synchronously."""
        if not data:
            return 0
        
        total_stored = 0
        for i in range(0, len(data), self.config.batch_size):
            batch = data[i:i + self.config.batch_size]
            stored = self._store_congress_batch_sync(data_type, congress, batch)
            total_stored += stored
        
        return total_stored
    
    def _store_congress_batch_sync(self, data_type: str, congress: int, batch: List[Dict]) -> int:
        """Store a batch of Congress data."""
        if self.config.dry_run:
            return len(batch)
        
        table_name = f"congress_{data_type}"
        
        try:
            if self.config.use_copy:
                # Use COPY method for faster insertion
                df = pd.DataFrame(batch)
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df, table_name)
                raw_conn.close()
            else:
                # Use standard INSERT/UPDATE
                conn = psycopg2.connect(self.config.database_url)
                cursor = conn.cursor()
                
                for record in batch:
                    # Normalize record for database
                    normalized = self._normalize_congress_record(record, data_type, congress)
                    
                    # Check for duplicates
                    if self.config.enable_deduplication:
                        content_hash = deduplicator.get_content_hash(normalized)
                        if deduplicator.is_duplicate(table_name, content_hash, normalized.get('id')):
                            continue
                    
                    # Insert record
                    self._insert_congress_record(cursor, table_name, normalized)
                
                conn.commit()
                cursor.close()
                conn.close()
            
            return len(batch)
            
        except Exception as e:
            logger.error(f"Error storing Congress batch: {e}")
            raise
    
    def _store_govinfo_data(self, df: pd.DataFrame, collection: str, file_path: str) -> tuple[int, int]:
        """Store GovInfo data."""
        if self.config.dry_run:
            return len(df), 0
        
        stored = 0
        duplicates = 0
        
        try:
            if self.config.use_copy:
                # Use COPY method
                df_local = df.copy()
                df_local['id'] = df_local.get('id', df_local.index.astype(str))
                df_local['collection'] = collection
                
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df_local, 'govinfo_documents')
                raw_conn.close()
                stored = len(df_local)
            else:
                # Use standard INSERT/UPDATE
                conn = psycopg2.connect(self.config.database_url)
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    doc_id = str(row.get('id') or row.get('documentId') or os.path.basename(file_path))
                    
                    record = {
                        'id': doc_id,
                        'collection': collection,
                        'date': row.get('date'),
                        'title': row.get('title'),
                        'url': file_path,
                        'metadata': Json(row.to_dict()),
                        'raw': Json(row.to_dict())
                    }
                    
                    # Check for duplicates
                    if self.config.enable_deduplication:
                        content_hash = deduplicator.get_content_hash(record, exclude_fields=['raw'])
                        if deduplicator.is_duplicate('govinfo_documents', content_hash, doc_id):
                            duplicates += 1
                            continue
                    
                    # Insert record
                    cursor.execute("""
                        INSERT INTO govinfo_documents (id, collection, date, title, url, metadata, raw, created_on)
                        VALUES (%(id)s, %(collection)s, %(date)s, %(title)s, %(url)s, %(metadata)s, %(raw)s, now())
                        ON CONFLICT (id) DO UPDATE SET
                          collection = EXCLUDED.collection,
                          date = EXCLUDED.date,
                          title = EXCLUDED.title,
                          url = EXCLUDED.url,
                          metadata = EXCLUDED.metadata,
                          raw = EXCLUDED.raw
                    """, record)
                    stored += 1
                
                conn.commit()
                cursor.close()
                conn.close()
        
        except Exception as e:
            logger.error(f"Error storing GovInfo data: {e}")
            raise
        
        return stored, duplicates
    
    def _store_openstates_data(self, bills: List[Dict]) -> tuple[int, int]:
        """Store OpenStates data."""
        if self.config.dry_run:
            return len(bills), 0
        
        stored = 0
        duplicates = 0
        
        try:
            if self.config.use_copy:
                # Use COPY method
                df_rows = []
                for bill in bills:
                    normalized = self._normalize_openstates_bill(bill)
                    df_rows.append(normalized)
                
                df = pd.DataFrame(df_rows)
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df, 'openstates_bills')
                raw_conn.close()
                stored = len(df)
            else:
                # Use standard INSERT/UPDATE
                conn = psycopg2.connect(self.config.database_url)
                cursor = conn.cursor()
                
                for bill in bills:
                    normalized = self._normalize_openstates_bill(bill)
                    
                    # Check for duplicates
                    if self.config.enable_deduplication:
                        content_hash = deduplicator.get_content_hash(normalized, exclude_fields=['raw'])
                        if deduplicator.is_duplicate('openstates_bills', content_hash, normalized['id']):
                            duplicates += 1
                            continue
                    
                    # Insert record
                    cursor.execute("""
                        INSERT INTO openstates_bills (id, session, jurisdiction, identifier, title, classification, subjects, created_at, updated_at, first_action_date, latest_action_date, latest_action_description, openstates_url, raw, updated_on)
                        VALUES (%(id)s, %(session)s, %(jurisdiction)s, %(identifier)s, %(title)s, %(classification)s, %(subjects)s, %(created_at)s, %(updated_at)s, %(first_action_date)s, %(latest_action_date)s, %(latest_action_description)s, %(openstates_url)s, %(raw)s, now())
                        ON CONFLICT (id) DO UPDATE SET
                          session = EXCLUDED.session,
                          jurisdiction = EXCLUDED.jurisdiction,
                          identifier = EXCLUDED.identifier,
                          title = EXCLUDED.title,
                          classification = EXCLUDED.classification,
                          subjects = EXCLUDED.subjects,
                          created_at = EXCLUDED.created_at,
                          updated_at = EXCLUDED.updated_at,
                          first_action_date = EXCLUDED.first_action_date,
                          latest_action_date = EXCLUDED.latest_action_date,
                          latest_action_description = EXCLUDED.latest_action_description,
                          openstates_url = EXCLUDED.openstates_url,
                          raw = EXCLUDED.raw,
                          updated_on = now()
                    """, normalized)
                    stored += 1
                
                conn.commit()
                cursor.close()
                conn.close()
        
        except Exception as e:
            logger.error(f"Error storing OpenStates data: {e}")
            raise
        
        return stored, duplicates
    
    def _normalize_congress_record(self, record: Dict, data_type: str, congress: int) -> Dict:
        """Normalize Congress record for database storage."""
        # This is a simplified version - in practice, you'd have specific normalization
        # for each data type with proper field mapping
        normalized = {
            'id': record.get('id') or record.get('bill_id') or record.get('bioguide_id'),
            'congress': congress,
            'raw': Json(record)
        }
        
        # Add data-type specific fields
        if data_type == 'bills':
            normalized.update({
                'bill_id': record.get('bill_id'),
                'title': record.get('title'),
                'sponsor_id': record.get('sponsor', {}).get('bioguideId'),
                'introduced_date': record.get('introducedDate')
            })
        elif data_type == 'members':
            normalized.update({
                'bioguide_id': record.get('bioguideId'),
                'first_name': record.get('firstName'),
                'last_name': record.get('lastName'),
                'state': record.get('state'),
                'party': record.get('partyName')
            })
        # Add more data type specific normalization as needed
        
        return normalized
    
    def _normalize_openstates_bill(self, bill: Dict) -> Dict:
        """Normalize OpenStates bill for database storage."""
        return {
            'id': bill.get('id'),
            'session': bill.get('session'),
            'jurisdiction': bill.get('jurisdiction', {}).get('id') if isinstance(bill.get('jurisdiction'), dict) else bill.get('jurisdiction'),
            'identifier': bill.get('identifier'),
            'title': bill.get('title'),
            'classification': bill.get('classification') or [],
            'subjects': bill.get('subject') or [],
            'created_at': bill.get('created_at'),
            'updated_at': bill.get('updated_at'),
            'first_action_date': bill.get('first_action_date'),
            'latest_action_date': bill.get('latest_action_date'),
            'latest_action_description': bill.get('latest_action_description'),
            'openstates_url': bill.get('openstates_url'),
            'raw': Json(bill)
        }
    
    def _insert_congress_record(self, cursor, table_name: str, record: Dict):
        """Insert Congress record into database."""
        # This is a simplified version - you'd need specific INSERT statements
        # for each table with proper column mapping
        columns = list(record.keys())
        placeholders = [f"%({col})s" for col in columns]
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (id) DO UPDATE SET
              {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'id'])}
        """
        
        cursor.execute(query, record)
    
    def print_summary(self):
        """Print ingestion summary."""
        print("\n" + "="*80)
        print("🎉 UNIFIED INGESTION SUMMARY")
        print("="*80)
        
        total_records = 0
        total_duplicates = 0
        total_duration = 0
        total_errors = 0
        
        for result in self.results:
            status = "✅" if result.success else "❌"
            print(f"\n{status} {result.source.upper()} - {result.data_type}")
            print(f"   📊 Records: {result.records_processed:,}")
            print(f"   🔄 Duplicates: {result.duplicates_found:,}")
            print(f"   ⏱️ Duration: {result.duration:.2f}s")
            print(f"   🌐 API Calls: {result.api_calls}")
            
            if result.errors:
                print(f"   ❌ Errors: {len(result.errors)}")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"      - {error}")
            
            total_records += result.records_processed
            total_duplicates += result.duplicates_found
            total_duration += result.duration
            total_errors += len(result.errors)
        
        print(f"\n📈 TOTALS:")
        print(f"   📊 Records Processed: {total_records:,}")
        print(f"   🔄 Duplicates Found: {total_duplicates:,}")
        print(f"   ⏱️ Total Duration: {total_duration:.2f}s")
        print(f"   ❌ Total Errors: {total_errors}")
        
        if total_errors == 0:
            print("\n🎉 All ingestions completed successfully!")
        else:
            print(f"\n⚠️ {total_errors} errors encountered. Check logs for details.")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Unified Legislative Data Ingestion Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest specific Congress data
  python unified_ingestion.py --source congress --data-type bills --congress 118

  # Ingest all Congress data for multiple congresses
  python unified_ingestion.py --source congress --data-type all --congress 116 117 118

  # Ingest GovInfo collection
  python unified_ingestion.py --source govinfo --collection BILLS --year 2023

  # Ingest OpenStates data
  python unified_ingestion.py --source openstates --jurisdiction nc --per-page 100

  # Comprehensive ingestion of all sources
  python unified_ingestion.py --source all --comprehensive
        """
    )
    
    # Source selection
    parser.add_argument(
        '--source',
        type=str,
        choices=[s.value for s in DataSource],
        required=True,
        help='Data source to ingest from'
    )
    
    # Congress parameters
    parser.add_argument(
        '--data-type',
        type=str,
        choices=[dt.value for dt in CongressDataType],
        nargs='+',
        help='Congress data type(s) to ingest'
    )
    parser.add_argument(
        '--congress',
        type=int,
        nargs='+',
        help='Congress number(s) (e.g., 116 117 118)'
    )
    
    # GovInfo parameters
    parser.add_argument(
        '--collection',
        type=str,
        choices=[c.value for c in GovInfoCollection],
        help='GovInfo collection'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Year for GovInfo collection'
    )
    
    # OpenStates parameters
    parser.add_argument(
        '--jurisdiction',
        type=str,
        help='OpenStates jurisdiction code'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='OpenStates search query'
    )
    
    # Processing options
    parser.add_argument(
        '--max-pages',
        type=int,
        default=999999,
        help='Maximum pages to fetch (default: 999999)'
    )
    parser.add_argument(
        '--per-page',
        type=int,
        default=999999,
        help='Records per page (default: 999999)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for database operations (default: 1000)'
    )
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=5,
        help='Maximum concurrent requests for async operations (default: 5)'
    )
    
    # Output options
    parser.add_argument(
        '--download-dir',
        type=str,
        default='./data',
        help='Download directory for files (default: ./data)'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='./logs',
        help='Log directory (default: ./logs)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without storing data'
    )
    
    # Processing flags
    parser.add_argument(
        '--use-copy',
        action='store_true',
        help='Use COPY method for faster database insertion'
    )
    parser.add_argument(
        '--use-sqlalchemy',
        action='store_true',
        help='Use SQLAlchemy for database operations'
    )
    parser.add_argument(
        '--disable-async',
        action='store_true',
        help='Disable async processing'
    )
    parser.add_argument(
        '--disable-deduplication',
        action='store_true',
        help='Disable duplicate detection'
    )
    parser.add_argument(
        '--disable-monitoring',
        action='store_true',
        help='Disable monitoring'
    )
    
    # Special flags
    parser.add_argument(
        '--comprehensive',
        action='store_true',
        help='Run comprehensive ingestion of all available data'
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create configuration
    config = IngestionConfig(
        use_copy=args.use_copy,
        use_sqlalchemy=args.use_sqlalchemy,
        use_async=not args.disable_async,
        max_concurrent=args.max_concurrent,
        batch_size=args.batch_size,
        max_pages=args.max_pages,
        per_page=args.per_page,
        download_dir=args.download_dir,
        log_dir=args.log_dir,
        dry_run=args.dry_run,
        enable_deduplication=not args.disable_deduplication,
        enable_monitoring=not args.disable_monitoring
    )
    
    # Validate API keys based on source
    source = DataSource(args.source)
    if source in [DataSource.CONGRESS, DataSource.ALL] and not config.congress_api_key:
        logger.error("CONGRESS_API_KEY environment variable must be set for Congress ingestion")
        sys.exit(1)
    
    if source in [DataSource.GOVINFO, DataSource.ALL] and not config.govinfo_api_key:
        logger.error("GOVINFO_API_KEY environment variable must be set for GovInfo ingestion")
        sys.exit(1)
    
    if source in [DataSource.OPENSTATES, DataSource.ALL] and not config.openstates_api_key:
        logger.warning("OPENSTATES_API_KEY not set - OpenStates ingestion will be skipped")
    
    # Create ingester
    ingester = UnifiedIngester(config)
    
    # Prepare parameters
    kwargs = {}
    
    if args.data_type:
        kwargs['data_type'] = args.data_type
    if args.congress:
        kwargs['congress'] = args.congress
    if args.collection:
        kwargs['collection'] = args.collection
    if args.year:
        kwargs['year'] = args.year
    if args.jurisdiction:
        kwargs['jurisdiction'] = args.jurisdiction
    if args.query:
        kwargs['query'] = args.query
    if args.per_page:
        kwargs['per_page'] = args.per_page
    if args.comprehensive:
        kwargs['comprehensive'] = True
    
    # Run ingestion
    try:
        logger.info(f"Starting unified ingestion for source: {source.value}")
        results = ingester.ingest(source, **kwargs)
        
        # Print summary
        ingester.print_summary()
        
        # Exit with error code if any ingestions failed
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            logger.error(f"{failed_count} ingestion(s) failed")
            sys.exit(1)
        else:
            logger.info("All ingestions completed successfully")
            
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()