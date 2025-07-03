import pytest
import pytest_asyncio # For async fixtures
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session as SQLModelSession # Renamed to avoid conflict
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession # Renamed
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from unittest.mock import patch, AsyncMock, MagicMock
import uuid
import json
from datetime import datetime, timezone

# Adjust import paths as necessary
from diagram.main import app, get_async_session
from diagram.models import UMLDiagramDB, CreateDiagramRequest, UpdateDiagramRequest
from diagram.database import DATABASE_URL # To override for tests
import diagram.storage as storage_module # To mock MinIO client

# Use an in-memory SQLite database for testing
# Change the DATABASE_URL for the test session
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db" # In-memory SQLite for async

# Create a synchronous engine for initial table creation if needed,
# or ensure init_db can run with SQLite.
# For async, SQLModel needs an async engine.
test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False) # Turn off echo for tests

# Async session fixture for tests
@pytest_asyncio.fixture(scope="function") # function scope for clean DB each test
async def test_db_session() -> SQLModelAsyncSession: # type: ignore
    # Create tables for each test function if using function scope
    async with test_async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    TestAsyncSessionLocal = sessionmaker(
        bind=test_async_engine, class_=SQLModelAsyncSession, expire_on_commit=False
    )
    async with TestAsyncSessionLocal() as session:
        yield session

    # Drop tables after each test function
    async with test_async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

# Fixture to override the get_async_session dependency in the app
@pytest_asyncio.fixture(name="client")
async def client_fixture(test_db_session: SQLModelAsyncSession): # type: ignore
    def override_get_async_session():
        yield test_db_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    # Mock MinIO client within the storage module for all tests in this file
    mock_minio = MagicMock(spec=storage_module.minio_client)

    with patch.object(storage_module, 'minio_client', mock_minio), \
         patch.object(storage_module, 'ensure_bucket_exists', AsyncMock(return_value=None)) as mock_ensure_bucket, \
         patch.object(storage_module, 'upload_diagram_payload', AsyncMock()) as mock_upload, \
         patch.object(storage_module, 'get_diagram_payload', AsyncMock()) as mock_get, \
         patch.object(storage_module, 'delete_diagram_payload', AsyncMock()) as mock_delete:

        # Store mocks on the client or a shared context if needed by tests directly
        # For now, tests will assert calls on these globally patched mocks or rely on their setup
        storage_module.mock_upload_global = mock_upload # type: ignore
        storage_module.mock_get_global = mock_get # type: ignore
        storage_module.mock_delete_global = mock_delete # type: ignore
        storage_module.mock_minio_global = mock_minio # type: ignore

        # Ensure the bucket check is called during app startup simulation if necessary
        # TestClient doesn't run startup events by default unless you manage app lifespan
        # For this setup, we assume ensure_bucket_exists is handled or not critical for these unit tests
        # Or, we can explicitly call startup handlers if needed:
        # await app.router.startup() -> This is how you might do it with LifespanManager in httpx

        yield TestClient(app) # type: ignore

    app.dependency_overrides.clear()


