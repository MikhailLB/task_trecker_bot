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
from models import Base, Task, User, Project, Subproject


from datetime import datetime
from datetime import date, time
from typing import Any

class EditUserSG(StatesGroup):
    user_name = State()
    user_contact_text = State()
    user_role = State()
    user_final = State()

async def on_dialog_start(start_data: Any, manager: DialogManager):
    manager.dialog_data['user_db'] = manager.start_data['user_db']

async def user_name_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['user_name'] = text
    await manager.next()

async def user_name_getter(dialog_manager: DialogManager, **kwargs):
    return {
        'db_user_name' : dialog_manager.dialog_data['user_db'].username
    }

async def user_contact_text_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['user_contact_text'] = text
    await manager.next()

async def user_contact_text_getter(dialog_manager: DialogManager, **kwargs):
    return {
        'db_user_contact_text' : dialog_manager.dialog_data['user_db'].contact_text
    }

# async def user_role_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
#     manager.dialog_data['user_role'] = text
#     await manager.next()

async def user_role_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data['user_role'] = item_id
    await manager.next()

async def user_role_getter(dialog_manager: DialogManager, **kwargs):
    return {
        'db_user_role' : dialog_manager.dialog_data['user_db'].role
    }

async def user_final_handler(query: CallbackQuery, widget: Any, manager: DialogManager):

    db_session : AsyncSession = manager.middleware_data.get('db_session')
    user = manager.dialog_data['user_db']
    user.role = manager.dialog_data.get('user_role', manager.dialog_data['user_db'].role)
    user.username = manager.dialog_data.get('user_name', manager.dialog_data['user_db'].username)
    user.contact_text = manager.dialog_data.get('user_contact_text', manager.dialog_data['user_db'].contact_text)
    db_session.add(user)
    await db_session.commit()
    await manager.done()

async def user_final_getter(dialog_manager: DialogManager, **kwargs):
    return {
        "user_key" : dialog_manager.dialog_data['user_db'].telegram_key,
        "user_name": dialog_manager.dialog_data.get('user_name', dialog_manager.dialog_data['user_db'].username),
        "user_contact_text": dialog_manager.dialog_data.get('user_contact_text', dialog_manager.dialog_data['user_db'].contact_text),
        "user_role": dialog_manager.dialog_data.get('user_role', dialog_manager.dialog_data['user_db'].role),
    }

edit_user_dialog = Dialog(
    Window(
        Format("Измените имя пользователя. Текущие: {db_user_name}"),
        TextInput(id="user_name", on_success=user_name_handler, on_error=user_name_handler),
        Back(),
        Next(),
        Cancel(),
        getter=user_name_getter,
        state=EditUserSG.user_name,
    ),
    Window(
        Format("Измените текст пользователя. Текущий :{db_user_contact_text}"),
        TextInput(id="user_contact_text", on_success=user_contact_text_handler, on_error=user_contact_text_handler),
        Back(),
        Next(),
        Cancel(),
        getter=user_contact_text_getter,
        state=EditUserSG.user_contact_text,
    ),
    Window(
        Format("Измените роль пользователя. Текущий :{db_user_role}"),
        # TextInput(id="user_role", on_success=user_role_handler, on_error=user_role_handler),
        Column(
            Select(
            Format("{item}"),
            id="user_role_select",
            item_id_getter=lambda item: item,  # Используем сам элемент массива как id
            items=['ADMIN', 'MODERATOR', 'USER', 'UNGREGISTERD'],  # Используем элементы из данных окна по ключу `fruits`
            on_click=user_role_select_handler
        )),
        Button(
            text=Const(' '),
            id='placeholder'
        ),
        Back(),
        Next(),
        Cancel(),
        getter=user_role_getter,
        state=EditUserSG.user_role,
    ),
    Window(
        Format("Обновленные данные пользователя:\nКлюч: {user_key}\nИмя: {user_name}\nТекст: {user_contact_text}\nRole: {user_role}"),
        Button(
            text=Const("Сохранить"),
            id="confirm_add",
            on_click=user_final_handler,
        ),
        Back(),
        Cancel(),
        getter=user_final_getter,
        state=EditUserSG.user_final,

    ),
    on_start=on_dialog_start
)