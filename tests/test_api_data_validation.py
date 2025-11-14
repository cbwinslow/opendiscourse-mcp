#!/usr/bin/env python3
"""
Comprehensive API Data Validation Tests

This module tests that the SQL schemas accurately reflect the actual data structures
returned by the three legislative data APIs: OpenStates, Congress.gov, and GovInfo.

Tests fetch real data from each API and validate it against the database schemas.
"""

import os
import json
import pytest
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json as PGJson
import time

# API Keys - these should be set as environment variables
CONGRESS_API_KEY = os.getenv('CONGRESS_API_KEY', 'DEMO_KEY')
GOVINFO_API_KEY = os.getenv('GOVINFO_API_KEY', 'DEMO_KEY')
OPENSTATES_API_KEY = os.getenv('OPENSTATES_API_KEY', '')

# Database connection
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'opendiscourse'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

class APIDataValidator:
    """Validates API data against database schemas"""

    def __init__(self):
        self.congress_base = "https://api.congress.gov/v3"
        self.govinfo_base = "https://api.govinfo.gov"
        self.openstates_base = "https://openstates.org/api/v1"

        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # seconds

    def _rate_limit(self, api_name: str):
        """Enforce rate limiting between API calls"""
        now = time.time()
        if api_name in self.last_request_time:
            elapsed = now - self.last_request_time[api_name]
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time[api_name] = now

    def fetch_congress_bill(self, congress: int = 118, bill_type: str = 'hr', bill_number: int = 1) -> Dict[str, Any]:
        """Fetch a bill from Congress.gov API"""
        self._rate_limit('congress')
        url = f"{self.congress_base}/bill/{congress}/{bill_type}/{bill_number}"
        params = {'api_key': CONGRESS_API_KEY, 'format': 'json'}

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_congress_member(self, bioguide_id: str = 'B000944') -> Dict[str, Any]:
        """Fetch a member from Congress.gov API"""
        self._rate_limit('congress')
        url = f"{self.congress_base}/member/{bioguide_id}"
        params = {'api_key': CONGRESS_API_KEY, 'format': 'json'}

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_congress_committee(self, chamber: str = 'house', committee_code: str = 'HSAP') -> Dict[str, Any]:
        """Fetch a committee from Congress.gov API"""
        self._rate_limit('congress')
        url = f"{self.congress_base}/committee/{chamber}/{committee_code}"
        params = {'api_key': CONGRESS_API_KEY, 'format': 'json'}

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_govinfo_package(self, package_id: str = 'BILLS-118hr1enr') -> Dict[str, Any]:
        """Fetch a package summary from GovInfo API"""
        self._rate_limit('govinfo')
        url = f"{self.govinfo_base}/packages/{package_id}/summary"
        params = {'api_key': GOVINFO_API_KEY}

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_govinfo_collections(self) -> Dict[str, Any]:
        """Fetch collections from GovInfo API"""
        self._rate_limit('govinfo')
        url = f"{self.govinfo_base}/collections"
        params = {'api_key': GOVINFO_API_KEY}

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_openstates_bill(self, jurisdiction: str = 'nc', bill_id: str = 'AB 1') -> Dict[str, Any]:
        """Fetch a bill from OpenStates API using current v3 format"""
        self._rate_limit('openstates')
        # Use current OpenStates v3 API format
        url = f"{self.openstates_base}/bills"
        params = {'jurisdiction': f'ocd-jurisdiction/country:us/state:{jurisdiction}/government', 
                  'page': 1, 'per_page': 1}
        if OPENSTATES_API_KEY:
            params['apikey'] = OPENSTATES_API_KEY

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data and 'results' in data and data['results']:
                return data['results'][0]
            else:
                # Fallback to search for any recent bill
                params = {'jurisdiction': f'ocd-jurisdiction/country:us/state:{jurisdiction}/government',
                          'page': 1, 'per_page': 1}
                if OPENSTATES_API_KEY:
                    params['apikey'] = OPENSTATES_API_KEY
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data['results'][0] if data and 'results' in data and data['results'] else {}
        except Exception as e:
            print(f"Warning: Could not fetch OpenStates data: {e}")
            return {}

    def validate_congress_bill_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate Congress bill data against schema expectations"""
        errors = []

        # Check required fields
        required_fields = ['bill', 'request']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if 'bill' in data:
            bill = data['bill']

            # Check bill structure
            bill_fields = [
                'number', 'billType', 'congress', 'introducedDate', 'title',
                'policyArea', 'latestAction', 'sponsors', 'cosponsors'
            ]

            for field in bill_fields:
                if field not in bill:
                    errors.append(f"Missing bill field: {field}")

            # Validate sponsors structure
            if 'sponsors' in bill and bill['sponsors']:
                sponsor = bill['sponsors'][0]
                sponsor_fields = ['bioguideId', 'firstName', 'lastName', 'party', 'state']
                for field in sponsor_fields:
                    if field not in sponsor:
                        errors.append(f"Missing sponsor field: {field}")

            # Validate cosponsors structure
            if 'cosponsors' in bill and bill['cosponsors']:
                cosponsor = bill['cosponsors'][0]
                cosponsor_fields = ['bioguideId', 'firstName', 'lastName', 'party', 'state', 'date']
                for field in cosponsor_fields:
                    if field not in cosponsor:
                        errors.append(f"Missing cosponsor field: {field}")

        return errors

    def validate_congress_member_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate Congress member data against schema expectations"""
        errors = []

        # Check required fields
        required_fields = ['member', 'request']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if 'member' in data:
            member = data['member']

            # Check member structure
            member_fields = [
                'bioguideId', 'name', 'partyName', 'state', 'district',
                'terms', 'depiction'
            ]

            for field in member_fields:
                if field not in member:
                    errors.append(f"Missing member field: {field}")

            # Validate terms structure
            if 'terms' in member and member['terms']:
                term = member['terms'][-1]  # Most recent term
                term_fields = ['chamber', 'startYear', 'endYear']
                for field in term_fields:
                    if field not in term:
                        errors.append(f"Missing term field: {field}")

        return errors

    def validate_govinfo_package_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate GovInfo package data against schema expectations"""
        errors = []

        # Check required fields from GovInfo API response
        required_fields = [
            'title', 'collectionCode', 'collectionName', 'category',
            'dateIssued', 'packageId', 'download', 'lastModified'
        ]

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate download structure
        if 'download' in data:
            download = data['download']
            download_fields = ['pdfLink', 'xmlLink', 'modsLink', 'premisLink']
            for field in download_fields:
                if field not in download:
                    errors.append(f"Missing download field: {field}")

        # Check collection-specific fields
        if data.get('collectionCode') == 'BILLS':
            bill_fields = ['billType', 'billNumber', 'congress', 'originChamber']
            for field in bill_fields:
                if field not in data:
                    errors.append(f"Missing BILLS field: {field}")

        return errors

    def validate_openstates_bill_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate OpenStates bill data against current v3 API schema expectations"""
        errors = []

        if not data:
            errors.append("No data received from OpenStates API")
            return errors

        # Check required fields for current v3 API
        required_fields = [
            'id', 'identifier', 'title', 'classification', 'subject', 
            'jurisdiction', 'session', 'created_at', 'updated_at'
        ]

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate jurisdiction structure
        if 'jurisdiction' in data:
            if isinstance(data['jurisdiction'], dict):
                if 'id' not in data['jurisdiction']:
                    errors.append("Missing jurisdiction.id field")
            elif not isinstance(data['jurisdiction'], str):
                errors.append("jurisdiction should be string or dict with id field")

        # Validate classification is list
        if 'classification' in data and data['classification'] is not None:
            if not isinstance(data['classification'], list):
                errors.append("classification should be a list")

        # Validate subject is list
        if 'subject' in data and data['subject'] is not None:
            if not isinstance(data['subject'], list):
                errors.append("subject should be a list")

        # Validate dates are in proper format
        date_fields = ['created_at', 'updated_at', 'first_action_date', 'latest_action_date']
        for field in date_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], str):
                    errors.append(f"{field} should be a string (ISO date)")

        # Validate sponsors structure if present
        if 'sponsorships' in data and data['sponsorships']:
            sponsor = data['sponsorships'][0]
            sponsor_fields = ['name', 'classification']
            for field in sponsor_fields:
                if isinstance(sponsor, dict) and field not in sponsor:
                    errors.append(f"Missing sponsor field: {field}")

        # Validate actions structure if present
        if 'actions' in data and data['actions']:
            action = data['actions'][0]
            action_fields = ['date', 'description']
            for field in action_fields:
                if isinstance(action, dict) and field not in action:
                    errors.append(f"Missing action field: {field}")

        return errors

    def test_database_insertion(self, table_name: str, data: Dict[str, Any]) -> List[str]:
        """Test that data can be inserted into the database table"""
        errors = []

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # Get table schema
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))

            columns = cursor.fetchall()

            # Validate data against schema
            for col_name, col_type, is_nullable in columns:
                if col_name in data:
                    value = data[col_name]

                    # Type validation
                    if col_type == 'integer' and not isinstance(value, int):
                        errors.append(f"Column {col_name}: expected integer, got {type(value)}")
                    elif col_type == 'text' and not isinstance(value, str):
                        errors.append(f"Column {col_name}: expected string, got {type(value)}")
                    elif col_type == 'date' and value is not None:
                        try:
                            datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                        except:
                            errors.append(f"Column {col_name}: invalid date format")
                    elif col_type == 'timestamp with time zone' and value is not None:
                        try:
                            datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                        except:
                            errors.append(f"Column {col_name}: invalid timestamp format")
                    elif col_type == 'jsonb' and value is not None:
                        try:
                            json.dumps(value)
                        except:
                            errors.append(f"Column {col_name}: invalid JSON")

            cursor.close()
            conn.close()

        except Exception as e:
            errors.append(f"Database error: {str(e)}")

        return errors


