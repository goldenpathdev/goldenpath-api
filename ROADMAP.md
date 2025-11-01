# Golden Path API & CLI Development Roadmap

## Overview

This document tracks the development roadmap for both the **Golden Path API** (backend) and **Golden Path CLI** (command-line interface). As we build out API endpoints, we'll simultaneously implement the corresponding CLI commands for testing and user interaction.

## Current State

### ✅ Completed

**API (goldenpath-api)**:
- FastAPI application structure
- Database models (Alembic migrations)
- S3 registry integration working
- `/health` endpoint (working)
- `/api/v1/golden-paths` GET endpoint (working - returns S3 data)
- Docker Compose development environment with hot-reload
- PostgreSQL database integration

**CLI (goldenpath-cli)**:
- Basic Click CLI structure
- Configuration management (`~/.goldenpath/config.json`)
- HTTP client (httpx) with authentication
- Commands:
  - `gp config set/get/show` - Configuration management
  - `gp list` - List Golden Paths (stub)
  - `gp fetch` - Fetch Golden Path (stub)
  - `gp search` - Search Golden Paths (stub)
  - `gp create` - Create Golden Path (stub)

**Infrastructure**:
- Local Docker Compose dev environment
- ECS deployment to AWS (public IP testing mode)
- S3 bucket for Golden Path storage
- PostgreSQL database

## Development Workflow

### Phase 1: Core CRUD Operations

#### Epic 1.1: List Golden Paths
**API Tasks**:
- [x] Basic GET `/api/v1/golden-paths` working with S3
- [x] Implement pagination (`page`, `per_page` parameters)
- [x] Add filtering by namespace
- [x] Add sorting options (`sort_by`: name, namespace, version, last_modified)
- [x] Return pagination metadata (total_count, total_pages, has_next, has_prev)
- [ ] Add database caching layer

**CLI Tasks**:
- [x] Basic `gp list` command structure
- [x] Update client to handle paginated response format
- [ ] Implement API call with error handling
- [ ] Add namespace filtering (`--namespace`)
- [ ] Add pagination options (`--page`, `--per-page`)
- [ ] Add sorting options (`--sort`)
- [ ] Rich table formatting
- [ ] Add `--json` output option

**Test Plan**:
1. ✅ Test basic list endpoint (all paths)
2. ✅ Test pagination (page=1&per_page=2)
3. ✅ Test namespace filtering (namespace=@goldenpathdev)
4. ✅ Test combined pagination and filtering
5. ⏳ Install CLI dependencies and run `gp list` command
6. ⏳ Test with no Golden Paths (empty state)

---

#### Epic 1.2: Fetch Golden Path
**API Tasks**:
- [ ] Implement GET `/api/v1/golden-paths/{namespace}/{name}`
- [ ] Add version parameter support
- [ ] Return markdown content from S3
- [ ] Add cache headers
- [ ] Track download analytics

**CLI Tasks**:
- [ ] Implement `gp fetch @goldenpath/hello-world`
- [ ] Parse namespace/name from path argument
- [ ] Save to current directory or specified path
- [ ] Add `--version` option
- [ ] Show download progress
- [ ] Display success message with file location

**Test Plan**:
1. Fetch existing Golden Path from S3
2. Verify file saved correctly
3. Test version specification
4. Test error handling (not found, network error)

---

#### Epic 1.3: Create Golden Path
**API Tasks**:
- [ ] Implement POST `/api/v1/golden-paths`
- [ ] Validate multipart/form-data upload
- [ ] Parse YAML frontmatter
- [ ] Validate namespace ownership (via API key → user)
- [ ] Upload to S3
- [ ] Store metadata in database
- [ ] Return created Golden Path details

**CLI Tasks**:
- [ ] Implement `gp create my-path.md --namespace @username --name my-path`
- [ ] Read local markdown file
- [ ] Validate file format
- [ ] Upload via API
- [ ] Display success/error message
- [ ] Add `--version` option (default: 0.0.1)

**Test Plan**:
1. Create Golden Path from local file
2. Verify uploaded to S3
3. Verify metadata in database
4. Test authentication required
5. Test duplicate detection

---

#### Epic 1.4: Search Golden Paths
**API Tasks**:
- [ ] Implement GET `/api/v1/search?q={query}`
- [ ] Search in name, description, tags
- [ ] Return ranked results
- [ ] Add search analytics

**CLI Tasks**:
- [ ] Implement `gp search "deployment"`
- [ ] Display search results in table
- [ ] Highlight matched terms
- [ ] Add `--limit` option

**Test Plan**:
1. Search for existing Golden Path
2. Search for non-existent term
3. Test partial matches
4. Test special characters

---

#### Epic 1.5: Delete Golden Path
**API Tasks**:
- [ ] Implement DELETE `/api/v1/golden-paths/{namespace}/{name}`
- [ ] Verify ownership via API key
- [ ] Delete from S3
- [ ] Delete from database
- [ ] Add version support (delete specific version vs all)

**CLI Tasks**:
- [ ] Implement `gp delete @username/my-path`
- [ ] Add confirmation prompt
- [ ] Add `--force` flag to skip confirmation
- [ ] Add `--version` to delete specific version
- [ ] Display success message

**Test Plan**:
1. Delete owned Golden Path
2. Test unauthorized deletion (error)
3. Test deletion with confirmation
4. Test force deletion

---

### Phase 2: User Management & Authentication

