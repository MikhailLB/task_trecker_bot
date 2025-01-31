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
from dialogs.edit_user import EditUserSG
from config import SELECT_HIGH

class MenuUsersSG(StatesGroup):
    users_select = State()

async def users_select_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    q = select(User)
    
    users = (await db_session.execute(q)).scalars().all()

    return {
        'scroll_list' : [(f'{user.username}:{user.role}', user.id)for user in users]
    }

async def users_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    result = await db_session.execute(select(User).where(User.id == item_id))
    user = result.scalar()

    await manager.start(EditUserSG.user_name, data={"user_db": user})

menu_users_dialog = Dialog(
Window(
    Const("Пользователи:"),
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
    Cancel(),
    getter=users_select_getter,
    state=MenuUsersSG.users_select,
    ),
)