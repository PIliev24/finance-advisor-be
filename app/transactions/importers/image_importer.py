import base64
import json

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.transactions.importers.base import ImporterBase
from app.transactions.models import Category, TransactionType
from app.transactions.schemas import TransactionCreate

logger = structlog.get_logger()

EXTRACTION_PROMPT = """Extract all financial transactions from this image. \
Return a JSON array where each element has:
- "date": string in YYYY-MM-DD format
- "amount": positive number
- "type": "income" or "expense"
- "category": one of [food, transport, housing, utilities, entertainment, health, \
education, clothing, savings, investments, salary, freelance, gifts, subscriptions, \
insurance, debt_payment, other]
- "description": brief description

Return ONLY valid JSON array, no other text."""

MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class ImageImporter(ImporterBase):
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def parse(
        self, file_content: bytes, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Send image to vision LLM and parse extracted transactions."""
        mime_type = self._detect_mime_type(filename)
        b64_image = base64.b64encode(file_content).decode("utf-8")

        message = HumanMessage(
            content=[
                {"type": "text", "text": EXTRACTION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                },
            ]
        )

        response = await self._llm.ainvoke([message])
        raw_text = response.content if isinstance(response.content, str) else str(response.content)

        return self._parse_llm_response(raw_text, filename)

    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename extension."""
        lower = filename.lower()
        for ext, mime in MIME_TYPES.items():
            if lower.endswith(ext):
                return mime
        return "image/png"

    def _parse_llm_response(
        self, raw_text: str, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Parse LLM JSON response into transactions and idempotency keys."""
        json_str = self._extract_json(raw_text)

        try:
            items = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error("image_llm_json_error", filename=filename, error=str(exc))
            return [], []

        if not isinstance(items, list):
            logger.error("image_llm_not_array", filename=filename)
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
                logger.warning("image_item_skipped", index=idx, reason=str(exc))

        return transactions, idempotency_keys

    def _extract_json(self, raw_text: str) -> str:
        """Strip markdown code fences if present."""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
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
