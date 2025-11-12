import Link from 'next/link'

export default function Examples() {
  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Examples & Tutorials</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Practical examples and code samples showing how to use the MCP Legislative Data Server for real-world legislative analysis.
          </p>
        </div>

        {/* Quick Start Example */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Quick Start Example</h2>

          <div className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Search Recent House Bills</h3>
            <p className="text-gray-600 mb-6">
              This example shows how to search for recent House bills in the 118th Congress and display the results.
            </p>

            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">API Request</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`POST /mcp/execute
Content-Type: application/json

{
  "user_id": "demo_user",
  "site": "congress",
  "function": "search_bills",
  "args": {
    "congress": 118,
    "billType": "hr",
    "page": 1
  }
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Sample Response</h4>
                <pre className="bg-gray-900 text-blue-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "status": "success",
  "result": {
    "bills": [
      {
        "congress": 118,
        "billType": "hr",
        "billNumber": "1234",
        "title": "Infrastructure Investment Act",
        "latestAction": {
          "date": "2024-01-15",
          "description": "Referred to committee"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "count": 20
    }
  }
}`}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Use Cases */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Common Use Cases</h2>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Legislative Tracking */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Legislative Tracking</h3>
              <p className="text-gray-600 mb-4">
                Monitor bills through the legislative process, track amendments, and analyze voting patterns.
              </p>
              <ul className="text-sm text-gray-600 space-y-1 mb-4">
                <li>• Track bill progress and status changes</li>
                <li>• Monitor committee assignments</li>
                <li>• Analyze sponsorship patterns</li>
                <li>• Follow related legislation</li>
              </ul>
              <Link href="#legislative-tracking" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                View Example →
              </Link>
            </div>

            {/* Policy Analysis */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Policy Analysis</h3>
              <p className="text-gray-600 mb-4">
                Analyze legislative trends, identify policy priorities, and understand legislative agendas.
              </p>
              <ul className="text-sm text-gray-600 space-y-1 mb-4">
                <li>• Identify trending policy areas</li>
                <li>• Analyze legislative productivity</li>
                <li>• Compare state vs federal approaches</li>
                <li>• Track policy implementation</li>
              </ul>
              <Link href="#policy-analysis" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                View Example →
              </Link>
            </div>

            {/* Research & Journalism */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Research & Journalism</h3>
              <p className="text-gray-600 mb-4">
                Conduct in-depth research on legislative topics, find related bills, and analyze legislative history.
              </p>
              <ul className="text-sm text-gray-600 space-y-1 mb-4">
                <li>• Full-text bill search</li>
                <li>• Historical legislative analysis</li>
                <li>• Cross-reference related bills</li>
                <li>• Export data for analysis</li>
              </ul>
              <Link href="#research-journalism" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                View Example →
              </Link>
            </div>

            {/* Data Analytics */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Data Analytics</h3>
              <p className="text-gray-600 mb-4">
                Build dashboards, perform statistical analysis, and create visualizations from legislative data.
              </p>
              <ul className="text-sm text-gray-600 space-y-1 mb-4">
                <li>• Statistical analysis of bill data</li>
                <li>• Trend identification and forecasting</li>
                <li>• Interactive data visualizations</li>
                <li>• Automated reporting</li>
              </ul>
              <Link href="#data-analytics" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                View Example →
              </Link>
            </div>
          </div>
        </section>

        {/* Detailed Examples */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Detailed Examples</h2>

          {/* Legislative Tracking Example */}
          <div id="legislative-tracking" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-4">Legislative Tracking: Monitor Infrastructure Bills</h3>
            <p className="text-gray-600 mb-6">
              Track all infrastructure-related bills through the legislative process, from introduction to enactment.
            </p>

            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">1. Search for Infrastructure Bills</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "researcher_123",
  "site": "congress",
  "function": "search_bills_by_text_content",
  "args": {
    "search_text": "infrastructure",
    "congress": 118,
    "limit": 50
  }
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">2. Get Detailed Bill Information</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "researcher_123",
  "site": "congress",
  "function": "get_bill",
  "args": {
    "congress": 118,
    "billType": "hr",
    "billNumber": "1234"
  }
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">3. Track Legislative Actions</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "researcher_123",
  "site": "congress",
  "function": "get_bill_actions",
  "args": {
    "congress": 118,
    "billType": "hr",
    "billNumber": "1234"
  }
}`}</code>
                </pre>
              </div>
            </div>
          </div>

          {/* Policy Analysis Example */}
          <div id="policy-analysis" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-4">Policy Analysis: Healthcare Legislation Trends</h3>
            <p className="text-gray-600 mb-6">
              Analyze healthcare policy trends across multiple Congresses and states.
            </p>

            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Federal Healthcare Bills Analysis</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "analyst_456",
  "site": "congress",
  "function": "get_congressional_trends",
  "args": {
    "start_year": 2020,
    "end_year": 2024,
    "topics": ["healthcare", "medicare", "medicaid"]
  }
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">State-Level Healthcare Policies</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "analyst_456",
  "site": "openstates",
  "function": "search_bills_advanced",
  "args": {
    "keywords": ["healthcare", "insurance", "medical"],
    "jurisdiction": "ca",
    "limit": 100
  }
}`}</code>
                </pre>
              </div>
            </div>
          </div>

          {/* Research Example */}
          <div id="research-journalism" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-4">Research: Climate Change Legislation</h3>
            <p className="text-gray-600 mb-6">
              Research comprehensive climate change legislation across federal and state levels.
            </p>

            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Federal Climate Bills</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "researcher_789",
  "site": "congress",
  "function": "search_bills_by_text_content",
  "args": {
    "search_text": "climate change OR global warming OR greenhouse gas",
    "congress": 118,
    "limit": 200
  }
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">State Climate Policies</h4>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                  <code>{`{
  "user_id": "researcher_789",
  "site": "openstates",
  "function": "find_related_bills",
  "args": {
    "bill_id": "CA_2023_AB123",
    "jurisdiction": "ca",
    "limit": 20
  }
}`}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Code Integration Examples */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Code Integration Examples</h2>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Python Client */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Python Integration</h3>
              <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm mb-4">
                <code>{`import requests
import json

class MCPClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def execute(self, user_id, site, function, **args):
        payload = {
            "user_id": user_id,
            "site": site,
            "function": function,
            "args": args
        }
        response = requests.post(
            f"{self.base_url}/mcp/execute",
            json=payload
        )
        return response.json()

# Usage
client = MCPClient()
result = client.execute(
    "my_user_id",
    "congress",
    "search_bills",
    congress=118,
    billType="hr"
)`}</code>
              </pre>
              <p className="text-sm text-gray-600">
                Complete Python client for easy MCP server integration.
              </p>
            </div>

            {/* JavaScript/Node.js */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Node.js Integration</h3>
              <pre className="bg-gray-900 text-yellow-400 p-4 rounded-md overflow-x-auto text-sm mb-4">
                <code>{`const axios = require('axios');

class MCPClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.client = axios.create({ baseURL });
  }

  async execute(userId, site, functionName, args = {}) {
    const payload = {
      user_id: userId,
      site,
      function: functionName,
      args
    };

    const response = await this.client.post('/mcp/execute', payload);
    return response.data;
  }
}

