"""
Golden Path REST API.

Provides HTTP endpoints for Golden Path registry operations.
Designed to be called by stdio MCP clients.
"""

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError

from .auth import verify_api_key
from .registry import GoldenPathRegistry

# Initialize FastAPI app
app = FastAPI(
    title="Golden Path Registry API",
    description="REST API for Golden Path storage and retrieval",
    version="1.0.0"
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/golden-paths")
async def create_golden_path(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form("0.0.1"),
    namespace: str = Depends(verify_api_key)
):
    """
    Upload a Golden Path to the registry.

    Args:
        file: Golden Path markdown file
        name: Golden Path name (kebab-case)
        version: Semver version (default: 0.0.1)
        namespace: User's namespace (from API key)

    Returns:
        Upload confirmation with registry location
    """
    # Read file content
    content = await file.read()

    # Upload to S3
    result = registry.create_path(namespace, name, version, content)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@app.get("/api/v1/golden-paths/{namespace}/{name}")
async def fetch_golden_path(
    namespace: str,
    name: str,
    version: str = "latest",
    user_namespace: str = Depends(verify_api_key)
):
    """
    Fetch a Golden Path from the registry.

    Args:
        namespace: Golden Path namespace
        name: Golden Path name
        version: Version to fetch (default: latest)
        user_namespace: Authenticated user's namespace

    Returns:
        Golden Path content and metadata
    """
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
    namespace: str = None,
    user_namespace: str = Depends(verify_api_key)
):
    """
    List Golden Paths in the registry.

    Args:
        namespace: Optional namespace filter
        user_namespace: Authenticated user's namespace

    Returns:
        List of Golden Paths with metadata
    """
    try:
        paths = registry.list_paths(namespace)
        return {"paths": paths}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/search")
async def search_golden_paths(
    q: str,
    user_namespace: str = Depends(verify_api_key)
):
    """
    Search Golden Paths by query.

    Args:
        q: Search query
        user_namespace: Authenticated user's namespace

    Returns:
        List of matching Golden Paths
    """
    try:
        results = registry.search_paths(q)
        return {"results": results}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/golden-paths/{namespace}/{name}")
async def delete_golden_path(
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
