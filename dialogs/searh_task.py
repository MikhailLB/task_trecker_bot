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
from sqlalchemy import intersect
from sqlalchemy.sql import func
from models import Base, Task, User, Project, Subproject

from config import SELECT_HIGH

from dialogs.menu_task import MenuTaskSG, menu_task_dialog


class SearchTaskSG(StatesGroup):
    task_filters = State()
    task_add_filter = State()
    task_text_filter = State()
    task_tasks_list = State()
    task_groups = State()
    task_chouse_group = State()

async def filters_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    manager.dialog_data['add_filter_name'] = item_id
    await manager.next()


async def filter_getter(dialog_manager: DialogManager, **kwargs):
    filter_name = dialog_manager.dialog_data['add_filter_name']
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    
    match filter_name:
        case 'Исполнитель':
            result = await db_session.execute(select(User))
            users = result.scalars().all()
            select_list = [(user.username, user.id) for user in users]
        case 'Проект':
            result = await db_session.execute(select(Project))
            projects = result.scalars().all()
            select_list = [(project.name, project.id) for project in projects]
        case 'Подпроект':
            result = await db_session.execute(select(Subproject))
            subprojects = result.scalars().all()
            select_list = [(subproject.name, subproject.id) for subproject in subprojects]
        case 'Приоритет':
            # Предположим, что приоритеты хранятся как строки в поле priority
            select_list = [(priority, priority) for priority in ['высокий', 'нормальный', 'низкий']]
        case 'Текст задачи':
            # Поиск вхождения строки "текст" в task_text
            select_list = [('Добавить текст', 1)]
        case _:
            pass
    return {
        'filter_name': filter_name,
        'scroll_list': select_list
    }

async def add_filter_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    filter_name = manager.dialog_data['add_filter_name']
    db_session: AsyncSession = manager.middleware_data.get('db_session')
    current_filter_id = item_id
    
    match filter_name:
        case 'Исполнитель':
            query = select(Task).join(Task.responsible_user).where(User.id == current_filter_id)
            manager.dialog_data['query_filter_user_id'] = query
        case 'Проект':
            query = select(Task).join(Task.project).where(Project.id == current_filter_id)
            manager.dialog_data['query_filter_project_id'] = query
        case 'Подпроект':
            query = select(Task).join(Task.subproject).where(Subproject.id == current_filter_id)
            manager.dialog_data['query_filter_subproject_id'] = query
        case 'Приоритет':
            query = select(Task).where(Task.priority == current_filter_id)
            manager.dialog_data['query_filter_priority'] = query
        case 'Текст задачи':
            print(90)
            await manager.switch_to(SearchTaskSG.task_text_filter)
            # Предполагаем, что item_id содержит часть текста задачи для поиска
            return
        case _:
            raise ValueError(f"Неизвестный фильтр: {filter_name}")

    # Можно добавить дополнительные действия, например, обновление состояния или отправку сообщения
    await callback.answer(f"Установлен фильтр: {filter_name}")
    await manager.switch_to(SearchTaskSG.task_filters)


async def task_text_filter_handler(message: Message, widget: TextInput, manager: DialogManager, text: str):
    item_id = text
    query = select(Task).where(Task.task_text.ilike(f'%{item_id}%'))
    manager.dialog_data['query_filter_task_text'] = query
    await manager.switch_to(SearchTaskSG.task_filters)


async def get_intersected_query(manager: DialogManager):
    query_keys = [
        'query_filter_user_id',
        'query_filter_project_id',
        'query_filter_subproject_id',
        'query_filter_priority',
        'query_filter_task_text'
    ]
    
    queries = [manager.start_data['query_initial']] + [manager.dialog_data[key] for key in query_keys if key in manager.dialog_data]
    
    if not queries:
        return None  # Если нужно вернуть все задачи, можно использовать select(Task)
    
    # Создаем финальный запрос с пересечением id
    final_query = select(Task).where(Task.id.in_( intersect(* [query.with_only_columns(Task.id) for query in queries] )))
    
    return final_query

async def tasklist_getter(dialog_manager: DialogManager, **kwargs):
    db_session : AsyncSession = dialog_manager.middleware_data.get('db_session')
    filtered_query = await get_intersected_query(dialog_manager)
    final_query = dialog_manager.dialog_data.get('final_query', filtered_query)
    result = await db_session.execute(final_query)
    tasks = result.scalars().all()
    return {
        'scroll_list': [ (task.task_text[:45], task.id) for task in tasks ]
    }


async def group_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    manager.dialog_data['group_by_name'] = item_id
    await manager.next()

