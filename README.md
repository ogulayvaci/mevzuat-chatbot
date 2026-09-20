# Mevzuat Chatbot

A simple AI-powered chatbot for Turkish legislation, developed as a technical case study.

The application uses:

- React for the frontend
- FastAPI for the backend
- OpenAI `gpt-5.4-mini`
- OpenAI function calling
- FastMCP for MCP communication
- Azure Container Apps for the deployed MCP server

## Architecture

The application flow is:

```text
User
  ↓
React Frontend
  ↓
FastAPI Backend
  ↓
OpenAI gpt-5.4-mini
  ↓
Function Calling
  ↓
Backend MCP Client
  ↓
Azure-hosted MCP Server
  ↓
Turkish legislation data
  ↓
OpenAI final response
  ↓
Frontend
```

The backend connects directly to the MCP server using `fastmcp`.

OpenAI function calling is used to decide which MCP tool should be executed. The backend executes the selected MCP tool and sends the result back to the model so it can generate the final answer.

Multiple sequential tool calls are supported.

## Project Structure

```text
mevzuat-chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── main.py
│   │   └── services/
│   │       ├── mcp_service.py
│   │       └── openai_service.py
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
│
├── mcp-server/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── source/
│       ├── UPSTREAM.md
│       └── ...
│
├── .gitignore
└── README.md
```

## MCP Tools

The chatbot exposes a focused set of MCP capabilities to the language model:

- `search_mevzuat`
- `get_mevzuat_content`
- `search_within_mevzuat`

For questions about a specific law, the model first finds the relevant legislation and obtains its `mevzuatId`.

It can then use that ID to search inside the legislation for the relevant article, definition, rule, obligation, exception, or concept.

Example:

```text
User:
6698 sayılı Kişisel Verilerin Korunması Kanununda açık rıza nedir?

1. search_mevzuat
   → finds Law No. 6698
   → mevzuatId: 104383

2. search_within_mevzuat
   → searches for "açık rıza"

3. OpenAI
   → generates the final answer using the retrieved legislation
```

The backend also limits the number of MCP tool rounds to avoid unbounded tool-call loops.

## Requirements

Before running the project locally, make sure the following are installed:

- Python 3.12+
- Node.js 20.19+ or a newer compatible version
- npm
- Docker Desktop, if building or running the MCP server locally

## Backend Setup

Go to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using the provided template:

```bash
cp .env.example .env
```

Configure the environment variables:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
MCP_SERVER_URL=https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io/mcp
```

The `.env` file is excluded from Git and must not be committed.

Start the backend:

```bash
python -m uvicorn app.main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

## Backend Health Check

The backend exposes:

```text
GET /health
```

The endpoint checks both the FastAPI application and the configured MCP server health endpoint.

Healthy example:

```json
{
  "status": "healthy",
  "mcp": "online"
}
```

If the MCP server cannot be reached:

```json
{
  "status": "degraded",
  "mcp": "offline"
}
```

Example:

```bash
curl http://127.0.0.1:8000/health
```

## Backend API

### Standard Chat

Endpoint:

```text
POST /api/chat
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"6698 sayılı Kişisel Verilerin Korunması Kanununda açık rıza nedir?"}'
```

### Streaming Chat

Endpoint:

```text
POST /api/chat/stream
```

Example:

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"6698 sayılı Kişisel Verilerin Korunması Kanununda açık rıza nedir?"}'
```

The React frontend uses the streaming endpoint.

## OpenAI Integration

The backend uses:

```text
gpt-5.4-mini
```

The OpenAI API key is stored only in the backend environment.

The implementation uses `AsyncOpenAI`, so OpenAI requests do not block the FastAPI event loop while waiting for external responses.

OpenAI function calling is used to let the model select the appropriate legislation tool.

The backend then:

```text
receives function call
        ↓
executes MCP tool
        ↓
returns tool result to OpenAI
        ↓
model may request another tool
        ↓
final answer
```

A typical flow is:

```text
search_mevzuat
        ↓
mevzuatId
        ↓
search_within_mevzuat
        ↓
