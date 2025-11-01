import datetime
import enum
import pathlib

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Index, Integer, String, TIMESTAMP, select


data_path = pathlib.Path(__file__).parent.parent / "data"
if not data_path.exists():
    data_path.mkdir(exist_ok=True)

files_path = data_path / "files"
if not files_path.exists():
    files_path.mkdir(exist_ok=True)

db_path = data_path / "materials.db"
db_url = f"sqlite+aiosqlite:///{str(db_path)}"

engine = create_async_engine(db_url, echo=False)
Base = declarative_base()


class Markdown(Base):
    __tablename__ = "markdowns"

    id = Column(String, primary_key=True)
    date = Column(String, nullable=False)
    path = Column(String, nullable=False)
    title = Column(String)
    created_at = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # 索引
    __table_args__ = (
        Index("idx_date", "date"),
        Index("idx_title", "title"),
    )


class UserRole(enum.Enum):
    User = 1
    Admin = 2


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(Integer, default=UserRole.User)


# noinspection PyTypeChecker
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(User.__table__.select().where(User.username=="admin"))
        admin_user = result.fetchone()
        if not admin_user:
            from user import hash_password
            new_admin = User(
                username="admin",
                password=hash_password("THEPassword"),
                role=UserRole.Admin.value
            )
            session.add(new_admin)
            await session.commit()
            print("默认管理员用户已创建: admin / THEPassword")


async def db():
    async with AsyncSessionLocal() as session:
        yield session