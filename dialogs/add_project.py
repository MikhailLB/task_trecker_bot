from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back, Next, Cancel, Column, Select
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Calendar

from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Project, Subproject, Task
from db_functions import project_exists


from datetime import datetime
from datetime import date, time
from typing import Any

class AddProjectSG(StatesGroup):
    project_name = State()
    project_final= State()

async def project_name_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    project_name = text
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    if await project_exists(db_session, project_name):
        await message.answer(f"Проект '{project_name}' уже существует.")
        return False
    manager.dialog_data['project_name'] = text
    await manager.next()

async def project_final_getter(dialog_manager: DialogManager, **kwargs):
    return {
        'project_name': dialog_manager.dialog_data.get('project_name', '')
    }

async def project_final_handler(query: CallbackQuery, widget: Any, manager: DialogManager):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    project = Project(name=manager.dialog_data['project_name'])
    db_session.add(project)
    await db_session.commit()
    await manager.done()

add_project_dialog = Dialog(
Window(
    Const("Введите название проекта:"),
    TextInput(id="project_name", on_success=project_name_handler),
    Cancel(),
    state=AddProjectSG.project_name,
),
Window(
    Format("Проект: {project_name}"),
    Button(
        text=Const("Сохранить"),
        id="confirm_add",
        on_click=project_final_handler,
    ),
    Back(),
    Cancel(),
    getter=project_final_getter,
    state=AddProjectSG.project_final,
),
)