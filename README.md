# Mevzuat Chatbot

A simple AI-powered chatbot for Turkish legislation, developed as a technical case study.

The application uses:

- React for the frontend
- FastAPI for the backend
- OpenAI `gpt-5.4-mini`
- OpenAI function calling
- FastMCP for MCP communication
- Azure Container Apps for the deployed MCP server

## Quick Start

The shortest way to run the application locally is to use the already deployed MCP server and start only the backend and frontend.

### 1. Clone the repository

```bash
git clone <repository-url>
cd mevzuat-chatbot
```

### 2. Start the backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `backend/.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
MCP_SERVER_URL=https://mevzuat-case-mcp.happycoast-5b0771d5.westeurope.azurecontainerapps.io/mcp
```

Then start the FastAPI backend:

```bash
python -m uvicorn app.main:app --reload
```

Verify that the backend and MCP server are reachable:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "mcp": "online"
}
```

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open:

```text
http://localhost:5173
```

The chatbot is now ready to use.

### Optional: Run the MCP server locally

The application does not require a local MCP server for the normal Quick Start flow because the deployed Azure MCP endpoint is already configured.

To build and run the MCP server locally:

```bash
docker build -t mevzuat-case-mcp ./mcp-server
docker run --rm -p 8001:8000 mevzuat-case-mcp
```

Then change the backend `.env` value to:

```env
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
```

Restart the backend after changing the environment variable.

---

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

OpenAI function calling is used to select which MCP tool should be executed. For the initial legislation request, tool usage is required so that answers are grounded through MCP rather than being accepted directly from the model.

After the first MCP call, subsequent tool selection is automatic. The model may request additional MCP tools or produce the final answer when it has enough retrieved legislation context.

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

The backend limits the number of MCP tool rounds to avoid unbounded tool-call loops.

The included upstream MCP snapshot still contains the full original MCP tool set, but this application only exposes and uses the three selected legislation tools through the backend.

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
  -d '{"message":"657 sayılı Devlet Memurları Kanununda disiplin cezaları nelerdir?"}'
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

For the first legislation turn, tool usage is required.

This ensures that the backend performs at least one MCP tool call before accepting a final legislation answer.

After the first tool round, tool selection returns to automatic mode so the model can either:

- request another MCP tool
- use the retrieved context
- generate the final answer

The backend flow is:

```text
User message
     ↓
OpenAI request with required tool use
     ↓
MCP function call
     ↓
Backend executes MCP tool
     ↓
Tool output returned to OpenAI
     ↓
Optional additional tool calls
     ↓
Final grounded answer
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

To keep the submitted Docker build self-contained and easy to rebuild, the tested MCP source snapshot is included under:

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

The submitted Dockerfile does not depend on cloning the upstream GitHub repository during build.

The snapshot still contains the original upstream tool set and supporting files. The submitted application intentionally uses only the three selected legislation tools listed earlier.

## MCP Docker Image

The Dockerfile required by the case is located at:

```text
mcp-server/Dockerfile
```

Build the MCP image locally:

```bash
docker build -t mevzuat-case-mcp ./mcp-server
```

To perform an uncached build:

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

The upstream snapshot also contains optional integrations and dependencies that are not used by this application.

These were left in the snapshot to preserve the tested upstream source rather than rewriting unrelated upstream functionality.

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

### Azure Resources Used

The deployment used:

```text
Resource Group:
rg-cs-7f31a8

Region:
westeurope

Azure Container Registry:
mevzuatcaseogul

Container Apps Environment:
mevzuat-case-env

