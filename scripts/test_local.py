#!/usr/bin/env python3
"""
Local Test Runner

Run tests locally before pushing to GitHub.
This helps catch issues early and saves CI/CD time.
"""

import subprocess
import sys
import os
import time
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def check_env_vars():
    """Check required environment variables."""
    print_header("Checking Environment Variables")

    required = ["OPENAI_API_KEY", "API_SECRET_KEY"]
    missing = []

    for var in required:
        if os.getenv(var):
            print(f"  ✓ {var} is set")
        else:
            print(f"  ✗ {var} is NOT set")
            missing.append(var)

    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        print("\nSet them with:")
        if sys.platform == "win32":
            for var in missing:
                print(f"  $env:{var} = 'your-value-here'")
        else:
            for var in missing:
                print(f"  export {var}='your-value-here'")
        return False

    print("\n✓ All environment variables set")
    return True


def run_tests(test_file=None):
    """Run pytest tests."""
    if test_file:
        print_header(f"Running {test_file}")
        cmd = ["pytest", f"tests/{test_file}", "-v", "--timeout=180"]
    else:
        print_header("Running All Tests")
        cmd = ["pytest", "tests/", "-v", "--timeout=180"]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def start_server():
    """Start the API server in background."""
    print_header("Starting API Server")

    if sys.platform == "win32":
        # Windows
        process = subprocess.Popen(
            ["python", "api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        # Unix/Mac
        process = subprocess.Popen(
            ["python", "api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

    print("  Waiting for server to start...")
    time.sleep(10)
    print("  ✓ Server started (PID: {})".format(process.pid))

    return process


def stop_server(process):
    """Stop the API server."""
    print("\n  Stopping server...")
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                          capture_output=True)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        print("  ✓ Server stopped")
    except Exception as e:
        print(f"  Warning: Could not stop server: {e}")
        print("  You may need to stop it manually")


def main():
    """Main test runner."""
    print_header("Local Test Runner")

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    print(f"  Working directory: {os.getcwd()}")

    # Check environment variables
    if not check_env_vars():
        sys.exit(1)

    # Install test dependencies
    print_header("Installing Test Dependencies")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pytest", "pytest-timeout", "requests"],
        capture_output=True
    )
    if result.returncode == 0:
        print("  ✓ Test dependencies installed")
    else:
        print("  ✗ Failed to install dependencies")
        sys.exit(1)

    # Start server
    server_process = None
    try:
        server_process = start_server()

        # Run health tests
        health_ok = run_tests("test_health.py")

        if not health_ok:
            print("\n❌ Health tests failed!")
            return False

        print("\n✓ Health tests passed")

        # Run API tests
        api_ok = run_tests("test_api.py")

        if not api_ok:
            print("\n❌ API tests failed!")
            return False

        print("\n✓ API tests passed")

        print_header("All Tests Passed! ✅")
        print("  You can safely push to GitHub now.")
        return True

    finally:
        if server_process:
            stop_server(server_process)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
