#models.py
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

Base.metadata.naming_convention = convention

# Определяем модель пользователя
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
    telegram_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contact_text: Mapped[str] = mapped_column(String(), nullable=True, default='Здравствуйте!')
    role: Mapped[str] = mapped_column(String(50), nullable=False, default='UNGREGISTERD')

    tasks_responsible_for = relationship('Task', back_populates='responsible_user', foreign_keys='Task.responsible_user_id')
    tasks_created_by = relationship('Task', back_populates='author', foreign_keys='Task.author_id')
    task_answers = relationship('TaskAnswer', back_populates='user')

    def __repr__(self):
        return f'<User {self.username}>'


# Определяем модель проекта
class Project(Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    tasks = relationship('Task', back_populates='project')
    subprojects = relationship('Subproject', back_populates='project')


# Определяем модель подпроекта
class Subproject(Base):
    __tablename__ = 'subprojects'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'), index=True)

    tasks = relationship('Task', back_populates='subproject')
    project = relationship('Project', back_populates='subprojects')


# Определяем модель задачи
class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_text: Mapped[str] = mapped_column(String(50), nullable=False)
    result_description: Mapped[str] = mapped_column(String(200), nullable=False)
    link: Mapped[str] = mapped_column(String(255), nullable=True)
    deadline: Mapped[datetime] = mapped_column(nullable=False)
    execution_time: Mapped[datetime] = mapped_column(nullable=True)
    responsible_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'), index=True)
    subproject_id: Mapped[int] = mapped_column(ForeignKey('subprojects.id'), index=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default='нормальный')
    status_text: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    is_inplan: Mapped[bool] = mapped_column(default=False)
    is_arhived: Mapped[bool] = mapped_column(default=False)

    responsible_user = relationship('User', back_populates='tasks_responsible_for', foreign_keys=[responsible_user_id])
    project = relationship('Project', back_populates='tasks')
    subproject = relationship('Subproject', back_populates='tasks')
    author = relationship('User', back_populates='tasks_created_by', foreign_keys=[author_id])
    answers = relationship('TaskAnswer', back_populates='task', cascade='all, delete-orphan')


# Определяем модель ответа на задачу
class TaskAnswer(Base):
    __tablename__ = 'task_answers'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    date_answered: Mapped[datetime] = mapped_column(default=func.now())

    user = relationship('User', back_populates='task_answers')
    task = relationship('Task', back_populates='answers')

    def __repr__(self):
        return f'<TaskAnswer {self.id} for task {self.task.id}>'