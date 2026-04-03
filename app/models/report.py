from pydantic import BaseModel
from typing import List, Optional


class HitDetail(BaseModel):
    entity_type: str
    rule_type: str
    location: str
    original_preview: str
    masked_preview: str
    confidence: float = 1.0
    masked_by: Optional[str] = None
    skipped_reason: Optional[str] = None


class Report(BaseModel):
    task_id: str
    original_file: str
    output_file: str
    status: str
    total_hits: int
    details: List[HitDetail]
