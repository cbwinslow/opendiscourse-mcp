from crewai import Agent, Crew, Process, Task
from crewai_tools import DirectoryReadTool, FileReadTool, CodeDocsTool

# Database Administration Crew
db_admin_agent = Agent(
    role="Database Administrator",
    goal="Optimize database performance, ensure data integrity, and manage database operations for the OpenDiscourse project",
    backstory="""You are a senior database administrator with deep expertise in PostgreSQL, data modeling,
    performance optimization, and database security. You have extensive experience with large-scale data ingestion
    systems and know how to design efficient schemas for complex data relationships.""",
    tools=[DirectoryReadTool(), FileReadTool(), CodeDocsTool()],
    verbose=True
)

db_admin_tasks = [
    Task(
        description="Analyze existing database schemas and identify optimization opportunities",
        expected_output="Detailed analysis of current database schemas with performance recommendations and optimization suggestions",
        agent=db_admin_agent
    ),
    Task(
        description="Review and optimize database queries, indexes, and data ingestion processes",
        expected_output="Optimized SQL queries, index recommendations, and improved data ingestion strategies",
        agent=db_admin_agent
    ),
    Task(
        description="Design and implement database monitoring and alerting systems",
        expected_output="Comprehensive monitoring setup with triggers, alerts, and performance dashboards",
        agent=db_admin_agent
    ),
    Task(
        description="Create database backup, recovery, and maintenance procedures",
        expected_output="Complete backup and recovery documentation, maintenance scripts, and disaster recovery plans",
        agent=db_admin_agent
    ),
    Task(
        description="Implement database security best practices and access controls",
        expected_output="Security audit, access control implementation, and security documentation",
        agent=db_admin_agent
    )
]

database_admin_crew = Crew(
    agents=[db_admin_agent],
    tasks=db_admin_tasks,
    process=Process.sequential,
    verbose=True
)