Container App:
mevzuat-case-mcp
```

### Azure CLI Deployment

The following sequence documents the deployment flow used for the case.

Set the deployment variables:

```bash
RESOURCE_GROUP=rg-cs-7f31a8
LOCATION=westeurope
ACR_NAME=mevzuatcaseogul
CONTAINERAPP_ENV=mevzuat-case-env
CONTAINERAPP_NAME=mevzuat-case-mcp
IMAGE_NAME=mevzuat-case-mcp
```

Create the Azure Container Registry:

```bash
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --location $LOCATION
```

Log in to the registry:

```bash
az acr login --name $ACR_NAME
```

Build and push the image for Azure Container Apps:

```bash
docker buildx build \
  --platform linux/amd64 \
  -t $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
  --push \
  ./mcp-server
```

Create the Container Apps environment:

```bash
az containerapp env create \
  --name $CONTAINERAPP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

Managed identity with the `AcrPull` role should normally be preferred for registry access.

In this case, the provided Azure account did not have permission to create the required role assignment.

For that reason, registry credentials were used as a deployment fallback.

Enable ACR admin credentials:

```bash
az acr update \
  --name $ACR_NAME \
  --admin-enabled true
```

Read the registry credentials into shell variables:

```bash
ACR_USERNAME=$(az acr credential show \
  --name $ACR_NAME \
  --query username \
  --output tsv)

ACR_PASSWORD=$(az acr credential show \
  --name $ACR_NAME \
  --query passwords[0].value \
  --output tsv)
```

Create the Container App:

```bash
az containerapp create \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPP_ENV \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --ingress external \
  --target-port 8000
```

If the Container App already exists and only the image needs to be updated:

```bash
az containerapp update \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
```

Get the public hostname:

```bash
az containerapp show \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

Verify the deployment:

```bash
curl https://<container-app-fqdn>/health
```

Expected example:

```json
{
  "status": "healthy",
  "service": "Mevzuat MCP Server",
  "version": "0.1.0"
}
```

The MCP endpoint is:

```text
https://<container-app-fqdn>/mcp
```

A real FastMCP client call should also be used to confirm that the deployed service can establish an MCP session and execute the selected legislation tools.

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
dist/
.DS_Store
```

The following template is intentionally included:

```text
backend/.env.example
```

It contains configuration names but no API key.

The real `.env` file must never be committed or included in a manual ZIP submission.

The preferred submission method is a Git repository containing only tracked project files.

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

The project was tested from a clean Git state.

The following checks succeeded.

### Frontend

```bash
npm ci
npm run build
npm run lint
```

### Backend

Using Python 3.12:

```bash
pip install -r requirements.txt
python -m compileall app
pip check
```

### Docker

The MCP image was successfully built and run locally:

```bash
docker build --no-cache \
  -t mevzuat-case-mcp-clean \
  ./mcp-server
```

The resulting container:

- started successfully
- passed its health check
- exposed the MCP endpoint
- listed MCP tools
- successfully executed real legislation tool calls

### Azure

The cloud deployment was validated using:

- `/health`
- FastMCP session establishment
- tool listing
- real tool execution

### Backend Integration

The following were also verified:

- backend `/health`
- normal `/api/chat`
- `/api/chat/stream`
- input validation
- incremental streaming
- MCP-backed legislation answers

### Frontend Integration

The React UI was tested with multiple legislation questions from different laws.

The following were verified:

- streamed answers
- Markdown rendering
- multiple sequential questions
- dynamic health indicator
- backend outage detection
- recovery behavior

## Scope

The implementation intentionally focuses on the core requirements of the case:

- MCP server containerization
- cloud MCP deployment
- backend access to the MCP server
- OpenAI integration
- enforced MCP usage for legislation answers
- MCP tool execution
- React chat interface
- streamed responses
- clear local setup instructions
- documented Azure deployment steps

The following were intentionally kept out of scope because they were not required by the case:

- authentication
- user accounts
- databases
- persistent conversation history
- queues
- Kubernetes
- CI/CD infrastructure
- additional AI providers in the submitted application
- support for every upstream MCP feature

The upstream source snapshot may still contain optional integrations from the original project, but they are neither configured nor used by this application.

The goal was to keep the implementation focused, understandable, and easy to run while satisfying the requested case functionality.
