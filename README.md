# Golden Path REST API

HTTP REST API for Golden Path registry operations.

## Architecture

```
stdio MCP Client → HTTPS → REST API → S3
```

This API is designed to be called by stdio MCP servers running locally on user machines.

## Endpoints

### Create Golden Path
```
POST /api/v1/golden-paths
Authorization: Bearer {api_key}
Content-Type: multipart/form-data

file: {golden_path.md}
name: {path-name}
version: {semver}
```

### Fetch Golden Path
```
GET /api/v1/golden-paths/{namespace}/{name}?version=latest
Authorization: Bearer {api_key}
```

### List Golden Paths
```
GET /api/v1/golden-paths?namespace={optional}
Authorization: Bearer {api_key}
```

### Search Golden Paths
```
GET /api/v1/search?q={query}
Authorization: Bearer {api_key}
```

### Delete Golden Path
```
DELETE /api/v1/golden-paths/{namespace}/{name}?version=latest
Authorization: Bearer {api_key}
```

## Authentication

Uses Bearer token authentication. API keys map to namespaces:

```python
VALID_API_KEYS = {
    "gp_dev_hardcoded": "@goldenpathdev"
}
```

## Development

### Run Locally
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Build Docker Image
```bash
docker build -t goldenpath-api .
docker run -p 8000:8000 goldenpath-api
```

### Deploy to ECS
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin {account}.dkr.ecr.us-east-1.amazonaws.com

docker tag goldenpath-api:latest {account}.dkr.ecr.us-east-1.amazonaws.com/goldenpath-api:latest
docker push {account}.dkr.ecr.us-east-1.amazonaws.com/goldenpath-api:latest

# Force new deployment
aws ecs update-service \
  --cluster goldenpath-cluster-dev \
  --service goldenpath-api-service-dev \
  --force-new-deployment
```

## Environment Variables

- `PORT`: HTTP port (default: 8000)
- `AWS_REGION`: AWS region for S3 (default: us-east-1)
- `BUCKET_NAME`: S3 bucket name (default: goldenpath-registry)
