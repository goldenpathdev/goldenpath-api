# Golden Path API Authentication

## Overview

The Golden Path REST API uses **Bearer token authentication** via the standard `Authorization` header.

## Authentication Header

```
Authorization: Bearer {api_key}
```

## Authentication Requirements

### Read Operations (Optional Auth)

These endpoints work **with or without** authentication:

- `GET /api/v1/golden-paths` - List Golden Paths
- `GET /api/v1/golden-paths/{namespace}/{name}` - Fetch Golden Path
- `GET /api/v1/search` - Search Golden Paths

**Without auth**: Public read access
**With auth**: Same access (auth may enable future features like private paths)

### Write Operations (Required Auth)

These endpoints **require** authentication:

- `POST /api/v1/golden-paths` - Create Golden Path
- `DELETE /api/v1/golden-paths/{namespace}/{name}` - Delete Golden Path

**Without auth**: Returns `401 Unauthorized`
**With auth**: Creates/deletes in your namespace

## API Keys

### Development

```bash
GOLDENPATH_API_KEY=gp_dev_hardcoded
```

This key maps to namespace `@goldenpathdev`.

### Production

API keys will be managed through user accounts and will map to user namespaces.

## MCP Client Integration

The stdio MCP client automatically includes the API key when available:

```typescript
// In .claude.json:
{
  "mcpServers": {
    "goldenpath": {
      "type": "stdio",
      "command": "node",
      "args": ["/path/to/goldenpath-mcp/build/index.js"],
      "env": {
        "GOLDENPATH_API_BASE": "http://localhost:8000",
        "GOLDENPATH_API_KEY": "gp_dev_hardcoded"
      }
    }
  }
}
```

The MCP client checks for `GOLDENPATH_API_KEY` environment variable and includes it in all requests:

```typescript
const headers = {
  "Authorization": `Bearer ${apiKey}`,
  // ... other headers
};
```

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

Returned when authentication is required but not provided.

### 403 Forbidden

```json
{
  "detail": "Not authorized to delete from namespace @other"
}
```

Returned when trying to modify resources in a namespace you don't own.

## Command Authorization

### Commands Requiring API Key

- `/gp:create` - Upload new Golden Path
- `/gp:remove` - Delete Golden Path

**User Experience**: If `GOLDENPATH_API_KEY` is not set, these commands will fail with authentication error.

### Commands NOT Requiring API Key

- `/gp:list` - List Golden Paths
- `/gp:info` - Show Golden Path details
- `/gp:search` - Search Golden Paths
- `/gp:pave` - Execute Golden Path
- `/gp:help` - Show help

**User Experience**: These commands work without any configuration.

## Security Considerations

### Current Implementation

- API keys are hardcoded in `api/auth.py`
- Single development key: `gp_dev_hardcoded`
- No encryption in transit (HTTP for local dev)

### Production Requirements

- [ ] Database-backed API key management
- [ ] User account system
- [ ] HTTPS only (TLS encryption)
- [ ] Key rotation support
- [ ] Rate limiting per key
- [ ] Audit logging
- [ ] Key scopes/permissions

## Example Requests

### List Golden Paths (No Auth)

```bash
curl http://localhost:8000/api/v1/golden-paths
```

### List Golden Paths (With Auth)

```bash
curl -H "Authorization: Bearer gp_dev_hardcoded" \
  http://localhost:8000/api/v1/golden-paths
```

### Create Golden Path (Auth Required)

```bash
curl -X POST \
  -H "Authorization: Bearer gp_dev_hardcoded" \
  -F "file=@hello-world.md" \
  -F "name=hello-world" \
  -F "version=1.0.0" \
  http://localhost:8000/api/v1/golden-paths
```

### Delete Golden Path (Auth Required)

```bash
curl -X DELETE \
  -H "Authorization: Bearer gp_dev_hardcoded" \
  "http://localhost:8000/api/v1/golden-paths/@goldenpathdev/hello-world?version=1.0.0"
```

## Future Enhancements

### OAuth 2.0 Integration

Future versions may support OAuth 2.0 for third-party integrations:

```
Authorization: Bearer {oauth_access_token}
```

### API Key Formats

Production API keys will follow a structured format:

```
gp_live_{base64_random_32_bytes}
gp_test_{base64_random_32_bytes}
```

### Namespace Mapping

API keys will map to user accounts which own namespaces:

```
gp_live_abc123 → user@example.com → @username
```

## Testing Authentication

### Test Script

```bash
#!/bin/bash

API_BASE="http://localhost:8000"
API_KEY="gp_dev_hardcoded"

# Test read without auth (should work)
echo "=== List without auth ==="
curl -s $API_BASE/api/v1/golden-paths | jq

# Test read with auth (should work)
echo "=== List with auth ==="
curl -s -H "Authorization: Bearer $API_KEY" \
  $API_BASE/api/v1/golden-paths | jq

# Test write without auth (should fail)
echo "=== Create without auth (should fail) ==="
curl -s -X POST $API_BASE/api/v1/golden-paths \
  -F "file=@test.md" -F "name=test" | jq

# Test write with auth (should work)
echo "=== Create with auth (should work) ==="
curl -s -X POST \
  -H "Authorization: Bearer $API_KEY" \
  $API_BASE/api/v1/golden-paths \
  -F "file=@test.md" -F "name=test" | jq
```
