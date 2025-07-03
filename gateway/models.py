from pydantic import BaseModel
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, Dict, Any

class Token(BaseModel):
    token: str

class UserLogin(BaseModel):
    username: str
    password: str

# This model is primarily for the gateway to understand what it's forwarding/receiving
# The source of truth for diagram structure will be in the diagram service
class UMLDiagram(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    payload_url: str # URL to the actual diagram data in MinIO
    created_at: datetime
    updated_at: datetime

class CreateDiagramRequestFromGateway(BaseModel):
    name: str
    payload: Dict[str, Any] # The actual diagram content
    # owner_id will be handled by auth or taken from authenticated user in a real scenario
    # For now, gateway might just pass it through if provided by client, or diagram service assigns it

class UpdateDiagramRequestFromGateway(BaseModel):
    name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
