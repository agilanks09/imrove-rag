from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class LoanDocument(BaseModel):
    document_id: str
    borrower_name: Optional[str] = None
    loan_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    loan_term: Optional[int] = None
    property_address: Optional[str] = None
    property_type: Optional[str] = None
    lender_name: Optional[str] = None
    loan_type: Optional[str] = None
    loan_purpose: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    document_type: Optional[str] = None
    embedding: Optional[List[float]] = None
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict) -> "LoanDocument":
        return cls(**data)
