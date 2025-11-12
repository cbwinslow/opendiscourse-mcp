from crewai import Agent, Crew, Process, Task
from crewai_tools import DirectoryReadTool, FileReadTool, CodeDocsTool

# Software Design Crew
design_agent = Agent(
    role="Software Architect & Designer",
    goal="Design scalable, maintainable, and efficient software architecture for the OpenDiscourse project",
    backstory="""You are a senior software architect with extensive experience in designing distributed systems,
    microservices, and data-intensive applications. You excel at creating clean architectures that balance
    performance, maintainability, and scalability while considering future growth and evolution.""",
    tools=[DirectoryReadTool(), FileReadTool(), CodeDocsTool()],
    verbose=True
)

design_tasks = [
    Task(
        description="Analyze current system architecture and identify design patterns and anti-patterns",
        expected_output="Comprehensive architectural analysis with identified patterns, potential issues, and improvement recommendations",
        agent=design_agent
    ),
    Task(
        description="Design improved system architecture with better separation of concerns and modularity",
        expected_output="Detailed architectural design documents with component diagrams, data flow diagrams, and design rationale",
        agent=design_agent
    ),
    Task(
        description="Review and improve code organization, package structure, and dependency management",
        expected_output="Restructured codebase with improved organization, clear module boundaries, and optimized dependencies",
        agent=design_agent
    ),
    Task(
        description="Design scalable data processing pipelines and ingestion workflows",
        expected_output="Optimized data pipeline designs with performance considerations, error handling, and monitoring integration",
        agent=design_agent
    ),
    Task(
        description="Create design guidelines and coding standards for the project",
        expected_output="Comprehensive design guidelines, coding standards, and best practices documentation",
        agent=design_agent
    )
]

software_design_crew = Crew(
    agents=[design_agent],
    tasks=design_tasks,
    process=Process.sequential,
    verbose=True
)