def test_read_root_diagram_service(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Diagram Service"}

def test_health_check_diagram_service(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_diagram_success(client: TestClient, test_db_session: SQLModelAsyncSession):
    diagram_payload_content = {"type": "class", "nodes": []}
    diagram_name = "My Test Diagram"
    owner_id = uuid.uuid4()

    # Configure mock for upload_diagram_payload
    # The actual object_name is generated inside the endpoint. We can't know it beforehand
    # unless we mock uuid.uuid4() or make the object_name predictable.
    # For this test, we'll have mock_upload_diagram_payload return a known URL
    # and verify it was called with an object name matching the pattern.

    # Let's make the mock return a URL that includes the object name it received.
    # This requires a side_effect.
    async def mock_upload_side_effect(object_name: str, data: bytes):
        # We can assert object_name format here if needed, e.g. check(uuid.UUID(object_name.split('.')[0]))
        return f"s3://{storage_module.MINIO_BUCKET_NAME}/{object_name}"

    storage_module.mock_upload_global.side_effect = mock_upload_side_effect


    response = client.post(
        "/diagrams",
        json={"name": diagram_name, "payload": diagram_payload_content, "owner_id": str(owner_id)}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == diagram_name
    assert data["owner_id"] == str(owner_id)
    # The payload_url is now dynamic based on the object_name generated in the endpoint
    # We need to extract the object_name from the mock call to build the expected URL.
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify MinIO upload was called correctly
    storage_module.mock_upload_global.assert_called_once()
    args, kwargs = storage_module.mock_upload_global.call_args
    called_object_name = args[0]
    assert ".json" in called_object_name # Verify it's a json file
    try:
        uuid.UUID(called_object_name.split('.')[0]) # Check that the name part is a UUID
    except ValueError:
        pytest.fail(f"Object name {called_object_name} does not start with a valid UUID.")

    assert args[1] == json.dumps(diagram_payload_content).encode('utf-8')

    expected_payload_url = f"s3://{storage_module.MINIO_BUCKET_NAME}/{called_object_name}"
    assert data["payload_url"] == expected_payload_url

    # Verify data in DB
    db_diagram = await test_db_session.get(UMLDiagramDB, uuid.UUID(data["id"]))
    assert db_diagram is not None
    assert db_diagram.name == diagram_name
    assert db_diagram.payload_url == expected_payload_url

@pytest.mark.asyncio
async def test_get_diagram_success(client: TestClient, test_db_session: SQLModelAsyncSession):
    # 1. Create a diagram first (directly in DB for this test, or via API)
    diagram_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    object_name = f"{diagram_id}.json"
    payload_url = f"s3://{storage_module.MINIO_BUCKET_NAME}/{object_name}"
    created_time = datetime.now(timezone.utc)

    db_item = UMLDiagramDB(
        id=diagram_id,
        name="Fetched Diagram",
        owner_id=owner_id,
        payload_url=payload_url,
        created_at=created_time,
        updated_at=created_time
    )
    test_db_session.add(db_item)
    await test_db_session.commit()
    await test_db_session.refresh(db_item)

    # Configure mock for get_diagram_payload
    mock_payload_content = {"type": "sequence", "participants": []}
    mock_payload_bytes = json.dumps(mock_payload_content).encode('utf-8')
    storage_module.mock_get_global.return_value = mock_payload_bytes

    response = client.get(f"/diagrams/{diagram_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(diagram_id)
    assert data["name"] == "Fetched Diagram"
    assert data["payload_url"] == payload_url
    assert data["payload"] == mock_payload_content # Check that payload is included

    storage_module.mock_get_global.assert_called_once_with(object_name)

@pytest.mark.asyncio
async def test_get_diagram_not_found(client: TestClient):
    non_existent_id = uuid.uuid4()
    response = client.get(f"/diagrams/{non_existent_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Diagram not found"}

@pytest.mark.asyncio
async def test_get_diagrams_list_success(client: TestClient, test_db_session: SQLModelAsyncSession):
    # 1. Create multiple diagrams
    created_time = datetime.now(timezone.utc)
    diagram1_id = uuid.uuid4()
    diagram2_id = uuid.uuid4()

    item1 = UMLDiagramDB(id=diagram1_id, name="Diagram 1", owner_id=uuid.uuid4(), payload_url="s3://b/1.json", created_at=created_time, updated_at=created_time)
    item2 = UMLDiagramDB(id=diagram2_id, name="Diagram 2", owner_id=uuid.uuid4(), payload_url="s3://b/2.json", created_at=created_time, updated_at=created_time)

    test_db_session.add(item1)
    test_db_session.add(item2)
    await test_db_session.commit()

    response = client.get("/diagrams")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Verify based on one of the items (e.g. by name or id)
    # Note: The list order is not guaranteed unless specified in the query
    ids_in_response = {item["id"] for item in data}
    assert str(diagram1_id) in ids_in_response
    assert str(diagram2_id) in ids_in_response

    for item_data in data:
        assert "payload" not in item_data # List endpoint doesn't return full payloads

# TODO: Add tests for PUT /diagrams/{id}
# TODO: Add tests for DELETE /diagrams/{id}
# TODO: Add tests for error cases with MinIO (e.g., upload fails, get fails but not FileNotFoundError)
