"""S3 registry operations for Golden Paths."""

import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional


class GoldenPathRegistry:
    """Manages Golden Path storage in S3."""

    def __init__(self, bucket_name: str = "goldenpath-registry", region: str = "us-east-1"):
        """
        Initialize registry.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3', region_name=region)

    def create_path(
        self,
        namespace: str,
        name: str,
        version: str,
        content: bytes
    ) -> Dict:
        """
        Upload Golden Path to S3.

        Args:
            namespace: Namespace with @ prefix (e.g., "@goldenpathdev")
            name: Golden Path name (kebab-case)
            version: Semver version
            content: File content as bytes

        Returns:
            Success response with S3 location
        """
        # Validate YAML frontmatter
        if not content.startswith(b'---'):
            return {
                "success": False,
                "error": "Invalid Golden Path: missing YAML frontmatter"
            }

        # Construct S3 key
        s3_key = f"{namespace}/{name}/{version}.md"

        try:
            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType='text/markdown',
                Metadata={
                    'namespace': namespace,
                    'name': name,
                    'version': version
                }
            )

            return {
                "success": True,
                "namespace": namespace,
                "name": name,
                "version": version,
                "s3_location": f"s3://{self.bucket_name}/{s3_key}",
                "registry_path": f"{namespace}/{name}:{version}"
            }

        except ClientError as e:
            return {
                "success": False,
                "error": str(e)
            }

    def fetch_path(
        self,
        namespace: str,
        name: str,
        version: str = "latest"
    ) -> Dict:
        """
        Fetch Golden Path from S3.

        Args:
            namespace: Namespace with @ prefix
            name: Golden Path name
            version: Version to fetch

        Returns:
            Golden Path content and metadata

        Raises:
            ClientError: If path not found
        """
        s3_key = f"{namespace}/{name}/{version}.md"

        try:
            response = self.s3.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            content = response['Body'].read().decode('utf-8')

            return {
                "namespace": namespace,
                "name": name,
                "version": version,
                "content": content,
                "last_modified": response['LastModified'].isoformat()
            }

        except self.s3.exceptions.NoSuchKey:
            raise ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
                'GetObject'
            )

    def list_paths(self, namespace: Optional[str] = None) -> List[Dict]:
        """
        List Golden Paths in registry.

        Args:
            namespace: Optional namespace filter

        Returns:
            List of Golden Path metadata
        """
        prefix = namespace if namespace else ""

        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            paths = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.md'):
                    # Parse key: namespace/name/version.md
                    parts = key.split('/')
                    if len(parts) >= 3:
                        paths.append({
                            "namespace": parts[0],
                            "name": parts[1],
                            "version": parts[2].replace('.md', ''),
                            "last_modified": obj['LastModified'].isoformat()
                        })

            return paths

        except ClientError as e:
            raise e

    def delete_path(
        self,
        namespace: str,
        name: str,
        version: str = "latest"
    ) -> Dict:
        """
        Delete Golden Path from S3.

        Args:
            namespace: Namespace with @ prefix
            name: Golden Path name
            version: Version to delete

        Returns:
            Deletion confirmation
        """
        s3_key = f"{namespace}/{name}/{version}.md"

        try:
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                "success": True,
                "namespace": namespace,
                "name": name,
                "version": version,
                "message": f"Deleted {namespace}/{name}:{version}"
            }

        except ClientError as e:
            return {
                "success": False,
                "error": str(e)
            }

    def search_paths(self, query: str) -> List[Dict]:
        """
        Search Golden Paths by name or namespace.

        Args:
            query: Search query

        Returns:
            List of matching Golden Paths
        """
        # Simple implementation: list all and filter
        all_paths = self.list_paths()
        query_lower = query.lower()

        return [
            path for path in all_paths
            if query_lower in path['name'].lower()
            or query_lower in path['namespace'].lower()
        ]
