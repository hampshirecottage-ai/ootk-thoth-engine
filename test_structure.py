import sys
from pathlib import Path
from dotenv import load_dotenv

# Set project root path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Load .env variables
load_dotenv(BASE_DIR / ".env")

def test_imports():
    """Verify that modules in src/ and scripts/ can be imported without error."""
    print("1. Testing Module Imports...")
    try:
        from src import ootk_engine
        print("   ✓ Successfully imported src.ootk_engine")
    except Exception as e:
        print(f"   ✗ Failed to import src.ootk_engine: {e}")

    try:
        from src.spread_engine import fetch_all_cards, analyze_elemental_balance
        print("   ✓ Successfully imported functions from src.spread_engine")
    except Exception as e:
        print(f"   ✗ Failed to import src.spread_engine: {e}")

def test_directory_paths():
    """Verify that required directories exist or can be resolved."""
    print("\n2. Testing Directory & File Locations...")
    required_dirs = ["config", "database", "prompts", "src", "scripts", "static/images", "templates"]
    
    for d in required_dirs:
        target_path = BASE_DIR / d
        if target_path.exists():
            print(f"   ✓ Directory found: {d}/")
        else:
            print(f"   ✗ Directory missing: {d}/")

def test_database_connection():
    """Verify database connection using the updated configuration."""
    print("\n3. Testing Database Connection...")
    try:
        from scripts.fetch_cards import get_thoth_cards
        cards = get_thoth_cards()
        if cards:
            print(f"   ✓ Database query successful! Retrieved {len(cards)} card records.")
        else:
            print("   ! Database connection succeeded, but returned 0 records.")
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")

def test_output_directory():
    """Verify output directory creation logic."""
    print("\n4. Testing Output Directory Guard...")
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.exists():
        print(f"   ✓ Output directory ready: {output_dir}")

if __name__ == "__main__":
    print("=== OOTK THOTH ENGINE INTEGRATION TEST ===\n")
    test_imports()
    test_directory_paths()
    test_database_connection()
    test_output_directory()
    print("\n=== TEST SUITE COMPLETE ===")
