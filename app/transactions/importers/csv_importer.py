import csv
import io
import re
from datetime import datetime

import structlog

from app.transactions.importers.base import ImporterBase
from app.transactions.models import Category, TransactionType
from app.transactions.schemas import TransactionCreate

logger = structlog.get_logger()

DATE_HEADERS = {"date", "transaction_date", "дата"}
AMOUNT_HEADERS = {"amount", "sum", "сума"}
DESCRIPTION_HEADERS = {"description", "memo", "описание"}
CATEGORY_HEADERS = {"category"}
TYPE_HEADERS = {"type"}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
]

VALID_CATEGORIES = {c.value for c in Category}


class CSVImporter(ImporterBase):
    async def parse(
        self, file_content: bytes, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Parse CSV file content and return transactions with idempotency keys."""
        text = self._decode_content(file_content)
        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            logger.warning("csv_no_headers", filename=filename)
            return [], []

        column_map = self._detect_columns(reader.fieldnames)
        logger.info("csv_columns_detected", filename=filename, mapping=column_map)

        transactions: list[TransactionCreate] = []
        idempotency_keys: list[str] = []

        for row_num, row in enumerate(reader, start=2):
            try:
                txn, key = self._parse_row(row, column_map, row_num)
                transactions.append(txn)
                idempotency_keys.append(key)
            except (ValueError, KeyError) as exc:
                logger.warning("csv_row_skipped", row=row_num, reason=str(exc))

        return transactions, idempotency_keys

    def _decode_content(self, file_content: bytes) -> str:
        """Decode bytes to string with encoding fallback."""
        try:
            return file_content.decode("utf-8")
        except UnicodeDecodeError:
            return file_content.decode("latin-1")

    def _detect_columns(self, fieldnames: list[str]) -> dict[str, str]:
        """Auto-detect column mapping from CSV headers."""
        mapping: dict[str, str] = {}
        for field in fieldnames:
            normalized = field.strip().lower()
            if normalized in DATE_HEADERS:
                mapping["date"] = field
            elif normalized in AMOUNT_HEADERS:
                mapping["amount"] = field
            elif normalized in DESCRIPTION_HEADERS:
                mapping["description"] = field
            elif normalized in CATEGORY_HEADERS:
                mapping["category"] = field
            elif normalized in TYPE_HEADERS:
                mapping["type"] = field
        return mapping

    def _parse_row(
        self, row: dict[str, str], column_map: dict[str, str], row_num: int
    ) -> tuple[TransactionCreate, str]:
        """Parse a single CSV row into a TransactionCreate and idempotency key."""
        date_raw = self._get_field(row, column_map, "date", required=True)
        amount_raw = self._get_field(row, column_map, "amount", required=True)

        if not date_raw or not amount_raw:
            raise ValueError(f"Row {row_num}: missing date or amount")

        date_str = self._normalize_date(date_raw.strip())
        amount_val = self._parse_amount(amount_raw.strip())

        description = self._get_field(row, column_map, "description")
        description = description.strip() if description else None

        category = self._resolve_category(self._get_field(row, column_map, "category"))
        txn_type = self._resolve_type(self._get_field(row, column_map, "type"), amount_val)

        txn = TransactionCreate(
            type=txn_type,
            amount=abs(amount_val),
            category=category,
            description=description,
            date=date_str,
        )

        key = self.generate_idempotency_key(date_str, abs(amount_val), description)
        return txn, key

    def _get_field(
        self, row: dict[str, str], column_map: dict[str, str], field: str, *, required: bool = False
    ) -> str | None:
        """Get field value from row using column mapping."""
        col_name = column_map.get(field)
        if col_name is None:
            if required:
                raise ValueError(f"Required column '{field}' not found in headers")
            return None
        value = row.get(col_name, "").strip()
        if not value and required:
            raise ValueError(f"Empty value for required column '{field}'")
        return value if value else None

    def _normalize_date(self, date_str: str) -> str:
        """Try multiple date formats and return YYYY-MM-DD."""
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Unrecognized date format: '{date_str}'")

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string, handling commas and currency symbols."""
        cleaned = re.sub(r"[^\d.,\-+]", "", amount_str)
        cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError as exc:
            raise ValueError(f"Invalid amount: '{amount_str}'") from exc

    def _resolve_category(self, raw: str | None) -> Category:
        """Resolve category string to Category enum, defaulting to 'other'."""
        if not raw:
            return Category.other
        normalized = raw.strip().lower()
        if normalized in VALID_CATEGORIES:
            return Category(normalized)
        return Category.other

    def _resolve_type(self, raw: str | None, amount: float) -> TransactionType:
        """Resolve transaction type from explicit value or amount sign."""
        if raw:
            normalized = raw.strip().lower()
            if normalized in ("income", "expense"):
                return TransactionType(normalized)
        return TransactionType.expense if amount < 0 else TransactionType.income
