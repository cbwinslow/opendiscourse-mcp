'use client'

import { useState } from 'react'
import Link from 'next/link'

type SiteType = 'congress' | 'openstates' | 'govinfo'

export default function ApiReference() {
  const [selectedSite, setSelectedSite] = useState<SiteType>('congress')
  const [searchTerm, setSearchTerm] = useState('')

  const functionData = {
    congress: {
      name: 'Congress.gov API',
      description: 'Access federal legislative data including bills, members, committees, and legislative actions.',
      functions: [
        {
          name: 'search_bills',
          description: 'Search for bills by congress, bill type, and other criteria',
          parameters: [
            { name: 'congress', type: 'Optional[int]', description: 'Congress number (e.g., 118)' },
            { name: 'billType', type: 'Optional[str]', description: 'Bill type (hr, s, hjres, etc.)' },
            { name: 'page', type: 'int', description: 'Page number for pagination', default: '1' }
          ],
          example: `{
  "user_id": "your_user_id",
  "site": "congress",
  "function": "search_bills",
  "args": {
    "congress": 118,
    "billType": "hr",
    "page": 1
  }
}`
        },
        {
          name: 'get_bill',
          description: 'Get detailed information about a specific bill',
          parameters: [
            { name: 'congress', type: 'int', description: 'Congress number' },
            { name: 'billType', type: 'str', description: 'Bill type (hr, s, hjres, etc.)' },
            { name: 'billNumber', type: 'str', description: 'Bill number' }
          ],
          example: `{
  "user_id": "your_user_id",
  "site": "congress",
  "function": "get_bill",
  "args": {
    "congress": 118,
    "billType": "hr",
    "billNumber": "1234"
  }
}`
        },
        {
          name: 'get_bill_actions',
          description: 'Get legislative actions for a specific bill',
          parameters: [
            { name: 'congress', type: 'int', description: 'Congress number' },
            { name: 'billType', type: 'str', description: 'Bill type' },
            { name: 'billNumber', type: 'str', description: 'Bill number' }
          ]
        },
        {
          name: 'get_bill_text',
          description: 'Get the text content of a bill',
          parameters: [
            { name: 'congress', type: 'int', description: 'Congress number' },
            { name: 'billType', type: 'str', description: 'Bill type' },
            { name: 'billNumber', type: 'str', description: 'Bill number' }
          ]
        },
        {
          name: 'list_members',
          description: 'List members of Congress',
          parameters: [
            { name: 'congress', type: 'Optional[int]', description: 'Congress number' },
            { name: 'chamber', type: 'Optional[str]', description: 'House or Senate' }
          ]
        },
        {
          name: 'get_member',
          description: 'Get detailed information about a specific member',
          parameters: [
            { name: 'bioguideId', type: 'str', description: 'Member\'s bioguide ID' }
          ]
        },
        {
          name: 'search_bills_by_text_content',
          description: 'Search bills by text content using advanced text search',
          parameters: [
            { name: 'search_text', type: 'str', description: 'Text to search for in bill content' },
            { name: 'congress', type: 'Optional[int]', description: 'Limit search to specific congress' },
            { name: 'bill_type', type: 'Optional[str]', description: 'Limit search to specific bill type' },
            { name: 'limit', type: 'int', description: 'Maximum number of results', default: '100' }
          ]
        },
        {
          name: 'analyze_bill_sponsors_congress',
          description: 'Analyze bill sponsorship patterns in Congress',
          parameters: [
            { name: 'congress', type: 'Optional[int]', description: 'Congress number to analyze' },
            { name: 'party', type: 'Optional[str]', description: 'Filter by party (D, R, I)' }
          ]
        },
        {
          name: 'get_congressional_trends',
          description: 'Get legislative trends and statistics for Congress',
          parameters: [
            { name: 'congress', type: 'Optional[int]', description: 'Congress number' },
            { name: 'start_year', type: 'Optional[int]', description: 'Start year for analysis' },
            { name: 'end_year', type: 'Optional[int]', description: 'End year for analysis' }
          ]
        }
      ]
    },
    openstates: {
      name: 'OpenStates API',
      description: 'State-level legislative data from all 50 states, including bills, legislators, and events.',
      functions: [
        {
          name: 'search_bills',
          description: 'Search for bills in state legislatures',
          parameters: [
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation (e.g., "nc", "ca")' },
            { name: 'q', type: 'Optional[str]', description: 'Search query' },
            { name: 'page', type: 'int', description: 'Page number', default: '1' },
            { name: 'per_page', type: 'int', description: 'Results per page', default: '50' }
          ],
          example: `{
  "user_id": "your_user_id",
  "site": "openstates",
  "function": "search_bills",
  "args": {
    "jurisdiction": "nc",
    "q": "education",
    "page": 1
  }
}`
        },
        {
          name: 'get_bill',
          description: 'Get detailed information about a specific bill',
          parameters: [
            { name: 'openstates_bill_id', type: 'str', description: 'OpenStates bill ID' }
          ]
        },
        {
          name: 'search_people',
          description: 'Search for legislators',
          parameters: [
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation' },
            { name: 'name', type: 'Optional[str]', description: 'Legislator name' },
            { name: 'party', type: 'Optional[str]', description: 'Political party' }
          ]
        },
        {
          name: 'get_person',
          description: 'Get detailed information about a legislator',
          parameters: [
            { name: 'person_id', type: 'str', description: 'OpenStates person ID' }
          ]
        },
        {
          name: 'search_events',
          description: 'Search for legislative events',
          parameters: [
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation' },
            { name: 'q', type: 'Optional[str]', description: 'Search query' }
          ]
        },
        {
          name: 'get_event',
          description: 'Get detailed information about a legislative event',
          parameters: [
            { name: 'event_id', type: 'str', description: 'OpenStates event ID' }
          ]
        },
        {
          name: 'search_bills_advanced',
          description: 'Advanced bill search with multiple criteria',
          parameters: [
            { name: 'keywords', type: 'Optional[List[str]]', description: 'Keywords to search for' },
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation' },
            { name: 'classification', type: 'Optional[str]', description: 'Bill classification' },
            { name: 'status', type: 'Optional[str]', description: 'Bill status' },
            { name: 'limit', type: 'int', description: 'Maximum results', default: '100' }
          ]
        },
        {
          name: 'get_bill_statistics',
          description: 'Get comprehensive statistics on bill data',
          parameters: [
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation' },
            { name: 'start_date', type: 'Optional[str]', description: 'Start date (YYYY-MM-DD)' },
            { name: 'end_date', type: 'Optional[str]', description: 'End date (YYYY-MM-DD)' }
          ]
        },
        {
          name: 'find_related_bills',
          description: 'Find bills related by topic or sponsor',
          parameters: [
            { name: 'bill_id', type: 'str', description: 'Base bill ID' },
            { name: 'jurisdiction', type: 'Optional[str]', description: 'State abbreviation' },
            { name: 'limit', type: 'int', description: 'Maximum related bills', default: '10' }
          ]
        }
      ]
    },
    govinfo: {
      name: 'GovInfo API',
      description: 'Official publications from all three branches of government, including statutes and regulations.',
      functions: [
        {
          name: 'list_collections',
          description: 'List available document collections',
          parameters: [],
          example: `{
  "user_id": "your_user_id",
  "site": "govinfo",
  "function": "list_collections",
  "args": {}
}`
        },
        {
          name: 'bulk_download',
          description: 'Download bulk data files',
          parameters: [
            { name: 'collection', type: 'str', description: 'Collection name' },
            { name: 'year', type: 'Optional[int]', description: 'Year to download' }
          ]
        },
        {
          name: 'fetch_bulk_file',
          description: 'Fetch a specific bulk file',
          parameters: [
            { name: 'collection', type: 'str', description: 'Collection name' },
            { name: 'file_name', type: 'str', description: 'File name' }
          ]
        },
        {
          name: 'ingest_xml_to_df',
          description: 'Convert XML data to DataFrame',
          parameters: [
            { name: 'xml_content', type: 'str', description: 'XML content to parse' },
            { name: 'collection', type: 'str', description: 'Collection type' }
          ]
        },
        {
          name: 'search_documents_advanced',
          description: 'Advanced document search',
          parameters: [
            { name: 'collection', type: 'Optional[str]', description: 'Collection to search' },
            { name: 'title', type: 'Optional[str]', description: 'Title search term' },
            { name: 'date_from', type: 'Optional[str]', description: 'Start date (YYYY-MM-DD)' },
            { name: 'date_to', type: 'Optional[str]', description: 'End date (YYYY-MM-DD)' },
            { name: 'limit', type: 'int', description: 'Maximum results', default: '100' }
          ]
        },
        {
          name: 'analyze_document_collections',
          description: 'Analyze document collections for trends',
          parameters: [
            { name: 'collection', type: 'Optional[str]', description: 'Collection to analyze' },
            { name: 'start_year', type: 'Optional[int]', description: 'Start year' },
            { name: 'end_year', type: 'Optional[int]', description: 'End year' }
          ]
        },
        {
          name: 'query_recent_documents',
          description: 'Query recently published documents',
          parameters: [
            { name: 'collection', type: 'Optional[str]', description: 'Collection filter' },
            { name: 'days', type: 'int', description: 'Days back to search', default: '30' },
            { name: 'limit', type: 'int', description: 'Maximum results', default: '100' }
          ]
        }
      ]
    }
  }

  const dataModel = {
    congress_bills: {
      description: 'Federal bills and legislation',
      fields: {
        id: 'text (primary key)',
        congress: 'smallint',
        bill_type: 'text',
        bill_number: 'integer',
        title: 'text',
        latest_action_date: 'date',
        latest_action_description: 'text',
        subjects: 'text[]',
        sponsors: 'jsonb',
        raw: 'jsonb'
      }
    },
    congress_members: {
      description: 'Congress members and representatives',
      fields: {
        bioguide_id: 'text (primary key)',
        first_name: 'text',
        last_name: 'text',
        party: 'text',
        state: 'text',
        district: 'text',
        raw: 'jsonb'
      }
    },
    openstates_bills: {
      description: 'State legislative bills',
      fields: {
        id: 'text (primary key)',
        session: 'text',
        jurisdiction: 'text',
        identifier: 'text',
        title: 'text',
        classification: 'text[]',
        subjects: 'text[]',
        created_at: 'timestamptz',
        updated_at: 'timestamptz',
        first_action_date: 'date',
        latest_action_date: 'date',
        latest_action_description: 'text',
        openstates_url: 'text',
        raw: 'jsonb'
      }
    },
    openstates_people: {
      description: 'State legislators and officials',
      fields: {
        id: 'text (primary key)',
        name: 'text',
        party: 'text',
        jurisdiction: 'text',
        given_name: 'text',
        family_name: 'text',
        image: 'text',
        email: 'text',
        gender: 'text',
        birth_date: 'date',
        death_date: 'date',
        extras: 'jsonb',
        raw: 'jsonb'
      }
    },
    govinfo_documents: {
      description: 'Official government publications',
      fields: {
        id: 'text (primary key)',
        collection: 'text',
        date: 'date',
        title: 'text',
        url: 'text',
        metadata: 'jsonb',
        raw: 'jsonb'
      }
    }
  }

  const filteredFunctions = functionData[selectedSite].functions.filter(func =>
    func.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    func.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">API Reference</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Complete documentation for all MCP Legislative Data Server functions across Congress.gov, OpenStates, and GovInfo APIs.
          </p>
        </div>

        {/* API Selection */}
        <div className="mb-8">
          <div className="flex flex-wrap gap-2 mb-6">
            {(Object.keys(functionData) as SiteType[]).map(site => (
              <button
                key={site}
                onClick={() => setSelectedSite(site)}
                className={`px-6 py-2 rounded-lg font-semibold transition-colors ${
                  selectedSite === site
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {functionData[site].name}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="max-w-md">
            <input
              type="text"
              placeholder="Search functions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* API Description */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 mb-8">
          <h2 className="text-xl font-semibold text-blue-900 mb-2">{functionData[selectedSite].name}</h2>
          <p className="text-blue-800">{functionData[selectedSite].description}</p>
        </div>

        {/* Function List */}
        <div className="space-y-6 mb-12">
          {filteredFunctions.map(func => (
            <div key={func.name} className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-900">{func.name}</h3>
                <span className="text-sm text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">
                  {selectedSite}
                </span>
              </div>

              <p className="text-gray-600 mb-4">{func.description}</p>

              {/* Parameters */}
              {func.parameters.length > 0 && (
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Parameters:</h4>
                  <div className="space-y-2">
                    {func.parameters.map(param => (
                      <div key={param.name} className="flex items-start space-x-3 text-sm">
                        <code className="bg-gray-100 px-2 py-1 rounded text-blue-600 font-mono">
                          {param.name}
                        </code>
                        <span className="text-gray-500 font-mono">{param.type}</span>
                        <span className="text-gray-700 flex-1">{param.description}</span>
                        {param.default && (
                          <span className="text-gray-500">Default: {param.default}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Example */}
              {func.example && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Example Request:</h4>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                    <code>{func.example}</code>
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Data Model Section */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Database Schema</h2>
          <p className="text-gray-600 mb-8">
            Complete database schema for all tables populated by the MCP server. All tables use PostgreSQL with appropriate indexing for performance.
          </p>

          <div className="grid md:grid-cols-2 gap-6">
            {Object.entries(dataModel).map(([tableName, tableInfo]) => (
              <div key={tableName} className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2 capitalize">
                  {tableName.replace('_', ' ')}
                </h3>
                <p className="text-gray-600 mb-4">{tableInfo.description}</p>

                <div className="space-y-2">
                  {Object.entries(tableInfo.fields).map(([field, type]) => (
                    <div key={field} className="flex justify-between items-center py-1 border-b border-gray-100 last:border-b-0">
                      <code className="text-blue-600 font-mono text-sm">{field}</code>
                      <span className="text-gray-500 font-mono text-sm">{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Usage Notes */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Usage Notes</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Authentication</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• Register API keys before making requests</li>
                <li>• Keys are stored securely per user</li>
                <li>• Different keys required for each data source</li>
                <li>• Keys are validated before each API call</li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Rate Limits</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• Respect API provider rate limits</li>
                <li>• Implement exponential backoff for retries</li>
                <li>• Cache frequently accessed data</li>
                <li>• Use bulk operations when available</li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Data Formats</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• JSON responses for API calls</li>
                <li>• CSV, JSON, Parquet export formats</li>
                <li>• PostgreSQL JSONB for flexible metadata</li>
                <li>• Pandas DataFrames for analysis</li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Error Handling</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• Check response status codes</li>
                <li>• Handle network timeouts gracefully</li>
                <li>• Validate input parameters</li>
                <li>• Log errors for debugging</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Navigation */}
        <section className="text-center">
          <div className="bg-gray-50 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Explore More</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Ready to put this API knowledge into practice? Check out our examples and troubleshooting guides.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/examples" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                View Examples
              </Link>
              <Link href="/troubleshooting" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                Troubleshooting Guide
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}