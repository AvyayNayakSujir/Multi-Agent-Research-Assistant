# API Testing Guide - Multi-Agent AI Research Assistant

This reference document lists raw `curl` commands to test the endpoints and behaviors of the backend API.

> [!IMPORTANT]
> **Quota Notice:** success-case research requests will invoke real paid API calls to Groq and Tavily (as configured in your `.env` file). Auth failures and validation errors short-circuit early and are free of charge.

## How to Import into Postman
You can import any of the `curl` commands below directly into Postman:
1. Copy the raw `curl` command.
2. Open Postman, click **Import** (top left).
3. Paste the `curl` command into the text box and click **Import**.

---

## Health Check Endpoint

### 1. Root Health Check
- **Description:** Verifies that the FastAPI server is running and returns basic health status.
- **Request:**
  ```bash
  curl -X GET http://localhost:8000/health \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `200 OK`
- **Expected Response:**
  ```json
  {"status": "ok"}
  ```

---

## Research Endpoint: Success Cases (`POST /api/v1/research`)

All successful research requests require a valid `X-API-Key` header matching the `API_KEY` defined in the server's environment configuration.

### 2. Valid Query with Default Max Iterations (3)
- **Description:** Generates a report with default parameters.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Explain async programming in Python."}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `200 OK`
- **Expected Response Shape:**
  ```json
  {
    "query": "Explain async programming in Python.",
    "draft": "...[Synthesized draft text]...",
    "approved": true,
    "iterations_used": 1,
    "sources": [
      {
        "url": "https://example.com/source",
        "title": "Example Source Title"
      }
    ]
  }
  ```

### 3. Valid Query with Explicit Max Iterations Boundary (1)
- **Description:** Restricts the workflow to exactly 1 critique pass (no loop allowed).
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "FastAPI overview", "max_iterations": 1}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `200 OK`

### 4. Valid Query with Explicit Max Iterations Boundary (5)
- **Description:** Allows up to 5 critique loops.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Tavily vs Serper API comparisons", "max_iterations": 5}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `200 OK`

### 5. Prompt likely to approve immediately vs revision loops
- **Description:** These behaviors are probabilistic depending on LLM critique evaluation:
  - **First Pass Approval:** Simple queries with highly specific matching sources (e.g. `"What is the capital of France?"`) are likely to resolve on the first pass (`approved: true`, `iterations_used: 1`).
  - **Revision Loop:** Contradictory, vague, or complex queries (e.g. `"Synthesize conflicting views on Groq hardware vs Nvidia GPUs in 2026"`) are likely to trigger at least one critique loop rejection and edit cycle before final completion.

---

## Research Endpoint: Auth Failures (`POST /api/v1/research`)

### 6. Missing API Key Header
- **Description:** Triggers 401 because the `X-API-Key` header is absent.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -d '{"query": "Is Python 3.14 out?"}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `401 Unauthorized`
- **Expected Response:**
  ```json
  {
    "error": "UnauthorizedError",
    "message": "API Key is missing",
    "request_id": "..."
  }
  ```

### 7. Incorrect API Key Value
- **Description:** Triggers 401 because the `X-API-Key` value is wrong.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: wrong-api-key" \
       -d '{"query": "Is Python 3.14 out?"}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `401 Unauthorized`
- **Expected Response:**
  ```json
  {
    "error": "UnauthorizedError",
    "message": "Invalid API Key",
    "request_id": "..."
  }
  ```

---

## Research Endpoint: Validation Failures (`POST /api/v1/research`)

All validations fail with `422 Unprocessable Entity` before entering the workflow execution pipeline.

### 8. Empty Query String
- **Description:** Query is empty (`""`).
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": ""}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 9. Whitespace-Only Query
- **Description:** Query contains only spaces.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "    "}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 10. Query Below Minimum Length (2 chars)
- **Description:** Query contains less than 3 characters after stripping.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "ab"}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 11. Query Exceeding Maximum Length (501 chars)
- **Description:** Query is longer than 500 characters.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras dapibus. Vivam."}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 12. max_iterations Below Lower Bound (0)
- **Description:** Requesting `0` iterations when bounds are 1-5.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Valid topic name", "max_iterations": 0}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 13. max_iterations Above Upper Bound (6)
- **Description:** Requesting `6` iterations.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Valid topic name", "max_iterations": 6}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 14. Missing `query` Field Entirely
- **Description:** Sending request JSON without query attribute.
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"max_iterations": 3}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `422 Unprocessable Entity`

### 15. Malformed JSON Body
- **Description:** Request JSON syntax is invalid (missing closing brace).
- **Request:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "FastAPI overview", "max_iterations": 3' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
- **Expected Status:** `400 Bad Request` (or 422 depending on FastAPI parser fallback)

---

## Research Endpoint: Rate Limiting (`POST /api/v1/research`)

> [!CAUTION]
> Firing this rate-limit test script will invoke real research calls and consume Groq and Tavily paid API quota until the limiter blocks the requests. Execute with caution!

### 16. Exceeding the Rate Limit
- **Description:** Fires 11 requests in quick succession. The 11th request will be blocked by slowapi (limit: 10/minute) and return a status code of `429`.
- **Request (Bash/WSL/Git Bash Loop):**
  ```bash
  for i in {1..11}; do
    echo "Firing request $i..."
    curl -X POST http://localhost:8000/api/v1/research \
         -H "Content-Type: application/json" \
         -H "X-API-Key: dev-api-key" \
         -d '{"query": "Rate limiting testing query"}' \
         -w "\nHTTP Status: %{http_code}\n\n"
  done
  ```
- **Expected Status on 11th call:** `429 Too Many Requests`
- **Expected Response shape on 429:**
  ```json
  {
    "error": "RateLimitExceeded",
    "message": "Rate limit exceeded: 10 per 1 minute",
    "request_id": "..."
  }
  ```

---

## Research Endpoint: Multi-API-Key Limits (`POST /api/v1/research`)

### 17. Independent Rate Limit Buckets
- **Description:** If you have multiple valid API keys, each retains its own independent rate limit bucket. To verify this, exhaust one key's limit (e.g. fire 11 times with Key A) and confirm that requests using Key B continue to succeed.
- **Request:**
  ```bash
  # 1. Exhaust limit for key-alpha (11th request yields 429)
  for i in {1..11}; do
    curl -s -o /dev/null -w "Alpha call $i: %{http_code}\n" \
         -X POST http://localhost:8000/api/v1/research \
         -H "Content-Type: application/json" \
         -H "X-API-Key: key-alpha" \
         -d '{"query": "FastAPI multikey check"}'
  done

  # 2. Key-beta should still succeed (returns 200)
  curl -X POST http://localhost:8000/api/v1/research \
       -H "Content-Type: application/json" \
       -H "X-API-Key: key-beta" \
       -d '{"query": "FastAPI multikey check"}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```

