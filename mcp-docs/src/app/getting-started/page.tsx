import Link from 'next/link'

export default function GettingStarted() {
  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Getting Started</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Set up your MCP Legislative Data Server and start accessing comprehensive legislative data from Congress.gov, OpenStates, and GovInfo.
          </p>
        </div>

        {/* Quick Setup Overview */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 mb-8">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">Quick Setup Overview</h3>
              <ol className="list-decimal list-inside space-y-1 text-blue-800">
                <li>Install the MCP server and dependencies</li>
                <li>Register API keys for data sources</li>
                <li>Configure database connection</li>
                <li>Start the server and begin querying data</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Prerequisites */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Prerequisites</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">System Requirements</h3>
              <ul className="space-y-2 text-gray-700">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Python 3.8 or higher
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  PostgreSQL database
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  4GB+ RAM recommended
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Linux/macOS/Windows
                </li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">API Keys Required</h3>
              <div className="space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Congress.gov API Key</p>
                    <p className="text-sm text-gray-600">Free registration at congress.gov</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">OpenStates API Key</p>
                    <p className="text-sm text-gray-600">Free registration at openstates.org</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">GovInfo API Key</p>
                    <p className="text-sm text-gray-600">Free registration at govinfo.gov</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Installation Steps */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Installation</h2>

          <div className="space-y-6">
            {/* Step 1: Clone Repository */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-start">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-semibold">1</span>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Clone the Repository</h3>
                  <p className="text-gray-600 mb-3">Download the MCP server codebase from GitHub.</p>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto">
                    <code>git clone https://github.com/cbwinslow/opendiscourse-mcp.git
cd opendiscourse-mcp</code>
                  </pre>
                </div>
              </div>
            </div>

            {/* Step 2: Install Dependencies */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-start">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-semibold">2</span>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Install Python Dependencies</h3>
                  <p className="text-gray-600 mb-3">Install all required Python packages using pip.</p>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto">
                    <code>pip install -r requirements.txt</code>
                  </pre>
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-sm text-yellow-800">
                      <strong>Note:</strong> For GPU acceleration, also install CuDF: <code>pip install cudf</code>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 3: Setup Database */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-start">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-semibold">3</span>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Setup PostgreSQL Database</h3>
                  <p className="text-gray-600 mb-3">Create a PostgreSQL database and run the schema setup.</p>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto">
                    <code># Create database
createdb legislative_data

# Run schema setup (if available)
psql -d legislative_data -f schema.sql</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Configuration */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Configuration</h2>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">API Key Registration</h3>
            <p className="text-gray-600 mb-4">
              Register API keys for each data source you want to use. The server will prompt you to register keys when you first use functions requiring them.
            </p>

            <div className="grid md:grid-cols-3 gap-4 mb-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">Congress.gov</h4>
                <p className="text-sm text-blue-700 mb-2">Federal legislative data</p>
                <a href="https://www.congress.gov/developers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 text-sm">
                  Register API Key →
                </a>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <h4 className="font-semibold text-green-900 mb-2">OpenStates</h4>
                <p className="text-sm text-green-700 mb-2">State legislative data</p>
                <a href="https://openstates.org/api/register/" target="_blank" rel="noopener noreferrer" className="text-green-600 hover:text-green-800 text-sm">
                  Register API Key →
                </a>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <h4 className="font-semibold text-purple-900 mb-2">GovInfo</h4>
                <p className="text-sm text-purple-700 mb-2">Official publications</p>
                <a href="https://www.govinfo.gov/developers" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:text-purple-800 text-sm">
                  Register API Key →
                </a>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="font-semibold text-gray-900 mb-2">Environment Variables</h4>
              <p className="text-sm text-gray-600 mb-3">Set these environment variables for database connection:</p>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
                <code>export DATABASE_URL="postgresql://user:password@localhost:5432/legislative_data"
export REDIS_URL="redis://localhost:6379"  # Optional, for caching</code>
              </pre>
            </div>
          </div>
        </section>

        {/* First API Call */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Your First API Call</h2>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Start the MCP Server</h3>
            <p className="text-gray-600 mb-4">
              Launch the MCP server to begin accepting API calls.
            </p>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto mb-4">
              <code>python -m mcp_server.main</code>
            </pre>

            <h3 className="text-xl font-semibold text-gray-900 mb-4">Make Your First API Call</h3>
            <p className="text-gray-600 mb-4">
              Test the server with a simple bill search from Congress.gov.
            </p>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto mb-4">
              <code>{`{
  "user_id": "your_user_id",
  "site": "congress",
  "function": "search_bills",
  "args": {
    "congress": 118,
    "billType": "hr",
    "page": 1
  }
}`}</code>
            </pre>

            <div className="bg-green-50 border-l-4 border-green-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    <strong>Success!</strong> You should receive a JSON response with House bills from the 118th Congress.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Data Ingestion */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Data Ingestion</h2>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Populate Your Database</h3>
            <p className="text-gray-600 mb-4">
              Use the enhanced ingestion system to populate your database with legislative data for advanced querying and analytics.
            </p>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Congress Data Ingestion</h4>
                <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm mb-3">
                  <code>python mcp_server/scripts/enhanced_congress_ingest.py \
  --congress 118 \
  --use-gpu \
  --parallel</code>
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">OpenStates Data Ingestion</h4>
                <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm mb-3">
                  <code>python scripts/ingestion/openstates/openstates_ingest.py \
  --jurisdiction nc \
  --use-parallel</code>
                </pre>
              </div>
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-sm text-blue-800">
                <strong>Tip:</strong> The ingestion scripts support GPU acceleration, parallel processing, and progress tracking.
                Check the <Link href="/troubleshooting" className="text-blue-600 hover:text-blue-800">troubleshooting guide</Link> for common issues.
              </p>
            </div>
          </div>
        </section>

        {/* Next Steps */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Next Steps</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Explore the API</h3>
              <p className="text-gray-600 mb-4">
                Learn about all available functions and their capabilities.
              </p>
              <Link href="/api-reference" className="inline-flex items-center text-blue-600 hover:text-blue-800">
                View API Reference
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">See Examples</h3>
              <p className="text-gray-600 mb-4">
                Practical examples and use cases for legislative data analysis.
              </p>
              <Link href="/examples" className="inline-flex items-center text-blue-600 hover:text-blue-800">
                View Examples
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>
        </section>

        {/* Support */}
        <section className="text-center">
          <div className="bg-gray-50 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Need Help?</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Check our troubleshooting guide for common issues and solutions, or explore the documentation for detailed usage instructions.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/troubleshooting" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                Troubleshooting Guide
              </Link>
              <a href="https://github.com/cbwinslow/opendiscourse-mcp" target="_blank" rel="noopener noreferrer" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                GitHub Repository
              </a>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}