async def group_getter(dialog_manager: DialogManager, **kwargs):
    db_session: AsyncSession = dialog_manager.middleware_data.get('db_session')
    group_name = dialog_manager.dialog_data['group_by_name']
    filtered_query = await get_intersected_query(dialog_manager)
    match group_name:
        case 'Исполнитель':
            grouped_query = (
                filtered_query
                .join(Task.responsible_user)
                .subquery()
            )
            final_grouped_query = (
                select(User, func.count(grouped_query.c.id).label('task_count'))
                .join(grouped_query, User.id == grouped_query.c.responsible_user_id)
                .group_by(User.id)
            )
            result = await db_session.execute(final_grouped_query)
            select_list = [(f'{user.username} [ {task_count} ]', user.id) for user, task_count in result]
            return {
                'group_name': group_name,
                'scroll_list': select_list
            }
        case 'Проект':
            grouped_query = (
                filtered_query
                .join(Task.project)
                .subquery()
            )
            final_grouped_query = (
                select(Project, func.count(grouped_query.c.id).label('task_count'))
                .join(grouped_query, Project.id == grouped_query.c.project_id)
                .group_by(Project.id)
            )
            result = await db_session.execute(final_grouped_query)
            select_list = [(f'{project.name} [ {task_count} ]', project.id) for project, task_count in result]
            return {
                'group_name': group_name,
                'scroll_list': select_list
            }
        case 'Подпроект':
            grouped_query = (
                filtered_query
                .join(Task.subproject)
                .subquery()
            )
            final_grouped_query = (
                select(Subproject, func.count(grouped_query.c.id).label('task_count'))
                .join(grouped_query, Subproject.id == grouped_query.c.subproject_id)
                .group_by(Subproject.id)
            )
            result = await db_session.execute(final_grouped_query)
            select_list = [(f'{subproject.name} [ {task_count} ]', subproject.id) for subproject, task_count in result]
            return {
                'group_name': group_name,
                'scroll_list': select_list
            }
        case 'Приоритет':
            grouped_query = (
                filtered_query
                .join(Task.responsible_user)
                .subquery()
            )

            # Создаем финальный запрос для группировки задач по приоритету
            final_grouped_query = (
                select(Task.priority, func.count(grouped_query.c.id).label('task_count'))
                .join(grouped_query, Task.id == grouped_query.c.id)
                .group_by(Task.priority)
            )

            result = await db_session.execute(final_grouped_query)
            select_list = [(f'{priority} [ {task_count} ]', priority) for priority, task_count in result]
            return {
                'group_name': group_name,
                'scroll_list': select_list
            }
        case _:
            raise ValueError(f"Unknown group name: {group_name}")
    

async def chouse_group_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    group_name = manager.dialog_data['group_by_name']
    filtered_query = await get_intersected_query(manager)
    match group_name:
        case 'Исполнитель':
            manager.dialog_data['final_query'] = filtered_query.filter(Task.responsible_user_id == item_id)
        case 'Проект':
            manager.dialog_data['final_query'] = filtered_query.filter(Task.project_id == item_id)
        case 'Подпроект':
            manager.dialog_data['final_query'] = filtered_query.filter(Task.subproject_id == item_id)
        case 'Приоритет':
            manager.dialog_data['final_query'] = filtered_query.filter(Task.priority == item_id)
        case _:
            raise ValueError(f"Unknown group name: {group_name}")
    
    await manager.switch_to(SearchTaskSG.task_tasks_list)

async def task_select_handler(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: int):
    db_session : AsyncSession = manager.middleware_data.get('db_session')
    result = await db_session.execute( select(Task).join(Task.responsible_user).where(Task.id == item_id) )
    task = result.scalar()
    task_menu_data={
        'taskORM': task,
        'userORM':manager.start_data['userORM'],
        'bot': manager.start_data['bot'],
        }
    await manager.start(manager.start_data['task_show_mode_state'], data=task_menu_data)


search_task_dialog = Dialog(
    Window(
        Const("Выберете фильтры:"),
        Column(
            Select(
                    Format("{item}"),
                    id="select_a",
                    item_id_getter=lambda item: item,  
                    items=['Исполнитель', 'Проект', 'Подпроект', 'Приоритет', 'Текст задачи'],
                    on_click=filters_select_handler,
                    type_factory=str
                ),
            ),
        Cancel(),
        SwitchTo(Const("Показать"), id="sec", state=SearchTaskSG.task_tasks_list),
        SwitchTo(Const("Группировать"), id="to_group", state=SearchTaskSG.task_groups),
        state=SearchTaskSG.task_filters,
    ),
    Window(
        Format("Добавить фильтр по {filter_name}"),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),
                id="select_a",
                item_id_getter=lambda item: item[1],
                items='scroll_list',
                on_click=add_filter_select_handler,
                type_factory=str

            ),
            id="scrolling_group",
            width=1,
            height=SELECT_HIGH,

        ),
        Back(),
        Cancel(),
        getter=filter_getter,
        state=SearchTaskSG.task_add_filter,
    ),
    Window(
        Const("Задачи"),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),
                id="select_a",
                item_id_getter=lambda item: item[1],
                items='scroll_list',
                on_click=task_select_handler,
                type_factory=int

            ),
            id="scrolling_group",
            width=1,
            height=5,

        ),
        SwitchTo(Const("Back"), id="begin_back", state=SearchTaskSG.task_filters),
        Cancel(),
        getter=tasklist_getter,
        state=SearchTaskSG.task_tasks_list
    ),
    Window(
    Const("Группировать по:"),
    Column(
        Select(
                Format("{item}"),
                id="select_a",
                item_id_getter=lambda item: item,  
                items=['Исполнитель', 'Проект', 'Подпроект', 'Приоритет'],
                on_click=group_select_handler,
                type_factory=str
            ),
        ),
    Cancel(),
    state=SearchTaskSG.task_groups,
    ),
    Window(
    Format("Группировка по {group_name}"),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="select_a",
            item_id_getter=lambda item: item[1],
            items='scroll_list',
            on_click=chouse_group_select_handler,
            type_factory=str

        ),
        id="scrolling_group",
        width=1,
        height=SELECT_HIGH,

    ),
    Back(),
    Cancel(),
    getter=group_getter,
    state=SearchTaskSG.task_chouse_group,
    ),
    Window(
    Format("Отправьте текст:"),
    TextInput(id="task_text_filter", on_success=task_text_filter_handler),
    state=SearchTaskSG.task_text_filter,
    ),
)
    