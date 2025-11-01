import pathlib

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base


data_path = pathlib.Path(__file__).parent.parent.parent / "data"
if not data_path.exists():
    data_path.mkdir(exist_ok=True)

files_path = data_path / "files"
if not files_path.exists():
    files_path.mkdir(exist_ok=True)

db_path = data_path / "materials.db"
db_url = f"sqlite+aiosqlite:///{str(db_path)}"

engine = create_async_engine(db_url, echo=False)
Base = declarative_base()

# noinspection PyTypeChecker
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    from .models import User, UserRole
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(User.__table__.select().where(User.username=="admin"))
        admin_user = result.fetchone()
        if not admin_user:
            from core.user import hash_password
            new_admin = User(
                username="admin",
                password=hash_password("THEPassword"),
                role=UserRole.Admin
            )
            session.add(new_admin)
            await session.commit()
            print("默认管理员用户已创建: admin / THEPassword")


async def db():
    async with AsyncSessionLocal() as session:
        yield session
