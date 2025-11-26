#!/usr/bin/env python3
"""Simple coverage analysis script."""

import os
import sys
import inspect
import importlib
from typing import Set, Dict, List

def get_module_functions(module_path: str) -> Dict[str, List[str]]:
    """Get all functions and methods in a module."""
    functions = {}
    try:
        # Convert path to module name
        module_name = module_path.replace('/', '.').replace('.py', '')

        # Import the module
        module = importlib.import_module(module_name)

        # Get all members
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                source_file = inspect.getfile(obj)
                if module_path in source_file:
                    if source_file not in functions:
                        functions[source_file] = []
                    functions[source_file].append(name)
            elif inspect.isclass(obj):
                # Get methods of the class
                for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if not method_name.startswith('_'):
                        source_file = inspect.getfile(method_obj)
                        if module_path in source_file:
                            if source_file not in functions:
                                functions[source_file] = []
                            functions[source_file].append(f"{obj.__name__}.{method_name}")
    except Exception as e:
        print(f"Error analyzing {module_path}: {e}")

    return functions

def analyze_main_coverage():
    """Analyze coverage for main.py."""
    print("Analyzing main.py coverage...")

    main_functions = get_module_functions('mcp_server/main')
    print(f"Found {len(main_functions)} files with functions in main.py")

    for file, funcs in main_functions.items():
        print(f"  {file}: {len(funcs)} functions")
        for func in funcs[:5]:  # Show first 5
            print(f"    - {func}")
        if len(funcs) > 5:
            print(f"    ... and {len(funcs) - 5} more")

def analyze_client_coverage():
    """Analyze coverage for API clients."""
    print("\nAnalyzing client coverage...")

    clients = ['congress_client', 'openstates_client', 'govinfo_client']
    for client in clients:
        print(f"\n{client}:")
        client_functions = get_module_functions(f'mcp_server/clients/{client}')
        for file, funcs in client_functions.items():
            print(f"  {len(funcs)} functions")
            # Count methods (functions with dots)
            methods = [f for f in funcs if '.' in f]
            print(f"  {len(methods)} methods")

def main():
    print("Coverage Analysis for MCP Server")
    print("=" * 40)

    analyze_main_coverage()
    analyze_client_coverage()

    print("\nCoverage Targets:")
    print("- main.py: 90%+")
    print("- API clients: 80%+")
    print("- Overall: 80%+")

if __name__ == "__main__":
    main()
