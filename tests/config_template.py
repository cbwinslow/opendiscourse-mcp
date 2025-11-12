# API Data Validation Configuration
# Copy this file to config.py and fill in your API keys

# API Keys (get from respective services)
CONGRESS_API_KEY = "DEMO_KEY"  # Get from https://api.congress.gov/sign-up/
GOVINFO_API_KEY = "DEMO_KEY"   # Get from https://www.govinfo.gov/api-signup
OPENSTATES_API_KEY = ""        # Optional, get from https://openstates.org/api/

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'opendiscourse',
    'user': 'postgres',
    'password': ''
}

# Test Configuration
TEST_CONFIG = {
    'congress': {
        'congress': 118,
        'bill_type': 'hr',
        'bill_number': 1,
        'bioguide_id': 'B000944',  # Sherrod Brown
        'committee_code': 'HSAP'
    },
    'govinfo': {
        'package_id': 'BILLS-118hr1enr',
        'collection_code': 'BILLS'
    },
    'openstates': {
        'state': 'ca',
        'bill_id': 'AB 1'
    }
}