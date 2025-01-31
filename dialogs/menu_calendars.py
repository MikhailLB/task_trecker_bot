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

from datetime import datetime, timedelta
from datetime import date, time
from typing import Any

from common_func import get_tasks_for_user
from models import Base, Task, User, Project, Subproject, TaskAnswer
from dialogs.edit_user import EditUserSG
from config import SELECT_HIGH

class MenuCalendarsSG(StatesGroup):
    month_select = State()
    week_select = State()
    day_select = State()


async def task_calendar_handler(callback: CallbackQuery, widget, manager: DialogManager, selected_date: date):
    await callback.answer(str(selected_date))
    manager.dialog_data['target_date'] = datetime.combine(selected_date, datetime.min.time())
    await manager.switch_to(MenuCalendarsSG.day_select)

async def days_select_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    current_date = datetime.combine(datetime.now().date(), datetime.min.time())
    target_date = dialog_manager.dialog_data.get('target_date', current_date)
    q = (
        select(Task)
        .where(Task.deadline == target_date)
        .order_by(Task.execution_time.nulls_last())  # Сначала ранние задачи, затем NULL
    )
    
    tasks = (await db_session.execute(q)).scalars().all()
    return {
        'target_date' : target_date.strftime('%d.%m.%Y'),
        'scroll_list' : [(f'{task.task_text[:45]}', task.id)for task in tasks]
    }

async def week_select_getter(dialog_manager: DialogManager, **kwargs):
    current_date = datetime.now().date()
    dates_array = []

    for i in range(7):
        date = current_date + timedelta(days=i)
        dates_array.append(date.strftime('%Y-%m-%d'))
    return {
        'scroll_list' : dates_array
    }

async def week_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    date_object = datetime.strptime(item_id, '%Y-%m-%d')
    manager.dialog_data['target_date'] = date_object
    await manager.switch_to(MenuCalendarsSG.day_select)


async def days_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    result = await db_session.execute( select(Task).join(Task.responsible_user).where(Task.id == item_id) )
    task = result.scalar()
    task_menu_data={
        'taskORM': task,
        'userORM':manager.start_data['userORM'],
        'bot': manager.start_data['bot'],
        }
    await manager.start(manager.start_data['task_show_mode_state'], data=task_menu_data)


async def on_dialog_start(start_data: Any, manager: DialogManager):
    manager.dialog_data['show_mode_state'] = manager.current_context().state

async def back_to_show_handler(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(manager.dialog_data['show_mode_state'])

menu_calendars_dialog = Dialog(
Window(
    Const("Выберете дату исполнения задачи:"),
    Calendar(id="calendar", on_click=task_calendar_handler),
    Cancel(),
    state=MenuCalendarsSG.month_select,
),
Window(
    Const("Выберете дату исполнения задачи:"),
    Column(
        Select(
            Format("{item}"),
            id="select_a",
            item_id_getter=lambda item: item,  
            items='scroll_list',
            on_click=week_select_handler,
            type_factory=str

        ),
    ),
    Cancel(),
    state=MenuCalendarsSG.week_select,
    getter=week_select_getter,
),
Window(
    Format("Задачи на {target_date}:"),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="select_a",
            item_id_getter=lambda item: item[1],  
            items='scroll_list',
            on_click=days_select_handler,
            type_factory=int

        ),
        id="scrolling_group",
        width=1,
        height=SELECT_HIGH,

    ),
    Button(
        Const("Back"), id="back_to_show", on_click=back_to_show_handler,
    ),
    Cancel(),
    getter=days_select_getter,
    state=MenuCalendarsSG.day_select,
    ),
    on_start=on_dialog_start,
)