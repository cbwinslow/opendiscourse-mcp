'use client'

import { useState } from 'react'

// Function documentation data
const functionDocs = {
  congress: {
    search_bills: {
      name: "search_bills",
      description: "Search for bills in Congress.gov API",
      parameters: {
        congress: { type: "Optional[int]", description: "Congress number to search in", required: false },
        billType: { type: "Optional[str]", description: "Type of bill (hr, s, hjres, etc.)", required: false },
        page: { type: "int", description: "Page number for pagination", required: false, default: 1 }
      },
      returns: {
        type: "dict",
        description: "Congress API response containing bills data",
        structure: "Standard Congress.gov API bill search response format"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Search for House bills in 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "search_bills",
  "args": {"congress": 118, "billType": "hr"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with user_id, site, function, and args",
        output: "JSON response from Congress.gov API"
      }
    },
    get_bill: {
      name: "get_bill",
      description: "Get detailed information about a specific bill",
      parameters: {
        congress: { type: "int", description: "Congress number", required: true },
        billType: { type: "str", description: "Type of bill (hr, s, hjres, etc.)", required: true },
        billNumber: { type: "str", description: "Bill number", required: true }
      },
      returns: {
        type: "dict",
        description: "Complete bill details from Congress.gov",
        structure: "Full Congress.gov bill object with actions, sponsors, text, etc."
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Get details for H.R. 1 from 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "get_bill",
  "args": {"congress": 118, "billType": "hr", "billNumber": "1"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with congress (int), billType (str), billNumber (str)",
        output: "JSON bill object from Congress.gov API"
      }
    },
    get_bill_actions: {
      name: "get_bill_actions",
      description: "Get legislative actions for a specific bill",
      parameters: {
        congress: { type: "int", description: "Congress number", required: true },
        billType: { type: "str", description: "Type of bill", required: true },
        billNumber: { type: "str", description: "Bill number", required: true }
      },
      returns: {
        type: "dict",
        description: "List of all actions taken on the bill",
        structure: "Congress.gov actions API response"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Get actions for S. 1 from 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "get_bill_actions",
  "args": {"congress": 118, "billType": "s", "billNumber": "1"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with congress, billType, billNumber",
        output: "JSON actions array from Congress.gov"
      }
    },
    get_bill_text: {
      name: "get_bill_text",
      description: "Get the text content of a bill",
      parameters: {
        congress: { type: "int", description: "Congress number", required: true },
        billType: { type: "str", description: "Type of bill", required: true },
        billNumber: { type: "str", description: "Bill number", required: true }
      },
      returns: {
        type: "dict",
        description: "Bill text in various formats",
        structure: "Congress.gov text API response with HTML, PDF, XML formats"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Get text for H.R. 1234",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "get_bill_text",
  "args": {"congress": 118, "billType": "hr", "billNumber": "1234"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with congress, billType, billNumber",
        output: "JSON with text content in multiple formats"
      }
    },
    list_members: {
      name: "list_members",
      description: "List congressional members",
      parameters: {
        congress: { type: "Optional[int]", description: "Congress number", required: false },
        chamber: { type: "Optional[str]", description: "House or Senate", required: false }
      },
      returns: {
        type: "dict",
        description: "List of congressional members",
        structure: "Congress.gov members API response"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "List all members of 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "list_members",
  "args": {"congress": 118}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional congress and chamber filters",
        output: "JSON members array"
      }
    },
    get_member: {
      name: "get_member",
      description: "Get detailed information about a specific member",
      parameters: {
        bioguideId: { type: "str", description: "Member's bioguide ID", required: true }
      },
      returns: {
        type: "dict",
        description: "Complete member profile",
        structure: "Congress.gov member detail response"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Get member details for bioguide ID S001227",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "get_member",
  "args": {"bioguideId": "S001227"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with bioguideId string",
        output: "JSON member object"
      }
    },
    bulk_download_collection: {
      name: "bulk_download_collection",
      description: "Get bulk download URLs for collections",
      parameters: {
        collection: { type: "str", description: "Collection name", required: true },
        year: { type: "Optional[int]", description: "Year for collection", required: false }
      },
      returns: {
        type: "dict",
        description: "Bulk download information",
        structure: "URLs and metadata for bulk data access"
      },
      requirements: ["Valid Congress.gov API key registered"],
      examples: [
        {
          description: "Get bulk download info for bills collection",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "bulk_download_collection",
  "args": {"collection": "BILLS"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with collection name and optional year",
        output: "JSON with bulk download URLs and status"
      }
    },
    query_congress_bills: {
      name: "query_congress_bills",
      description: "Query Congress bills from the database",
      parameters: {
        congress: { type: "Optional[int]", description: "Congress number filter", required: false },
        bill_type: { type: "Optional[str]", description: "Bill type filter", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Database query results",
        structure: "{count: int, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Query House bills from 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "query_congress_bills",
  "args": {"congress": 118, "bill_type": "hr", "limit": 50}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional congress, bill_type, limit",
        output: "JSON with count, data array, and columns list",
        sqlTable: "congress_bills (id text PK, congress smallint, bill_type text, bill_number int, title text, latest_action_date date, latest_action_description text, subjects text[], sponsors jsonb, raw jsonb)"
      }
    },
    analyze_bill_sponsors_congress: {
      name: "analyze_bill_sponsors_congress",
      description: "Analyze bill sponsorship patterns in Congress data",
      parameters: {
        congress: { type: "Optional[int]", description: "Congress number filter", required: false },
        bill_type: { type: "Optional[str]", description: "Bill type filter", required: false }
      },
      returns: {
        type: "dict",
        description: "Sponsorship analysis results",
        structure: "{total_cosponsored_bills: int, unique_sponsors: int, top_sponsors: dict, sample_data: list}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Analyze sponsors in 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "analyze_bill_sponsors_congress",
  "args": {"congress": 118}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional congress and bill_type filters",
        output: "JSON with sponsorship statistics and rankings",
        sqlTable: "congress_bills (sponsors jsonb field contains sponsor information)"
      }
    },
    get_congressional_trends: {
      name: "get_congressional_trends",
      description: "Analyze congressional activity trends by congress number",
      parameters: {
        start_congress: { type: "Optional[int]", description: "Starting congress number", required: false },
        end_congress: { type: "Optional[int]", description: "Ending congress number", required: false }
      },
      returns: {
        type: "dict",
        description: "Congressional trends analysis",
        structure: "{trends_by_type: dict, summary_stats: dict, bill_type_breakdown: dict}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Get trends for congresses 115-118",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "get_congressional_trends",
  "args": {"start_congress": 115, "end_congress": 118}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional start_congress and end_congress",
        output: "JSON with trend data by congress and bill type",
        sqlTable: "congress_bills (congress smallint, bill_type text, subjects text[])"
      }
    },
    search_congress_bills_advanced: {
      name: "search_congress_bills_advanced",
      description: "Advanced search for Congress bills with multiple criteria",
      parameters: {
        keywords: { type: "Optional[List[str]]", description: "Keywords to search in titles", required: false },
        sponsors: { type: "Optional[List[str]]", description: "Sponsor names to search for", required: false },
        congress: { type: "Optional[int]", description: "Congress number filter", required: false },
        bill_type: { type: "Optional[str]", description: "Bill type filter", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Advanced search results",
        structure: "{count: int, search_criteria: dict, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Search for infrastructure bills sponsored by specific members",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "search_congress_bills_advanced",
  "args": {
    "keywords": ["infrastructure", "transportation"],
    "sponsors": ["Smith", "Johnson"],
    "congress": 118,
    "limit": 25
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional keywords list, sponsors list, congress, bill_type, limit",
        output: "JSON with search results and criteria used",
        sqlTable: "congress_bills (title text, sponsors jsonb, congress smallint, bill_type text)"
      }
    },
    analyze_member_activity: {
      name: "analyze_member_activity",
      description: "Analyze legislative activity for congressional members",
      parameters: {
        bioguide_id: { type: "Optional[str]", description: "Specific member ID to analyze", required: false },
        congress: { type: "Optional[int]", description: "Congress number filter", required: false }
      },
      returns: {
        type: "dict",
        description: "Member activity analysis",
        structure: "{member_info: dict, sponsored_bills_count: int, sponsored_bills: list, activity_summary: dict}"
      },
      requirements: ["PostgreSQL database with congress_members and congress_bills tables populated"],
      examples: [
        {
          description: "Analyze activity for member S001227 in 118th Congress",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "analyze_member_activity",
  "args": {"bioguide_id": "S001227", "congress": 118}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional bioguide_id and congress",
        output: "JSON with member info and sponsored bills analysis",
        sqlTable: "congress_members (bioguide_id text PK, first_name text, last_name text, party text, state text, district text, raw jsonb), congress_bills (sponsors jsonb)"
      }
    },
    compare_congresses: {
      name: "compare_congresses",
      description: "Compare legislative activity between two congresses",
      parameters: {
        congress1: { type: "int", description: "First congress number", required: true },
        congress2: { type: "int", description: "Second congress number", required: true }
      },
      returns: {
        type: "dict",
        description: "Congress comparison results",
        structure: "{congress_comparison: dict, bill_type_distribution: dict, congress1: int, congress2: int}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Compare 117th and 118th Congresses",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "compare_congresses",
  "args": {"congress1": 117, "congress2": 118}
}`
        }
      ],
      dataTypes: {
        input: "JSON with congress1 and congress2 integers",
        output: "JSON with comparison metrics and bill type distributions",
        sqlTable: "congress_bills (congress smallint, bill_type text, subjects text[])"
      }
    },
    export_congress_data: {
      name: "export_congress_data",
      description: "Export Congress bills data with filtering",
      parameters: {
        congress: { type: "Optional[int]", description: "Congress number filter", required: false },
        bill_type: { type: "Optional[str]", description: "Bill type filter", required: false },
        format: { type: "str", description: "Export format", required: false, default: "csv" },
        output_path: { type: "Optional[str]", description: "Custom output path", required: false }
      },
      returns: {
        type: "dict",
        description: "Export status and details",
        structure: "{status: str, file: str, format: str, records: int, filters: dict}"
      },
      requirements: ["PostgreSQL database with congress_bills table populated"],
      examples: [
        {
          description: "Export 118th Congress House bills as JSON",
          code: `{
  "user_id": "alice",
  "site": "congress",
  "function": "export_congress_data",
  "args": {
    "congress": 118,
    "bill_type": "hr",
    "format": "json",
    "output_path": "congress_118_hr_bills.json"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional congress, bill_type, format, output_path",
        output: "JSON with export status and file information",
        sqlTable: "congress_bills (all columns exported)",
        supportedFormats: "csv, json, parquet"
      }
    }
  },
  openstates: {
    search_bills: {
      name: "search_bills",
      description: "Search for bills in OpenStates API",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction code (e.g., 'nc' for North Carolina)", required: false },
        q: { type: "Optional[str]", description: "Search query", required: false },
        page: { type: "int", description: "Page number", required: false, default: 1 },
        per_page: { type: "int", description: "Results per page", required: false, default: 50 }
      },
      returns: {
        type: "dict",
        description: "OpenStates API search results",
        structure: "Standard OpenStates bills search response"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Search for bills in North Carolina",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "search_bills",
  "args": {"jurisdiction": "nc", "q": "education"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, q, page, per_page",
        output: "JSON response from OpenStates API"
      }
    },
    get_bill: {
      name: "get_bill",
      description: "Get detailed information about a specific bill",
      parameters: {
        openstates_bill_id: { type: "str", description: "OpenStates bill ID", required: true }
      },
      returns: {
        type: "dict",
        description: "Complete bill details from OpenStates",
        structure: "Full OpenStates bill object with sponsors, actions, versions, etc."
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Get bill details for a specific OpenStates bill ID",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_bill",
  "args": {"openstates_bill_id": "ocd-bill/12345678-1234-1234-1234-123456789012"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with openstates_bill_id string",
        output: "JSON bill object from OpenStates API"
      }
    },
    search_people: {
      name: "search_people",
      description: "Search for people (legislators) in OpenStates",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction code", required: false },
        name: { type: "Optional[str]", description: "Name to search for", required: false },
        page: { type: "int", description: "Page number", required: false, default: 1 },
        per_page: { type: "int", description: "Results per page", required: false, default: 50 }
      },
      returns: {
        type: "dict",
        description: "People search results",
        structure: "OpenStates people search response"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Search for legislators named 'Smith' in North Carolina",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "search_people",
  "args": {"jurisdiction": "nc", "name": "Smith"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, name, page, per_page",
        output: "JSON people array from OpenStates"
      }
    },
    get_person: {
      name: "get_person",
      description: "Get detailed information about a specific person",
      parameters: {
        person_id: { type: "str", description: "OpenStates person ID", required: true }
      },
      returns: {
        type: "dict",
        description: "Complete person profile",
        structure: "OpenStates person detail response"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Get person details for a specific ID",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_person",
  "args": {"person_id": "ocd-person/12345678-1234-1234-1234-123456789012"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with person_id string",
        output: "JSON person object from OpenStates"
      }
    },
    search_events: {
      name: "search_events",
      description: "Search for legislative events in OpenStates",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction code", required: false },
        before: { type: "Optional[str]", description: "Events before date (ISO format)", required: false },
        after: { type: "Optional[str]", description: "Events after date (ISO format)", required: false },
        page: { type: "int", description: "Page number", required: false, default: 1 },
        per_page: { type: "int", description: "Results per page", required: false, default: 20 }
      },
      returns: {
        type: "dict",
        description: "Events search results",
        structure: "OpenStates events search response"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Search for events in North Carolina after 2023-01-01",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "search_events",
  "args": {"jurisdiction": "nc", "after": "2023-01-01T00:00:00Z"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, before, after dates, page, per_page",
        output: "JSON events array from OpenStates"
      }
    },
    get_event: {
      name: "get_event",
      description: "Get detailed information about a specific event",
      parameters: {
        event_id: { type: "str", description: "OpenStates event ID", required: true }
      },
      returns: {
        type: "dict",
        description: "Complete event details",
        structure: "OpenStates event detail response"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Get event details for a specific ID",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_event",
  "args": {"event_id": "ocd-event/12345678-1234-1234-1234-123456789012"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with event_id string",
        output: "JSON event object from OpenStates"
      }
    },
    get_openapi_schema: {
      name: "get_openapi_schema",
      description: "Get the OpenAPI schema for OpenStates API",
      parameters: {},
      returns: {
        type: "dict",
        description: "OpenAPI schema document",
        structure: "Complete OpenAPI specification for OpenStates API"
      },
      requirements: ["Valid OpenStates API key registered"],
      examples: [
        {
          description: "Get the OpenAPI schema",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_openapi_schema",
  "args": {}
}`
        }
      ],
      dataTypes: {
        input: "JSON with empty args",
        output: "JSON OpenAPI schema document"
      }
    },
    query_bills: {
      name: "query_bills",
      description: "Query bills from the database",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        session: { type: "Optional[str]", description: "Session filter", required: false },
        classification: { type: "Optional[List[str]]", description: "Classification filter", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Database query results",
        structure: "{count: int, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Query bills from North Carolina 2023 session",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "query_bills",
  "args": {"jurisdiction": "nc", "session": "2023", "limit": 50}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, session, classification list, limit",
        output: "JSON with count, data array, and columns list",
        sqlTable: "openstates_bills (id text PK, session text, jurisdiction text, identifier text, title text, classification text[], subjects text[], created_at timestamptz, updated_at timestamptz, first_action_date date, latest_action_date date, latest_action_description text, openstates_url text, raw jsonb)"
      }
    },
    export_bills: {
      name: "export_bills",
      description: "Export bills data to file",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        format: { type: "str", description: "Export format", required: false, default: "csv" },
        output_path: { type: "Optional[str]", description: "Custom output path", required: false }
      },
      returns: {
        type: "dict",
        description: "Export status",
        structure: "{status: str, file: str, format: str, records: int}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Export North Carolina bills as JSON",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "export_bills",
  "args": {"jurisdiction": "nc", "format": "json"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, format, output_path",
        output: "JSON with export status and file information",
        sqlTable: "openstates_bills (all columns exported)",
        supportedFormats: "csv, json, parquet"
      }
    },
    analyze_bill_sponsors: {
      name: "analyze_bill_sponsors",
      description: "Analyze bill sponsorship patterns",
      parameters: {
        bill_id: { type: "Optional[str]", description: "Specific bill ID to analyze", required: false },
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        limit: { type: "int", description: "Maximum bills to analyze", required: false, default: 50 }
      },
      returns: {
        type: "dict",
        description: "Sponsorship analysis results",
        structure: "{total_bills: int, unique_sponsors: int, top_sponsors: dict, sample_data: list}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Analyze sponsors in North Carolina bills",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "analyze_bill_sponsors",
  "args": {"jurisdiction": "nc", "limit": 100}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional bill_id, jurisdiction, limit",
        output: "JSON with sponsorship statistics and rankings",
        sqlTable: "openstates_bills (sponsors jsonb field contains sponsor information)"
      }
    },
    find_related_bills: {
      name: "find_related_bills",
      description: "Find bills related by sponsors, subjects, or keywords",
      parameters: {
        bill_id: { type: "str", description: "Original bill ID", required: true },
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        similarity_threshold: { type: "float", description: "Similarity threshold", required: false, default: 0.3 }
      },
      returns: {
        type: "dict",
        description: "Related bills analysis",
        structure: "{related_bills_count: int, related_bills: list, search_criteria: dict}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Find bills related to a specific bill by sponsors",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "find_related_bills",
  "args": {"bill_id": "ocd-bill/12345678-1234-1234-1234-123456789012", "jurisdiction": "nc"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with bill_id, optional jurisdiction, similarity_threshold",
        output: "JSON with related bills list and search criteria",
        sqlTable: "openstates_bills (id, sponsors jsonb, subjects text[], classification text[], title text)"
      }
    },
    get_legislative_trends: {
      name: "get_legislative_trends",
      description: "Analyze legislative trends over time",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        start_date: { type: "Optional[str]", description: "Start date (ISO format)", required: false },
        end_date: { type: "Optional[str]", description: "End date (ISO format)", required: false },
        group_by: { type: "str", description: "Time grouping", required: false, default: "month" }
      },
      returns: {
        type: "dict",
        description: "Legislative trends analysis",
        structure: "{trends: list, summary: dict, grouping: str}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Get monthly bill trends for North Carolina in 2023",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_legislative_trends",
  "args": {
    "jurisdiction": "nc",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "group_by": "month"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction, start_date, end_date, group_by",
        output: "JSON with trend data and summary statistics",
        sqlTable: "openstates_bills (created_at timestamptz, jurisdiction text, classification text[], subjects text[])"
      }
    },
    search_bills_advanced: {
      name: "search_bills_advanced",
      description: "Advanced bill search with multiple criteria",
      parameters: {
        keywords: { type: "Optional[List[str]]", description: "Keywords to search", required: false },
        sponsors: { type: "Optional[List[str]]", description: "Sponsor names", required: false },
        classification: { type: "Optional[List[str]]", description: "Classification filter", required: false },
        status: { type: "Optional[str]", description: "Status filter", required: false },
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        date_from: { type: "Optional[str]", description: "Start date", required: false },
        date_to: { type: "Optional[str]", description: "End date", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Advanced search results",
        structure: "{count: int, search_criteria: dict, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Search for education bills sponsored by Democrats in North Carolina",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "search_bills_advanced",
  "args": {
    "keywords": ["education", "school"],
    "sponsors": ["Democratic"],
    "jurisdiction": "nc",
    "date_from": "2023-01-01",
    "limit": 50
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional keywords, sponsors, classification, status, jurisdiction, date_from, date_to, limit",
        output: "JSON with search results and criteria used",
        sqlTable: "openstates_bills (title text, sponsors jsonb, classification text[], jurisdiction text, created_at timestamptz)"
      }
    },
    get_bill_statistics: {
      name: "get_bill_statistics",
      description: "Get statistical overview of bills",
      parameters: {
        jurisdiction: { type: "Optional[str]", description: "Jurisdiction filter", required: false },
        classification: { type: "Optional[List[str]]", description: "Classification filter", required: false }
      },
      returns: {
        type: "dict",
        description: "Bill statistics summary",
        structure: "{summary: dict, top_classifications: dict}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Get bill statistics for North Carolina",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "get_bill_statistics",
  "args": {"jurisdiction": "nc"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional jurisdiction and classification filters",
        output: "JSON with statistical summary and classification breakdown",
        sqlTable: "openstates_bills (jurisdiction text, classification text[], subjects text[], sponsors jsonb)"
      }
    },
    export_filtered_data: {
      name: "export_filtered_data",
      description: "Export filtered data with advanced options",
      parameters: {
        table: { type: "str", description: "Table name", required: false, default: "openstates_bills" },
        filters: { type: "Optional[Dict[str, Any]]", description: "Filter criteria", required: false },
        format: { type: "str", description: "Export format", required: false, default: "csv" },
        output_path: { type: "Optional[str]", description: "Custom output path", required: false }
      },
      returns: {
        type: "dict",
        description: "Export status and details",
        structure: "{status: str, table: str, filters_applied: dict, records_exported: int, file: str, format: str, columns: list}"
      },
      requirements: ["PostgreSQL database with specified table populated"],
      examples: [
        {
          description: "Export filtered bills data",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "export_filtered_data",
  "args": {
    "table": "openstates_bills",
    "filters": {"jurisdiction": "nc", "classification": ["bill"]},
    "format": "parquet",
    "output_path": "nc_bills_filtered.parquet"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with table, optional filters dict, format, output_path",
        output: "JSON with export status and file information",
        sqlTable: "openstates_bills, openstates_people, openstates_events (any table with filters applied)",
        supportedFormats: "csv, json, parquet"
      }
    },
    compare_legislatures: {
      name: "compare_legislatures",
      description: "Compare legislative activity between jurisdictions",
      parameters: {
        jurisdiction1: { type: "str", description: "First jurisdiction", required: true },
        jurisdiction2: { type: "str", description: "Second jurisdiction", required: true },
        metric: { type: "str", description: "Comparison metric", required: false, default: "bill_count" }
      },
      returns: {
        type: "dict",
        description: "Jurisdiction comparison results",
        structure: "{comparison: dict, differences: dict, jurisdiction1: str, jurisdiction2: str}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Compare North Carolina and California legislatures",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "compare_legislatures",
  "args": {"jurisdiction1": "nc", "jurisdiction2": "ca"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with jurisdiction1, jurisdiction2, optional metric",
        output: "JSON with comparison metrics and differences",
        sqlTable: "openstates_bills (jurisdiction text, classification text[], subjects text[], sponsors jsonb)"
      }
    },
    generate_bill_report: {
      name: "generate_bill_report",
      description: "Generate a comprehensive report for a specific bill",
      parameters: {
        bill_id: { type: "str", description: "Bill ID to report on", required: true }
      },
      returns: {
        type: "dict",
        description: "Comprehensive bill report",
        structure: "{bill_id: str, bill_data: dict, sponsor_analysis: dict, subject_analysis: dict, summary_report: str}"
      },
      requirements: ["PostgreSQL database with openstates_bills table populated"],
      examples: [
        {
          description: "Generate a detailed report for a specific bill",
          code: `{
  "user_id": "alice",
  "site": "openstates",
  "function": "generate_bill_report",
  "args": {"bill_id": "ocd-bill/12345678-1234-1234-1234-123456789012"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with bill_id string",
        output: "JSON with complete bill analysis and formatted report",
        sqlTable: "openstates_bills (all columns used for comprehensive analysis)"
      }
    }
  },
  govinfo: {
    list_collections: {
      name: "list_collections",
      description: "List available GovInfo collections",
      parameters: {},
      returns: {
        type: "dict",
        description: "Available collections",
        structure: "GovInfo collections API response"
      },
      requirements: ["Valid GovInfo API key registered"],
      examples: [
        {
          description: "List all available GovInfo collections",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "list_collections",
  "args": {}
}`
        }
      ],
      dataTypes: {
        input: "JSON with empty args",
        output: "JSON collections list from GovInfo API"
      }
    },
    bulk_download: {
      name: "bulk_download",
      description: "Get bulk download URLs for collections",
      parameters: {
        collection: { type: "str", description: "Collection code", required: true },
        year: { type: "Optional[int]", description: "Year for collection", required: false }
      },
      returns: {
        type: "dict",
        description: "Bulk download information",
        structure: "{bulk_url: str, files: list}"
      },
      requirements: ["Valid GovInfo API key registered"],
      examples: [
        {
          description: "Get bulk download URLs for BILLS collection",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "bulk_download",
  "args": {"collection": "BILLS", "year": 2023}
}`
        }
      ],
      dataTypes: {
        input: "JSON with collection and optional year",
        output: "JSON with bulk URLs and file listings"
      }
    },
    fetch_bulk_file: {
      name: "fetch_bulk_file",
      description: "Download a bulk file from GovInfo",
      parameters: {
        url: { type: "str", description: "File URL to download", required: true },
        out_path: { type: "str", description: "Output path", required: true },
        chunk_size: { type: "int", description: "Download chunk size", required: false, default: 65536 },
        resume: { type: "bool", description: "Resume partial downloads", required: false, default: true }
      },
      returns: {
        type: "dict",
        description: "Download status",
        structure: "Download utility response"
      },
      requirements: ["Valid GovInfo API key registered", "Write access to output directory"],
      examples: [
        {
          description: "Download a bulk XML file",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "fetch_bulk_file",
  "args": {
    "url": "https://www.govinfo.gov/bulkdata/BILLS/118/1/BILLS-118-1.xml",
    "out_path": "./downloads/bills_118_1.xml"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with url, out_path, optional chunk_size, resume",
        output: "JSON with download status and file information"
      }
    },
    ingest_xml_to_df: {
      name: "ingest_xml_to_df",
      description: "Parse XML file to DataFrame",
      parameters: {
        xml_path: { type: "str", description: "Path to XML file", required: true },
        record_xpath: { type: "str", description: "XPath for records", required: false, default: ".//record" }
      },
      returns: {
        type: "DataFrame",
        description: "Parsed XML data",
        structure: "Pandas DataFrame with XML data"
      },
      requirements: ["XML file exists at specified path"],
      examples: [
        {
          description: "Parse a GovInfo XML file",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "ingest_xml_to_df",
  "args": {
    "xml_path": "./downloads/bills_118_1.xml",
    "record_xpath": ".//bill"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with xml_path and optional record_xpath",
        output: "Pandas DataFrame with parsed XML data"
      }
    },
    query_govinfo_documents: {
      name: "query_govinfo_documents",
      description: "Query GovInfo documents from database",
      parameters: {
        collection: { type: "Optional[str]", description: "Collection filter", required: false },
        start_date: { type: "Optional[str]", description: "Start date filter", required: false },
        end_date: { type: "Optional[str]", description: "End date filter", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Database query results",
        structure: "{count: int, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Query BILLS collection documents from 2023",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "query_govinfo_documents",
  "args": {
    "collection": "BILLS",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "limit": 50
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional collection, start_date, end_date, limit",
        output: "JSON with count, data array, and columns list",
        sqlTable: "govinfo_documents (id text PK, collection text, date date, title text, url text, metadata jsonb, raw jsonb)"
      }
    },
    analyze_document_collections: {
      name: "analyze_document_collections",
      description: "Analyze document distribution across collections",
      parameters: {},
      returns: {
        type: "dict",
        description: "Collection analysis results",
        structure: "{collection_analysis: list, summary: dict}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Analyze document distribution across all collections",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "analyze_document_collections",
  "args": {}
}`
        }
      ],
      dataTypes: {
        input: "JSON with empty args",
        output: "JSON with collection statistics and rankings",
        sqlTable: "govinfo_documents (collection text, date date, title text)"
      }
    },
    get_document_trends: {
      name: "get_document_trends",
      description: "Analyze document publication trends over time",
      parameters: {
        collection: { type: "Optional[str]", description: "Collection filter", required: false },
        group_by: { type: "str", description: "Time grouping", required: false, default: "month" }
      },
      returns: {
        type: "dict",
        description: "Document trends analysis",
        structure: "{trends: list, summary: dict, grouping: str, collection_filter: str}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Get monthly publication trends for BILLS collection",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "get_document_trends",
  "args": {"collection": "BILLS", "group_by": "quarter"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional collection and group_by",
        output: "JSON with trend data and summary statistics",
        sqlTable: "govinfo_documents (date date, collection text)"
      }
    },
    search_documents_advanced: {
      name: "search_documents_advanced",
      description: "Advanced search for GovInfo documents",
      parameters: {
        keywords: { type: "Optional[List[str]]", description: "Keywords to search in titles", required: false },
        collection: { type: "Optional[str]", description: "Collection filter", required: false },
        start_date: { type: "Optional[str]", description: "Start date filter", required: false },
        end_date: { type: "Optional[str]", description: "End date filter", required: false },
        limit: { type: "int", description: "Maximum results", required: false, default: 100 }
      },
      returns: {
        type: "dict",
        description: "Advanced search results",
        structure: "{count: int, search_criteria: dict, data: list, columns: list}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Search for executive orders in the Federal Register",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "search_documents_advanced",
  "args": {
    "keywords": ["executive", "order"],
    "collection": "FR",
    "start_date": "2023-01-01",
    "limit": 50
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional keywords list, collection, start_date, end_date, limit",
        output: "JSON with search results and criteria used",
        sqlTable: "govinfo_documents (title text, collection text, date date)"
      }
    },
    analyze_document_metadata: {
      name: "analyze_document_metadata",
      description: "Analyze metadata patterns in GovInfo documents",
      parameters: {
        collection: { type: "Optional[str]", description: "Collection filter", required: false }
      },
      returns: {
        type: "dict",
        description: "Metadata analysis results",
        structure: "{metadata_analysis: list, title_word_frequency: dict, collection_filter: str, titles_analyzed: int}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Analyze metadata patterns in BILLS collection",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "analyze_document_metadata",
  "args": {"collection": "BILLS"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional collection filter",
        output: "JSON with metadata statistics and word frequency analysis",
        sqlTable: "govinfo_documents (collection text, title text, metadata jsonb)"
      }
    },
    compare_collections: {
      name: "compare_collections",
      description: "Compare document characteristics between two GovInfo collections",
      parameters: {
        collection1: { type: "str", description: "First collection code", required: true },
        collection2: { type: "str", description: "Second collection code", required: true }
      },
      returns: {
        type: "dict",
        description: "Collection comparison results",
        structure: "{collection_comparison: dict, differences: dict, collection1: str, collection2: str}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Compare BILLS and PLAW collections",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "compare_collections",
  "args": {"collection1": "BILLS", "collection2": "PLAW"}
}`
        }
      ],
      dataTypes: {
        input: "JSON with collection1 and collection2 strings",
        output: "JSON with comparison metrics and differences",
        sqlTable: "govinfo_documents (collection text, date date, title text, metadata jsonb)"
      }
    },
    export_govinfo_data: {
      name: "export_govinfo_data",
      description: "Export GovInfo documents data with filtering",
      parameters: {
        collection: { type: "Optional[str]", description: "Collection filter", required: false },
        start_date: { type: "Optional[str]", description: "Start date filter", required: false },
        end_date: { type: "Optional[str]", description: "End date filter", required: false },
        format: { type: "str", description: "Export format", required: false, default: "csv" },
        output_path: { type: "Optional[str]", description: "Custom output path", required: false }
      },
      returns: {
        type: "dict",
        description: "Export status and details",
        structure: "{status: str, file: str, format: str, records: int, filters: dict}"
      },
      requirements: ["PostgreSQL database with govinfo_documents table populated"],
      examples: [
        {
          description: "Export BILLS collection documents as Parquet",
          code: `{
  "user_id": "alice",
  "site": "govinfo",
  "function": "export_govinfo_data",
  "args": {
    "collection": "BILLS",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "format": "parquet"
  }
}`
        }
      ],
      dataTypes: {
        input: "JSON with optional collection, start_date, end_date, format, output_path",
        output: "JSON with export status and file information",
        sqlTable: "govinfo_documents (all columns exported)",
        supportedFormats: "csv, json, parquet"
      }
    }
  }
}

// Available sites and their functions
const availableSites = {
  congress: [
    "search_bills", "get_bill", "get_bill_actions", "get_bill_text",
    "list_members", "get_member", "bulk_download_collection",
    "query_congress_bills", "analyze_bill_sponsors_congress",
    "get_congressional_trends", "search_congress_bills_advanced",
    "analyze_member_activity", "compare_congresses", "export_congress_data"
  ],
  openstates: [
    "search_bills", "get_bill", "search_people", "get_person",
    "search_events", "get_event", "get_openapi_schema",
    "query_bills", "export_bills", "analyze_bill_sponsors",
    "find_related_bills", "get_legislative_trends", "search_bills_advanced",
    "get_bill_statistics", "export_filtered_data", "compare_legislatures",
    "generate_bill_report"
  ],
  govinfo: [
    "list_collections", "bulk_download", "fetch_bulk_file", "ingest_xml_to_df",
    "query_govinfo_documents", "analyze_document_collections",
    "get_document_trends", "search_documents_advanced",
    "analyze_document_metadata", "compare_collections", "export_govinfo_data"
  ]
}

export default function Home() {
  const [selectedSite, setSelectedSite] = useState<string>('')
  const [selectedFunction, setSelectedFunction] = useState<string>('')
  const [functionDoc, setFunctionDoc] = useState<any>(null)

  const handleSiteChange = (site: string) => {
    setSelectedSite(site)
    setSelectedFunction('')
    setFunctionDoc(null)
  }

  const handleFunctionChange = (func: string) => {
    setSelectedFunction(func)
    if (selectedSite && func) {
      setFunctionDoc(functionDocs[selectedSite as keyof typeof functionDocs][func])
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-900">
          MCP Legislative Data API Documentation
        </h1>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">Function Reference</h2>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Site Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Legislative Data Source
              </label>
              <select
                value={selectedSite}
                onChange={(e) => handleSiteChange(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Choose a data source...</option>
                <option value="congress">Congress.gov API</option>
                <option value="openstates">OpenStates API</option>
                <option value="govinfo">GovInfo API</option>
              </select>
              <p className="text-sm text-gray-600 mt-1">
                Select the legislative data source you want to work with
              </p>
            </div>

            {/* Function Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Function
              </label>
              <select
                value={selectedFunction}
                onChange={(e) => handleFunctionChange(e.target.value)}
                disabled={!selectedSite}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="">
                  {selectedSite ? 'Choose a function...' : 'Select a data source first'}
                </option>
                {selectedSite && availableSites[selectedSite as keyof typeof availableSites].map(func => (
                  <option key={func} value={func}>
                    {func.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </option>
                ))}
              </select>
              <p className="text-sm text-gray-600 mt-1">
                Choose the specific function you want to use
              </p>
            </div>
          </div>
        </div>

        {/* Function Documentation */}
        {functionDoc && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="border-b border-gray-200 pb-4 mb-6">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                {functionDoc.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h3>
              <p className="text-gray-600">{functionDoc.description}</p>
            </div>

            {/* Parameters */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Parameters</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full table-auto border-collapse border border-gray-300">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="border border-gray-300 px-4 py-2 text-left">Parameter</th>
                      <th className="border border-gray-300 px-4 py-2 text-left">Type</th>
                      <th className="border border-gray-300 px-4 py-2 text-left">Required</th>
                      <th className="border border-gray-300 px-4 py-2 text-left">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(functionDoc.parameters).map(([param, details]: [string, any]) => (
                      <tr key={param} className="hover:bg-gray-50">
                        <td className="border border-gray-300 px-4 py-2 font-mono text-sm">{param}</td>
                        <td className="border border-gray-300 px-4 py-2 font-mono text-sm text-blue-600">{details.type}</td>
                        <td className="border border-gray-300 px-4 py-2">
                          {details.required ? (
                            <span className="text-red-600 font-semibold">Yes</span>
                          ) : (
                            <span className="text-green-600">No</span>
                          )}
                          {details.default && (
                            <span className="text-gray-500 text-sm ml-1">(default: {details.default})</span>
                          )}
                        </td>
                        <td className="border border-gray-300 px-4 py-2">{details.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Returns */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Returns</h4>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="font-semibold text-gray-900 mb-1">
                  Type: <code className="bg-gray-200 px-2 py-1 rounded text-sm">{functionDoc.returns.type}</code>
                </p>
                <p className="text-gray-700 mb-2">{functionDoc.returns.description}</p>
                {functionDoc.returns.structure && (
                  <p className="text-sm text-gray-600">
                    <strong>Structure:</strong> {functionDoc.returns.structure}
                  </p>
                )}
              </div>
            </div>

            {/* Requirements */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Requirements</h4>
              <ul className="list-disc list-inside space-y-1">
                {functionDoc.requirements.map((req: string, index: number) => (
                  <li key={index} className="text-gray-700">{req}</li>
                ))}
              </ul>
            </div>

            {/* Examples */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Examples</h4>
              {functionDoc.examples.map((example: any, index: number) => (
                <div key={index} className="mb-4">
                  <p className="text-gray-700 mb-2">{example.description}</p>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                    <code>{example.code}</code>
                  </pre>
                </div>
              ))}
            </div>

            {/* Data Types */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Data Types & Database Schema</h4>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h5 className="font-semibold text-gray-900 mb-2">Input/Output Types</h5>
                  <ul className="space-y-1 text-sm">
                    <li><strong>Input:</strong> {functionDoc.dataTypes.input}</li>
                    <li><strong>Output:</strong> {functionDoc.dataTypes.output}</li>
                    {functionDoc.dataTypes.supportedFormats && (
                      <li><strong>Supported Formats:</strong> {functionDoc.dataTypes.supportedFormats}</li>
                    )}
                  </ul>
                </div>
                {functionDoc.dataTypes.sqlTable && (
                  <div>
                    <h5 className="font-semibold text-gray-900 mb-2">Database Table</h5>
                    <p className="text-sm text-gray-700">{functionDoc.dataTypes.sqlTable}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Expected Results */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-3">Expected Results & Usage Notes</h4>
              <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
                <div className="flex">
                  <div className="ml-3">
                    <p className="text-sm text-blue-700">
                      <strong>Usage:</strong> This function {functionDoc.description.toLowerCase()}.
                      Make sure you have registered the appropriate API key for the selected data source before calling this function.
                    </p>
                    {functionDoc.dataTypes.sqlTable && (
                      <p className="text-sm text-blue-700 mt-2">
                        <strong>Database Requirements:</strong> Requires data to be ingested into the database first using the ingestion endpoints.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-gray-600">
          <p className="mb-2">
            <strong>MCP Legislative Data Server</strong> - Comprehensive API for legislative data analysis
          </p>
          <p className="text-sm">
            Supports Congress.gov, OpenStates, and GovInfo APIs with advanced analytics and export capabilities
          </p>
        </div>
      </div>
    </div>
  )
}
