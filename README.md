# Smart Financial Advisor 💳📊

A conversational AI financial assistant built with Google's **Agent Development Kit (ADK)** and **Gemini 2.5 Flash**. The agent helps individuals log expenses, track spending category breakdowns, analyze savings plans to hit monthly goals, convert foreign currencies, find nearby stores, and generate visual financial receipt images and video animations.

![Smart Financial Advisor Demo](./demo.gif)

---

## 🚀 Key Features & Implemented Capabilities

The capabilities below are fully implemented and wired into the agent codebase (`app/agent.py` and `agents-cli-manifest.yaml`):

### 🧠 Cross-Session Long-Term Memory
- **Vertex AI Memory Bank Service**: Persists user preferences (monthly income, savings goals, spending habits, favorite stores) across sessions using `VertexAiMemoryBankService` and `PreloadMemoryTool`.

### 🗄️ Firestore Expense Database
- **Live Expense Logging & Retrieval**: Queries and updates a Cloud Firestore `expenses` collection via:
  - `list_expenses`: Filter expenses by category (e.g., Dining, Groceries, Utilities, Shopping).
  - `add_expense`: Record new transactions with dollar amount, category, date, and discretionary flag.
  - `calculate_category_breakdown`: Compute total spent, fixed vs. discretionary spending, and category totals.
  - `update_expense_category`: Re-categorize transactions.

### 💡 Savings & Budget Optimization
- **`analyze_savings_plan`**: Analyzes net income vs. total expenses to recommend cuts targeting discretionary spending to achieve a monthly savings goal.

### 🖼️ Multimodal Generation & Cloud Storage
- **Image Generation (`generate_expense_image`)**: Generates visual infographics and receipts using `gemini-3.1-flash-lite-image` in the `global` region, saves ADK session artifacts, and uploads public assets to Google Cloud Storage.
- **Video Generation (`generate_expense_video`)**: Generates animated videos for savings goals using Google's Omni model (`gemini-omni-flash-preview`) in the `global` region via the Vertex AI Interactions API.

### 🌐 Location, FX Currency & Code Execution
- **Google Maps & Places**:
  - `geocode_address`: Converts addresses into latitude/longitude coordinates via Google Maps Geocoding API.
  - `find_nearby_places`: Finds nearby budget-friendly stores using Google Places REST API (`searchNearby`).
- **Live Foreign Exchange (`convert_currency`)**: Converts currency values using real-time market exchange rates.
- **Code Execution Sandbox**: Runs Python code calculations via `AgentEngineSandboxCodeExecutor`.

### 🎨 Responsive Web UI & A2UI Protocol
- **FastAPI Proxy + Custom Web Chat UI**:
  - Native **A2UI Protocol v0.8** mini-renderer for interactive UI cards.
  - Dark / Light Mode theme toggle with local persistence.
  - Animated 3-dot typing indicator and message timestamps.
  - One-click copy buttons and quick suggestion prompt pills.

---

## 🛠️ Architecture Overview

```
Browser / Web UI
      │
      ▼
FastAPI Proxy Server (A2A Protocol)
      │
      ▼
ADK Agent Runtime (app/agent.py)
   ├── Vertex AI Memory Bank (Long-Term Memory)
   ├── Cloud Firestore (Expenses DB)
   ├── Google Cloud Storage (Public Assets)
   ├── Gemini 2.5 Flash / Flash Lite Image / Omni Models
   └── Google Maps & FX REST APIs
```

---

## 💻 Local Setup & Development Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend development)
- Google Cloud SDK (`gcloud`) with `aiplatform.user` permissions

### 1. Environment Setup

Clone the repository and install dependencies using `uv` or `pip`:

```bash
cd smart-financial-advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r pyproject.toml
```

Set up required environment variables in a `.env` file:

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_REGION=us-east1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

### 2. Seed Firestore Database

Initialize sample transaction records in Cloud Firestore:

```bash
python seed_firestore.py
```

### 3. Run Agent Locally with ADK

Start the local ADK Development server:

```bash
adk web app
```

### 4. Run Custom Web Frontend Locally

Navigate to the `frontend/` directory, set environment variables, and start the FastAPI proxy server:

```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/YOUR_PROJECT_NUMBER/locations/us-east1/reasoningEngines/YOUR_ENGINE_ID"
export AGENT_DIRECTORY="app"

uvicorn main:app --host 0.0.0.0 --port 8080
```

Access the frontend interface in your browser by opening the port `8080` on your machine.

---

## 🔮 Future / Planned Enhancements

The following features were outlined in initial design briefs and are planned for future iterations:
- [ ] *Planned*: Direct bank account synchronization API integration (Plaid / Teller).
- [ ] *Planned*: Automated monthly PDF report generation and email dispatch.
