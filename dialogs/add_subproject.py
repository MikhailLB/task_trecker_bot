#add_subproject.py
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back, Next, Cancel, Column, Select, ScrollingGroup
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Calendar

from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Base, Task, User, Project, Subproject
from db_functions import project_exists, subproject_exists
from config import SELECT_HIGH

from datetime import datetime
from datetime import date, time
from typing import Any

class AddSubprojectSG(StatesGroup):
    project_select = State()
    subproject_name = State()
    subproject_final = State()

async def project_list_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    result = await db_session.execute(select(Project))
    projects = result.scalars().all()
    return {
        'scroll_list': projects
    }

async def on_project_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    query = select(Project).where(Project.id == item_id)
    result = await db_session.execute(query)
    project = result.scalar()
    if project:
        manager.dialog_data['project'] = project
        await manager.next()
    else:
        await callback.message.answer("Проект не найден. Попробуйте снова.")
        return False

async def subproject_name_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    subproject_name = text
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    project = manager.dialog_data['project']
    if await subproject_exists(db_session, project.id, subproject_name):
        await message.answer(f"Подпроект '{subproject_name}' уже существует для проекта '{project.name}'.")
        return False
    manager.dialog_data['subproject_name'] = text
    await manager.next()

async def subproject_final_getter(dialog_manager: DialogManager, **kwargs):
    project = dialog_manager.dialog_data.get('project')
    subproject_name = dialog_manager.dialog_data.get('subproject_name', '')
    return {
        'project_name': project.name if project else '',
        'subproject_name': subproject_name
    }

async def subproject_final_handler(query: CallbackQuery, widget: Any, manager: DialogManager):
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    project = manager.dialog_data['project']
    subproject = Subproject(name=manager.dialog_data['subproject_name'], project_id=project.id)
    db_session.add(subproject)
    await db_session.commit()
    await manager.done()

add_subproject_dialog = Dialog(
    Window(
        Const("Выберите проект, к которому хотите добавить подпроект:"),
        ScrollingGroup(
            Select(
                Format("{item.name}"),
                id="select_project",
                item_id_getter=lambda item: item.id,
                items='scroll_list',
                on_click=on_project_selected,
                type_factory=int
            ),
            id="scrolling_group",
            width=1,
            height=SELECT_HIGH,
        ),
        Cancel(),
        getter=project_list_getter,
        state=AddSubprojectSG.project_select,
    ),
    Window(
        Const("Введите название подпроекта:"),
        TextInput(id="subproject_name", on_success=subproject_name_handler),
        Cancel(),
        state=AddSubprojectSG.subproject_name,
    ),
    Window(
        Format("Проект: {project_name}\nПодпроект: {subproject_name}"),
        Button(
            text=Const("Сохранить"),
            id="confirm_add",
            on_click=subproject_final_handler,
        ),
        Back(),
        Cancel(),
        getter=subproject_final_getter,
        state=AddSubprojectSG.subproject_final,
    ),
)