---

## Research Endpoint: Streaming Status Updates (`POST /api/v1/research/stream`)

This endpoint streams Server-Sent Events (SSE) in real-time as the agent nodes execute, concluding with the final research report.

### 18. Stream Status Updates and Final Result
- **Description:** Initiates a research query and streams real-time status updates, followed by the final report payload.
- **Request:**
  ```bash
  curl -N -X POST http://localhost:8000/api/v1/research/stream \
       -H "Content-Type: application/json" \
       -H "X-API-Key: dev-api-key" \
       -d '{"query": "Explain async programming in Python."}' \
       -w "\nHTTP Status: %{http_code}\n"
  ```
  *(Note: The `-N` or `--no-buffer` flag in `curl` is crucial to prevent buffer lag and display events in real-time as they are yielded by the server).*
- **Expected Response Stream:**
  ```text
  data: {"type": "status", "message": "Searching sources..."}

  data: {"type": "status", "message": "Scraping & filtering content..."}

  data: {"type": "status", "message": "Retrieving info..."}

  data: {"type": "status", "message": "Drafting report..."}

  data: {"type": "status", "message": "Revising the report..."}

  data: {"type": "status", "message": "Finalizing report..."}

  data: {"type": "result", "payload": {"query": "Explain async programming in Python.", "draft": "...", "approved": true, "iterations_used": 1, "sources": [...]}}
  ```