OpenAI final answer
```

The backend supports multiple sequential MCP tool calls and enforces a maximum number of tool rounds.

## Streaming

The `/api/chat/stream` endpoint supports progressive response delivery.

When a legislation question requires MCP tools, the backend first completes the required tool-call sequence and then requests the final OpenAI response using Responses API streaming.

OpenAI `response.output_text.delta` events are forwarded to the frontend as they arrive.

The frontend consumes the response using the browser Fetch Streams API and progressively updates the assistant message.

This means the user does not need to wait for the complete final answer before text starts appearing.

If the model answers directly without using an MCP tool, the current implementation may return that response as a single chunk.

Streaming errors are handled inside the response generator so that the frontend receives a user-friendly error message instead of an unexplained connection failure.

## Frontend Setup

Open a separate terminal and go to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm ci
```

Start the development server:

```bash
npm run dev
```

The frontend normally runs at:

```text
http://localhost:5173
```

The frontend communicates with:

```text
http://127.0.0.1:8000
```

The backend includes CORS configuration for:

```text
http://localhost:5173
http://127.0.0.1:5173
```

## Frontend Features

The frontend provides a simple React chat interface with:

- user and assistant messages
- example legislation questions
- real streamed responses
- Markdown rendering
- loading state
- error handling
- responsive layout
- Enter to send
- Shift + Enter for a new line
- dynamic backend/MCP status
- a small `Technical case study` footer label

The status indicator checks the backend health endpoint periodically.

It displays:

```text
Sistem hazır
```

when the backend can reach the configured MCP server, and:

```text
Bağlantı sorunu
```

when the MCP health check fails.

## MCP Server

The MCP server is based on the upstream project originally provided for the case:

```text
https://github.com/saidsurucu/mevzuat-mcp
```

During development, the upstream repository later became unavailable through anonymous Git access.

To keep the submitted Docker build self-contained and reproducible, the tested MCP source snapshot is included under:

```text
mcp-server/source/
```

The snapshot corresponds to the tested upstream commit:

```text
5671233b3e77ea82d11cf35a22af1985c27bf892
```

Additional source provenance information is documented in:

```text
mcp-server/source/UPSTREAM.md
```

The submitted Dockerfile no longer depends on cloning the upstream GitHub repository during build.

## MCP Docker Image

The Dockerfile required by the case is located at:

```text
mcp-server/Dockerfile
```

Build the MCP image locally:

```bash
docker build -t mevzuat-case-mcp ./mcp-server
```

To perform a completely uncached build:

```bash
docker build --no-cache -t mevzuat-case-mcp ./mcp-server
```

Run it locally:

```bash
docker run --rm -p 8001:8000 mevzuat-case-mcp
```

Test the local MCP health endpoint:

```bash
curl http://127.0.0.1:8001/health
```

Expected example:

```json
{
  "status": "healthy",
  "service": "Mevzuat MCP Server",
  "version": "0.1.0"
}
```

The Docker build context is intentionally kept small through `mcp-server/.dockerignore`.

## Docker Image Scope

The upstream MCP project includes Playwright as a Python dependency.

For this case, the selected MCP tools:

- `search_mevzuat`
- `get_mevzuat_content`
- `search_within_mevzuat`

work through the Bedesten-based flow and do not require browser automation.

The custom Dockerfile does not install the Playwright Chromium browser binary.

The Playwright Python package may still be installed because it is part of the upstream dependency set, but the selected case flow does not rely on Chromium or browser automation.

This was validated using real MCP tool calls both locally and against the Azure deployment.

## Docker Platform Note

The development machine used for the case was an Apple Silicon Mac.

A native Docker build therefore produces:

```text
linux/arm64
```

Azure Container Apps required:

```text
linux/amd64
```

For the Azure deployment, the image was rebuilt using Docker Buildx:

```bash
docker buildx build \
  --platform linux/amd64 \
  -t <registry>.azurecr.io/mevzuat-case-mcp:latest \
  --push \
  ./mcp-server
```

The architecture can be checked with:

```bash
docker image inspect <image> \
  --format '{{.Os}}/{{.Architecture}}'
```

Expected cloud deployment architecture:

```text
linux/amd64
```

