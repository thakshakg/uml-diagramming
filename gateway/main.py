import httpx # Required for making HTTP requests
import os # Required to access environment variables
from fastapi import FastAPI, HTTPException, Body
from typing import List, Optional, Dict, Any
from uuid import UUID # Removed uuid4 and datetime as they are in models
from .models import Token, UMLDiagram, UserLogin, CreateDiagramRequestFromGateway, UpdateDiagramRequestFromGateway # Import models

app = FastAPI()

DIAGRAM_SERVICE_URL = os.getenv("DIAGRAM_SERVICE_URL", "http://localhost:8001") # Default for local dev if not set

@app.get("/")
async def root():
    return {"message": "API Gateway"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin = Body(...)):
    # Mock login - in a real app, this would call an auth service or check a DB
    if user_credentials.username == "testuser" and user_credentials.password == "password":
        return Token(token="fake-jwt-token")
    raise HTTPException(status_code=401, detail="Invalid credentials")

async def forward_request(method: str, path: str, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None):
    async with httpx.AsyncClient() as client:
        try:
            url = f"{DIAGRAM_SERVICE_URL}{path}"
            response = await client.request(method, url, params=params, json=json_data, timeout=10.0)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Diagram service unavailable: {e}")


@app.get("/diagrams", response_model=List[UMLDiagram])
async def get_diagrams():
    # Forward to Diagram Service
    return await forward_request(method="GET", path="/diagrams")

@app.post("/diagrams", response_model=UMLDiagram, status_code=201)
async def create_diagram(diagram_data: CreateDiagramRequestFromGateway = Body(...)): # Use specific model
    # Forward to Diagram Service
    return await forward_request(method="POST", path="/diagrams", json_data=diagram_data.model_dump())

@app.get("/diagrams/{id}", response_model=UMLDiagram)
async def get_diagram(id: UUID):
    # Forward to Diagram Service
    return await forward_request(method="GET", path=f"/diagrams/{id}")

@app.put("/diagrams/{id}", response_model=UMLDiagram)
async def update_diagram(id: UUID, diagram_data: UpdateDiagramRequestFromGateway = Body(...)): # Use specific model
    # Forward to Diagram Service
    return await forward_request(method="PUT", path=f"/diagrams/{id}", json_data=diagram_data.model_dump(exclude_unset=True))

@app.delete("/diagrams/{id}", response_model=Dict[str, bool])
async def delete_diagram(id: UUID):
    # Forward to Diagram Service
    return await forward_request(method="DELETE", path=f"/diagrams/{id}")

# BaseModel is now imported from .models
