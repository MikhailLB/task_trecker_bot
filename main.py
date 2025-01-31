from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import types

from aiogram_dialog import (
    Dialog, DialogManager, setup_dialogs, StartMode, Window,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

import uuid
import asyncio
from re import Match
from datetime import datetime, timedelta

from dialogs.add_task import AddTaskSG, add_task_dialog
from dialogs.add_user import AddUserSG, add_user_dialog
from dialogs.add_project import AddProjectSG, add_project_dialog
from dialogs.add_subproject import AddSubprojectSG, add_subproject_dialog
from dialogs.edit_user import EditUserSG, edit_user_dialog
from dialogs.searh_task import SearchTaskSG, search_task_dialog
from dialogs.menu_task import MenuTaskSG, menu_task_dialog
from dialogs.menu_users import MenuUsersSG, menu_users_dialog
from dialogs.menu_calendars import MenuCalendarsSG, menu_calendars_dialog
from dialogs.send_plan import SendPlanSG, send_plan_dialog
# from dialogs.test import TestSG, test_dialog

from config import API_TOKEN

from middlewares import DatabaseMiddleware, UserDBMiddleware
from database import reload_tables, async_session
from models import Base, Task, User, Project, Subproject, TaskAnswer
from sqlalchemy.future import select
from sqlalchemy import select, func, and_
from sqlalchemy.orm import aliased


storage = MemoryStorage()


bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)
dp.update.middleware(DatabaseMiddleware(session=async_session))
dp.update.middleware(UserDBMiddleware())

dp.include_router(add_task_dialog)
dp.include_router(add_user_dialog)
dp.include_router(add_project_dialog)
dp.include_router(add_subproject_dialog)
dp.include_router(edit_user_dialog)
dp.include_router(search_task_dialog)
dp.include_router(menu_task_dialog)
dp.include_router(send_plan_dialog)
dp.include_router(menu_users_dialog)
dp.include_router(menu_calendars_dialog)


# dp.include_router(test_dialog)

setup_dialogs(dp)



@dp.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    result = await db_session.execute(select(func.count(User.id)))
    number_of_users = result.scalar()
    if number_of_users == 0:
        telegram_id = message.from_user.id
        telegram_key = uuid.uuid4()
        username = message.from_user.username
        new_user = User(
            telegram_id=telegram_id,
            telegram_key=str(telegram_key),
            username=username if username else "unknown",
            role="ADMIN"
        )
        db_session.add(new_user)
        await db_session.commit()
        await message.answer("Вы успешно зарегистрированы как администратор!")
        return
    if db_user == None and number_of_users != 0:
        telegram_id = message.from_user.id
        telegram_key = uuid.uuid4()
        username = message.from_user.username
        new_user = User(
            telegram_id=telegram_id,
            telegram_key=str(telegram_key),
            username=username if username else str(telegram_key),
            role="UNGREGISTERD"
        )
        db_session.add(new_user)
        await db_session.commit()
        await message.answer(f"Ваш ключ для регистрации: {telegram_key}")
        return
    if db_user.role == "UNGREGISTERD" or db_user.role == "USER":
        await message.answer(f"Ваш ключ для регистрации: {db_user.telegram_key}")
        return
    if db_user.role == "ADMIN":
        await message.answer(f"Вы администратор! Ваш ключ для регистрации: {db_user.telegram_key}")
        return

