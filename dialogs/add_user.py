from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back, Next, Cancel, Select, Column
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Calendar



from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Base, Task, User, Project, Subproject

from typing import Any

class AddUserSG(StatesGroup):
    user_key = State()

from dialogs.edit_user import EditUserSG, edit_user_dialog

async def user_key_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    telegram_key = text
    manager.dialog_data['user_key'] = telegram_key
    result = await db_session.execute(select(User).where(User.telegram_key == telegram_key))
    user = result.scalar()
    if user:
        manager.dialog_data['user_db'] = user
        await manager.start(EditUserSG.user_name, data={"user_db": user})
    else:
        await message.answer('Ключ пользователя не найден в базе данных')

add_user_dialog = Dialog(
    Window(
        Const("Enter user key:"),
        TextInput(id="user_key", on_success=user_key_handler),
        Cancel(),
        state=AddUserSG.user_key,
    ),
)