// Usage
const client = new MCPClient();
const result = await client.execute(
  'my_user_id',
  'openstates',
  'search_bills',
  { jurisdiction: 'nc', q: 'education' }
);`}</code>
              </pre>
              <p className="text-sm text-gray-600">
                Node.js client with async/await support for modern JavaScript applications.
              </p>
            </div>
          </div>
        </section>

        {/* Data Export Examples */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Data Export & Analysis</h2>

          <div className="bg-white p-8 rounded-lg border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Export Legislative Data for Analysis</h3>
            <p className="text-gray-600 mb-6">
              Export data in various formats for further analysis, reporting, or integration with other tools.
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">CSV Export</h4>
                <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm mb-3">
                  <code>{`POST /mcp/export_data
{
  "user_id": "analyst_123",
  "database_url": "postgresql://...",
  "table": "congress_bills",
  "format": "csv",
  "where_clause": "congress = 118",
  "output_path": "bills_118.csv"
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">JSON Export</h4>
                <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm mb-3">
                  <code>{`POST /mcp/export_data
{
  "user_id": "analyst_123",
  "database_url": "postgresql://...",
  "table": "openstates_bills",
  "format": "json",
  "where_clause": "jurisdiction = 'ca'",
  "output_path": "ca_bills.json"
}`}</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Parquet Export</h4>
                <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm mb-3">
                  <code>{`POST /mcp/export_data
{
  "user_id": "analyst_123",
  "database_url": "postgresql://...",
  "table": "govinfo_documents",
  "format": "parquet",
  "output_path": "govinfo_data.parquet"
}`}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Best Practices */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Best Practices</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Performance Optimization</h3>
              <ul className="space-y-3 text-gray-600">
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Use database queries for large datasets instead of API calls
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Implement caching for frequently accessed data
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Use bulk operations when available
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Paginate results for large queries
                </li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Error Handling</h3>
              <ul className="space-y-3 text-gray-600">
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Always check API response status
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Implement retry logic with exponential backoff
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Handle rate limiting gracefully
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 0118 0z" />
                  </svg>
                  Validate input parameters before sending
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* Navigation */}
        <section className="text-center">
          <div className="bg-gray-50 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Need More Help?</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Check out our comprehensive API reference or troubleshooting guide for additional support.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/api-reference" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                API Reference
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