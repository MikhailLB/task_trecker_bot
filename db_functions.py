from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Base, Task, User, Project, Subproject

async def project_exists(db_session, project_name):
    query = select(Project).where(Project.name == project_name)
    result = await db_session.execute(query)
    return result.scalars().first() is not None

async def number_of_projects(db_session, project_name):
    result = await db_session.execute(select(func.count(Project.id)))
    return result.scalars()

async def subproject_exists(db_session, project_id, subproject_name):
    query = select(Subproject).where(Subproject.project_id == project_id, Subproject.name == subproject_name)
    result = await db_session.execute(query)
    return result.scalars().first() is not None