@dp.message(Command("add_task"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        await dialog_manager.start(AddTaskSG.task_text, mode=StartMode.RESET_STACK, data={'db_user': db_user})

@dp.message(Command("add_user"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        await dialog_manager.start(AddUserSG.user_key, mode=StartMode.RESET_STACK)

@dp.message(Command("add_project"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    await dialog_manager.start(AddProjectSG.project_name, mode=StartMode.RESET_STACK)

@dp.message(Command("add_subproject"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        await dialog_manager.start(AddSubprojectSG.project_select, mode=StartMode.RESET_STACK)

@dp.message(Command("search_tasks"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        search_menu_data = {
            'query_initial': select(Task),
            'task_show_mode_state' : MenuTaskSG.admin_task_show,
            'userORM': db_user,
            'bot': bot,
        }
        await dialog_manager.start(SearchTaskSG.task_filters, mode=StartMode.RESET_STACK,data=search_menu_data)
@dp.message(Command("search_planned_tasks"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        search_menu_data = {
            'query_initial': select(Task).where(Task.is_inplan == True),
            'task_show_mode_state' : MenuTaskSG.admin_task_show,
            'userORM': db_user,
            'bot': bot,
        }
        await dialog_manager.start(SearchTaskSG.task_filters, mode=StartMode.RESET_STACK,data=search_menu_data)

@dp.message(Command("send_plan"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        await dialog_manager.start( SendPlanSG.presentations_show, mode=StartMode.RESET_STACK, data={'bot': bot} )    

@dp.message(Command("menu_users"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        await dialog_manager.start( MenuUsersSG.users_select, mode=StartMode.RESET_STACK,)  

@dp.message(Command("today_calendar"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        calendar_data = {
            'task_show_mode_state' : MenuTaskSG.admin_task_show,
            'userORM': db_user,
            'bot': bot
        }
        await dialog_manager.start( MenuCalendarsSG.day_select, mode=StartMode.RESET_STACK, data=calendar_data ) 

@dp.message(Command("month_calendar"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        calendar_data = {   
            'task_show_mode_state' : MenuTaskSG.admin_task_show,
            'userORM': db_user,
            'bot': bot
        }
        await dialog_manager.start( MenuCalendarsSG.month_select, mode=StartMode.RESET_STACK, data=calendar_data )

@dp.message(Command("week_calendar"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    if db_user.role == "ADMIN":
        calendar_data = {   
            'task_show_mode_state' : MenuTaskSG.admin_task_show,
            'userORM': db_user,
            'bot': bot
        }
        await dialog_manager.start( MenuCalendarsSG.week_select, mode=StartMode.RESET_STACK, data=calendar_data )

@dp.message(F.text.regexp(r"^/task_(\d+)$").as_("task_id"))
async def any_digits_handler(message: Message, task_id: Match[str], dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    q = select(Task).where(Task.id == task_id.group(1))
    taskORM = (await db_session.execute(q)).scalar()
    if db_user.role == "ADMIN":
        await dialog_manager.start( MenuTaskSG.admin_task_show, mode=StartMode.RESET_STACK, data={'taskORM': taskORM,'userORM': db_user, 'bot': bot} )
    if db_user.role == "MODERATOR":
        await dialog_manager.start( MenuTaskSG.moder_task_show, mode=StartMode.RESET_STACK, data={'taskORM': taskORM,'userORM': db_user, 'bot': bot} )

@dp.message(Command("test"))
async def start(message: Message, dialog_manager: DialogManager, db_session: AsyncSession, db_user: User):
    pass
    # Создаем алиасы для таблицы TaskAnswer


async def background_task():
    while True:
        async with async_session() as db_session:
            async with db_session.begin():
                TaskAnswerAlias = aliased(TaskAnswer)
                # Подзапрос для получения последнего ответа для каждой задачи
                last_answer_subquery = (
                    select(
                        TaskAnswer.task_id,
                        TaskAnswer.text,
                        TaskAnswer.date_answered,
                        func.row_number().over(
                            partition_by=TaskAnswer.task_id,
                            order_by=TaskAnswer.date_answered.desc()
                        ).label('rn')
                    )
                    .where(TaskAnswer.text == 'Задача закрыта')
                    .subquery()
                )

                # Основной запрос для получения задач
                query = (
                    select(Task, last_answer_subquery.c.date_answered)
                    .join(last_answer_subquery, Task.id == last_answer_subquery.c.task_id)
                    .where(
                        and_(
                            Task.status_text == 'закрыто',
                            Task.is_arhived == False,
                            last_answer_subquery.c.rn == 1
                        )
                    )
                )
                tasks_with_last_answers = (await db_session.execute(query)).all()
                current_date = datetime.now().date()
                for task, date_answered in tasks_with_last_answers:
                    print(f"Задача ID: {task.id}, Последний ответ: {date_answered}")
                    if date_answered.date() < current_date:
                        task.is_arhived = True
                        task.is_inplan = False

                await db_session.commit()
                await asyncio.sleep(60)

async def main():
    asyncio.create_task(background_task())
    await bot.set_my_commands([
        types.BotCommand(command="/add_task", description="Добавить задачу"),
        types.BotCommand(command="/search_tasks", description="Поиск задач"),
        types.BotCommand(command="/search_planned_tasks", description="Поиск запланированных задач"),
        types.BotCommand(command="/send_plan", description="Отправить план дня"),
        types.BotCommand(command="/menu_users", description="Открыть меню пользователей"),
        types.BotCommand(command="/today_calendar", description="Календарь на день"),
        types.BotCommand(command="/week_calendar", description="Календарь на неделю"),
        types.BotCommand(command="/month_calendar", description="Календарь на месяц"),
        types.BotCommand(command="/add_user", description="Добавить пользователя"),
        types.BotCommand(command="/add_project", description="Добавить проект"),
        types.BotCommand(command="/add_subproject", description="Добавить подпроект"),
        # types.BotCommand(command="/test", description="Тестовая команда"),      
    ])
    # await bot.delete_webhook(True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())