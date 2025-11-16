from contextlib import asynccontextmanager
import requests
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
    total: Mapped[int]
    vat: Mapped[int]
    client_phone: Mapped[str]
    cashier_inn: Mapped[str]

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

def get_repository(session: Session = Depends(get_session)): # <-- добавим зависимость получения репозитория
    return ReceiptRepository(session)

# Создание таблиц
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables() # в реальном приложении лучше пользоваться alembic для накатки миграций!
    yield

# FastAPI приложение
app = FastAPI(lifespan=lifespan)

class ReceiptRepository: # <-- добавим репозиторий и его методы
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _map_to_receipt(record: Receipt) -> ReceiptPublic:
        return ReceiptPublic(**record.__dict__)


    def create(self, receipt: ReceiptCreate) -> ReceiptPublic:
        db_receipt = Receipt(**receipt.model_dump())
        self.session.add(db_receipt)
        self.session.commit()
        self.session.refresh(db_receipt)
        return self._map_to_receipt(db_receipt)

    def get_all(self, offset: int = 0, limit: int = 100) -> list[ReceiptPublic]:
        stmt = select(Receipt).offset(offset).limit(limit)
        receipts = self.session.scalars(stmt).all()
        return [self._map_to_receipt(receipt) for receipt in receipts]


# Роуты
@app.post("/receipts/", response_model=ReceiptPublic, status_code=status.HTTP_201_CREATED,)
def create_receipt(*, receipt: ReceiptCreate, repo: ReceiptRepository = Depends(get_repository)):
    return repo.create(receipt) # <-- используем репу


@app.get("/receipts/", response_model=list[ReceiptPublic])
def read_receipts(
    *,
    repo: ReceiptRepository = Depends(get_repository),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    return repo.get_all(offset=offset, limit=limit) # <-- используем репу