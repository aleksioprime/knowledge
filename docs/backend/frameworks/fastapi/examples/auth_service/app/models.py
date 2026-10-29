from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
)


class Permission(Base):
    __tablename__ = 'permissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, lazy='selectin')


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy='selectin')

    @property
    def role_names(self) -> list[str]:
        return sorted(role.name for role in self.roles)

    @property
    def permission_codes(self) -> set[str]:
        return {perm.code for role in self.roles for perm in role.permissions}


class LoginHistory(Base):
    __tablename__ = 'login_history'
    __table_args__ = (Index('ix_login_history_user_created', 'user_id', 'created_at'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    user_agent: Mapped[str] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(45))
    success: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
