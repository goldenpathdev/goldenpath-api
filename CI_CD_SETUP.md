# CI/CD Setup for Golden Path API

## Overview

Automated deployment pipeline that builds, pushes, and deploys the Golden Path API to AWS ECS whenever code is pushed to the `main` branch.

## Workflow File

Location: `.github/workflows/deploy-api.yml`

## Deployment Flow

```
Push to main → GitHub Actions → Build Docker Image → Push to ECR → Update ECS Service → Verify Deployment
```

## Prerequisites

### GitHub Secrets Required

You need to configure the following secrets in your GitHub repository:

1. **AWS_ACCESS_KEY_ID**: AWS access key for GitHub Actions
2. **AWS_SECRET_ACCESS_KEY**: AWS secret access key for GitHub Actions

These credentials must have permissions for:
- ECR (push images)
- ECS (update service, describe services)

### GitHub Variables Required

1. **AWS_REGION**: The AWS region (e.g., `us-east-1`)

### Setting up GitHub Secrets

1. Go to repository settings: `https://github.com/goldenpathdev/goldenpath-api/settings/secrets/actions`
2. Click "New repository secret"
3. Add `AWS_ACCESS_KEY_ID` with your AWS access key
4. Add `AWS_SECRET_ACCESS_KEY` with your AWS secret access key

### Setting up GitHub Variables

1. Go to repository settings: `https://github.com/goldenpathdev/goldenpath-api/settings/variables/actions`
2. Click "New repository variable"
3. Name: `AWS_REGION`
4. Value: `us-east-1`

## Workflow Steps

### 1. Checkout Code
Uses `actions/checkout@v4` to clone the repository.

### 2. Configure AWS Credentials
Uses `aws-actions/configure-aws-credentials@v4` with AWS access keys for authentication.

### 3. Login to ECR
Uses `aws-actions/amazon-ecr-login@v2` to authenticate with Amazon ECR.

### 4. Build and Push Docker Image
- Builds Docker image with tag based on commit SHA
- Tags image as both `<sha>` and `latest`
- Pushes both tags to ECR repository: `105249143262.dkr.ecr.us-east-1.amazonaws.com/goldenpath-api`

### 5. Force ECS Service Update
Uses `aws ecs update-service --force-new-deployment` to trigger a new deployment with the latest image.

### 6. Wait for Deployment
Uses `aws ecs wait services-stable` to wait for the deployment to complete successfully.

### 7. Verify Deployment
Retrieves and displays deployment status from ECS.

## Environment Configuration

The workflow uses these environment variables:

```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: goldenpath-api
  ECS_CLUSTER: goldenpath-cluster-prod
  ECS_SERVICE: goldenpath-service-prod
  CONTAINER_NAME: goldenpath-api
```

## Manual Deployment

You can also trigger the workflow manually:

1. Go to Actions tab in GitHub
2. Select "Deploy API to ECS" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Health Check Verification

After deployment, verify the health endpoint:

```bash
curl https://0jx9t9xz7j.execute-api.us-east-1.amazonaws.com/prod/health | jq .
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected"
}
```

If database is unavailable:
```json
{
  "status": "degraded",
  "database": "disconnected",
  "error": "Connection error message"
}
```

## Monitoring Deployments

### View Deployment Logs

```bash
# GitHub Actions logs
# Go to: https://github.com/goldenpathdev/goldenpath-api/actions

# ECS task logs
aws logs tail /ecs/goldenpath-prod --follow --region us-east-1

# ECS service status
aws ecs describe-services \
  --cluster goldenpath-cluster-prod \
  --services goldenpath-service-prod \
  --region us-east-1
```

### Check Deployment Status

```bash
aws ecs describe-services \
  --cluster goldenpath-cluster-prod \
  --services goldenpath-service-prod \
  --region us-east-1 \
  --query 'services[0].deployments[*].[status,desiredCount,runningCount,rolloutState]' \
  --output table
```

## Troubleshooting

### Deployment Fails

1. **Check GitHub Actions logs** for build or push errors
2. **Check ECS events** for deployment issues:
   ```bash
   aws ecs describe-services \
     --cluster goldenpath-cluster-prod \
     --services goldenpath-service-prod \
     --region us-east-1 \
     --query 'services[0].events[:5]' \
     --output table
   ```

### Container Won't Start

1. **Check task logs**:
   ```bash
   aws logs tail /ecs/goldenpath-prod --since 30m
   ```

2. **Check environment variables** in task definition

3. **Verify IAM role permissions** for task execution

### Image Not Found

1. **Verify ECR repository exists**:
   ```bash
   aws ecr describe-repositories --repository-names goldenpath-api
   ```

2. **Check image was pushed**:
   ```bash
   aws ecr list-images --repository-name goldenpath-api
   ```

## Rollback

If a deployment fails and you need to rollback:

```bash
# Get previous task definition revision
aws ecs list-task-definitions --family-prefix goldenpath-prod

# Update service to use previous revision
aws ecs update-service \
  --cluster goldenpath-cluster-prod \
  --service goldenpath-service-prod \
  --task-definition goldenpath-prod:PREVIOUS_REVISION
```

## Future Improvements

- [ ] Add automated tests before deployment
- [ ] Implement blue/green deployment
- [ ] Add Slack/email notifications for deployment status
- [ ] Implement automatic rollback on health check failure
- [ ] Add deployment metrics and monitoring
- [ ] Configure staging environment workflow
