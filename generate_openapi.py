#!/usr/bin/env python3
"""
Generate OpenAPI specification from FastAPI app.

This script exports the OpenAPI spec in both JSON and YAML formats.
Run this whenever API endpoints or schemas change.

Usage:
    python generate_openapi.py
"""

import json
import yaml
from pathlib import Path

from api.main import app

def main():
    """Generate OpenAPI spec in JSON and YAML formats."""
    # Get OpenAPI schema
    openapi_schema = app.openapi()

    # Paths for output files
    json_path = Path(__file__).parent / "openapi.json"
    yaml_path = Path(__file__).parent / "openapi.yaml"

    # Write JSON format
    with open(json_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"✅ Generated: {json_path}")

    # Write YAML format
    with open(yaml_path, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, default_flow_style=False)
    print(f"✅ Generated: {yaml_path}")

    # Print summary
    paths = openapi_schema.get("paths", {})
    print(f"\n📊 API Summary:")
    print(f"   Total endpoints: {len(paths)}")

    # Count by tag
    tags = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            for tag in details.get("tags", ["untagged"]):
                tags[tag] = tags.get(tag, 0) + 1

    print(f"   Endpoints by tag:")
    for tag, count in sorted(tags.items()):
        print(f"     - {tag}: {count}")

if __name__ == "__main__":
    main()
