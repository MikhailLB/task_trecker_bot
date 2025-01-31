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
from models import User, Project, Subproject, Task
from db_functions import project_exists
from sqlalchemy.orm import selectinload
from sqlalchemy import intersect, desc

from datetime import datetime
from datetime import date, time
from typing import Any

from common_func import get_tasks_for_user
from models import Base, Task, User, Project, Subproject, TaskAnswer
from config import SELECT_HIGH

class SendPlanSG(StatesGroup):
    presentations_show = State()
    presentation_show= State()

def get_all_users_query():
    subquery = (
        select(Task.responsible_user_id)
        .where(Task.is_inplan == True)
        .distinct()
    )
    query = select(User).where(User.role != 'UNGREGISTERD').where(User.id.in_(subquery))
    return query

async def presentation_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    user_id = dialog_manager.dialog_data['user_id']
    presentation_text = await get_tasks_for_user(db_session, user_id)
    return {
        'presentation_text': presentation_text
    }

async def users_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    manager.dialog_data['user_id'] = item_id
    await manager.next()

async def presentations_select_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    
    users = (await db_session.execute(get_all_users_query())).scalars().all()

    return {
        'scroll_list' : [(f'{user.username}', user.id)for user in users]
    }

async def send_all_users_presentations(callback: CallbackQuery, button: Button, manager: DialogManager):
    db_session: AsyncSession = manager.middleware_data.get('db_session')

    users = (await db_session.execute(get_all_users_query())).scalars().all()
    for user in users:
        presentation_text = await get_tasks_for_user(db_session, user.id)
        await callback.message.answer(f"Представление для {user.username}")
        await callback.message.answer(presentation_text, parse_mode='html')

async def plan_confirm_handler(callback: CallbackQuery, button: Button, manager: DialogManager):
    db_session: AsyncSession = manager.middleware_data.get('db_session')

    users = (await db_session.execute(get_all_users_query())).scalars().all()
    bot = manager.start_data['bot']
    for user in users:
        presentation_text = await get_tasks_for_user(db_session, user.id)
        await bot.send_message(user.telegram_id, presentation_text, parse_mode='html')
    await callback.message.answer("Планы задач отправлены пользователям!")



send_plan_dialog = Dialog(
Window(
    Const("Представления:"),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="select_a",
            item_id_getter=lambda item: item[1],  
            items='scroll_list',
            on_click=users_select_handler,
            type_factory=int

        ),
        id="scrolling_group",
        width=1,
        height=SELECT_HIGH,

    ),
    Button(
        Const("Печать все"), id="print_all", on_click=send_all_users_presentations,
    ),
    Button(
        Const("Подтвердить план"), id="plan_confirm", on_click=plan_confirm_handler,
    ),
    Cancel(),
    getter=presentations_select_getter,
    state=SendPlanSG.presentations_show,
    ),
    Window(
    Format("{presentation_text}"),
    Back(),
    getter=presentation_getter,
    state=SendPlanSG.presentation_show,
    parse_mode="html",
    ),
)