## Azure Deployment

All Azure resources used for this case were created inside the provided resource group.

The cloud architecture is:

```text
Docker Image
   ↓
Azure Container Registry
   ↓
Azure Container Apps
   ↓
Public HTTPS MCP Endpoint
```

### Azure Container Registry

An Azure Container Registry was created using the Basic SKU.

The Docker image was pushed to the private registry before deployment.

Example registry login:

```bash
az acr login --name <registry-name>
```

Example image tag:

```bash
docker tag \
  mevzuat-case-mcp:latest \
  <registry>.azurecr.io/mevzuat-case-mcp:latest
```

Example push:

```bash
docker push \
  <registry>.azurecr.io/mevzuat-case-mcp:latest
```

For the final Azure deployment from Apple Silicon, the image was built and pushed as `linux/amd64` using Docker Buildx.

### Azure Container Apps Environment

An Azure Container Apps Environment was created inside the provided resource group.

The MCP server was then deployed as an Azure Container App with:

- external ingress enabled
- target port `8000`
- public HTTPS access

## Registry Authentication

Managed identity was initially preferred for pulling the private Azure Container Registry image.

However, the provided Azure account did not have permission to create the required `AcrPull` role assignment.

As a fallback, Azure Container Registry credentials were provided to the Container App during deployment.

The credentials were not stored in source code or committed to Git.

## Azure Architecture Issue

The first cloud deployment attempt used an image built natively on Apple Silicon:

```text
linux/arm64
```

Azure Container Apps required an AMD64-compatible image.

The image was therefore rebuilt with:

```bash
docker buildx build \
  --platform linux/amd64 \
  ...
```

The existing Azure Container App was then updated to use the AMD64 image.

## Deployed MCP Server

The deployed MCP service is currently available at:

```text
https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io
```

Health endpoint:

```text
https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io/health
```

MCP endpoint:

```text
https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io/mcp
```

The deployment was verified using:

- the public `/health` endpoint
- MCP session establishment
- MCP tool listing
- `search_mevzuat`
- `search_within_mevzuat`
- `get_mevzuat_content`

Real legislation data was successfully retrieved from both the local Docker container and the Azure-deployed MCP server.

## Security

Sensitive values such as the OpenAI API key are stored only in:

```text
backend/.env
```

The repository ignores sensitive and local files including:

```text
.env
.env.*
.venv/
node_modules/
__pycache__/
*.pyc
```

The following template is intentionally included:

```text
backend/.env.example
```

It contains configuration names but no API key.

Before submission, the Git repository was also checked to ensure that the real `.env` file was not tracked.

## Validation and Error Handling

The backend validates incoming chat messages.

Invalid requests such as:

- missing messages
- empty strings
- whitespace-only input
- invalid data types
- excessively long input

are rejected before unnecessary model calls are made.

If OpenAI returns an empty response, the user receives a readable fallback message.

Internal service errors are logged on the backend while user-facing responses remain generic and do not expose internal exception details.

## Verification

The final project was tested from a clean Git clone.

The following checks succeeded:

### Frontend

```bash
npm ci
npm run build
npm run lint
```

### Backend

A fresh Python 3.12 virtual environment was created and:

```bash
pip install -r requirements.txt
python -m compileall app
pip check
```

completed successfully.

### Docker

A clean Docker build was verified with:

```bash
docker build --no-cache -t mevzuat-case-mcp-clean ./mcp-server
```

The resulting container:

- started successfully
- passed its health check
- exposed the MCP endpoint
- listed MCP tools
- successfully executed real legislation tool calls

## Scope

The implementation intentionally focuses on the core requirements of the case:

- MCP server containerization
- cloud MCP deployment
- backend access to the MCP server
- OpenAI integration
- MCP tool usage
- React chat interface
- streamed responses
- clear local setup instructions

The following were intentionally kept out of scope because they were not required by the case:

- authentication
- user accounts
- databases
- persistent conversation history
- queues
- Kubernetes
- CI/CD infrastructure
- additional AI providers
- support for every upstream MCP feature

The goal was to keep the implementation focused, understandable, and easy to run while satisfying the requested case functionality.
