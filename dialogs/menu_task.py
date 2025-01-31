from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back, Next, Cancel, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Calendar, ScrollingGroup, Select, Column
from datetime import datetime, date, time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import intersect, desc
from sqlalchemy.sql import func
from sqlalchemy.orm import selectinload
from models import Task, User, Project, Subproject, TaskAnswer
from common_func import add_task_answer
from config import SELECT_HIGH

class MenuTaskSG(StatesGroup):
    admin_task_show = State()
    moder_task_show = State()
    task_answers = State()
    task_answer_show = State()
    add_task_answer = State()

async def task_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    task = dialog_manager.start_data['taskORM']
    db_session.add(task)
    await db_session.refresh(task, attribute_names=["responsible_user", "project", "subproject", "author"])
    return {
        "task_text": task.task_text,
        "task_result": task.result_description,
        "task_link": task.link if task.link else "Нет",
        "task_due_date": task.deadline.date().strftime("%d.%m.%Y"),
        "task_due_time": task.execution_time.time().strftime("%H:%M") if task.execution_time else "Нет",
        "task_responsible": task.responsible_user.username if task.responsible_user else "Нет ответственного",
        "task_project": task.project.name if task.project else "Нет проекта",
        "task_subproject": task.subproject.name if task.subproject else "Нет подпроекта",
        "task_priority": task.priority,
        "task_status": task.status_text,
        "task_is_inplan": "Да" if task.is_inplan else "Нет",
        "task_is_arhived": "Да" if task.is_arhived else "Нет",
        "task_author": task.author.username if task.author else "Нет автора",
        "task_id_link": f'/task_{task.id}',
    }

async def task_action_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    text = item_id
    db_session: AsyncSession = manager.middleware_data.get('db_session')

    taskORM = manager.start_data['taskORM']
    q = select(Task).where(Task.id == taskORM.id) #because user already in middleware db_session
    task = (await db_session.execute(q)).scalar()

    userORM = manager.start_data['userORM'] 
    q = select(User).where(User.id == userORM.id) #because user already in middleware db_session
    user = (await db_session.execute(q)).scalar()
    match text:
        case "Добавить в план":
            task.is_inplan = True
        case "Удалить из плана":
            task.is_inplan = False
        case "Добавить в архив":
            task.is_arhived = True
        case "Вернуть из архива":
            task.is_arhived = False
        case 'Добавить ответ':
            await manager.switch_to(MenuTaskSG.add_task_answer)
            return
        case "Ответы":
            await manager.switch_to(MenuTaskSG.task_answers)
            return
        case "Закрыть задачу":
            task.status_text = 'закрыто'
            await add_task_answer(f"Задача закрыта", db_session, user, task, manager.start_data['bot'])
        case 'Вернуть статус назначено':
            task.status_text = 'назначено'
            await add_task_answer(f"Задача назначена", db_session, user, task, manager.start_data['bot'])
        case _:
            await callback.answer(f"Действие '{text}' не определено")
            return

    await db_session.commit()
    
    await callback.answer(f"Действие '{text}' выполнено успешно")

async def answers_select_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    task: Task = dialog_manager.start_data['taskORM']
    db_session.add(task)
    await db_session.refresh(task, attribute_names=["responsible_user", "project", "subproject", "author"]) 
    answers = await db_session.execute(
        select(TaskAnswer)
        .options(selectinload(TaskAnswer.user))
        .where(TaskAnswer.task_id == task.id)
        .order_by(desc(TaskAnswer.date_answered))
    )
    answers = answers.scalars().all()
    return {
        'scroll_list' : [(f'{answer.user.username}:{answer.text}',answer.id)for answer in answers]
    }

async def on_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    result = await db_session.execute( select(TaskAnswer).where(TaskAnswer.id == item_id) )
    answer = result.scalar()
    manager.dialog_data['answer_text'] = answer.text
    await manager.next()

async def back_to_show_handler(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(manager.dialog_data['show_mode_state'])

async def add_task_answer_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):

    answer_text = text
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    
    taskORM = manager.start_data['taskORM']
    q = select(Task).where(Task.id == taskORM.id) #because user already in middleware db_session
    task = (await db_session.execute(q)).scalar()

    userORM = manager.start_data['userORM'] 
    q = select(User).where(User.id == userORM.id) #because user already in middleware db_session
    user = (await db_session.execute(q)).scalar()

    await add_task_answer(answer_text, db_session, user, task, manager.start_data['bot'])
    task.status_text = 'отвечено'
    await db_session.commit()
    await manager.switch_to(manager.dialog_data['show_mode_state'])

task_jinja_template = Jinja(
            "<b>Детали задачи:</b>\n\n"
            "<b>Текст:</b> {{task_text}}\n"
            "<b>Результат:</b> {{task_result}}\n"
            "<b>Ссылка:</b> {{task_link}}\n"
            "<b>Дата выполнения:</b> {{task_due_date}}\n"
            "<b>Время выполнения:</b> {{task_due_time}}\n"
            "<b>Ответственный:</b> {{task_responsible}}\n"
            "<b>Проект:</b> {{task_project}}\n"
            "<b>Подпроект:</b> {{task_subproject}}\n"
            "<b>Приоритет:</b> {{task_priority}}\n"
            "<b>Статус:</b> {{task_status}}\n"
            "<b>В плане:</b> {{task_is_inplan}}\n"
            "<b>Архивирован:</b> {{task_is_arhived}}\n"
            "<b>Автор:</b> {{task_author}}\n"
            "<b>Задача:</b> {{task_id_link}}\n"
        )

async def on_dialog_start(start_data: Any, manager: DialogManager):
    manager.dialog_data['show_mode_state'] = manager.current_context().state

menu_task_dialog = Dialog(
    Window(
        task_jinja_template,
        Column(
            Select(
            Format("{item}"),
            id="select_a",
            item_id_getter=lambda item: item, 
            items=['Добавить в план', 'Удалить из плана', 'Добавить в архив', 'Вернуть из архива', 'Закрыть задачу', 'Вернуть статус назначено','Добавить ответ' ,'Ответы'],
            on_click=task_action_select_handler 
        )),
        Cancel(),
        getter=task_getter,
        state=MenuTaskSG.admin_task_show,
        parse_mode="HTML",
    ),
    Window(
        task_jinja_template,
        Column(
            Select(
            Format("{item}"),
            id="select_a",
            item_id_getter=lambda item: item, 
            items=['Добавить ответ','Ответы'],
            on_click=task_action_select_handler 
        )),
        Cancel(),
        getter=task_getter,
        state=MenuTaskSG.moder_task_show,
        parse_mode="HTML",
    ),
    Window(
        Const("Ответы:"),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),
                id="select_a",
                item_id_getter=lambda item: item[1],  
                items='scroll_list',
                on_click=on_selected,
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
        getter=answers_select_getter,
        state=MenuTaskSG.task_answers,

    ),
    Window(
        Format("{dialog_data[answer_text]}"),
        Back(),
        state=MenuTaskSG.task_answer_show
    ),
    Window(
    Format("Введите ответ:"),
    TextInput(id="task_text_filter", on_success=add_task_answer_handler),
    state=MenuTaskSG.add_task_answer,
    ),
    on_start=on_dialog_start
)