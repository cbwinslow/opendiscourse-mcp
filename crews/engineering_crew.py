from crewai import Agent, Crew, Process, Task
from crewai_tools import DirectoryReadTool, FileReadTool, CodeDocsTool

# Engineering Crew
engineering_agent = Agent(
    role="Senior Software Engineer",
    goal="Implement, optimize, and maintain high-quality code for the OpenDiscourse project",
    backstory="""You are a senior software engineer with expertise in Python, FastAPI, database integration,
    and distributed systems. You have extensive experience in building robust, scalable applications and
    excel at writing clean, efficient, and well-tested code.""",
    tools=[DirectoryReadTool(), FileReadTool(), CodeDocsTool()],
    verbose=True
)

engineering_tasks = [
    Task(
        description="Review existing codebase and identify code quality issues, bugs, and improvement opportunities",
        expected_output="Detailed code review with identified issues, refactoring suggestions, and quality improvements",
        agent=engineering_agent
    ),
    Task(
        description="Implement performance optimizations and memory management improvements",
        expected_output="Optimized code with improved performance, reduced memory usage, and better resource management",
        agent=engineering_agent
    ),
    Task(
        description="Enhance error handling, logging, and monitoring throughout the application",
        expected_output="Comprehensive error handling, structured logging, and monitoring integration",
        agent=engineering_agent
    ),
    Task(
        description="Implement automated testing improvements and test coverage enhancements",
        expected_output="Expanded test suite with better coverage, integration tests, and automated testing pipelines",
        agent=engineering_agent
    ),
    Task(
        description="Refactor code for better maintainability, readability, and adherence to best practices",
        expected_output="Clean, well-structured code following Python best practices and design patterns",
        agent=engineering_agent
    )
]

engineering_crew = Crew(
    agents=[engineering_agent],
    tasks=engineering_tasks,
    process=Process.sequential,
    verbose=True
)
