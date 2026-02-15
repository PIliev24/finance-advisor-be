from pydantic import BaseModel


class ImportResult(BaseModel):
    total_parsed: int
    total_created: int
    total_skipped: int
    total_failed: int
    errors: list[str]
