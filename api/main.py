"""
Golden Path REST API.

Provides HTTP endpoints for Golden Path registry operations.
Designed to be called by stdio MCP clients.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from sqlalchemy import text

from .auth import verify_api_key, optional_verify_api_key
from .registry import GoldenPathRegistry
from .database import engine
from .routers import users, api_keys
from contextlib import asynccontextmanager

# Configure logging with JSON format for structured analytics
import json
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_analytics(event: str, data: dict):
    """Log analytics event with structured data."""
    logger.info(f"ANALYTICS: {json.dumps({'event': event, **data})}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Golden Path API")
    # Database connection is already handled by get_db() dependency
    yield
    logger.info("Shutting down Golden Path API")
    await engine.dispose()

# Initialize FastAPI app
app = FastAPI(
    title="Golden Path Registry API",
    description="REST API for Golden Path storage and retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize registry
registry = GoldenPathRegistry()

# Include routers
app.include_router(users.router)
app.include_router(api_keys.router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint with database connectivity test.

    Returns:
        - status: "ok" if all checks pass, "degraded" if database fails
        - database: Connection status ("connected" or "disconnected")
        - error: Error message if database check fails
    """
    health_status = {
        "status": "ok",
        "database": "unknown"
    }

    # Test database connectivity
    try:
        async with engine.connect() as conn:
            # Simple query to verify database is responding
            await conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["status"] = "degraded"
        health_status["database"] = "disconnected"
        health_status["error"] = str(e)

    return health_status


@app.post("/api/v1/golden-paths")
async def create_golden_path(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form("0.0.1"),
    namespace: str = Depends(verify_api_key)
):
    """
    Upload a Golden Path to the registry.

    Args:
        file: Golden Path markdown file
        name: str = Form(...),
        version: Semver version (default: 0.0.1)
        namespace: User's namespace (from API key)

    Returns:
        Upload confirmation with registry location
    """
    # Log analytics
    log_analytics("create", {
        "visitor_id": request.headers.get("x-visitor-id", "anonymous"),
        "client_version": request.headers.get("x-client-version", "unknown"),
        "namespace": namespace,
        "name": name,
        "version": version
    })

    # Read file content
    content = await file.read()

    # Upload to S3
    result = registry.create_path(namespace, name, version, content)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@app.get("/api/v1/golden-paths/{namespace}/{name}")
async def fetch_golden_path(
    request: Request,
    namespace: str,
    name: str,
    version: str = "latest",
    user_namespace: str | None = Depends(optional_verify_api_key)
):
    """
    Fetch a Golden Path from the registry.

    Args:
        namespace: Golden Path namespace
        name: Golden Path name
        version: Version to fetch (default: latest)
        user_namespace: Authenticated user's namespace (optional)

    Returns:
        Golden Path content and metadata
    """
    # Log analytics
    log_analytics("fetch", {
        "visitor_id": request.headers.get("x-visitor-id", "anonymous"),
        "client_version": request.headers.get("x-client-version", "unknown"),
        "path": f"{namespace}/{name}:{version}",
        "authenticated": user_namespace is not None
    })

    try:
        result = registry.fetch_path(namespace, name, version)
        return result

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(
                status_code=404,
                detail=f"Golden Path not found: {namespace}/{name}:{version}"
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/golden-paths")
async def list_golden_paths(
    request: Request,
    namespace: str = None,
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "name",
    user_namespace: str | None = Depends(optional_verify_api_key)
):
    """
    List Golden Paths in the registry with pagination and sorting.

    Args:
        namespace: Optional namespace filter
        page: Page number (default: 1)
        per_page: Items per page (default: 50, max: 100)
        sort_by: Sort field (name, namespace, version, last_modified) (default: name)
        user_namespace: Authenticated user's namespace (optional)

    Returns:
        Paginated list of Golden Paths with metadata
    """
    # Validate and constrain parameters
    page = max(1, page)  # Must be at least 1
    per_page = min(max(1, per_page), 100)  # Between 1 and 100

    # Validate sort_by
    valid_sort_fields = ["name", "namespace", "version", "last_modified"]
    if sort_by not in valid_sort_fields:
        sort_by = "name"

    # Log analytics
    log_analytics("list", {
        "visitor_id": request.headers.get("x-visitor-id", "anonymous"),
        "client_version": request.headers.get("x-client-version", "unknown"),
        "namespace": namespace,
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
        "authenticated": user_namespace is not None
    })

    try:
        # Get all matching paths
        all_paths = registry.list_paths(namespace)

        # Sort paths
        reverse = sort_by == "last_modified"  # Newest first for timestamps
        all_paths.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

        # Calculate pagination
        total_count = len(all_paths)
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        # Paginate
        paths = all_paths[start_idx:end_idx]

        return {
            "paths": paths,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/search")
async def search_golden_paths(
    request: Request,
    q: str,
    user_namespace: str | None = Depends(optional_verify_api_key)
):
    """
    Search Golden Paths by query.

    Args:
        q: Search query
        user_namespace: Authenticated user's namespace (optional)

    Returns:
        List of matching Golden Paths
    """
    # Log analytics
    log_analytics("search", {
        "visitor_id": request.headers.get("x-visitor-id", "anonymous"),
        "client_version": request.headers.get("x-client-version", "unknown"),
        "query": q,
        "authenticated": user_namespace is not None
    })

    try:
        results = registry.search_paths(q)
        return {"results": results}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/golden-paths/{namespace}/{name}")
async def delete_golden_path(
    request: Request,
    namespace: str,
    name: str,
    version: str = "latest",
    user_namespace: str = Depends(verify_api_key)
):
    """
    Delete a Golden Path from the registry.

    Args:
        namespace: Golden Path namespace
        name: Golden Path name
        version: Version to delete (default: latest)
        user_namespace: Authenticated user's namespace

    Returns:
        Deletion confirmation
    """
    # Log analytics
    log_analytics("delete", {
        "visitor_id": request.headers.get("x-visitor-id", "anonymous"),
        "client_version": request.headers.get("x-client-version", "unknown"),
        "path": f"{namespace}/{name}:{version}",
        "user_namespace": user_namespace
    })

    # Authorization check: can only delete your own namespace
    if namespace != user_namespace:
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized to delete from namespace {namespace}"
        )

    result = registry.delete_path(namespace, name, version)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
