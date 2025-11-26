#!/usr/bin/env python3
"""
Congress Bulk Ingestion Runner
Demonstrates how to iterate over Congress sessions and ingest all available data.
"""

import os
import sys
from congress_bulk_ingest import CongressBulkIngester

def main():
    """Run bulk ingestion for multiple Congress sessions."""

    # Congress sessions to process (105-118 covers ~1997-2025)
    congress_sessions = list(range(105, 119))  # 105 through 118

    print("🏛️  Congress Bulk Data Ingestion")
    print("=" * 50)
    print(f"Target Congress sessions: {congress_sessions}")
    print(f"Total sessions to process: {len(congress_sessions)}")
    print()

    # Data types to ingest for each Congress
    data_types = [
        'bills',        # Legislative bills
        'members',      # Congress members
        'committees',   # Committee information
        'votes',        # Roll call votes
        'bill_actions', # Bill action history
        'bill_text',    # Bill text content
        'summaries',    # Bill summaries
        'treaties',     # Treaties
        'nominations',  # Nomination actions
        'hearings',     # Committee hearings
        'congress'      # Congress session info
    ]

    print(f"Data types per session: {', '.join(data_types)}")
    print(f"Total data types: {len(data_types)}")
    print()

    # Initialize the bulk ingester
    try:
        ingester = CongressBulkIngester()
        print("✅ CongressBulkIngester initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ingester: {e}")
        sys.exit(1)

    print()
    print("🚀 Starting bulk ingestion loop...")
    print()

    # Run bulk ingestion for all Congress sessions
    results = ingester.ingest_multiple_sessions(
        congresses=congress_sessions,
        data_types=data_types,
        max_pages=20,  # Limit pages for testing
        delay_between_sessions=3  # 3 second delay between sessions
    )

    # Print detailed results
    print("\n" + "=" * 70)
    print("📊 BULK INGESTION RESULTS")
    print("=" * 70)

    print(f"Total Congress sessions processed: {results['sessions_processed']}/{results['total_sessions']}")
    print(f"Total data type successes: {results['total_successes']}")
    print(f"Total data type failures: {results['total_failures']}")
    print(".2f")
    print()

    # Show results for each Congress session
    print("Session-by-session results:")
    print("-" * 50)

    for congress_num, session_result in results['session_results'].items():
        status = "✅" if session_result['failure_count'] == 0 else "⚠️"
        print(f"{status} Congress {congress_num}: {session_result['success_count']}/{len(session_result['data_types_processed'])} successful")
        if session_result['failure_count'] > 0:
            failed_types = [dt for dt, details in session_result['details'].items()
                          if details.get('status') != 'success']
            print(f"   Failed: {', '.join(failed_types)}")

    print()
    print("🎉 Bulk ingestion completed!")
    print("Check congress_ingestion.log for detailed logs")

if __name__ == "__main__":
    main()
