import hashlib
from abc import ABC, abstractmethod

from app.transactions.schemas import TransactionCreate


class ImporterBase(ABC):
    @abstractmethod
    async def parse(
        self, file_content: bytes, filename: str
    ) -> tuple[list[TransactionCreate], list[str]]:
        """Parse file content and return a list of transactions with idempotency keys."""
        ...

    @staticmethod
    def generate_idempotency_key(date: str, amount: float, description: str | None) -> str:
        """Generate deterministic hash for deduplication."""
        raw = f"{date}|{amount}|{description or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
