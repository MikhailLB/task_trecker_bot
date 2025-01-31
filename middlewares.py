from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Awaitable, Dict, Any
from database import Base, engine

from sqlalchemy.sql import func
from sqlalchemy.future import select
from models import Base, Task, User, Project, Subproject

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.session = session

    async def __call__(
        self, 
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, 
        data: Dict[str, Any]) -> Any:

        async with self.session() as session:
            db_session = session
            data['db_session'] = db_session
            result = await handler(event, data)
            return result

class UserDBMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, 
        data: Dict[str, Any]) -> Any:
        if event.message:
            db_session = data['db_session']
            telegram_id = event.message.from_user.id
            result = await db_session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalars().first()
            data['db_user'] = user

        result = await handler(event, data)
        if event.message:
            pass
        return result

# class UserDBMiddleware(BaseMiddleware):
#     def __init__(self) -> None:
#         self.counter = 0

#     async def __call__(
#         self,
#         handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
#         event: Message,
#         data: Dict[str, Any]
#     ) -> Any:
#         print(type(event.message))
#         await event.message.answer('Hello')
        
#         self.counter += 1
#         data['counter'] = self.counter
#         return await handler(event, data)