import io
import json

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from pypdf import PdfReader

from app.transactions.importers.base import ImporterBase
from app.transactions.models import Category, TransactionType
from app.transactions.schemas import TransactionCreate

logger = structlog.get_logger()

MAX_TEXT_LENGTH = 10_000

EXTRACTION_PROMPT = """Extract all financial transactions from the following text. \
Return a JSON array where each element has:
- "date": string in YYYY-MM-DD format
- "amount": positive number
- "type": "income" or "expense"
- "category": one of [food, transport, housing, utilities, entertainment, health, \
education, clothing, savings, investments, salary, freelance, gifts, subscriptions, \
insurance, debt_payment, other]
- "description": brief description

Return ONLY valid JSON array, no other text.

Text:
{text}"""


class PDFImporter(ImporterBase):
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def parse(
        self, file_content: bytes, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Extract text from PDF, send to LLM, and parse transactions."""
        text = self._extract_text(file_content, filename)
        if not text.strip():
            logger.warning("pdf_empty_text", filename=filename)
            return [], []

        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(
                "pdf_text_truncated",
                filename=filename,
                original_length=len(text),
                truncated_to=MAX_TEXT_LENGTH,
            )
            text = text[:MAX_TEXT_LENGTH]

        prompt = EXTRACTION_PROMPT.format(text=text)
        message = HumanMessage(content=prompt)
        response = await self._llm.ainvoke([message])
        raw_text = response.content if isinstance(response.content, str) else str(response.content)

        return self._parse_llm_response(raw_text, filename)

    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from all PDF pages, concatenated with page separators."""
        reader = PdfReader(io.BytesIO(file_content))
        pages: list[str] = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"--- Page {i + 1} ---\n{page_text}")
        return "\n\n".join(pages)

    def _parse_llm_response(
        self, raw_text: str, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Parse LLM JSON response into transactions and idempotency keys."""
        json_str = self._extract_json(raw_text)

        try:
            items = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error("pdf_llm_json_error", filename=filename, error=str(exc))
            return [], []

        if not isinstance(items, list):
            logger.error("pdf_llm_not_array", filename=filename)
            return [], []

        transactions: list[TransactionCreate] = []
        idempotency_keys: list[str] = []

        for idx, item in enumerate(items):
            try:
                txn = self._item_to_transaction(item)
                key = self.generate_idempotency_key(txn.date, txn.amount, txn.description)
                transactions.append(txn)
                idempotency_keys.append(key)
            except (ValueError, KeyError) as exc:
                logger.warning("pdf_item_skipped", index=idx, reason=str(exc))

        return transactions, idempotency_keys

    def _extract_json(self, raw_text: str) -> str:
        """Strip markdown code fences if present."""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text.strip()

    def _item_to_transaction(self, item: dict) -> TransactionCreate:
        """Convert a single parsed dict to TransactionCreate."""
        category_raw = item.get("category", "other")
        valid_categories = {c.value for c in Category}
        category = category_raw if category_raw in valid_categories else "other"

        type_raw = item.get("type", "expense")
        valid_types = {t.value for t in TransactionType}
        txn_type = type_raw if type_raw in valid_types else "expense"

        return TransactionCreate(
            date=item["date"],
            amount=abs(float(item["amount"])),
            type=TransactionType(txn_type),
            category=Category(category),
            description=item.get("description"),
        )
