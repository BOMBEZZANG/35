"""Test NotebookLM API authentication with ADC."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.auth import default
from google.auth.transport.requests import Request
import requests

# Load environment variables
env_path = Path(__file__).parent / "config" / ".env"
load_dotenv(env_path)

def test_adc_authentication():
    """Test if ADC is properly configured."""
    print("=" * 70)
    print("Testing Google Cloud ADC (Application Default Credentials)")
    print("=" * 70)
    print()

    try:
        # Get credentials
        print("1. Getting credentials from ADC...")
        credentials, project = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        print(f"   ✓ Credentials found!")
        print(f"   Project from ADC: {project or 'None (using env var)'}")
        print()

        # Refresh token
        print("2. Refreshing access token...")
        credentials.refresh(Request())
        print(f"   ✓ Token refreshed!")
        print(f"   Token preview: {credentials.token[:50]}...")
        print()

        # Test API access
        print("3. Testing NotebookLM API access...")
        project_number = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
        endpoint_location = os.getenv("ENDPOINT_LOCATION", "global-")
        location = os.getenv("LOCATION", "global")

        if not project_number:
            print("   ✗ Error: GOOGLE_CLOUD_PROJECT_NUMBER not set in .env")
            return False

        print(f"   Project Number: {project_number}")
        print(f"   Endpoint Location: {endpoint_location}")
        print(f"   Location: {location}")
        print()

        # Try listing notebooks
        url = f"https://{endpoint_location}discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks"

        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }

        print(f"4. Making API request to list notebooks...")
        print(f"   URL: {url}")
        print()

        response = requests.get(url, headers=headers, timeout=30)

        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"   ✓ Success! API is accessible.")
            notebooks = response.json().get("notebooks", [])
            print(f"   Found {len(notebooks)} notebook(s)")
            print()
            return True
        elif response.status_code == 403:
            print(f"   ✗ Forbidden: NotebookLM Enterprise not enabled on this project")
            print(f"   Enable it at: https://console.cloud.google.com/")
            print()
            return False
        elif response.status_code == 401:
            print(f"   ✗ Unauthorized: ADC not set up correctly")
            print(f"   Run: gcloud auth application-default login")
            print()
            return False
        else:
            print(f"   ✗ Error: {response.text}")
            print()
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        print()
        print("Common issues:")
        print("  1. ADC not configured - run: gcloud auth application-default login")
        print("  2. Wrong project - check GOOGLE_CLOUD_PROJECT_NUMBER in .env")
        print("  3. NotebookLM not enabled - enable in Cloud Console")
        print()
        return False

def print_setup_instructions():
    """Print setup instructions if test fails."""
    print("=" * 70)
    print("ADC Setup Instructions")
    print("=" * 70)
    print()
    print("If the test failed, follow these steps:")
    print()
    print("1. Install Google Cloud SDK:")
    print("   https://cloud.google.com/sdk/docs/install")
    print()
    print("2. Authenticate:")
    print("   gcloud auth login")
    print()
    print("3. Setup Application Default Credentials:")
    print("   gcloud auth application-default login")
    print()
    print("4. (Optional) Set quota project:")
    print("   gcloud auth application-default set-quota-project YOUR_PROJECT_ID")
    print()
    print("5. Enable NotebookLM Enterprise:")
    print("   https://console.cloud.google.com/marketplace/product/google/notebooklm.googleapis.com")
    print()

if __name__ == "__main__":
    success = test_adc_authentication()

    if success:
        print("=" * 70)
        print("✓ ADC Setup Complete!")
        print("=" * 70)
        print()
        print("Your environment is ready to use NotebookLM API!")
        sys.exit(0)
    else:
        print_setup_instructions()
        sys.exit(1)
