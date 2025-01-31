
from sqlalchemy.sql import func
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Task, User, Project, Subproject, TaskAnswer
async def add_task_answer(answer_text: str, db_session : AsyncSession, user : User, task : Task, bot):
    await db_session.refresh(user)
    task_answer = TaskAnswer(
        text=answer_text,
        user=user,
        task=task
    )
    db_session.add(task_answer)
    await db_session.commit()
    users_send = await all_task_users(db_session, user, task)
    for user_send in users_send:
        await bot.send_message(user_send.telegram_id, f"Ответ на задачу: {task.task_text}\nОт пользователя: {user.username}\nОтвет:{answer_text}\nЗадача: /task_{task.id}")
    db_session.expunge(user)

async def all_task_users(db_session : AsyncSession, user : User, task : Task):
    admin_query = select(User).where(User.role == "ADMIN")
    users_send = (await db_session.execute(admin_query)).scalars().all()
    await db_session.refresh(task, attribute_names=["responsible_user", "project", "subproject", "author"])
    users_send.append(task.responsible_user)
    return users_send

async def get_tasks_for_user(db_session: AsyncSession, user_id: int) -> str:
    # Получаем пользователя с загруженными задачами, проектами, подпроектами и ответами на задачи
    # q = (
    #     select(User)
    #     .where(User.id == user_id)
    #     .options(
    #         selectinload(User.tasks_responsible_for).joinedload(Task.project),
    #         selectinload(User.tasks_responsible_for).joinedload(Task.subproject),
    #         selectinload(User.tasks_responsible_for).joinedload(Task.author),
    #         selectinload(User.tasks_responsible_for).joinedload(Task.answers).joinedload(TaskAnswer.user)
    #     )
    # )

    # Предположим, что User и Task уже импортированы

    # Создаем алиас для Task с фильтрацией
    filtered_tasks = aliased(Task, select(Task).where(Task.is_inplan == True).subquery())

    q = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.tasks_responsible_for.of_type(filtered_tasks))
            .joinedload(filtered_tasks.project),
            selectinload(User.tasks_responsible_for.of_type(filtered_tasks))
            .joinedload(filtered_tasks.subproject),
            selectinload(User.tasks_responsible_for.of_type(filtered_tasks))
            .joinedload(filtered_tasks.author),
            selectinload(User.tasks_responsible_for.of_type(filtered_tasks))
            .joinedload(filtered_tasks.answers)
            .joinedload(TaskAnswer.user)
        )
    )
    result = await db_session.execute(q)
    user = result.scalars().first()

    if not user:
        return "<b>Пользователь не найден.</b>"

    tasks = user.tasks_responsible_for

    if not tasks:
        return "<b>У пользователя нет задач.</b>"

    # Группируем задачи по проектам и подпроектам
    tasks_by_project = {}
    for task in tasks:
        project_name = task.project.name
        subproject_name = task.subproject.name
        if project_name not in tasks_by_project:
            tasks_by_project[project_name] = {}
        if subproject_name not in tasks_by_project[project_name]:
            tasks_by_project[project_name][subproject_name] = []
        tasks_by_project[project_name][subproject_name].append(task)

    # Формируем текст для печати
    # print_text = f"Задачи пользователя: <b>{user.username}</b>\n\n"
    print_text = ""
    print_text += f"{user.contact_text}\n\n"
    for project_name, subprojects in tasks_by_project.items():
        print_text += f"<u><b>Проект: {project_name}</b></u>\n"
        for subproject_name, tasks in subprojects.items():
            print_text += f" <b><i>Подпроект:</i></b> {subproject_name}\n"
            for task in tasks:
                print_text += f"  <b>Задача:</b> {task.task_text}\n"
                print_text += f"  <b>Описание результата:</b> {task.result_description}\n"
                print_text += f"  <b>Ссылка:</b> {task.link if task.link else 'Нет'}\n"
                print_text += f"  <b>Датa выполнения:</b> <u>{task.deadline.strftime('%Y-%m-%d')}</u>\n"
                print_text += f"  <b>Время выполнения:</b> {task.execution_time.strftime('%Y-%m-%d %H:%M:%S') if task.execution_time else 'Нет'}\n"
                print_text += f"  <b>Приоритет:</b> {task.priority}\n"
                print_text += f"  <b>Статус:</b> <u>{task.status_text}</u>\n"
                print_text += f"  <b>Создано:</b> {task.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                print_text += f"  <b>Автор:</b> <i>{task.author.username}</i>\n"
                print_text += f"  <b>Задача:</b>/task_{task.id}\n"
                # if task.answers:
                #     print_text += "  <b>Ответы:</b>\n"
                #     for answer in task.answers:
                #         print_text += f"   <b>Дата ответа:</b> <u>{answer.date_answered.strftime('%Y-%m-%d %H:%M:%S')}</u>\n"
                #         print_text += f"   <b>Текст ответа:</b> <i>{answer.text}</i>\n"
                print_text += "\n"
        print_text += "\n"

    return print_text