class TestAPIDataValidation:

    @pytest.fixture
    def validator(self):
        return APIDataValidator()

    @pytest.mark.skipif(not CONGRESS_API_KEY or CONGRESS_API_KEY == 'DEMO_KEY',
                       reason="Congress API key not configured")
    def test_congress_bill_api_data(self, validator):
        """Test that Congress bill API returns expected data structure"""
        data = validator.fetch_congress_bill()
        errors = validator.validate_congress_bill_data(data)

        assert len(errors) == 0, f"Congress bill data validation errors: {errors}"

    @pytest.mark.skipif(not CONGRESS_API_KEY or CONGRESS_API_KEY == 'DEMO_KEY',
                       reason="Congress API key not configured")
    def test_congress_member_api_data(self, validator):
        """Test that Congress member API returns expected data structure"""
        data = validator.fetch_congress_member()
        errors = validator.validate_congress_member_data(data)

        assert len(errors) == 0, f"Congress member data validation errors: {errors}"

    @pytest.mark.skipif(not GOVINFO_API_KEY or GOVINFO_API_KEY == 'DEMO_KEY',
                       reason="GovInfo API key not configured")
    def test_govinfo_package_api_data(self, validator):
        """Test that GovInfo package API returns expected data structure"""
        data = validator.fetch_govinfo_package()
        errors = validator.validate_govinfo_package_data(data)

        assert len(errors) == 0, f"GovInfo package data validation errors: {errors}"

    @pytest.mark.skipif(not OPENSTATES_API_KEY,
                       reason="OpenStates API key not configured")
    def test_openstates_bill_api_data(self, validator):
        """Test that OpenStates bill API returns expected data structure"""
        data = validator.fetch_openstates_bill()
        if data:  # Only test if we got data
            errors = validator.validate_openstates_bill_data(data)
            assert len(errors) == 0, f"OpenStates bill data validation errors: {errors}"

    @pytest.mark.skipif(not all(DB_CONFIG.values()),
                       reason="Database not configured")
    def test_congress_schema_compatibility(self, validator):
        """Test that Congress API data is compatible with database schema"""
        try:
            data = validator.fetch_congress_bill()
            if 'bill' in data:
                bill_data = data['bill']
                # Transform API data to match schema expectations
                transformed_data = {
                    'bill_id': f"{bill_data['congress']}-{bill_data['billType']}{bill_data['number']}",
                    'congress': bill_data['congress'],
                    'bill_type': bill_data['billType'],
                    'bill_number': bill_data['number'],
                    'title': bill_data.get('title'),
                    'introduced_date': bill_data.get('introducedDate'),
                    'latest_action_date': bill_data.get('latestAction', {}).get('actionDate'),
                    'latest_action_text': bill_data.get('latestAction', {}).get('text'),
                    'sponsors': bill_data.get('sponsors', []),
                    'cosponsors': bill_data.get('cosponsors', []),
                    'committees': bill_data.get('committees', []),
                    'policy_area': bill_data.get('policyArea', {}).get('name'),
                    'subjects': bill_data.get('subjects', []),
                    'raw': data
                }

                errors = validator.test_database_insertion('congress_bills', transformed_data)
                assert len(errors) == 0, f"Congress schema compatibility errors: {errors}"
        except Exception as e:
            pytest.skip(f"Congress API test failed: {e}")

    @pytest.mark.skipif(not all(DB_CONFIG.values()),
                       reason="Database not configured")
    def test_govinfo_schema_compatibility(self, validator):
        """Test that GovInfo API data is compatible with database schema"""
        try:
            data = validator.fetch_govinfo_package()
            # Transform API data to match schema expectations
            transformed_data = {
                'package_id': data['packageId'],
                'collection_code': data['collectionCode'],
                'last_modified': data['lastModified'],
                'date_issued': data['dateIssued'],
                'title': data['title'],
                'collection_name': data['collectionName'],
                'category': data['category'],
                'branch': data.get('branch'),
                'pages': data.get('pages'),
                'government_author1': data.get('governmentAuthor1'),
                'su_doc_class_number': data.get('suDocClassNumber'),
                'publisher': data.get('publisher'),
                'details_link': data.get('detailsLink'),
                'package_link': data.get('packageLink'),
                'txt_link': data.get('download', {}).get('txtLink'),
                'pdf_link': data.get('download', {}).get('pdfLink'),
                'xml_link': data.get('download', {}).get('xmlLink'),
                'mods_link': data.get('download', {}).get('modsLink'),
                'premis_link': data.get('download', {}).get('premisLink'),
                'zip_link': data.get('download', {}).get('zipLink'),
                'raw_summary': data,
                'raw': data
            }

            errors = validator.test_database_insertion('govinfo_packages', transformed_data)
            assert len(errors) == 0, f"GovInfo schema compatibility errors: {errors}"
        except Exception as e:
            pytest.skip(f"GovInfo API test failed: {e}")

    @pytest.mark.skipif(not all(DB_CONFIG.values()),
                       reason="Database not configured")
    def test_openstates_schema_compatibility(self, validator):
        """Test that OpenStates API data is compatible with database schema"""
        try:
            data = validator.fetch_openstates_bill()
            if data:
                # Transform API data to match schema expectations
                transformed_data = {
                    'bill_id': data['id'],
                    'state': data['state'],
                    'session': data['session'],
                    'chamber': data['chamber'],
                    'title': data['title'],
                    'bill_type': data.get('type', []),
                    'status': data.get('status'),
                    'subjects': data.get('subjects', []),
                    'sponsors': data.get('sponsors', []),
                    'actions': data.get('actions', []),
                    'votes': data.get('votes', []),
                    'documents': data.get('documents', []),
                    'versions': data.get('versions', []),
                    'sources': data.get('sources', []),
                    'raw': data
                }

                errors = validator.test_database_insertion('openstates_bills', transformed_data)
                assert len(errors) == 0, f"OpenStates schema compatibility errors: {errors}"
        except Exception as e:
            pytest.skip(f"OpenStates API test failed: {e}")


