import Link from 'next/link'

export default function Troubleshooting() {
  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Troubleshooting Guide</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Common issues and solutions for the MCP Legislative Data Server. Find answers to frequently asked questions and resolve problems quickly.
          </p>
        </div>

        {/* Quick Solutions */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Quick Solutions</h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* API Key Issues */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">API Key Issues</h3>
              <p className="text-gray-600 mb-3 text-sm">
                Problems with API key registration or authentication.
              </p>
              <Link href="#api-key-issues" className="text-red-600 hover:text-red-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>

            {/* Connection Problems */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Connection Issues</h3>
              <p className="text-gray-600 mb-3 text-sm">
                Database connection, network, or server connectivity problems.
              </p>
              <Link href="#connection-issues" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>

            {/* Data Ingestion */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Data Ingestion</h3>
              <p className="text-gray-600 mb-3 text-sm">
                Issues with importing or processing legislative data.
              </p>
              <Link href="#data-ingestion" className="text-green-600 hover:text-green-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>

            {/* Performance */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Performance Issues</h3>
              <p className="text-gray-600 mb-3 text-sm">
                Slow queries, memory problems, or GPU acceleration issues.
              </p>
              <Link href="#performance-issues" className="text-purple-600 hover:text-purple-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>

            {/* Rate Limiting */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Rate Limiting</h3>
              <p className="text-gray-600 mb-3 text-sm">
                API rate limit errors and throttling issues.
              </p>
              <Link href="#rate-limiting" className="text-orange-600 hover:text-orange-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>

            {/* Data Quality */}
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Data Quality</h3>
              <p className="text-gray-600 mb-3 text-sm">
                Missing data, inconsistencies, or data validation issues.
              </p>
              <Link href="#data-quality" className="text-indigo-600 hover:text-indigo-800 text-sm font-semibold">
                View Solutions →
              </Link>
            </div>
          </div>
        </section>

        {/* Detailed Solutions */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Detailed Solutions</h2>

          {/* API Key Issues */}
          <div id="api-key-issues" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">API Key Issues</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-red-400 bg-red-50 p-4">
                <h4 className="font-semibold text-red-900 mb-2">Error: "No API key registered"</h4>
                <p className="text-red-800 mb-3">This error occurs when trying to use a function without registering the required API key first.</p>
                <div className="bg-white p-3 rounded mb-3">
                  <h5 className="font-semibold text-gray-900 mb-2">Solution:</h5>
                  <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
                    <code>{`POST /mcp/register_token
{
  "site": "congress",
  "user_id": "your_user_id",
  "api_key": "your_congress_api_key"
}`}</code>
                  </pre>
                </div>
                <p className="text-sm text-red-700">
                  Register API keys for each data source you want to use before making API calls.
                </p>
              </div>

              <div className="border-l-4 border-red-400 bg-red-50 p-4">
                <h4 className="font-semibold text-red-900 mb-2">Error: "Invalid API key"</h4>
                <p className="text-red-800 mb-3">The API key provided is not valid or has expired.</p>
                <ul className="list-disc list-inside text-red-800 space-y-1 mb-3">
                  <li>Verify your API key is correct</li>
                  <li>Check if your key has expired</li>
                  <li>Ensure you're using the right key for the correct service</li>
                  <li>Try registering the key again</li>
                </ul>
              </div>

              <div className="border-l-4 border-blue-400 bg-blue-50 p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Getting API Keys</h4>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="text-center p-3 bg-white rounded">
                    <p className="font-semibold text-gray-900">Congress.gov</p>
                    <a href="https://www.congress.gov/developers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 text-sm">
                      Register Here
                    </a>
                  </div>
                  <div className="text-center p-3 bg-white rounded">
                    <p className="font-semibold text-gray-900">OpenStates</p>
                    <a href="https://openstates.org/api/register/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 text-sm">
                      Register Here
                    </a>
                  </div>
                  <div className="text-center p-3 bg-white rounded">
                    <p className="font-semibold text-gray-900">GovInfo</p>
                    <a href="https://www.govinfo.gov/developers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 text-sm">
                      Register Here
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Connection Issues */}
          <div id="connection-issues" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Connection Issues</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-blue-400 bg-blue-50 p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Database Connection Failed</h4>
                <p className="text-blue-800 mb-3">Unable to connect to PostgreSQL database.</p>
                <div className="space-y-3">
                  <div>
                    <h5 className="font-semibold text-gray-900">Check Database URL:</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>postgresql://user:password@localhost:5432/legislative_data</code>
                    </pre>
                  </div>
                  <div>
                    <h5 className="font-semibold text-gray-900">Verify PostgreSQL is running:</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>sudo systemctl status postgresql</code>
                    </pre>
                  </div>
                  <div>
                    <h5 className="font-semibold text-gray-900">Test connection:</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>psql -h localhost -U your_user -d legislative_data</code>
                    </pre>
                  </div>
                </div>
              </div>

              <div className="border-l-4 border-blue-400 bg-blue-50 p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Server Connection Timeout</h4>
                <p className="text-blue-800 mb-3">The MCP server is not responding or is running on a different port.</p>
                <ul className="list-disc list-inside text-blue-800 space-y-1">
                  <li>Check if the server is running: <code>ps aux | grep mcp_server</code></li>
                  <li>Verify the correct port (default: 8000)</li>
                  <li>Check server logs for errors</li>
                  <li>Ensure firewall allows connections on the server port</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Data Ingestion Issues */}
          <div id="data-ingestion" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Data Ingestion Issues</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-green-400 bg-green-50 p-4">
                <h4 className="font-semibold text-green-900 mb-2">Ingestion Script Fails</h4>
                <p className="text-green-800 mb-3">Data ingestion scripts are failing with errors.</p>
                <div className="space-y-3">
                  <div>
                    <h5 className="font-semibold text-gray-900">Check Dependencies:</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>pip install -r requirements.txt</code>
                    </pre>
                  </div>
                  <div>
                    <h5 className="font-semibold text-gray-900">Verify GPU Setup (optional):</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>pip install cudf</code>
                    </pre>
                  </div>
                  <div>
                    <h5 className="font-semibold text-gray-900">Run with verbose logging:</h5>
                    <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                      <code>python mcp_server/scripts/enhanced_congress_ingest.py --verbose</code>
                    </pre>
                  </div>
                </div>
              </div>

              <div className="border-l-4 border-green-400 bg-green-50 p-4">
                <h4 className="font-semibold text-green-900 mb-2">Memory Issues During Ingestion</h4>
                <p className="text-green-800 mb-3">Large datasets causing memory exhaustion.</p>
                <ul className="list-disc list-inside text-green-800 space-y-1">
                  <li>Use batch processing: <code>--batch-size 1000</code></li>
                  <li>Enable parallel processing: <code>--parallel</code></li>
                  <li>Increase system memory or use smaller date ranges</li>
                  <li>Use GPU acceleration for large datasets</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Performance Issues */}
          <div id="performance-issues" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Performance Issues</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-purple-400 bg-purple-50 p-4">
                <h4 className="font-semibold text-purple-900 mb-2">Slow Database Queries</h4>
                <p className="text-purple-800 mb-3">Queries are taking too long to execute.</p>
                <ul className="list-disc list-inside text-purple-800 space-y-1 mb-3">
                  <li>Add database indexes on frequently queried columns</li>
                  <li>Use LIMIT clauses for large result sets</li>
                  <li>Optimize WHERE clauses</li>
                  <li>Consider partitioning large tables</li>
                </ul>
                <div>
                  <h5 className="font-semibold text-gray-900">Add Index Example:</h5>
                  <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                    <code>CREATE INDEX idx_congress_bills_congress ON congress_bills(congress);</code>
                  </pre>
                </div>
              </div>

              <div className="border-l-4 border-purple-400 bg-purple-50 p-4">
                <h4 className="font-semibold text-purple-900 mb-2">GPU Acceleration Not Working</h4>
                <p className="text-purple-800 mb-3">GPU processing is not available or not working.</p>
                <ul className="list-disc list-inside text-purple-800 space-y-1">
                  <li>Install CUDA toolkit and cuDF: <code>pip install cudf</code></li>
                  <li>Verify GPU is available: <code>nvidia-smi</code></li>
                  <li>Check CUDA version compatibility</li>
                  <li>Use CPU fallback if GPU is unavailable</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Rate Limiting */}
          <div id="rate-limiting" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Rate Limiting</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-orange-400 bg-orange-50 p-4">
                <h4 className="font-semibold text-orange-900 mb-2">API Rate Limit Exceeded</h4>
                <p className="text-orange-800 mb-3">Too many requests to external APIs.</p>
                <ul className="list-disc list-inside text-orange-800 space-y-1 mb-3">
                  <li>Implement exponential backoff retry logic</li>
                  <li>Reduce request frequency</li>
                  <li>Use cached data when possible</li>
                  <li>Batch requests where supported</li>
                </ul>
                <div>
                  <h5 className="font-semibold text-gray-900">Example Retry Logic:</h5>
                  <pre className="bg-gray-900 text-green-400 p-2 rounded text-sm">
                    <code>{`import time
for attempt in range(3):
    try:
        response = make_api_call()
        break
    except RateLimitError:
        time.sleep(2 ** attempt)  # Exponential backoff`}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>

          {/* Data Quality Issues */}
          <div id="data-quality" className="bg-white p-8 rounded-lg border border-gray-200 mb-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Data Quality Issues</h3>

            <div className="space-y-6">
              <div className="border-l-4 border-indigo-400 bg-indigo-50 p-4">
                <h4 className="font-semibold text-indigo-900 mb-2">Missing or Incomplete Data</h4>
                <p className="text-indigo-800 mb-3">Some records are missing expected fields or data.</p>
                <ul className="list-disc list-inside text-indigo-800 space-y-1">
                  <li>Check API source data availability</li>
                  <li>Verify data transformation logic</li>
                  <li>Re-run ingestion for missing data</li>
                  <li>Use data validation checks</li>
                </ul>
              </div>

              <div className="border-l-4 border-indigo-400 bg-indigo-50 p-4">
                <h4 className="font-semibold text-indigo-900 mb-2">Data Inconsistencies</h4>
                <p className="text-indigo-800 mb-3">Data appears inconsistent across different sources or time periods.</p>
                <ul className="list-disc list-inside text-indigo-800 space-y-1">
                  <li>Cross-reference data with official sources</li>
                  <li>Implement data quality checks</li>
                  <li>Use data normalization procedures</li>
                  <li>Document known data limitations</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Frequently Asked Questions</h2>

          <div className="space-y-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">How do I update my API keys?</h3>
              <p className="text-gray-600 mb-3">
                Simply register the new key using the same endpoint. The old key will be replaced automatically.
              </p>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm">
                <code>{`POST /mcp/register_token
{
  "site": "congress",
  "user_id": "your_user_id",
  "api_key": "new_api_key_here"
}`}</code>
              </pre>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Can I use the server without a database?</h3>
              <p className="text-gray-600">
                No, the MCP server requires PostgreSQL for data storage and querying. The database is essential for the advanced analytics and data persistence features.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">How do I backup my data?</h3>
              <p className="text-gray-600 mb-3">
                Use standard PostgreSQL backup tools to backup your legislative data.
              </p>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm">
                <code>pg_dump legislative_data &gt; backup.sql</code>
              </pre>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">What are the system requirements?</h3>
              <ul className="text-gray-600 space-y-1">
                <li>• Python 3.8+</li>
                <li>• PostgreSQL database</li>
                <li>• 4GB+ RAM recommended</li>
                <li>• GPU optional (for acceleration)</li>
                <li>• Linux/macOS/Windows supported</li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">How do I monitor server performance?</h3>
              <p className="text-gray-600 mb-3">
                Check server logs, monitor database query performance, and use system monitoring tools.
              </p>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm">
                <code>{`# Check server logs
tail -f mcp_server.log

# Monitor database
psql -d legislative_data -c "SELECT * FROM pg_stat_activity;"`}</code>
              </pre>
            </div>
          </div>
        </section>

        {/* Getting Help */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Getting Additional Help</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Community Support</h3>
              <p className="text-gray-600 mb-4">
                Join our community forum to ask questions and share solutions with other users.
              </p>
              <a href="https://github.com/cbwinslow/opendiscourse-mcp/discussions" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-blue-600 hover:text-blue-800">
                Join Discussion
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Report Issues</h3>
              <p className="text-gray-600 mb-4">
                Found a bug or have a feature request? Report it on our GitHub repository.
              </p>
              <a href="https://github.com/cbwinslow/opendiscourse-mcp/issues" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-blue-600 hover:text-blue-800">
                Create Issue
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        </section>

        {/* Navigation */}
        <section className="text-center">
          <div className="bg-gray-50 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Still Need Help?</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Check our comprehensive documentation or explore our examples for more guidance.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/getting-started" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                Getting Started Guide
              </Link>
              <Link href="/api-reference" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                API Reference
              </Link>
              <Link href="/examples" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                Examples
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}