from pydantic import BaseModel
from typing import List, Optional

# This model defines the structured data we want the LLM to extract.
class StructuredObject(BaseModel):
    reason: str
    customer_name: str
    email_address: str
    product_name: str
    sentiment: str
    escalate: bool

# This is the main data object that flows through the system.
# It's the payload of our CloudEvents.
class OuterWrapper(BaseModel):
    message_id: str
    content: str
    metadata: dict
    structured: Optional[StructuredObject] = None
    route: Optional[str] = None
    support: Optional[dict] = None
    website: Optional[dict] = None
    finance: Optional[dict] = None
    error: List[str] = []
