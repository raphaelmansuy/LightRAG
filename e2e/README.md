# E2E Multi-Tenant Isolation Tests

This directory contains end-to-end tests to verify the isolation of data and processing pipelines in the multi-tenant LightRAG implementation.

## Contents

-   `test_multitenant_isolation.py`: A Python script that:
    1.  Creates two distinct tenants (Tenant A and Tenant B).
    2.  Creates a Knowledge Base (KB) for each tenant.
    3.  Ingests a unique "secret" document into each tenant's KB.
    4.  Waits for indexing to complete.
    5.  Verifies that Tenant A can retrieve its secret but **not** Tenant B's secret.
    6.  Verifies that Tenant B can retrieve its secret but **not** Tenant A's secret.

-   `run_isolation_test.sh`: A helper shell script that:
    1.  **Stops any existing LightRAG server** running on port 9621 to ensure a clean state.
    2.  Configures the environment to use **Ollama** with `granite4:latest` (LLM) and `bge-m3:latest` (Embedding).
    3.  Starts the server in the background.
    4.  Runs the python test script.

## Prerequisites

-   Python 3.10+
-   `requests` library installed (`pip install requests`)
-   LightRAG installed in the environment.
-   **Ollama** running locally (or configured via environment variables) if using the default configuration.

## How to Run

1.  **Navigate to the project root**:
    ```bash
    cd /path/to/LightRAG
    ```

2.  **Run the test script**:
    ```bash
    ./e2e/run_isolation_test.sh
    ```

## Environment Variables

The test script respects the following environment variables:

-   `LIGHTRAG_API_URL`: URL of the LightRAG API (default: `http://localhost:9621`)
-   `AUTH_USER`: Admin username (default: `admin`)
-   `AUTH_PASS`: Admin password (default: `admin123`)

## Troubleshooting

-   **Server Crash**: Check `server.log` in the root directory if the server fails to start or crashes during the test.
-   **Timeouts**: If indexing takes too long, you may need to increase the timeout in `test_multitenant_isolation.py` or check if the LLM/Embedding service is responsive.
