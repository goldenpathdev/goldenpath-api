# Golden Path Registry API Documentation

REST API for Golden Path storage, retrieval, and user management.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://api.goldenpath.dev`

## Authentication

All protected endpoints require Bearer token authentication using an API key.

### Header Format
```
Authorization: Bearer gp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Getting an API Key

1. Register via Cognito (OAuth or email)
2. API key is automatically generated if email is verified
3. Additional keys can be created via `/api/v1/users/me/api-keys`

## API Specifications

The API follows OpenAPI 3.1.0 specification:

- **JSON Format**: [openapi.json](./openapi.json)
- **YAML Format**: [openapi.yaml](./openapi.yaml)
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

## Endpoints Overview

### User Management (`/api/v1/users`)

#### Register User
```http
POST /api/v1/users/register
Content-Type: application/json

{
  "user_id": "cognito-user-id",
  "email": "user@example.com",
  "email_verified": true,
  "name": "John Doe",
  "auth_provider": "google|email|github"
}
```

**Response (201)**:
```json
{
  "user_id": "cognito-user-id",
  "email": "user@example.com",
  "email_verified": true,
  "namespace": "@john",
  "auth_provider": "google",
  "default_api_key": "gp_live_...",
  "message": null
}
```

**Note**: This endpoint is typically called by Cognito PostAuthentication Lambda.

#### Get Current User
```http
GET /api/v1/users/me
Authorization: Bearer gp_live_xxxxx
```

**Response (200)**:
```json
{
  "user_id": "cognito-user-id",
  "email": "user@example.com",
  "email_verified": true,
  "name": "John Doe",
  "namespace": "@john",
  "bio": null,
  "github_username": null,
  "auth_provider": "google",
  "subscription_tier": "free",
  "created_at": "2025-10-29T00:00:00Z",
  "updated_at": "2025-10-29T00:00:00Z"
}
```

#### Update User Profile
```http
PATCH /api/v1/users/me
Authorization: Bearer gp_live_xxxxx
Content-Type: application/json

{
  "name": "John Smith",
  "bio": "Building awesome things with Golden Paths",
  "github_username": "johnsmith"
}
```

**Response (200)**: Updated user object

### API Key Management (`/api/v1/users/me/api-keys`)

#### List API Keys
```http
GET /api/v1/users/me/api-keys
Authorization: Bearer gp_live_xxxxx
```

**Response (200)**:
```json
{
  "api_keys": [
    {
      "key_id": "key_xxxxx",
      "user_id": "cognito-user-id",
      "name": "Default API Key",
      "key_prefix": "gp_live_...",
      "scopes": ["read", "write"],
      "created_at": "2025-10-29T00:00:00Z",
      "last_used": "2025-10-29T01:00:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

#### Create API Key
```http
POST /api/v1/users/me/api-keys
Authorization: Bearer gp_live_xxxxx
Content-Type: application/json

{
  "name": "CI/CD Key",
  "scopes": ["read", "write"]
}
```

**Response (201)**:
```json
{
  "key_id": "key_xxxxx",
  "name": "CI/CD Key",
  "api_key": "gp_live_xxxxx...",
  "key_prefix": "gp_live_...",
  "scopes": ["read", "write"],
  "created_at": "2025-10-29T00:00:00Z",
  "message": "Save this API key securely. You won't be able to see it again."
}
```

**⚠️ Important**: The full `api_key` is only returned once. Save it securely!

#### Delete API Key
```http
DELETE /api/v1/users/me/api-keys/{key_id}
Authorization: Bearer gp_live_xxxxx
```

**Response (204)**: No content

**Note**: You cannot delete the API key you're currently using for authentication.

### Golden Path Management (`/api/v1/golden-paths`)

#### Create Golden Path
```http
POST /api/v1/golden-paths
Authorization: Bearer gp_live_xxxxx
Content-Type: multipart/form-data

file: <golden-path.md>
name: hello-world
version: 1.0.0
```

**Response (200)**:
```json
{
  "success": true,
  "path": "@namespace/hello-world:1.0.0",
  "s3_key": "@namespace/hello-world/1.0.0.md"
}
```

#### Fetch Golden Path
```http
GET /api/v1/golden-paths/{namespace}/{name}?version=latest
```

**Response (200)**:
```json
{
  "namespace": "@goldenpath",
  "name": "hello-world",
  "version": "1.0.0",
  "content": "--- yaml frontmatter and markdown content ---"
}
```

#### List Golden Paths
```http
GET /api/v1/golden-paths?namespace=@goldenpath
```

**Response (200)**:
```json
{
  "paths": [
    {
      "namespace": "@goldenpath",
      "name": "hello-world",
      "versions": ["1.0.0", "0.9.0"]
    }
  ]
}
```

#### Search Golden Paths
```http
GET /api/v1/search?q=github
```

**Response (200)**:
```json
{
  "results": [
    {
      "namespace": "@goldenpath",
      "name": "new-github-organization",
      "version": "1.0.0",
      "description": "Set up new GitHub organization"
    }
  ]
}
```

#### Delete Golden Path
```http
DELETE /api/v1/golden-paths/{namespace}/{name}?version=latest
Authorization: Bearer gp_live_xxxxx
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Golden Path deleted"
}
```

**Authorization**: You can only delete Golden Paths in your own namespace.

## Health Check

```http
GET /health
```

**Response (200)**:
```json
{
  "status": "ok"
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Missing Authorization header"
}
```

### 403 Forbidden
```json
{
  "detail": "Email must be verified before creating API keys"
}
```

### 404 Not Found
```json
{
  "detail": "API key not found or already deleted"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Rate Limiting

Currently no rate limiting is enforced in development. Production will implement:

- **Free tier**: 100 requests/hour
- **Teams tier**: 1000 requests/hour
- **Enterprise**: Custom limits

## Versioning

The API uses URL versioning (`/api/v1/`). Breaking changes will increment the version number.

## Regenerating OpenAPI Spec

After making changes to endpoints or schemas:

```bash
# Inside the API container
docker compose exec api python generate_openapi.py

# Copy specs to host
docker compose cp api:/app/openapi.json ./openapi.json
docker compose cp api:/app/openapi.yaml ./openapi.yaml
```

Or use the provided script:
```bash
./scripts/update_openapi.sh  # TODO: Create this script
```

## Testing

### Example: Register and Create API Key

```bash
# 1. Register user
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-123",
    "email": "test@example.com",
    "email_verified": true,
    "name": "Test User",
    "auth_provider": "email"
  }'

# Save the returned API key
API_KEY="gp_live_xxxxx"

# 2. Get current user
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $API_KEY"

# 3. Create additional API key
curl -X POST http://localhost:8000/api/v1/users/me/api-keys \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key", "scopes": ["read"]}'
```

## Schema Reference

See [openapi.json](./openapi.json) or [openapi.yaml](./openapi.yaml) for complete schema definitions including:

- `UserRegisterRequest`
- `UserRegisterResponse`
- `UserResponse`
- `UserUpdateRequest`
- `APIKeyCreateRequest`
- `APIKeyCreateResponse`
- `APIKeyResponse`
- `APIKeyListResponse`

## Support

- **Documentation**: https://docs.goldenpath.dev
- **Issues**: https://github.com/goldenpathdev/goldenpath-api/issues
- **Email**: support@goldenpath.dev
