#!/usr/bin/env python3
"""
Simplified Unified Legislative Data Ingestion Script

This is a working demonstration of the unified ingestion concept that consolidates
all the functionality into a single script with comprehensive parameters.

Usage Examples:
  # Ingest Congress bills
  python unified_ingestion_simple.py --source congress --data-type bills --congress 118

  # Ingest GovInfo collection  
  python unified_ingestion_simple.py --source govinfo --collection BILLS --year 2023

  # Ingest OpenStates data
  python unified_ingestion_simple.py --source openstates --jurisdiction nc

  # Run comprehensive ingestion
  python unified_ingestion_simple.py --source all --comprehensive
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


class DataSource(Enum):
    """Supported data sources."""
    CONGRESS = "congress"
    GOVINFO = "govinfo"
    OPENSTATES = "openstates"
    ALL = "all"


class CongressDataType(Enum):
    """Congress.gov data types."""
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
    """GovInfo collections."""
    BILLS = "BILLS"
    STATUTES = "STATUTES"
    CRR = "CRR"
    CRPT = "CRPT"
    CREC = "CREC"
    FR = "FR"
    GPO = "GPO"


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    source: str
    data_type: str
    success: bool
    records_processed: int = 0
    duplicates_found: int = 0
    errors: List[str] = None
    duration: float = 0.0
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.parameters is None:
            self.parameters = {}


class UnifiedIngester:
    """Simplified unified ingestion class."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results: List[IngestionResult] = []
        self.script_dir = Path(__file__).parent / "mcp_server" / "scripts"
        
    def ingest(self, source: DataSource, **kwargs) -> List[IngestionResult]:
        """Main ingestion method."""
        print(f"🚀 Starting ingestion for source: {source.value}")
        
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
        """Ingest from all sources."""
        all_results = []
        
        # Congress data
        if kwargs.get('congress') or kwargs.get('comprehensive'):
            congress_results = self._ingest_congress(**kwargs)
            all_results.extend(congress_results)
        
        # GovInfo data
        if kwargs.get('collection') or kwargs.get('comprehensive'):
            govinfo_results = self._ingest_govinfo(**kwargs)
            all_results.extend(govinfo_results)
        
        # OpenStates data
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
                    # Ingest all data types
                    for dt in CongressDataType:
                        if dt != CongressDataType.ALL:
                            # Remove conflicting parameters from kwargs
                            clean_kwargs = {k: v for k, v in kwargs.items() 
                                          if k not in ['data_type', 'congress']}
                            result = self._run_congress_script(congress, dt.value, **clean_kwargs)
                            results.append(result)
                else:
                    # Remove conflicting parameters from kwargs
                    clean_kwargs = {k: v for k, v in kwargs.items() 
                                  if k not in ['data_type', 'congress']}
                    result = self._run_congress_script(congress, data_type, **clean_kwargs)
                    results.append(result)
        
        return results
    
    def _ingest_govinfo(self, **kwargs) -> List[IngestionResult]:
        """Ingest GovInfo data."""
        collection = kwargs.get('collection', 'BILLS')
        year = kwargs.get('year')
        
        result = self._run_govinfo_script(collection, year, **kwargs)
        return [result]
    
    def _ingest_openstates(self, **kwargs) -> List[IngestionResult]:
        """Ingest OpenStates data."""
        jurisdiction = kwargs.get('jurisdiction')
        query = kwargs.get('query')
        
        result = self._run_openstates_script(jurisdiction, query, **kwargs)
        return [result]
    
    def _run_congress_script(self, congress: int, data_type: str, **kwargs) -> IngestionResult:
        """Run a Congress ingestion script."""
        start_time = time.time()
        result = IngestionResult(
            source="congress",
            data_type=f"{data_type}_{congress}",
            success=False,
            parameters={'congress': congress, 'data_type': data_type}
        )
        
        # Map data types to script files
        script_map = {
            'bills': 'congress_ingest.py',
            'members': 'congress_members_ingest.py',
            'committees': 'congress_committees_ingest.py',
            'votes': 'congress_votes_ingest.py',
            'bill_actions': 'congress_bill_actions_ingest.py',
            'bill_text': 'congress_bill_text_ingest.py',
            'summaries': 'congress_summaries_ingest.py',
            'treaties': 'congress_treaties_ingest.py',
            'nominations': 'congress_nominations_ingest.py',
            'hearings': 'congress_hearings_ingest.py',
            'congress': 'congress_congress_ingest.py'
        }
        
        script_file = script_map.get(data_type)
        if not script_file:
            result.errors.append(f"No script found for data type: {data_type}")
            result.duration = time.time() - start_time
            return result
        
        script_path = self.script_dir / script_file
        if not script_path.exists():
            result.errors.append(f"Script not found: {script_path}")
            result.duration = time.time() - start_time
            return result
        
        # Build command with environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        cmd = [
            'python', str(script_path),
            '--congress', str(congress)
        ]
        
        # Add pagination limits
        max_pages = kwargs.get('max_pages', 999999)
        if data_type in ['bills', 'members', 'committees', 'votes']:
            cmd.extend(['--max_pages', str(max_pages)])
        
        print(f"📋 Running: {' '.join(cmd)}")
        
        if self.dry_run:
            print(f"🔍 DRY RUN: Would execute {' '.join(cmd)}")
            result.success = True
            result.records_processed = 0  # Would be calculated from actual output
        else:
            try:
                # Run the script with environment
                result_process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=kwargs.get('timeout', 300),
                    env=env
                )
                
                if result_process.returncode == 0:
                    result.success = True
                    # Try to extract record count from output
                    output = result_process.stdout
                    if "records" in output.lower():
                        # Simple parsing - could be enhanced
                        lines = output.split('\n')
                        for line in lines:
                            if 'records' in line.lower() or 'processed' in line.lower():
                                try:
                                    # Extract numbers from the line
                                    import re
                                    numbers = re.findall(r'\d+', line)
                                    if numbers:
                                        result.records_processed = int(numbers[-1])
                                        break
                                except:
                                    pass
                else:
                    result.errors.append(f"Script failed with return code {result_process.returncode}")
                    result.errors.append(result_process.stderr)
                
            except subprocess.TimeoutExpired:
                result.errors.append("Script execution timed out")
            except Exception as e:
                result.errors.append(f"Error running script: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return result
    
    def _run_govinfo_script(self, collection: str, year: Optional[int], **kwargs) -> IngestionResult:
        """Run GovInfo ingestion script."""
        start_time = time.time()
        result = IngestionResult(
            source="govinfo",
            data_type=f"{collection}_{year or 'all'}",
            success=False,
            parameters={'collection': collection, 'year': year}
        )
        
        script_path = self.script_dir / 'govinfo_ingest.py'
        if not script_path.exists():
            result.errors.append(f"Script not found: {script_path}")
            result.duration = time.time() - start_time
            return result
        
        # Build command with environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        cmd = ['python', str(script_path), '--collection', collection]
        if year:
            cmd.extend(['--year', str(year)])
        
        download_dir = kwargs.get('download_dir', './data')
        cmd.extend(['--download_dir', download_dir])
        
        print(f"📋 Running: {' '.join(cmd)}")
        
        if self.dry_run:
            print(f"🔍 DRY RUN: Would execute {' '.join(cmd)}")
            result.success = True
            result.records_processed = 0
        else:
            try:
                result_process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=kwargs.get('timeout', 600)
                )
                
                if result_process.returncode == 0:
                    result.success = True
                    # Extract record count
                    output = result_process.stdout
                    if "documents" in output.lower() or "records" in output.lower():
                        try:
                            import re
                            numbers = re.findall(r'\d+', output)
                            if numbers:
                                result.records_processed = int(numbers[-1])
                        except:
                            pass
                else:
                    result.errors.append(f"Script failed with return code {result_process.returncode}")
                    result.errors.append(result_process.stderr)
                
            except subprocess.TimeoutExpired:
                result.errors.append("Script execution timed out")
            except Exception as e:
                result.errors.append(f"Error running script: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return result
    
    def _run_openstates_script(self, jurisdiction: Optional[str], query: Optional[str], **kwargs) -> IngestionResult:
        """Run OpenStates ingestion script."""
        start_time = time.time()
        result = IngestionResult(
            source="openstates",
            data_type=f"bills_{jurisdiction or 'all'}_{query or 'all'}",
            success=False,
            parameters={'jurisdiction': jurisdiction, 'query': query}
        )
        
        script_path = self.script_dir / 'openstates_ingest.py'
        if not script_path.exists():
            result.errors.append(f"Script not found: {script_path}")
            result.duration = time.time() - start_time
            return result
        
        # Build command with environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        cmd = ['python', str(script_path)]
        if jurisdiction:
            cmd.extend(['--jurisdiction', jurisdiction])
        if query:
            cmd.extend(['--q', query])
        
        per_page = kwargs.get('per_page', 50)
        cmd.extend(['--per_page', str(per_page)])
        
        print(f"📋 Running: {' '.join(cmd)}")
        
        if self.dry_run:
            print(f"🔍 DRY RUN: Would execute {' '.join(cmd)}")
            result.success = True
            result.records_processed = 0
        else:
            try:
                result_process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=kwargs.get('timeout', 600)
                )
                
                if result_process.returncode == 0:
                    result.success = True
                    # Extract record count
                    output = result_process.stdout
                    if "bills" in output.lower() or "records" in output.lower():
                        try:
                            import re
                            numbers = re.findall(r'\d+', output)
                            if numbers:
                                result.records_processed = int(numbers[-1])
                        except:
                            pass
                else:
                    result.errors.append(f"Script failed with return code {result_process.returncode}")
                    result.errors.append(result_process.stderr)
                
            except subprocess.TimeoutExpired:
                result.errors.append("Script execution timed out")
            except Exception as e:
                result.errors.append(f"Error running script: {e}")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        
        return result
    
    def print_summary(self):
        """Print ingestion summary."""
        print("\n" + "="*80)
        print("🎉 UNIFIED INGESTION SUMMARY")
        print("="*80)
        
        total_records = 0
        total_duration = 0
        total_errors = 0
        
        for result in self.results:
            status = "✅" if result.success else "❌"
            print(f"\n{status} {result.source.upper()} - {result.data_type}")
            print(f"   📊 Records: {result.records_processed:,}")
            print(f"   ⏱️ Duration: {result.duration:.2f}s")
            
            if result.errors:
                print(f"   ❌ Errors: {len(result.errors)}")
                for error in result.errors[:2]:  # Show first 2 errors
                    print(f"      - {error}")
            
            total_records += result.records_processed
            total_duration += result.duration
            total_errors += len(result.errors)
        
        print(f"\n📈 TOTALS:")
        print(f"   📊 Records Processed: {total_records:,}")
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
  # Ingest Congress bills
  python unified_ingestion_simple.py --source congress --data-type bills --congress 118

  # Ingest all Congress data types
  python unified_ingestion_simple.py --source congress --data-type all --congress 118

  # Ingest GovInfo collection
  python unified_ingestion_simple.py --source govinfo --collection BILLS --year 2023

  # Ingest OpenStates data
  python unified_ingestion_simple.py --source openstates --jurisdiction nc

  # Comprehensive ingestion
  python unified_ingestion_simple.py --source all --comprehensive
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
        default=50,
        help='Records per page (default: 50)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        default='./data',
        help='Download directory for files (default: ./data)'
    )
    
    # Special flags
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without executing scripts'
    )
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
    
    # Create ingester
    ingester = UnifiedIngester(dry_run=args.dry_run)
    
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
    if args.max_pages:
        kwargs['max_pages'] = args.max_pages
    if args.per_page:
        kwargs['per_page'] = args.per_page
    if args.timeout:
        kwargs['timeout'] = args.timeout
    if args.download_dir:
        kwargs['download_dir'] = args.download_dir
    if args.comprehensive:
        kwargs['comprehensive'] = True
    
    # Run ingestion
    try:
        source = DataSource(args.source)
        results = ingester.ingest(source, **kwargs)
        
        # Print summary
        ingester.print_summary()
        
        # Exit with error code if any ingestions failed
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            print(f"\n⚠️ {failed_count} ingestion(s) failed")
            sys.exit(1)
        else:
            print("\n✅ All ingestions completed successfully!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Ingestion interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()