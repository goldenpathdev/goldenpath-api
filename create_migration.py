"""Create initial Alembic migration."""
import subprocess
import sys

def create_migration():
    """Generate initial migration from models."""
    cmd = [
        "alembic", "revision", "--autogenerate",
        "-m", "Initial schema with users, api_keys, and golden_paths_metadata"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error creating migration: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(create_migration())
