from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import declarative_base, mapped_column, Mapped, sessionmaker, Session
from sqlalchemy import Integer, String, create_engine, select
from pydantic import BaseModel

# Базовый класс для моделей
Base = declarative_base()

# SQLAlchemy модель с Mapped аннотациями
class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    total: Mapped[int] = mapped_column(Integer)
    vat: Mapped[str] = mapped_column(String)
    client_phone: Mapped[str] = mapped_column(String)
    cashier_inn: Mapped[str] = mapped_column(String)

# Pydantic схемы
class ReceiptBase(BaseModel):
    total: int
    vat: int
    client_phone: str
    cashier_inn: str

class ReceiptCreate(ReceiptBase):
    pass

class ReceiptPublic(ReceiptBase):
    id: int

# Настройка базы данных
DATABASE_URL = "sqlite:///./receipts.db"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Зависимости
def get_session():
    with SessionLocal() as db:
        yield db

# Создание таблиц
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables() # в реальном приложении лучше пользоваться alembic для накатки миграций!
    yield


# FastAPI приложение
app = FastAPI(lifespan=lifespan)


# Роуты
@app.post("/receipts/", response_model=ReceiptPublic, status_code=status.HTTP_201_CREATED,)
def create_receipt(*, session: Session = Depends(get_session), receipt: ReceiptCreate):
    db_receipt = Receipt(**receipt.model_dump())
    session.add(db_receipt)
    session.commit()
    session.refresh(db_receipt)
    return db_receipt


@app.get("/receipts/", response_model=list[ReceiptPublic])
def read_receipts(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    stmt = select(Receipt).offset(offset).limit(limit)
    receipts = session.scalars(stmt).all()
    return receipts
