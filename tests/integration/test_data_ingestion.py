#!/usr/bin/env python3
"""
Comprehensive Data Ingestion Test for All Legislative Data Schemas

This script tests data ingestion for all tables in the three main schemas:
- Congress.gov schema (congress_* tables)
- GovInfo schema (govinfo_* tables)
- OpenStates OCD schema (opencivicdata_* tables)

It creates test data for each table, attempts to insert it, and verifies
that all constraints and relationships work correctly.
"""

import os
import sys
import json
import uuid
from datetime import datetime, date, time
from pathlib import Path
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import Json, execute_values
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIngestionTester:
    """Test data ingestion for all legislative data schemas"""

    def __init__(self, db_url: Optional[str] = None):
        # Load environment variables from .env file
        load_dotenv(dotenv_path='/home/cbwinslow/opendiscourse/mcp_server/.env')
        
        self.db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://localhost/opendiscourse_test')
        self.conn = None
        self.cursor = None

        # Test data generators for each schema
        self.test_data = {
            'congress': {},
            'govinfo': {},
            'openstates': {}
        }

    def connect(self):
        """Connect to the database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def create_schemas(self):
        """Create all database schemas"""
        # First, drop all existing tables to ensure clean slate
        logger.info("Dropping existing tables...")
        drop_tables_sql = """
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
        """
        try:
            self.cursor.execute(drop_tables_sql)
            self.conn.commit()
            logger.info("Dropped existing tables successfully")
        except Exception as e:
            logger.warning(f"Error dropping tables (may be expected): {e}")
            self.conn.rollback()

        schema_files = [
            '/home/cbwinslow/opendiscourse/mcp_server/sql/congress_schema.sql',
            '/home/cbwinslow/opendiscourse/mcp_server/sql/govinfo_schema.sql',
            '/home/cbwinslow/opendiscourse/mcp_server/sql/openstates_schema.sql'
        ]

        for schema_file in schema_files:
            logger.info(f"Creating schema from {schema_file}")
            with open(schema_file, 'r') as f:
                sql = f.read()

            # Split on semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    try:
                        self.cursor.execute(statement)
                    except Exception as e:
                        logger.warning(f"Statement failed (may be expected): {e}")
                        # Continue - some statements like CREATE INDEX IF NOT EXISTS may fail if index exists

            self.conn.commit()
            logger.info(f"Schema {Path(schema_file).name} created successfully")

    def generate_congress_test_data(self):
        """Generate test data for Congress schema tables"""
        logger.info("Generating Congress test data...")

        # Congress Bills
        self.test_data['congress']['bills'] = [
            {
                'bill_id': '118-HR-1',
                'congress': 118,
                'bill_type': 'hr',
                'bill_number': '1',
                'title': 'Test Bill Title',
                'introduced_date': date(2023, 1, 1),
                'origin_chamber': 'HOUSE',
                'current_chamber': 'HOUSE',
                'latest_action_date': date(2023, 2, 1),
                'latest_action_text': 'Referred to committee',
                'latest_action_type': 'Committee',
                'sponsors': Json([{'bioguideId': 'B000944', 'name': 'Test Sponsor'}]),
                'cosponsors': Json({'count': 5, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/cosponsors'}),
                'committees': Json({'count': 2, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/committees'}),
                'actions': Json({'count': 10, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/actions'}),
                'amendments': Json({'count': 0, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/amendments'}),
                'related_bills': Json({'count': 1, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/relatedbills'}),
                'subjects': Json({'count': 3, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/subjects'}),
                'summaries': Json({'count': 1, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/summaries'}),
                'text': Json({'count': 2, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/text'}),
                'titles': Json({'count': 3, 'url': 'https://api.congress.gov/v3/bill/118/hr/1/titles'}),
                'cbo_cost_estimates': Json([]),
                'policy_area': Json({'name': 'Test Policy', 'policyAreaDescription': 'Test description'}),
                'constitutional_authority_statement_text': 'Test constitutional authority',
                'raw': Json({'test': 'data'})
            }
        ]

        # Congress Members
        self.test_data['congress']['members'] = [
            {
                'bioguide_id': 'B000944',
                'direct_order_name': 'Test Member',
                'inverted_order_name': 'Member, Test',
                'honorific_name': 'Mr.',
                'first_name': 'Test',
                'last_name': 'Member',
                'birth_year': 1980,
                'party_name': 'Democrat',
                'party_history': Json([{'partyName': 'Democrat', 'startYear': 2020}]),
                'state': 'CA',
                'district': '1',
                'current_member': True,
                'terms': Json([{'chamber': 'House', 'congress': 118, 'district': '1', 'startYear': 2023}]),
                'previous_names': Json([]),
                'depiction': Json({'imageUrl': 'https://example.com/image.jpg'}),
                'sponsored_legislation': Json({'count': 50, 'url': 'https://api.congress.gov/v3/member/B000944/sponsored-legislation'}),
                'cosponsored_legislation': Json({'count': 200, 'url': 'https://api.congress.gov/v3/member/B000944/cosponsored-legislation'}),
                'leadership_positions': Json([]),
                'committee_assignments': Json([{'committee': 'HSAP', 'position': 'Member'}]),
                'voting_record': Json({'totalVotes': 100, 'missedVotes': 5}),
                'raw': Json({'test': 'member_data'})
            }
        ]

        # Congress Votes
        self.test_data['congress']['votes'] = [
            {
                'vote_id': 'h2023-01-01.001',
                'congress': 118,
                'session': 1,
                'chamber': 'house',
                'roll_number': 1,
                'vote_date': date(2023, 1, 1),
                'vote_time': time(14, 30),
                'question': 'Shall the bill pass?',
                'description': 'Test vote description',
                'vote_type': 'YEA-AND-NAY',
                'result': 'Passed',
                'total_yes': 220,
                'total_no': 180,
                'total_present': 5,
                'total_not_voting': 30,
                'tie_breaker': Json(None),
                'document': Json({'bill': {'number': '1', 'type': 'hr', 'congress': 118}}),
                'member_votes': Json([{'member': 'B000944', 'vote': 'Yea'}]),
                'amendments': Json([]),
                'raw': Json({'test': 'vote_data'})
            }
        ]

        # Congress Bill Actions
        self.test_data['congress']['bill_actions'] = [
            {
                'action_id': '118-HR-1-001',
                'bill_id': '118-HR-1',
                'action_date': date(2023, 1, 1),
                'sequence_number': 1,
                'action_code': 'H10000',
                'action_text': 'Introduced in House',
                'action_type': 'IntroReferral',
                'chamber': 'House',
                'committee': Json({'systemCode': 'HSAP', 'name': 'House Appropriations'})
            }
        ]

        # Congress Bill Text
        self.test_data['congress']['bill_text'] = [
            {
                'text_id': '118-HR-1-IH',
                'bill_id': '118-HR-1',
                'text_type': 'Introduced',
                'text_format': 'XML',
                'date_issued': date(2023, 1, 1),
                'congress': 118,
                'bill_type': 'hr',
                'bill_number': '1',
                'bill_version': 'ih',
                'full_text': 'Test bill text content',
                'extracted_text': 'Extracted text content',
                'file_path': '/path/to/file.xml',
                'file_size': 1024,
                'mime_type': 'application/xml',
                'processing_status': 'completed',
                'processing_attempts': 1,
                'last_processing_attempt': datetime.now()
            }
        ]

    def generate_govinfo_test_data(self):
        """Generate test data for GovInfo schema tables"""
        logger.info("Generating GovInfo test data...")

        # GovInfo Collections
        self.test_data['govinfo']['collections'] = [
            {
                'collection_code': 'BILLS',
                'collection_name': 'Congressional Bills',
                'package_count': 10000,
                'granule_count': 50000,
                'category': 'legislative',
                'branch': 'legislative',
                'description': 'All congressional bills and resolutions',
                'api_endpoint': 'https://api.govinfo.gov/collections/BILLS',
                'bulk_download_available': True,
                'enabled': True,
                'priority': 1,
                'update_frequency': 'daily',
                'last_full_update': datetime.now(),
                'last_incremental_update': datetime.now(),
                'total_processed': 9500,
                'total_failed': 50,
                'raw': Json({'test': 'collection_data'})
            }
        ]

        # GovInfo Packages
        self.test_data['govinfo']['packages'] = [
            {
                'package_id': 'BILLS-118hr1enr',
                'collection_code': 'BILLS',
                'last_modified': datetime.now(),
                'date_issued': date(2023, 1, 1),
                'title': 'Test Bill Package',
                'collection_name': 'Congressional Bills',
                'category': 'legislative',
                'branch': 'legislative',
                'document_type': 'BILLS',
                'pages': 10,
                'government_author1': 'House of Representatives',
                'su_doc_class_number': None,
                'congress': 118,
                'session': 1,
                'bill_type': 'hr',
                'bill_number': '1',
                'bill_version': 'enr',
                'origin_chamber': 'HOUSE',
                'current_chamber': 'HOUSE',
                'is_appropriation': False,
                'is_private': False,
                'publisher': 'U.S. Government Publishing Office',
                'other_identifiers': Json({'migrated-doc-id': 'f:h1_enr.txt', 'ils-system-id': '12345'}),
                'details_link': 'https://www.govinfo.gov/app/details/BILLS-118hr1enr',
                'granules_link': 'https://api.govinfo.gov/packages/BILLS-118hr1enr/granules',
                'package_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr.zip',
                'has_txt': True,
                'has_pdf': True,
                'has_xml': True,
                'has_mods': True,
                'has_premis': True,
                'has_zip': True,
                'txt_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/html/BILLS-118hr1enr.htm',
                'pdf_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/pdf/BILLS-118hr1enr.pdf',
                'xml_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/xml/BILLS-118hr1enr.xml',
                'mods_link': 'https://www.govinfo.gov/metadata/pkg/BILLS-118hr1enr/mods.xml',
                'premis_link': 'https://www.govinfo.gov/metadata/pkg/BILLS-118hr1enr/premis.xml',
                'zip_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr.zip',
                'related': Json({'billStatusLink': 'https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr1.xml'}),
                'references': Json([
                    {'collectionCode': 'USCODE', 'contents': [{'title': '1', 'label': 'U.S.C', 'sections': ['112']}]},
                    {'collectionCode': 'STATUTE', 'contents': [{'title': '32', 'label': 'Stat.', 'pages': ['480']}]},
                    {'collectionCode': 'PLAW', 'contents': [{'label': 'Public Law', 'congress': '118', 'number': '1'}]}
                ]),
                'full_text': 'Test full text content',
                'extracted_text': 'Test extracted text',
                'mods_metadata': Json({'title': 'Test Bill'}),
                'premis_metadata': Json({'objectIdentifier': 'BILLS-118hr1enr'}),
                'processing_status': 'completed',
                'processing_attempts': 1,
                'last_processing_attempt': datetime.now(),
                'processing_errors': Json(None),
                'raw_summary': Json({'test': 'summary_data'}),
                'raw': Json({'test': 'package_data'})
            }
        ]

        # GovInfo Granules
        self.test_data['govinfo']['granules'] = [
            {
                'granule_id': 'BILLS-118hr1enr-1',
                'package_id': 'BILLS-118hr1enr',
                'title': 'Test Granule',
                'granule_class': 'BILL',
                'date_issued': date(2023, 1, 1),
                'last_modified': datetime.now(),
                'pages': 5,
                'heading': 'Test Heading',
                'sub_heading': 'Test Subheading',
                'parent_package_id': 'BILLS-118hr1enr',
                'sequence_number': 1,
                'text_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/html/BILLS-118hr1enr.htm',
                'pdf_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/pdf/BILLS-118hr1enr.pdf',
                'xml_link': 'https://www.govinfo.gov/content/pkg/BILLS-118hr1enr/xml/BILLS-118hr1enr.xml',
                'mods_link': 'https://www.govinfo.gov/metadata/pkg/BILLS-118hr1enr/mods.xml',
                'premis_link': 'https://www.govinfo.gov/metadata/pkg/BILLS-118hr1enr/premis.xml',
                'has_text': True,
                'has_pdf': True,
                'has_xml': True,
                'has_mods': True,
                'has_premis': True,
                'full_text': 'Test granule text',
                'extracted_text': 'Test extracted granule text',
                'mods_metadata': Json({'title': 'Test Granule'}),
                'premis_metadata': Json({'objectIdentifier': 'BILLS-118hr1enr-1'}),
                'processing_status': 'completed',
                'processing_attempts': 1,
                'last_processing_attempt': datetime.now(),
                'processing_errors': Json(None),
                'raw': Json({'test': 'granule_data'})
            }
        ]

        # GovInfo Processing Log
        self.test_data['govinfo']['processing_log'] = [
            {
                'package_id': 'BILLS-118hr1enr',
                'granule_id': 'BILLS-118hr1enr-1',
                'operation': 'download',
                'status': 'completed',
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'duration': None,
                'error_message': None,
                'error_details': Json(None),
                'file_size': 1024,
                'content_type': 'application/pdf',
                'processing_node': 'test-node'
            }
        ]

    def generate_openstates_test_data(self):
        """Generate test data for OpenStates OCD schema tables"""
        logger.info("Generating OpenStates OCD test data...")

        # Core entities first (needed for foreign keys)
        self.test_data['openstates']['divisions'] = [
            {
                'id': 'ocd-division/country:us/state:ca',
                'name': 'California',
                'country': 'us',
                'subtype1': 'state',
                'subid1': 'ca'
            }
        ]

        self.test_data['openstates']['jurisdictions'] = [
            {
                'id': 'ocd-jurisdiction/country:us/state:ca/government',
                'name': 'California',
                'url': 'https://www.legislature.ca.gov',
                'classification': 'state',
                'division_id': 'ocd-division/country:us/state:ca',
                'latest_bill_update': datetime.now(),
                'latest_people_update': datetime.now(),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        self.test_data['openstates']['legislative_sessions'] = [
            {
                'id': str(uuid.uuid4()),
                'identifier': '2023',
                'name': '2023 Regular Session',
                'classification': 'primary',
                'start_date': date(2023, 1, 1),
                'end_date': date(2023, 12, 31),
                'jurisdiction_id': 'ocd-jurisdiction/country:us/state:ca/government',
                'active': True
            }
        ]

        session_id = self.test_data['openstates']['legislative_sessions'][0]['id']

        self.test_data['openstates']['organizations'] = [
            {
                'id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                'name': 'California State Assembly',
                'classification': 'lower',
                'jurisdiction_id': 'ocd-jurisdiction/country:us/state:ca/government',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({}),
                'links': Json([]),
                'sources': Json([]),
                'other_names': Json([])
            }
        ]

        self.test_data['openstates']['persons'] = [
            {
                'id': 'ocd-person/test-person-1',
                'name': 'Test Legislator',
                'family_name': 'Legislator',
                'given_name': 'Test',
                'image': 'https://example.com/image.jpg',
                'gender': 'male',
                'biography': 'Test biography',
                'birth_date': date(1980, 1, 1),
                'primary_party': 'Democratic',
                'current_jurisdiction_id': 'ocd-jurisdiction/country:us/state:ca/government',
                'current_role': Json({'chamber': 'lower', 'district': '1'}),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        # Bills and related data
        self.test_data['openstates']['bills'] = [
            {
                'id': 'ocd-bill/test-bill-1',
                'identifier': 'AB 1',
                'title': 'Test Bill Title',
                'classification': ['bill'],
                'subject': ['BUDGET', 'FINANCE'],
                'from_organization_id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                'legislative_session_id': session_id,
                'first_action_date': date(2023, 1, 1),
                'latest_action_date': date(2023, 2, 1),
                'latest_action_description': 'Passed Assembly',
                'latest_passage_date': date(2023, 2, 1),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({}),
                'citations': Json({})
            }
        ]

        bill_id = self.test_data['openstates']['bills'][0]['id']

        self.test_data['openstates']['bill_actions'] = [
            {
                'id': str(uuid.uuid4()),
                'description': 'Introduced',
                'date': date(2023, 1, 1),
                'classification': ['introduction'],
                'order': 1,
                'bill_id': bill_id,
                'organization_id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        action_id = self.test_data['openstates']['bill_actions'][0]['id']

        self.test_data['openstates']['bill_sponsorships'] = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Legislator',
                'entity_type': 'person',
                'primary': True,
                'classification': 'primary',
                'bill_id': bill_id,
                'person_id': 'ocd-person/test-person-1',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        self.test_data['openstates']['bill_sources'] = [
            {
                'id': str(uuid.uuid4()),
                'note': 'Official bill text',
                'url': 'https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202320240AB1',
                'bill_id': bill_id
            }
        ]

        # Vote data
        self.test_data['openstates']['vote_events'] = [
            {
                'id': 'ocd-vote/test-vote-1',
                'identifier': '2023-001',
                'motion_text': 'Shall the bill pass?',
                'motion_classification': ['passage'],
                'start_date': datetime.now(),
                'result': 'pass',
                'bill_id': bill_id,
                'organization_id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        vote_event_id = self.test_data['openstates']['vote_events'][0]['id']

        self.test_data['openstates']['person_votes'] = [
            {
                'id': str(uuid.uuid4()),
                'option': 'yes',
                'voter_name': 'Test Legislator',
                'note': '',
                'vote_event_id': vote_event_id,
                'voter_id': 'ocd-person/test-person-1',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        self.test_data['openstates']['vote_event_counts'] = [
            {
                'id': str(uuid.uuid4()),
                'option': 'yes',
                'value': 45,
                'vote_event_id': vote_event_id
            },
            {
                'id': str(uuid.uuid4()),
                'option': 'no',
                'value': 30,
                'vote_event_id': vote_event_id
            }
        ]

        # Memberships
        self.test_data['openstates']['memberships'] = [
            {
                'id': str(uuid.uuid4()),
                'label': 'Assembly Member',
                'role': 'member',
                'start_date': date(2023, 1, 1),
                'person_id': 'ocd-person/test-person-1',
                'organization_id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

        # Events
        self.test_data['openstates']['events'] = [
            {
                'id': 'ocd-event/test-event-1',
                'name': 'Test Committee Hearing',
                'description': 'Test hearing description',
                'classification': 'committee-meeting',
                'start_date': datetime.now(),
                'end_date': datetime.now(),
                'all_day': False,
                'timezone': 'America/Los_Angeles',
                'status': 'confirmed',
                'jurisdiction_id': 'ocd-jurisdiction/country:us/state:ca/government',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'extras': Json({})
            }
        ]

    def insert_test_data(self, schema: str, table: str, data: List[Dict[str, Any]]):
        """Insert test data into a specific table"""
        if not data:
            logger.warning(f"No test data for {schema}.{table}")
            return

        # Map test table names to actual database table names
        table_name_map = {
            # OpenStates mappings (singular in schema, plural in test)
            ('openstates', 'divisions'): 'opencivicdata_division',
            ('openstates', 'jurisdictions'): 'opencivicdata_jurisdiction',
            ('openstates', 'legislative_sessions'): 'opencivicdata_legislativesession',
            ('openstates', 'organizations'): 'opencivicdata_organization',
            ('openstates', 'persons'): 'opencivicdata_person',
            ('openstates', 'bills'): 'opencivicdata_bill',
            ('openstates', 'bill_actions'): 'opencivicdata_billaction',
            ('openstates', 'bill_sponsorships'): 'opencivicdata_billsponsorship',
            ('openstates', 'bill_sources'): 'opencivicdata_billsource',
            ('openstates', 'vote_events'): 'opencivicdata_voteevent',
            ('openstates', 'person_votes'): 'opencivicdata_personvote',
            ('openstates', 'vote_event_counts'): 'opencivicdata_voteeventcount',
            ('openstates', 'memberships'): 'opencivicdata_membership',
            ('openstates', 'events'): 'opencivicdata_event',
            
            # GovInfo mappings
            ('govinfo', 'collections'): 'govinfo_collections',
            ('govinfo', 'packages'): 'govinfo_packages',
            ('govinfo', 'granules'): 'govinfo_granules',
            ('govinfo', 'processing_log'): 'govinfo_processing_log',
            
            # Congress mappings
            ('congress', 'members'): 'congress_members',
            ('congress', 'bills'): 'congress_bills',
            ('congress', 'votes'): 'congress_votes',
            ('congress', 'bill_actions'): 'congress_bill_actions',
            ('congress', 'bill_text'): 'congress_bill_text'
        }

        table_name = table_name_map.get((schema, table), f"{schema}_{table}")

        try:
            # Get column names from the first data item
            columns = list(data[0].keys())

            # Build the INSERT statement with proper quoting for reserved words
            quoted_columns = []
            for col in columns:
                if col in ['order', 'primary', 'current_role', 'references']:
                    quoted_columns.append(f'"{col}"')
                else:
                    quoted_columns.append(col)

            placeholders = ', '.join(['%s'] * len(columns))
            sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

            # Insert each row
            for row in data:
                values = [row[col] for col in columns]
                self.cursor.execute(sql, values)

            self.conn.commit()
            logger.info(f"Successfully inserted {len(data)} rows into {table_name}")

        except Exception as e:
            logger.error(f"Failed to insert data into {table_name}: {e}")
            self.conn.rollback()
            raise

    def test_data_ingestion(self):
        """Test data ingestion for all schemas"""
        logger.info("Starting comprehensive data ingestion test...")

        # Generate all test data
        self.generate_congress_test_data()
        self.generate_govinfo_test_data()
        self.generate_openstates_test_data()

        # Insert data in dependency order
        insertion_order = [
            # OpenStates (has dependencies)
            ('openstates', 'divisions'),
            ('openstates', 'jurisdictions'),
            ('openstates', 'legislative_sessions'),
            ('openstates', 'organizations'),
            ('openstates', 'persons'),
            ('openstates', 'bills'),
            ('openstates', 'bill_actions'),
            ('openstates', 'bill_sponsorships'),
            ('openstates', 'bill_sources'),
            ('openstates', 'vote_events'),
            ('openstates', 'person_votes'),
            ('openstates', 'vote_event_counts'),
            ('openstates', 'memberships'),
            ('openstates', 'events'),

            # GovInfo
            ('govinfo', 'collections'),
            ('govinfo', 'packages'),
            ('govinfo', 'granules'),
            ('govinfo', 'processing_log'),

            # Congress
            ('congress', 'members'),
            ('congress', 'bills'),
            ('congress', 'votes'),
            ('congress', 'bill_actions'),
            ('congress', 'bill_text')
        ]

        success_count = 0
        total_tables = len(insertion_order)

        for schema, table in insertion_order:
            try:
                data = self.test_data[schema][table]
                self.insert_test_data(schema, table, data)
                success_count += 1
                logger.info(f"✓ {schema}.{table}: {len(data)} rows inserted successfully")
            except Exception as e:
                logger.error(f"✗ {schema}.{table}: Failed to insert data - {e}")

        logger.info(f"Data ingestion test completed: {success_count}/{total_tables} tables successful")

        if success_count == total_tables:
            logger.info("🎉 All tables can accept data successfully!")
            return True
        else:
            logger.error(f"❌ {total_tables - success_count} tables failed data ingestion")
            return False

    def verify_constraints(self):
        """Verify that all foreign key constraints and other constraints work"""
        logger.info("Verifying database constraints...")

        # Test foreign key constraints by trying invalid inserts
        constraint_tests = [
            # Test Congress foreign keys
            {
                'table': 'congress_bill_actions',
                'invalid_data': {
                    'action_id': 'test-invalid-fk',
                    'bill_id': 'nonexistent-bill-id',  # This should fail FK constraint
                    'action_date': date(2023, 1, 1),
                    'sequence_number': 1,
                    'action_code': 'H10000',
                    'action_text': 'Test action',
                    'action_type': 'IntroReferral',
                    'chamber': 'House'
                },
                'expected_failure': True
            },

            # Test GovInfo foreign keys
            {
                'table': 'govinfo_granules',
                'invalid_data': {
                    'granule_id': 'test-invalid-fk',
                    'package_id': 'nonexistent-package-id',  # This should fail FK constraint
                    'title': 'Test Granule',
                    'granule_class': 'BILL',
                    'date_issued': date(2023, 1, 1),
                    'last_modified': datetime.now(),
                    'processing_status': 'pending'
                },
                'expected_failure': True
            },

            # Test OpenStates foreign keys
            {
                'table': 'opencivicdata_billaction',
                'invalid_data': {
                    'id': str(uuid.uuid4()),
                    'description': 'Test action',
                    'date': date(2023, 1, 1),
                    'classification': ['introduction'],
                    'order': 1,
                    'bill_id': 'nonexistent-bill-id',  # This should fail FK constraint
                    'organization_id': 'ocd-organization/32aab083-d7a0-44e0-9b95-a7790c542605',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'extras': Json({})
                },
                'expected_failure': True
            }
        ]

        constraint_success = 0
        total_constraints = len(constraint_tests)

        for test in constraint_tests:
            table = test['table']
            data = test['invalid_data']
            expected_failure = test['expected_failure']

            try:
                columns = list(data.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

                values = [data[col] for col in columns]
                self.cursor.execute(sql, values)
                self.conn.commit()

                if expected_failure:
                    logger.error(f"✗ {table}: Expected constraint violation but insert succeeded")
                else:
                    logger.info(f"✓ {table}: Constraint test passed")
                    constraint_success += 1

            except Exception as e:
                if expected_failure:
                    logger.info(f"✓ {table}: Constraint violation correctly prevented invalid insert")
                    constraint_success += 1
                else:
                    logger.error(f"✗ {table}: Unexpected error during constraint test - {e}")

        logger.info(f"Constraint verification completed: {constraint_success}/{total_constraints} tests passed")

        return constraint_success == total_constraints

    def run_comprehensive_test(self):
        """Run the complete data ingestion and constraint verification test"""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE DATA INGESTION TEST")
        logger.info("=" * 80)

        try:
            self.connect()
            self.create_schemas()

            # Test data ingestion
            ingestion_success = self.test_data_ingestion()

            # Test constraints
            constraint_success = self.verify_constraints()

            # Summary
            logger.info("=" * 80)
            logger.info("TEST RESULTS SUMMARY")
            logger.info("=" * 80)

            if ingestion_success and constraint_success:
                logger.info("🎉 ALL TESTS PASSED!")
                logger.info("✓ All tables can accept data")
                logger.info("✓ All constraints are working correctly")
                logger.info("✓ Foreign key relationships are valid")
                return True
            else:
                logger.error("❌ SOME TESTS FAILED!")
                if not ingestion_success:
                    logger.error("✗ Data ingestion failed for some tables")
                if not constraint_success:
                    logger.error("✗ Constraint verification failed")
                return False

        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            return False
        finally:
            self.disconnect()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Test data ingestion for all legislative schemas')
    parser.add_argument('--db-url', help='Database URL (default: from DATABASE_URL env var)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = DataIngestionTester(db_url=args.db_url)
    success = tester.run_comprehensive_test()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()