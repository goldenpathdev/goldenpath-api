# CI/CD Setup Guide

This document explains how to set up GitHub Actions for automated deployment of the goldenpath-api service.

## Architecture

**Workflow**: `Push to main` → `Build Docker Image` → `Push to ECR` → `Update ECS Service` → `Wait for Deployment`

**Components**:
- **GitHub Actions**: CI/CD orchestration
- **Amazon ECR**: Docker image registry
- **Amazon ECS**: Container orchestration (Fargate)
- **IAM OIDC**: Secure authentication without long-lived credentials

## Prerequisites

1. **AWS Resources** (already provisioned):
   - ECR Repository: `goldenpath-api`
   - ECS Cluster: `goldenpath-cluster-prod`
   - ECS Service: `goldenpath-service-prod`
   - VPC, ALB, API Gateway, etc.

2. **GitHub Repository**: `goldenpathdev/goldenpath-api` (needs to be created)

## Setup Steps

### 1. Create IAM OIDC Provider for GitHub Actions

```bash
export AWS_PROFILE=goldenpath-dev

# Create OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role for GitHub Actions

Create a trust policy file `github-actions-trust-policy.json`:

```json
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
```

Create the IAM role:

```bash
# Create the role
aws iam create-role \
  --role-name GitHubActionsDeployAPI \
  --assume-role-policy-document file://github-actions-trust-policy.json

# Attach ECR permissions
aws iam attach-role-policy \
  --role-name GitHubActionsDeployAPI \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Create and attach ECS deployment policy
cat > ecs-deploy-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:RegisterTaskDefinition",
        "ecs:DescribeTaskDefinition",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name GitHubActionsDeployAPI \
  --policy-name ECSDeployment \
  --policy-document file://ecs-deploy-policy.json
```

### 3. Configure GitHub Repository Secrets

In your GitHub repository settings, add the following secret:

1. Navigate to: `Settings` → `Secrets and variables` → `Actions`
2. Click `New repository secret`
3. Add:
   - **Name**: `AWS_ROLE_ARN`
   - **Value**: `arn:aws:iam::105249143262:role/GitHubActionsDeployAPI`

### 4. Push Workflow to Repository

The workflow file is already created at `.github/workflows/deploy-api.yml`. When you push this to the `main` branch of the GitHub repository, it will be ready to run.

```bash
# Ensure you're in the goldenpath-api directory
cd /home/ubuntu/goldenpath.dev/environments/dev01/code/goldenpath-api

# Check git status
git status

# Add the workflow file
git add .github/workflows/deploy-api.yml

# Commit
git commit -m "Add GitHub Actions deployment workflow"

# Push to main branch
git push origin main
```

## Testing the CI/CD Pipeline

### Initial Test

1. Make a small change to verify the pipeline works:

```bash
# Example: Add a comment to the health endpoint
echo "# CI/CD test" >> api/routes/health.py

git add api/routes/health.py
git commit -m "Test: CI/CD pipeline verification"
git push origin main
```

2. Monitor the workflow:
   - Go to GitHub Actions tab in your repository
   - Watch the "Deploy API to ECS" workflow run
   - Verify each step completes successfully

3. Verify deployment:

```bash
# Check ECS service status
export AWS_PROFILE=goldenpath-dev
aws ecs describe-services \
  --cluster goldenpath-cluster-prod \
  --services goldenpath-service-prod \
  --query 'services[0].[serviceName,status,runningCount,desiredCount,deployments[*].[status,taskDefinition]]' \
  --output table

# Test the health endpoint (after ALB is enabled)
curl https://api.goldenpath.dev/health
```

## Workflow Behavior

**Triggers**:
- Automatic: Push to `main` branch
- Manual: GitHub Actions UI → "Run workflow"

**Steps**:
1. **Checkout code**: Get latest source from repository
2. **Configure AWS credentials**: Use OIDC to authenticate with AWS (no secrets stored)
3. **Login to ECR**: Get Docker registry credentials
4. **Build and push**: Create Docker image, tag with commit SHA + `latest`, push to ECR
5. **Force ECS update**: Trigger new deployment with updated image
6. **Wait for deployment**: Monitor until service is stable
7. **Verify deployment**: Show deployment status

**Deployment Strategy**:
- **Rolling update**: ECS deploys new tasks before stopping old ones
- **Zero downtime**: ALB routes traffic only to healthy tasks
- **Automatic rollback**: If new tasks fail health checks, ECS keeps old tasks running

## Troubleshooting

### Workflow Fails on AWS Authentication

**Error**: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Fix**: Verify OIDC provider is created and IAM role trust policy is correct:

```bash
# Check OIDC provider exists
aws iam list-open-id-connect-providers

# Verify trust policy
aws iam get-role --role-name GitHubActionsDeployAPI
```

### Workflow Fails on ECR Push

**Error**: "denied: access denied"

**Fix**: Verify IAM role has ECR permissions:

```bash
aws iam list-attached-role-policies --role-name GitHubActionsDeployAPI
```

### ECS Deployment Fails

**Error**: "Service failed to stabilize"

**Diagnosis**:

```bash
# Check task logs
aws logs tail /ecs/goldenpath-prod --since 10m --follow

# Check service events
aws ecs describe-services \
  --cluster goldenpath-cluster-prod \
  --services goldenpath-service-prod \
  --query 'services[0].events[0:5]' \
  --output table
```

### Health Check Failing

**Error**: Tasks continuously failing ALB health checks

**Fix**: Verify:
1. Application is listening on correct port (8000)
2. /health endpoint returns 200 OK
3. Security groups allow ALB → ECS traffic
4. Health check settings in target group are appropriate

```bash
# Test container locally
docker run -p 8000:8000 105249143262.dkr.ecr.us-east-1.amazonaws.com/goldenpath-api:latest

# In another terminal
curl http://localhost:8000/health
```

## Current Status

### ✅ Completed
- GitHub Actions workflow created
- Documentation written
- Workflow file ready to commit

### ⏳ Waiting On
- **AWS Support**: Enable ALB creation on account (account currently blocked)
- **GitHub Repository**: Create `goldenpathdev/goldenpath-api` repository
- **IAM Setup**: Create OIDC provider and GitHub Actions role

### 📋 Next Steps (After ALB Enabled)
1. Contact AWS support to enable ALB creation
2. Re-run terraform to create ALB: `terraform apply -target=module.alb -auto-approve`
3. Test /health endpoint: `curl https://api.goldenpath.dev/health`
4. Create GitHub repository: `goldenpathdev/goldenpath-api`
5. Set up IAM OIDC provider and role (steps above)
6. Push code to GitHub and test CI/CD pipeline

## Reference

**AWS Resources**:
- Account ID: `105249143262`
- Region: `us-east-1`
- ECR: `105249143262.dkr.ecr.us-east-1.amazonaws.com/goldenpath-api`
- ECS Cluster: `goldenpath-cluster-prod`
- ECS Service: `goldenpath-service-prod`
- API Domain: `api.goldenpath.dev`

**GitHub**:
- Organization: `goldenpathdev`
- Repository: `goldenpath-api` (to be created)
- Workflow: `.github/workflows/deploy-api.yml`
