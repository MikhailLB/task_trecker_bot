# add_task.py
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back, Next, Cancel
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Calendar, ScrollingGroup, Select, Column
from datetime import datetime, date, time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Project, Subproject, Task

from config import SELECT_HIGH

class AddTaskSG(StatesGroup):
    task_text = State()
    task_result = State()
    task_link = State()
    task_due_date = State()
    task_due_time = State()
    task_responsible = State()
    task_project = State()
    task_subproject = State()
    task_priority = State()
    task_final = State()

async def error(message: Message, dialog_: Any, manager: DialogManager, error_: ValueError):
    await message.answer("Неверный ввод!")

async def date_getter(dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data['task_status'] = 'создана'
    dialog_manager.dialog_data['task_priority'] = 'нормальный'
    return {
        "task_text": dialog_manager.dialog_data.get('task_text', ''),
        "task_result": dialog_manager.dialog_data.get('task_result', ''),
        "task_link": dialog_manager.dialog_data.get('task_link', ''),
        "task_due_date": dialog_manager.dialog_data.get('task_due_date', ''),
        "task_due_time": dialog_manager.dialog_data.get('task_due_time', ''),
        "task_responsible": dialog_manager.dialog_data.get('task_responsible', ''),
        "task_project": dialog_manager.dialog_data.get('project', ''),
        "task_subproject": dialog_manager.dialog_data.get('subproject', ''),
        "task_priority": dialog_manager.dialog_data.get('task_priority', ''),
        "task_status": dialog_manager.dialog_data.get('task_status', ''),
    }

async def end_handler(callback_query: CallbackQuery, button: Button, dialog_manager: DialogManager):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    task_data = dialog_manager.dialog_data

    # Создаем объект Task с новыми полями для статуса
    task = Task(
        task_text=task_data['task_text'],
        result_description=task_data['task_result'],
        link=task_data.get('task_link', None),
        deadline=task_data['task_due_date'],
        execution_time=task_data.get('task_due_time', None),
        responsible_user_id=task_data['task_responsible'].id,
        project_id=task_data['project'].id,
        subproject_id=task_data.get('subproject', None).id if task_data.get('subproject') else None,
        priority=task_data['task_priority'],
        status_text=task_data.get('task_status', ''),
        created_at=datetime.now(),
        author_id=dialog_manager.start_data['db_user'].id,
        is_inplan=False,
        is_arhived=False
    )

    # Добавляем задачу в сессию
    db_session.add(task)

    # Коммитим изменения в базу данных
    await db_session.commit()
    await callback_query.answer("Задача успешно добавлена!")
    await dialog_manager.done(result=task_data)

async def task_text_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    if len(text) > 50:
        await message.answer("Текст задачи должен быть 50 символов или меньше.")
        return
    manager.dialog_data['task_text'] = text
    await message.answer(f"Текст задачи: {text}")
    await manager.next()

async def task_result_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    if len(text) > 200:
        await message.answer("Описание результата задачи должно быть 200 символов или меньше.")
        return
    manager.dialog_data['task_result'] = text
    await message.answer(f"Описание результата: {text}")
    await manager.next()

async def task_link_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['task_link'] = text
    await message.answer(f"Ссылка: {text}")
    await manager.next()

async def task_due_date_handler_calendar(callback: CallbackQuery, widget, manager: DialogManager, selected_date: date):
    await callback.answer(str(selected_date))
    manager.dialog_data['task_due_date'] = selected_date
    await manager.next()

async def task_due_time_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    try:
        time = datetime.strptime(text, '%H:%M')
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM.")
        return
    manager.dialog_data['task_due_time'] = time
    await message.answer(f"Время выполнения: {time.strftime('%H:%M')}")
    await manager.next()

async def task_responsible_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    return {
        'scroll_list': users
    }

async def on_responsible_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    query = select(User).where(User.id == item_id)
    result = await db_session.execute(query)
    user = result.scalar()
    if user:
        manager.dialog_data['task_responsible'] = user
        await manager.next()
    else:
        await callback.message.answer("Пользователь не найден. Попробуйте снова.")
        return False

async def task_project_getter(dialog_manager: DialogManager, **kwargs):
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

async def task_subproject_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    project = dialog_manager.dialog_data.get('project')
    if project:
        query = select(Subproject).where(Subproject.project_id == project.id)
        result = await db_session.execute(query)
        subprojects = result.scalars().all()
        return {
            'scroll_list': subprojects
        }
    return {
        'scroll_list': []
    }

async def on_subproject_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    query = select(Subproject).where(Subproject.id == item_id)
    result = await db_session.execute(query)
    subproject = result.scalar()
    if subproject:
        manager.dialog_data['subproject'] = subproject
        await manager.next()
    else:
        await callback.message.answer("Подпроект не найден. Попробуйте снова.")
        return False

async def task_priority_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    text = item_id
    manager.dialog_data['task_priority'] = text
    await manager.next()

async def task_status_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['task_status'] = f"Создана {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} пользователем {manager.event.from_user.username}"
    await message.answer(f"Статус задачи: {manager.dialog_data['task_status']}")
    await manager.next()

add_task_dialog = Dialog(
    Window(
        Const("Введите текст задачи (максимум 50 символов):"),
        TextInput(id="task_text", on_success=task_text_handler, on_error=error),
        Cancel(),
        state=AddTaskSG.task_text,
    ),
    Window(
        Const("Введите требуемый результат (максимум 200 символов):"),
        TextInput(id="task_result", on_success=task_result_handler, on_error=error),
        Back(),
        Cancel(),
        state=AddTaskSG.task_result,
    ),
    Window(
        Const("Введите ссылку (опционально):"),
        TextInput(id="task_link", on_success=task_link_handler),
        Back(),
        Next(),
        Cancel(),
        state=AddTaskSG.task_link,
    ),
    Window(
        Const("Введите дату выполнения:"),
        Calendar(id="calendar", on_click=task_due_date_handler_calendar),
        Back(),
        Cancel(),
        state=AddTaskSG.task_due_date,
    ),
    Window(
        Const("Введите время выполнения (HH:MM)(опционально):"),
        TextInput(id="task_due_time", on_success=task_due_time_handler, on_error=error),
        Back(),
        Next(),
        Cancel(),
        state=AddTaskSG.task_due_time,
    ),
    Window(
        Const("Выберите ответственного человека:"),
        ScrollingGroup(
            Select(
                Format("{item.username}"),
                id="select_responsible",
                item_id_getter=lambda item: item.id,
                items="scroll_list",
                on_click=on_responsible_selected,
                type_factory=int
            ),
            id="scrolling_group_responsible",
            width=1,
            height=SELECT_HIGH,
        ),
        Back(),
        Cancel(),
        getter=task_responsible_getter,
        state=AddTaskSG.task_responsible,
    ),
    Window(
        Const("Выберите проект:"),
        ScrollingGroup(
            Select(
                Format("{item.name}"),
                id="select_project",
                item_id_getter=lambda item: item.id,
                items="scroll_list",
                on_click=on_project_selected,
                type_factory=int
            ),
            id="scrolling_group_project",
            width=1,
            height=SELECT_HIGH,
        ),
        Back(),
        Cancel(),
        getter=task_project_getter,
        state=AddTaskSG.task_project,
    ),
    Window(
        Const("Выберите подпроект:"),
        ScrollingGroup(
            Select(
                Format("{item.name}"),
                id="select_subproject",
                item_id_getter=lambda item: item.id,
                items="scroll_list",
                on_click=on_subproject_selected,
                type_factory=int
            ),
            id="scrolling_group_subproject",
            width=1,
            height=SELECT_HIGH,
        ),
        Back(),
        Cancel(),
        getter=task_subproject_getter,
        state=AddTaskSG.task_subproject,
    ),
    Window(
        Const("Введите приоритет:"),
        Column(
            Select(
                Format("{item}"),
                id="user_role_select",
                item_id_getter=lambda item: item,
                items=['высокий', 'нормальный', 'низкий'],
                on_click=task_priority_select_handler
            )
        ),
        Button(
            text=Const(' '),
            id='placeholder'
        ),
        Next(),
        Back(),
        Cancel(),
        state=AddTaskSG.task_priority,
    ),
    Window(
        Jinja(
            "<b>Детали задачи:</b>\n\n"
            "<b>Текст:</b> {{task_text}}\n"
            "<b>Результат:</b> {{task_result}}\n"
            "<b>Ссылка:</b> {{task_link}}\n"
            "<b>Дата выполнения:</b> {{task_due_date}}\n"
            "<b>Время выполнения:</b> {{task_due_time}}\n"
            "<b>Ответственный:</b> {{task_responsible.username}}\n"
            "<b>Проект:</b> {{task_project.name}}\n"
            "<b>Подпроект:</b> {{task_subproject.name if task_subproject else 'Нет'}}\n"
            "<b>Приоритет:</b> {{task_priority}}\n"
            "<b>Статус:</b> {{task_status}}\n"
        ),
        Button(Const("✅ Завершить"), id="end", on_click=end_handler),
        Back(),
        Cancel(),
        getter=date_getter,
        state=AddTaskSG.task_final,
        parse_mode="html",
    ),
)