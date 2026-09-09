# Mevzuat Chatbot

A simple AI-powered chatbot for Turkish legislation.

The application uses:

- React for the frontend
- FastAPI for the backend
- OpenAI `gpt-5.4-mini`
- MCP tools for legislation retrieval
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

## Project Structure

```text
mevzuat-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── services/
│   │       ├── mcp_service.py
│   │       └── openai_service.py
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── mcp-server/
│   └── Dockerfile
│
├── .gitignore
└── README.md
```

## MCP Tools

The chatbot currently exposes the following MCP capabilities to the language model:

- `search_mevzuat`
- `get_mevzuat_content`
- `search_within_mevzuat`

For questions about a specific law, the model first finds the relevant legislation and obtains its `mevzuatId`.

It can then use this ID to search inside the legislation for the relevant article, definition, rule, or concept.

Example flow:

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

## Requirements

Before running the project locally, make sure the following are installed:

- Python 3.12+
- Node.js
- npm
- Docker, if building the MCP image locally

## Backend Setup

Go to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using `.env.example`:

```bash
cp .env.example .env
```

Configure the environment variables:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
MCP_SERVER_URL=https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io/mcp
```

The `.env` file is excluded from Git and should never be committed.

Start the backend:

```bash
python -m uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "healthy"
}
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

The React frontend uses this endpoint.

## Frontend Setup

Go to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

The frontend communicates with:

```text
http://127.0.0.1:8000/api/chat/stream
```

The backend includes CORS configuration for local frontend development.

## MCP Server

The MCP server is based on the following upstream repository:

```text
https://github.com/saidsurucu/mevzuat-mcp
```

The MCP server source code is included under `mcp-server/source/` as a snapshot of the upstream project that was originally provided for the case.

The upstream repository later became unavailable, so the tested source snapshot was included in this repository to keep Docker builds self-contained and reproducible.

The snapshot corresponds to the following tested commit:

```text
5671233b3e77ea82d11cf35a22af1985c27bf892
```

The original source location and commit information are also documented in `mcp-server/source/UPSTREAM.md`.

## MCP Docker Image

The Dockerfile is located at:

```text
mcp-server/Dockerfile
```

Build the MCP image locally:

```bash
docker build -t mevzuat-case-mcp ./mcp-server
```

Run it locally:

```bash
docker run --rm -p 8001:8000 mevzuat-case-mcp
```

Test the health endpoint:

```bash
curl http://127.0.0.1:8001/health
```

## Docker Platform Note

The development machine used for this case was an Apple Silicon Mac.

A native Docker build therefore produced a:

```text
linux/arm64
```

image.

Azure Container Apps required a:

```text
linux/amd64
```

image.

The cloud deployment image was therefore rebuilt using Docker Buildx:

```bash
docker buildx build \
  --platform linux/amd64 \
  -t <registry>.azurecr.io/mevzuat-case-mcp:latest \
  --push \
  ./mcp-server
```

The image architecture can be verified with:

```bash
docker image inspect <image> \
  --format '{{.Os}}/{{.Architecture}}'
```

Expected output:

```text
linux/amd64
```

## Azure Deployment

All cloud resources were created inside the provided Azure resource group.

The deployment architecture is:

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

The Docker image was tagged using the Azure Container Registry login server:

```bash
docker tag \
  mevzuat-case-mcp:latest \
  <registry>.azurecr.io/mevzuat-case-mcp:latest
```

The image was then pushed:

```bash
docker push \
  <registry>.azurecr.io/mevzuat-case-mcp:latest
```

For the final deployment from an Apple Silicon machine, the image was built and pushed directly as `linux/amd64` using Docker Buildx.

### Azure Container Apps Environment

An Azure Container Apps Environment was created inside the provided resource group.

### Azure Container App

The MCP image was deployed as an Azure Container App with:

- external ingress enabled
- target port `8000`
- public HTTPS access

## Registry Authentication

Managed identity was initially preferred for pulling the private Azure Container Registry image.

However, the provided Azure account did not have permission to create the required `AcrPull` role assignment.

As a fallback, Azure Container Registry credentials were used during deployment.

These credentials were not stored in the source code or committed to Git.

## Deployed MCP Server

The MCP server is currently available at:

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

Both the health endpoint and real MCP tool calls were successfully tested after deployment.

## Docker Image Scope

The upstream MCP project includes Playwright and Chromium dependencies.

For this case, the Docker image was intentionally simplified and does not install Playwright or Chromium.

The selected MCP tools:

- `search_mevzuat`
- `get_mevzuat_content`
- `search_within_mevzuat`

work through the Bedesten-based flow without browser automation.

This was validated using real MCP tool calls both locally and against the Azure deployment.

Removing unnecessary browser dependencies keeps the image simpler and reduces the deployment scope.

## OpenAI Integration

The backend uses:

```text
gpt-5.4-mini
```

The OpenAI API key is stored only in the backend environment.

OpenAI function calling is used to let the model select the appropriate legislation tool.

The backend then executes the selected MCP tool and sends the tool result back to the model.

Multiple sequential tool calls are supported.

Example:

```text
search_mevzuat
        ↓
mevzuatId
        ↓
search_within_mevzuat
        ↓
OpenAI final answer
```

This allows the model to first locate legislation and then search inside the correct document.

## Frontend

The frontend provides a simple React chat interface.

It includes:

- user and assistant messages
- example legislation questions
- loading state
- streamed response handling
- Markdown rendering
- responsive layout
- a legal-information disclaimer

The frontend consumes the response stream using the browser Fetch Streams API.

## Streaming

The `/api/chat/stream` endpoint returns the generated assistant response as response chunks.

The frontend reads these chunks using a `ReadableStream` and progressively appends them to the assistant message.

The current implementation waits for the final OpenAI response after MCP tool execution and then sends that response to the frontend in chunks.

## Security

Sensitive values such as the OpenAI API key are stored only in `.env`.

The repository ignores local and sensitive files including:

```text
.env
.env.*
.venv/
node_modules/
__pycache__/
```

`.env.example` is included only as a configuration template and contains no secrets.

## Scope

The implementation intentionally focuses on the core requirements of the case:

- MCP server containerization
- cloud deployment
- backend MCP integration
- OpenAI integration
- MCP tool usage
- React chat interface
- streamed frontend responses

Features such as authentication, databases, persistent chat history, queues, and additional infrastructure were intentionally omitted to keep the solution focused on the requested functionality.
