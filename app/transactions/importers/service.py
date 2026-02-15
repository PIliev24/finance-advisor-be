import structlog
from langchain_core.language_models import BaseChatModel

from app.exceptions import ConflictError
from app.transactions.importers.csv_importer import CSVImporter
from app.transactions.importers.image_importer import ImageImporter
from app.transactions.importers.pdf_importer import PDFImporter
from app.transactions.importers.schemas import ImportResult
from app.transactions.schemas import TransactionCreate
from app.transactions.service import TransactionService

logger = structlog.get_logger()


class ImportService:
    def __init__(self, transaction_service: TransactionService, llm: BaseChatModel) -> None:
        self._transaction_service = transaction_service
        self._llm = llm

    async def import_csv(self, file_content: bytes, filename: str) -> ImportResult:
        """Import transactions from a CSV file."""
        importer = CSVImporter()
        transactions, idempotency_keys = await importer.parse(file_content, filename)
        return await self._create_transactions(transactions, idempotency_keys, filename)

    async def import_image(self, file_content: bytes, filename: str) -> ImportResult:
        """Import transactions from an image (receipt/screenshot)."""
        importer = ImageImporter(self._llm)
        transactions, idempotency_keys = await importer.parse(file_content, filename)
        return await self._create_transactions(transactions, idempotency_keys, filename)

    async def import_pdf(self, file_content: bytes, filename: str) -> ImportResult:
        """Import transactions from a PDF file."""
        importer = PDFImporter(self._llm)
        transactions, idempotency_keys = await importer.parse(file_content, filename)
        return await self._create_transactions(transactions, idempotency_keys, filename)

    async def _create_transactions(
        self,
        transactions: list[TransactionCreate],
        idempotency_keys: list[str],
        filename: str,
    ) -> ImportResult:
        """Create transactions via the transaction service, handling duplicates."""
        total_created = 0
        total_skipped = 0
        total_failed = 0
        errors: list[str] = []

        for i, txn in enumerate(transactions):
            try:
                await self._transaction_service.create(txn)
                total_created += 1
            except ConflictError:
                total_skipped += 1
                logger.debug(
                    "import_duplicate_skipped",
                    filename=filename,
                    row=i,
                    key=idempotency_keys[i] if i < len(idempotency_keys) else None,
                )
            except Exception as exc:
                total_failed += 1
                error_msg = f"Row {i + 1}: {exc}"
                errors.append(error_msg)
                logger.warning("import_row_failed", filename=filename, row=i, error=str(exc))

        logger.info(
            "import_completed",
            filename=filename,
            total_parsed=len(transactions),
            created=total_created,
            skipped=total_skipped,
            failed=total_failed,
        )

        return ImportResult(
            total_parsed=len(transactions),
            total_created=total_created,
            total_skipped=total_skipped,
            total_failed=total_failed,
            errors=errors,
        )
