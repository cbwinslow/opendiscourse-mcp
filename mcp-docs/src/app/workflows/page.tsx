'use client'

import { useState } from 'react'
import Link from 'next/link'

type WorkflowType = 'unified-ingestion' | 'personal-monitoring'

export default function Workflows() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType>('unified-ingestion')

  interface WorkflowSection {
    title: string
    content: string
    features?: string[]
    steps?: string[]
    components?: Array<{ name: string; description: string }>
    examples?: Array<{ title: string; code: string }>
    schema?: Array<{ table: string; description: string }>
  }

  interface WorkflowData {
    title: string
    description: string
    icon: React.ReactNode
    sections: WorkflowSection[]
  }

  const workflowData: Record<WorkflowType, WorkflowData> = {
    'unified-ingestion': {
      title: 'Unified Ingestion System',
      description: 'Complete legislative data ingestion from Congress.gov, OpenStates, and GovInfo with unified API access and automated processing.',
      icon: (
        <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      sections: [
        {
          title: 'System Overview',
          content: 'The Unified Ingestion System provides comprehensive access to legislative data from multiple sources through a single, optimized interface. It combines Congress.gov, OpenStates, and GovInfo APIs with advanced processing capabilities.',
          features: [
            'Multi-source data integration',
            'Automated bulk processing',
            'Real-time monitoring and logging',
            'Performance optimization with parallel processing',
            'Comprehensive error handling',
            'Flexible export formats (CSV, JSON, Parquet)'
          ]
        },
        {
          title: 'Quick Start',
          content: 'Get started with the unified ingestion system in minutes:',
          steps: [
            'Install dependencies: pip install -r requirements.txt',
            'Configure API keys for each data source',
            'Initialize the database: python mcp_server/db_init.py',
            'Run unified ingestion: python unified_ingestion.py',
            'Monitor progress through the web interface'
          ]
        },
        {
          title: 'Core Components',
          content: 'The system consists of several key components working together:',
          components: [
            {
              name: 'Base Client',
              description: 'Abstract base class providing common functionality for all API clients'
            },
            {
              name: 'Congress Client',
              description: 'Federal legislative data access with advanced querying capabilities'
            },
            {
              name: 'OpenStates Client',
              description: 'State-level legislative data from all 50 states'
            },
            {
              name: 'GovInfo Client',
              description: 'Official government publications and documents'
            },
            {
              name: 'Enhanced Ingestion',
              description: 'Parallel processing and performance optimization'
            }
          ]
        },
        {
          title: 'Advanced Features',
          content: 'Powerful features for comprehensive data analysis:',
          features: [
            'GPU acceleration for supported operations',
            'Intelligent caching and rate limiting',
            'Automatic retry mechanisms with exponential backoff',
            'Real-time progress tracking',
            'Comprehensive logging and monitoring',
            'Bulk data processing with parallel execution'
          ]
        },
        {
          title: 'API Usage Examples',
          content: 'Common usage patterns for the unified system:',
          examples: [
            {
              title: 'Basic Bill Search',
              code: `from mcp_server.clients.congress_client import CongressClient

client = CongressClient(api_key="your-key")
bills = client.search_bills(congress=118, billType="hr", page=1)`
            },
            {
              title: 'Advanced Querying',
              code: `results = client.query_congress_bills(
    filters={"sponsor_party": "D", "subjects": ["health"]},
    limit=100
)`
            },
            {
              title: 'Bulk Data Export',
              code: `client.export_congress_data(
    data_type="bills",
    format="csv",
    filters={"congress": 118}
)`
            }
          ]
        }
      ]
    },
    'personal-monitoring': {
      title: 'Personal Monitoring System',
      description: 'AI-powered personal productivity monitoring with activity tracking, screen capture analysis, and intelligent insights for optimizing your workflow.',
      icon: (
        <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      sections: [
        {
          title: 'System Overview',
          content: 'The Personal Monitoring System provides comprehensive tracking of your digital activities with AI-powered analysis and insights. It monitors applications, captures screenshots, analyzes productivity patterns, and provides intelligent summaries.',
          features: [
            'Real-time application usage tracking',
            'Automated screen capture with AI analysis',
            'Keystroke and mouse activity monitoring',
            'System metrics collection',
            'AI-powered activity summarization',
            'Productivity insights and recommendations'
          ]
        },
        {
          title: 'Quick Start',
          content: 'Set up personal monitoring in minutes:',
          steps: [
            'Install monitoring dependencies: ./setup_monitoring.sh',
            'Start Ollama service: ./start_ollama.sh',
            'Pull AI model: ollama pull llama3.2:1b',
            'Create database tables: ./create_tables.sh',
            'Start monitoring: ./start_monitoring.sh'
          ]
        },
        {
          title: 'Core Components',
          content: 'The monitoring system consists of four main components:',
          components: [
            {
              name: 'Activity Logger',
              description: 'Tracks application usage, keystrokes, mouse clicks, and system metrics in real-time'
            },
            {
              name: 'Screen Capture',
              description: 'Automated screenshot capture with AI-powered content analysis and categorization'
            },
            {
              name: 'Ollama Summarizer',
              description: 'Local AI analysis using Llama 3.2 model for intelligent activity summarization'
            },
            {
              name: 'Database Schema',
              description: 'Optimized PostgreSQL storage with JSONB fields for flexible data management'
            }
          ]
        },
        {
          title: 'Monitoring Features',
          content: 'Comprehensive monitoring capabilities:',
          features: [
            'Application window title and process tracking',
            'Keystroke counting (without content capture)',
            'Mouse movement and click tracking',
            'CPU, memory, and disk usage monitoring',
            'Periodic screenshot capture (every 5 minutes)',
            'AI-powered image analysis and categorization',
            'Real-time activity summarization'
          ]
        },
        {
          title: 'AI Analysis',
          content: 'Powered by local Ollama integration:',
          features: [
            'Local Llama 3.2 1B model for privacy',
            'Real-time screenshot content analysis',
            'Activity categorization (work, entertainment, development)',
            'Productivity pattern recognition',
            'Intelligent daily and weekly summaries',
            'Personalized insights and recommendations'
          ]
        },
        {
          title: 'Database Schema',
          content: 'Four optimized tables for comprehensive data storage:',
          schema: [
            {
              table: 'activity_logs',
              description: 'Application usage, keystrokes, mouse activity, and system metrics'
            },
            {
              table: 'screen_captures',
              description: 'Screenshot metadata, file paths, and AI analysis results'
            },
            {
              table: 'agent_interactions',
              description: 'AI analysis results, summaries, and insights'
            },
            {
              table: 'system_metrics',
              description: 'Performance metrics, resource usage, and monitoring statistics'
            }
          ]
        }
      ]
    }
  }

  const currentWorkflow = workflowData[selectedWorkflow]

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">System Workflows</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Complete documentation for unified ingestion and personal monitoring systems with step-by-step guides and examples.
          </p>
        </div>

        {/* Workflow Selection */}
        <div className="flex flex-wrap gap-4 mb-12 justify-center">
          {(Object.keys(workflowData) as WorkflowType[]).map(workflow => (
            <button
              key={workflow}
              onClick={() => setSelectedWorkflow(workflow)}
              className={`flex items-center space-x-3 px-6 py-3 rounded-lg font-semibold transition-all ${
                selectedWorkflow === workflow
                  ? 'bg-blue-600 text-white shadow-lg scale-105'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {workflowData[workflow].icon}
              <span>{workflowData[workflow].title}</span>
            </button>
          ))}
        </div>

        {/* Workflow Content */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          {/* Workflow Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-8">
            <div className="flex items-center space-x-4 mb-4">
              {currentWorkflow.icon}
              <h2 className="text-3xl font-bold">{currentWorkflow.title}</h2>
            </div>
            <p className="text-blue-100 text-lg">{currentWorkflow.description}</p>
          </div>

          {/* Workflow Sections */}
          <div className="p-8 space-y-12">
            {currentWorkflow.sections.map((section, index) => (
              <section key={index}>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">{section.title}</h3>
                <p className="text-gray-600 mb-6 text-lg">{section.content}</p>

                {/* Features List */}
                {section.features && (
                  <div className="grid md:grid-cols-2 gap-4 mb-6">
                    {section.features.map((feature, idx) => (
                      <div key={idx} className="flex items-start space-x-3">
                        <svg className="w-6 h-6 text-green-500 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span className="text-gray-700">{feature}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Steps List */}
                {section.steps && (
                  <ol className="space-y-3 mb-6">
                    {section.steps.map((step, idx) => (
                      <li key={idx} className="flex items-start space-x-3">
                        <span className="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-semibold">
                          {idx + 1}
                        </span>
                        <code className="bg-gray-100 px-3 py-2 rounded text-sm flex-1">{step}</code>
                      </li>
                    ))}
                  </ol>
                )}

                {/* Components Grid */}
                {section.components && (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
                    {section.components.map((component, idx) => (
                      <div key={idx} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                        <h4 className="font-semibold text-gray-900 mb-2">{component.name}</h4>
                        <p className="text-gray-600 text-sm">{component.description}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Code Examples */}
                {'examples' in section && section.examples && (
                  <div className="space-y-6 mb-6">
                    {section.examples.map((example, idx) => (
                      <div key={idx}>
                        <h4 className="font-semibold text-gray-900 mb-2">{example.title}</h4>
                        <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm">
                          <code>{example.code}</code>
                        </pre>
                      </div>
                    ))}
                  </div>
                )}

                {/* Schema Table */}
                {'schema' in section && section.schema && (
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="text-left p-3 border border-gray-200 font-semibold text-gray-900">Table</th>
                          <th className="text-left p-3 border border-gray-200 font-semibold text-gray-900">Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.schema.map((item, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="p-3 border border-gray-200 font-mono text-sm">{item.table}</td>
                            <td className="p-3 border border-gray-200 text-gray-700">{item.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            ))}
          </div>
        </div>

        {/* Navigation */}
        <section className="text-center mt-12">
          <div className="bg-gray-50 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Explore More</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Ready to dive deeper? Check out our API reference and examples for practical implementation guidance.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/api-reference" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                View API Reference
              </Link>
              <Link href="/examples" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                View Examples
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}