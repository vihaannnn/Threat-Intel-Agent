#!/usr/bin/env python3
"""
Central runner for Threat Intelligence Agent
- Optionally starts Docker services (Qdrant + OpenSearch)
- Launches MCP server in the background (stdio)
- Opens Streamlit web UI

Usage:
  python core/run_all.py [--local] [--no-docker]

Flags:
  --local      Prefer local models (PREFER_LOCAL_MODELS=true)
  --no-docker  Skip starting Docker services
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()


def info(msg: str) -> None:
    print(msg)


def run(cmd: list[str], check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, env=env)


def docker_running() -> bool:
    try:
        result = run(["docker", "ps"], check=False)
        return result.returncode == 0
    except Exception:
        return False


def ensure_container(name: str, args: list[str]) -> None:
    """Ensure Docker container is running, create if needed"""
    # Check if container exists and is running - use simpler approach
    try:
        # Direct check if container is running
        check_result = run(["docker", "inspect", "--format", "{{.State.Running}}", name], check=False)
        if check_result.returncode == 0 and check_result.stdout.strip() == "true":
            info(f"Container {name} is already running")
            return
    except Exception:
        pass
    
    # Check if container exists (running or stopped)
    try:
        exists_result = run(["docker", "inspect", name], check=False)
        if exists_result.returncode == 0:
            # Container exists, try to start it
            info(f"Starting existing container {name}...")
            start_result = run(["docker", "start", name], check=False)
            if start_result.returncode == 0:
                info(f"Container {name} started successfully")
            else:
                info(f"Could not start {name}, trying to recreate...")
                run(["docker", "rm", "-f", name], check=False)
                info(f"Creating new container {name}...")
                run(["docker", *args], check=True)
            return
    except Exception:
        pass
    
    # Container doesn't exist, create it
    info(f"Creating new container {name}...")
    run(["docker", *args], check=True)


def start_docker_services(skip: bool) -> None:
    if skip:
        info("Skipping Docker services (--no-docker)")
        return
    if not docker_running():
        info("⚠️  Docker is not running. Please start Docker Desktop and re-run, or pass --no-docker.")
        return
    info("Checking Docker services (Qdrant and OpenSearch)...")
    # Qdrant
    ensure_container(
        "qdrant-threat-intel",
        [
            "run", "-d",
            "--name", "qdrant-threat-intel",
            "-p", "6333:6333",
            "-p", "6334:6334",
            "-v", f"{ROOT}/qdrant_storage:/qdrant/storage",
            "qdrant/qdrant:latest",
        ],
    )
    # OpenSearch
    ensure_container(
        "opensearch-threat-intel",
        [
            "run", "-d",
            "--name", "opensearch-threat-intel",
            "-p", "9200:9200",
            "-p", "9600:9600",
            "-e", "discovery.type=single-node",
            "-e", "DISABLE_INSTALL_DEMO_CONFIG=true",
            "-e", "DISABLE_SECURITY_PLUGIN=true",
            "opensearchproject/opensearch:2.11.0",
        ],
    )
    info("Docker services ready")


def start_mcp_server(env: dict) -> subprocess.Popen:
    info("Starting MCP server in the background...")
    server_env = os.environ.copy()
    server_env.update(env)
    server_env["PYTHONPATH"] = str(ROOT)
    # Redirect only stdout to PIPE; stderr prints to console for diagnostics
    proc = subprocess.Popen(
        [sys.executable, "-m", "server.mcp_server"],
        cwd=str(ROOT),
        env=server_env,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
    )
    # Give server a moment to initialize
    time.sleep(3)
    return proc


def start_streamlit_ui(env: dict) -> int:
    info("Launching Streamlit UI...")
    ui_env = os.environ.copy()
    ui_env.update(env)
    # Use Python module syntax to avoid PATH issues
    return subprocess.call([sys.executable, "-m", "streamlit", "run", "core/web_ui.py"], cwd=str(ROOT), env=ui_env)


def check_setup() -> bool:
    """Check if basic setup is complete"""
    env_file = ROOT / ".env"
    if not env_file.exists():
        info(".env file not found")
        info("Run 'python setup_env.py' to create it, or manually create .env from env.example")
        return False
    
    # Check if Qdrant collection exists
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host="localhost", port=6333, timeout=2)
        collections = client.get_collections()
        if not any(c.name == "osv_vulnerabilities" for c in collections.collections):
            info("Qdrant collection 'osv_vulnerabilities' not found")
            info("Run 'python data/setup_local_qdrant.py' to set up the vector database")
            return False
    except Exception:
        info("Could not connect to Qdrant. Make sure Docker is running.")
        info("This is OK if you're starting Docker services now.")
    
    return True


def main(argv: list[str]) -> int:
    prefer_local = "--local" in argv
    no_docker = "--no-docker" in argv

    # Check setup
    info("=" * 60)
    info("Threat Intelligence Agent - Security Analysis Interface")
    info("=" * 60)
    
    if not check_setup():
        info("\nSetup incomplete. Please complete setup before running.")
        info("Quick setup:")
        info("  1. python setup_env.py  # Create .env file")
        info("  2. python data/setup_local_qdrant.py  # Set up vector database")
        info("  3. python core/run_all.py  # Run the interface")
        return 1

    # Resolve env preferences
    run_env: dict[str, str] = {}
    if prefer_local:
        run_env["PREFER_LOCAL_MODELS"] = "true"
        run_env["PREFERRED_LOCAL_MODEL"] = os.environ.get("PREFERRED_LOCAL_MODEL", "mistral-7b")
        info("PREFER_LOCAL_MODELS=true (local LLM preferred)")

    # Start services
    start_docker_services(skip=no_docker)

    # Start server (optional - only needed for MCP client)
    server_proc = None
    # Uncomment if you need MCP server
    # server_proc = start_mcp_server(run_env)

    try:
        # Start UI (blocks until closed)
        info("\nStarting Security Analysis Interface...")
        info("The Streamlit interface will open in your browser")
        info("Begin querying security vulnerabilities\n")
        code = start_streamlit_ui(run_env)
        return code
    finally:
        # Cleanup server
        if server_proc and server_proc.poll() is None:
            info("Stopping MCP server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