#### Epic 2.1: User Registration
**API Tasks**:
- [ ] Implement POST `/api/v1/users/register`
- [ ] Integrate with Cognito OAuth
- [ ] Auto-generate namespace from email/username
- [ ] Create default API key
- [ ] Return user details + API key

**CLI Tasks**:
- [ ] Implement `gp auth register`
- [ ] Open browser for OAuth flow
- [ ] Store API key in config
- [ ] Display welcome message with namespace

**Test Plan**:
1. Register new user via email
2. Register via Google OAuth
3. Verify API key created
4. Verify namespace assigned

---

#### Epic 2.2: User Profile
**API Tasks**:
- [ ] Implement GET `/api/v1/users/me`
- [ ] Implement PATCH `/api/v1/users/me`
- [ ] Allow updating display name, bio, website

**CLI Tasks**:
- [ ] Implement `gp profile show`
- [ ] Implement `gp profile update --name "John Doe"`
- [ ] Display profile in formatted table

**Test Plan**:
1. View own profile
2. Update profile fields
3. Verify changes persisted

---

#### Epic 2.3: API Key Management
**API Tasks**:
- [ ] Implement GET `/api/v1/users/me/api-keys`
- [ ] Implement POST `/api/v1/users/me/api-keys`
- [ ] Implement DELETE `/api/v1/users/me/api-keys/{key_id}`
- [ ] Allow naming API keys
- [ ] Track last used timestamp

**CLI Tasks**:
- [ ] Implement `gp keys list`
- [ ] Implement `gp keys create --name "My Dev Key"`
- [ ] Implement `gp keys delete {key_id}`
- [ ] Display table with key prefix, name, created, last used

**Test Plan**:
1. List API keys
2. Create new API key
3. Delete API key
4. Verify deleted key no longer works

---

### Phase 3: Advanced Features

#### Epic 3.1: Golden Path Versioning
**API Tasks**:
- [ ] Support semantic versioning (1.0.0, 1.0.1, etc.)
- [ ] List all versions for a Golden Path
- [ ] Fetch specific version
- [ ] Mark version as latest
- [ ] Delete specific version

**CLI Tasks**:
- [ ] `gp versions @goldenpath/hello-world`
- [ ] `gp fetch @goldenpath/hello-world --version 1.0.0`
- [ ] `gp create --version 1.0.1`

---

#### Epic 3.2: Analytics & Metrics
**API Tasks**:
- [ ] Track Golden Path downloads
- [ ] Track searches
- [ ] Track API key usage
- [ ] Endpoint: GET `/api/v1/analytics/golden-paths/{namespace}/{name}`

**CLI Tasks**:
- [ ] `gp stats @username/my-path`
- [ ] Display downloads, searches, stars

---

#### Epic 3.3: Social Features
**API Tasks**:
- [ ] Star/favorite Golden Paths
- [ ] View trending Golden Paths
- [ ] View recently created

**CLI Tasks**:
- [ ] `gp star @goldenpath/hello-world`
- [ ] `gp trending`
- [ ] `gp recent`

---

## Testing Strategy

### Unit Tests
- [ ] API endpoint tests (pytest)
- [ ] CLI command tests (pytest + Click testing)
- [ ] Database model tests
- [ ] S3 integration tests (mocked)

### Integration Tests
- [ ] End-to-end CLI → API → Database flows
- [ ] Authentication flows
- [ ] File upload/download flows

### Manual Testing Checklist
For each implemented endpoint/command pair:
1. Test happy path
2. Test authentication required
3. Test authorization (ownership)
4. Test validation errors
5. Test not found errors
6. Test network errors

## Development Commands

### API Development
```bash
# Start local dev environment
docker compose up -d

# Watch API logs
docker logs -f api-dev01

# Run migrations
docker exec api-dev01 alembic upgrade head

# Test endpoint
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/golden-paths
```

### CLI Development
```bash
# Install CLI in development mode
cd /home/ubuntu/goldenpath.dev/environments/dev01/code/goldenpath-cli
pip install -e .

# Configure for local API
gp config set api-url http://localhost:8000

# Test commands
gp list
gp fetch @goldenpath/hello-world
```

## Current Sprint (Week 1)

### Sprint Goal
Implement and test the core list/fetch/create operations

### Tasks
1. **Complete List Implementation**
   - [ ] API: Add pagination and filtering
   - [ ] CLI: Implement full list command with rich output
   - [ ] Test: Manual test with local API

2. **Implement Fetch**
   - [ ] API: GET endpoint for fetching Golden Path content
   - [ ] CLI: Download and save Golden Path locally
   - [ ] Test: Fetch from S3 and verify content

3. **Implement Create**
   - [ ] API: POST endpoint with file upload
   - [ ] CLI: Upload local markdown file
   - [ ] Test: End-to-end creation flow

## Notes

### Implementation Patterns
- **Error Handling**: All API endpoints return consistent error format (`{"error": "message", "detail": {}}`)
- **Authentication**: Bearer token via `Authorization: Bearer gp_live_xxxxx`
- **CLI Output**: Use Rich library for tables, progress bars, and colors
- **Configuration**: Store in `~/.goldenpath/config.json`

### Design Decisions
- **Why PostgreSQL + S3**: Metadata in DB for fast queries, content in S3 for scalability
- **Why Click over Typer**: More mature, better documentation
- **Why httpx over requests**: Async support for future parallelization

### Open Questions
- [ ] Should we support Golden Path dependencies?
- [ ] Should we have a "trending" algorithm?
- [ ] Should users be able to transfer ownership?
- [ ] Should we support organizations/teams?
