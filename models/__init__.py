from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

# This model defines the structured data we want the LLM to extract.
class StructuredObject(BaseModel):
    reason: str
    sentiment: Optional[str]
    company_id: Optional[str]
    company_name: Optional[str]
    customer_name: Optional[str]
    country: Optional[str]
    email_address: Optional[str]
    phone: Optional[str]
    product_name: Optional[str]
    escalate: bool

# This is the main data object that flows through the system.
# It's the payload of our CloudEvents.
class OuterWrapper(BaseModel):
    message_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    structured: Optional[StructuredObject] = None
    route: Optional[dict] = None
    support: Optional[dict] = None
    website: Optional[dict] = None
    finance: Optional[dict] = None
    comment: Optional[str] = None
    error: Optional[list] = Field(default_factory=list)

class Route(str, Enum):
    support = "support"
    finance = "finance"
    website = "website"
    unknown = "unknown"

class SelectedRoute(BaseModel):
    route: Route
    reason: str
    escalation_required: bool
