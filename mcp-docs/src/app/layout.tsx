import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MCP Legislative Data Server - Documentation",
  description: "Comprehensive documentation and help system for the MCP Legislative Data Server API",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div className="min-h-screen bg-gray-50">
          {/* Navigation Header */}
          <nav className="bg-white shadow-lg border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center">
                  <Link href="/" className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                      <span className="text-white font-bold text-sm">MCP</span>
                    </div>
                    <span className="font-bold text-xl text-gray-900">Legislative Data Server</span>
                  </Link>
                </div>

                <div className="flex items-center space-x-8">
                  <Link href="/" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors">
                    Home
                  </Link>
                  <Link href="/getting-started" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors">
                    Getting Started
                  </Link>
                  <Link href="/api-reference" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors">
                    API Reference
                  </Link>
                  <Link href="/examples" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors">
                    Examples
                  </Link>
                  <Link href="/troubleshooting" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors">
                    Troubleshooting
                  </Link>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="flex-1">
            {children}
          </main>

          {/* Footer */}
          <footer className="bg-white border-t border-gray-200 mt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className="grid md:grid-cols-3 gap-8">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">
                    MCP Legislative Data Server
                  </h3>
                  <p className="text-sm text-gray-600">
                    Comprehensive API for legislative data analysis across Congress.gov, OpenStates, and GovInfo.
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">
                    Quick Links
                  </h3>
                  <ul className="space-y-2">
                    <li><Link href="/getting-started" className="text-sm text-gray-600 hover:text-blue-600">Getting Started</Link></li>
                    <li><Link href="/api-reference" className="text-sm text-gray-600 hover:text-blue-600">API Reference</Link></li>
                    <li><Link href="/examples" className="text-sm text-gray-600 hover:text-blue-600">Examples</Link></li>
                  </ul>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">
                    Data Sources
                  </h3>
                  <ul className="space-y-2">
                    <li><span className="text-sm text-gray-600">Congress.gov API</span></li>
                    <li><span className="text-sm text-gray-600">OpenStates API</span></li>
                    <li><span className="text-sm text-gray-600">GovInfo API</span></li>
                  </ul>
                </div>
              </div>
              <div className="mt-8 pt-8 border-t border-gray-200">
                <p className="text-sm text-gray-500 text-center">
                  © 2025 MCP Legislative Data Server. Built with Next.js and TypeScript.
                </p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
