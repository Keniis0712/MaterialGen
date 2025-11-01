import datetime
import enum

from sqlalchemy import Column, Index, Integer, String, TIMESTAMP

from .db import Base


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