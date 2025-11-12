from crewai import Agent, Crew, Process, Task
from crewai_tools import DirectoryReadTool, FileReadTool, CodeDocsTool
from crewai_tools import DirectoryReadTool, FileReadTool, CodeDocsTool

# Documentation Crew
documentation_agent = Agent(
    role="Technical Documentation Specialist",
    goal="Create comprehensive, accurate, and well-structured documentation for the OpenDiscourse project",
    backstory="""You are an expert technical writer with extensive experience in documenting complex software systems,
    particularly those involving data ingestion, APIs, and database operations. You excel at creating clear,
    concise documentation that helps developers understand and contribute to projects.""",
    tools=[DirectoryReadTool(), FileReadTool(), CodeDocsTool()],
    verbose=True
)

documentation_tasks = [
    Task(
        description="Analyze the project structure and codebase to understand the system architecture",
        expected_output="A detailed analysis of the project structure, key components, and system architecture",
        agent=documentation_agent
    ),
    Task(
        description="Create comprehensive API documentation for all endpoints and MCP server functionality",
        expected_output="Complete API documentation with examples, parameters, and response formats",
        agent=documentation_agent
    ),
    Task(
        description="Document database schemas, relationships, and data flow processes",
        expected_output="Database documentation including schema diagrams, table relationships, and data ingestion flows",
        agent=documentation_agent
    ),
    Task(
        description="Create setup and deployment guides for the entire system",
        expected_output="Step-by-step installation, configuration, and deployment documentation",
        agent=documentation_agent
    ),
    Task(
        description="Document testing procedures and create testing guides",
        expected_output="Comprehensive testing documentation including unit tests, integration tests, and monitoring",
        agent=documentation_agent
    )
]

documentation_crew = Crew(
    agents=[documentation_agent],
    tasks=documentation_tasks,
    process=Process.sequential,
    verbose=True
)
