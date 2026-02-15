from fastapi import APIRouter, Query, UploadFile

from app.dependencies import APIKey, ImportServiceDep, TransactionServiceDep
from app.transactions.importers.schemas import ImportResult
from app.transactions.models import Category, TransactionType
from app.transactions.schemas import (
    MonthlySummary,
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter()


@router.post("/", status_code=201, response_model=TransactionResponse)
async def create_transaction(
    data: TransactionCreate,
    service: TransactionServiceDep,
    _api_key: APIKey,
) -> TransactionResponse:
    return await service.create(data)


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    service: TransactionServiceDep,
    _api_key: APIKey,
    date_from: str | None = None,
    date_to: str | None = None,
    category: Category | None = None,
    txn_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TransactionResponse]:
    filters = TransactionFilter(
        date_from=date_from,
        date_to=date_to,
        category=category,
        type=txn_type,
        limit=limit,
        offset=offset,
    )
    return await service.list_transactions(filters)


@router.get("/summary", response_model=list[MonthlySummary])
async def get_summary(
    service: TransactionServiceDep,
    _api_key: APIKey,
    year_month: str | None = Query(default=None),
) -> list[MonthlySummary]:
    return await service.get_summary(year_month)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    service: TransactionServiceDep,
    _api_key: APIKey,
) -> TransactionResponse:
    return await service.get_by_id(transaction_id)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    service: TransactionServiceDep,
    _api_key: APIKey,
) -> TransactionResponse:
    return await service.update(transaction_id, data)


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: str,
    service: TransactionServiceDep,
    _api_key: APIKey,
) -> None:
    await service.delete(transaction_id)


@router.post("/import/csv", status_code=201, response_model=ImportResult)
async def import_csv(
    file: UploadFile,
    service: ImportServiceDep,
    _api_key: APIKey,
) -> ImportResult:
    content = await file.read()
    return await service.import_csv(content, file.filename or "upload.csv")


@router.post("/import/image", status_code=201, response_model=ImportResult)
async def import_image(
    file: UploadFile,
    service: ImportServiceDep,
    _api_key: APIKey,
) -> ImportResult:
    content = await file.read()
    return await service.import_image(content, file.filename or "upload.png")


@router.post("/import/pdf", status_code=201, response_model=ImportResult)
async def import_pdf(
    file: UploadFile,
    service: ImportServiceDep,
    _api_key: APIKey,
) -> ImportResult:
    content = await file.read()
    return await service.import_pdf(content, file.filename or "upload.pdf")
