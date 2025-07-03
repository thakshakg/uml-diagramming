from sqlmodel import SQLModel, Field # Changed from pydantic BaseModel
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, Dict, Any

# Core Diagram model - this represents the structure in the database
# It's now a SQLModel model, which means it's also a Pydantic model
class UMLDiagramDB(SQLModel, table=True): # Added table=True
    # Make id Optional for the database, as it will be auto-generated if not provided by client
    # and primary_key=True is essential for SQLModel tables.
    # default_factory is for Pydantic, default (with sa_default for SQLAlch) is for DB.
    # For UUIDs, ensure your DB supports them or use a converter. PostgreSQL has native UUID.
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True)
    owner_id: UUID = Field(index=True) # In a real app, this would link to a User table via ForeignKey
    payload_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # __tablename__ = "umldiagram" # Optional: if you want to name the table differently

# Model for creating a new diagram (request from API Gateway) - Pydantic model
class CreateDiagramRequest(SQLModel): # Can be SQLModel too if preferred, or just Pydantic's BaseModel
    name: str
    payload: Dict[str, Any] # The actual diagram content to be stored in MinIO
    owner_id: Optional[UUID] = None # Could be set by gateway/auth or a default

# Model for updating an existing diagram (request from API Gateway)
class UpdateDiagramRequest(SQLModel): # Changed to SQLModel for consistency, can also be Pydantic BaseModel
    name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None # If payload is provided, it needs to be updated in MinIO

# Response model for diagram (what the Diagram Service returns)
# This can also be a SQLModel if it helps, but Pydantic BaseModel is fine
class UMLDiagramResponse(SQLModel): # Changed to SQLModel for consistency
    id: UUID
    name: str
    owner_id: UUID
    payload_url: str
    created_at: datetime
    updated_at: datetime
    payload: Optional[Dict[str, Any]] = None # Add optional payload field

# User model - as per README, though auth is optional and might be a separate service
# If this were a table, it would be `class User(SQLModel, table=True):`
class User(SQLModel): # Changed to SQLModel for consistency
    id: UUID = Field(default_factory=uuid4) # If it were a table, add primary_key=True
    username: str
    # password_hash: str # Not storing raw passwords
    email: str
    # created_at: datetime = Field(default_factory=datetime.utcnow)
    # This model is more for if this service handled user creation/management directly.
    # For now, owner_id in UMLDiagramDB is just a UUID.
    # If integrating with an auth service, we'd primarily use user IDs.
