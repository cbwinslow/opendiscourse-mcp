# Crew AI Crews for OpenDiscourse

This directory contains specialized Crew AI crews designed to work on the OpenDiscourse project. Each crew focuses on a specific aspect of software development and maintenance.

## Available Crews

### 1. Documentation Crew (`documentation_crew.py`)
- **Specialization**: Technical documentation and API documentation
- **Agent**: Technical Documentation Specialist
- **Tasks**:
  - Analyze project structure and architecture
  - Create comprehensive API documentation
  - Document database schemas and data flows
  - Create setup and deployment guides
  - Document testing procedures

### 2. Database Administration Crew (`database_admin_crew.py`)
- **Specialization**: Database optimization and administration
- **Agent**: Database Administrator
- **Tasks**:
  - Analyze and optimize database schemas
  - Review and optimize queries and indexes
  - Design monitoring and alerting systems
  - Create backup and recovery procedures
  - Implement database security best practices

### 3. Software Design Crew (`software_design_crew.py`)
- **Specialization**: System architecture and design patterns
- **Agent**: Software Architect & Designer
- **Tasks**:
  - Analyze current system architecture
  - Design improved system architecture
  - Review and improve code organization
  - Design scalable data processing pipelines
  - Create design guidelines and coding standards

### 4. Engineering Crew (`engineering_crew.py`)
- **Specialization**: Code implementation and optimization
- **Agent**: Senior Software Engineer
- **Tasks**:
  - Review existing codebase and identify issues
  - Implement performance optimizations
  - Enhance error handling and monitoring
  - Improve automated testing
  - Refactor code for better maintainability

## Usage

### Prerequisites

Ensure Crew AI is installed:
```bash
pip install crewai crewai-tools
```

### Running Crews

Use the `run_crews.py` script to execute the crews:

```bash
# Run all crews
python crews/run_crews.py

# Run a specific crew
python crews/run_crews.py documentation
python crews/run_crews.py database
python crews/run_crews.py design
python crews/run_crews.py engineering

# Dry run to see what would be executed
python crews/run_crews.py --dry-run
```

### Command Line Options

- `crew`: Which crew to run (documentation, database, design, engineering, or all)
- `--dry-run`: Show what would be done without actually running crews

## Configuration

Each crew is configured with:
- Specialized agents with domain expertise
- Sequential task execution
- Access to file system and code analysis tools
- Verbose logging for monitoring progress

## Output

Crews will analyze the OpenDiscourse project and provide:
- Detailed analysis reports
- Code improvements and optimizations
- Documentation updates
- Architectural recommendations
- Implementation suggestions

## Integration

The crews are designed to work with the existing OpenDiscourse MCP server project structure and can:
- Read and analyze source code
- Access database schemas
- Review configuration files
- Generate documentation
- Suggest code improvements

## Dependencies

- crewai>=0.30.0
- crewai-tools>=0.2.6