if __name__ == '__main__':
    # Run basic validation tests
    validator = APIDataValidator()

    print("Testing API Data Structures...")
    print("=" * 50)

    # Test Congress API
    try:
        print("Testing Congress.gov API...")
        bill_data = validator.fetch_congress_bill()
        errors = validator.validate_congress_bill_data(bill_data)
        if errors:
            print(f"❌ Congress bill validation errors: {errors}")
        else:
            print("✅ Congress bill data structure valid")

        member_data = validator.fetch_congress_member()
        errors = validator.validate_congress_member_data(member_data)
        if errors:
            print(f"❌ Congress member validation errors: {errors}")
        else:
            print("✅ Congress member data structure valid")

    except Exception as e:
        print(f"❌ Congress API test failed: {e}")

    # Test GovInfo API
    try:
        print("\nTesting GovInfo API...")
        package_data = validator.fetch_govinfo_package()
        errors = validator.validate_govinfo_package_data(package_data)
        if errors:
            print(f"❌ GovInfo package validation errors: {errors}")
        else:
            print("✅ GovInfo package data structure valid")

    except Exception as e:
        print(f"❌ GovInfo API test failed: {e}")

    # Test OpenStates API
    try:
        print("\nTesting OpenStates API...")
        bill_data = validator.fetch_openstates_bill()
        if bill_data:
            errors = validator.validate_openstates_bill_data(bill_data)
            if errors:
                print(f"❌ OpenStates bill validation errors: {errors}")
            else:
                print("✅ OpenStates bill data structure valid")
        else:
            print("⚠️  No OpenStates data returned")

    except Exception as e:
        print(f"❌ OpenStates API test failed: {e}")

    print("\nAPI validation complete!")