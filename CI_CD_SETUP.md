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

1. **AWS_ROLE_ARN**: The ARN of the IAM role that GitHub Actions will assume
   - Format: `arn:aws:iam::105249143262:role/github-actions-role`
   - This role must have permissions for:
     - ECR (push images)
     - ECS (update service, describe services)

### Setting up OIDC (Recommended)

The workflow uses OpenID Connect (OIDC) for secure authentication without storing AWS credentials.

#### Create IAM Role for GitHub Actions

```bash
# Create trust policy
cat > github-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::105249143262:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:goldenpathdev/goldenpath-api:*"
        }
      }
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name github-actions-goldenpath-api \
  --assume-role-policy-document file://github-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name github-actions-goldenpath-api \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name github-actions-goldenpath-api \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

#### Add Secret to GitHub

1. Go to repository settings: `https://github.com/goldenpathdev/goldenpath-api/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `AWS_ROLE_ARN`
4. Value: `arn:aws:iam::105249143262:role/github-actions-goldenpath-api`

## Workflow Steps

### 1. Checkout Code
Uses `actions/checkout@v4` to clone the repository.

### 2. Configure AWS Credentials
Uses `aws-actions/configure-aws-credentials@v4` with OIDC to assume the IAM role.

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
