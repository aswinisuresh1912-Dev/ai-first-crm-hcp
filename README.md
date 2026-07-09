# AI-First CRM HCP Module - Log Interaction Screen

An AI-First Customer Relationship Management (CRM) Healthcare Professional (HCP) module tailored for life-science field representatives. To maximize field-rep compliance and efficiency, this system features an intentionally locked (`readOnly`), state-driven structured form layout seamlessly paired with an autonomous conversational agent sidebar. All data extraction, structural adjustments, validation, and database storage tasks are driven exclusively via natural text interactions processed by the AI Agent.

## Core Tech Stack
- **Frontend:** React, Redux Toolkit, Lucide React, Vite
- **Backend:** Python, FastAPI, SQLAlchemy (SQLite)
- **AI Agent Framework:** LangGraph (Stateful Workflow graph tracking messages and form schemas)
- **LLM Provider:** Groq (`gemma2-9b-it`)

---

## System Architecture & State Synchronization Flow

The application eliminates manual form modification, relying entirely on structured state synchronizations between the React-Redux tree and a server-side LangGraph state network:

1. **User Interaction:** The user submits a free-text message detailing a clinical engagement or uses a quick-action simulation button.
2. **Payload Sync:** The entire conversation history alongside the current `form_data` state is dispatched to the FastAPI backend layer via an `/api/chat` POST request.
3. **LangGraph Evaluation:** The LangGraph stateful graph evaluates user intents, cross-references database variables, and orchestrates actions using **five (5) specific pharma sales-oriented agent tools**:
   - `log_interaction` *(Mandatory Tool 1)*: Uses entity extraction and structured LLM outputs to automatically parse baseline details (`hcp_name`, `interaction_type`, `date`, `time`, `attendees`, `topics_discussed`, `sentiment`) to fill out screen metrics.
   - `edit_interaction` *(Mandatory Tool 2)*: Serves as the *exclusive programmatic mechanism* for adjusting logged data. It handles structural changes and captures relative temporal expressions (e.g., resolving "change date to yesterday" into concrete timestamps like `2026-07-08`).
   - `search_hcp` *(Pharma Tool 3)*: Queries the compliance database directory to pull validated profiles (`specialty`, `email`), eliminating dirty or illegal input entries.
   - `suggest_follow_ups` *(Pharma Tool 4)*: Evaluates meeting sentiment notes and proactively computes clickable suggestion chips at the bottom of the interface.
   - `submit_interaction` *(Pharma Tool 5)*: Formally serializes the fully synchronized Redux layout state and commits the log records permanently to the SQLAlchemy SQLite transactional database.
4. **UI Reflected Changes:** The backend returns updated messages, form state, and highlighted indicators (`last_updated_fields`) causing changed fields on the frontend UI to dynamically alert the representative.

---

## Repository Structure

```text
ai-first-crm-hcp/
├── backend/                  # FastAPI & LangGraph Architecture
│   ├── agent.py              # LangGraph custom node definitions & tool bindings
│   ├── config.py             # Pydantic Settings & environment variables 
│   ├── database.py           # SQLAlchemy configuration & master data seeder
│   ├── main.py               # FastAPI router endpoints & CORS middleware
│   ├── models.py             # Database schemas (HCPs, Materials, Samples, Interactions)
│   ├── .env.template         # Configuration structural blueprint
│   └── requirements.txt      # Python dependencies list
├── frontend/                 # React SPA Interface
│   ├── src/
│   |    ├── store/
│   |          └── index.js   # Redux Toolkit slicer controlling locked form state
│   │   ├── App.jsx           # Locked form layout, interactive modals & chat panels
│   │   ├── index.css         # Stylized layouts, status colors & flashing notifications
│   │   ├── main.jsx          # App element attachment entry point
│   │   └── index.js          # Redux Toolkit slicer controlling locked form state
│   ├── index.html            # Core document framework
│   ├── package.json          # Node dependencies configuration
│   └── package-lock.json     # Lockfile dependency registry
├── task.pdf                  # Core round specification assignment guidelines
└── README.md                 # System overview and operational guide


Setup & Installation
1. Backend Setup
Navigate into the backend folder, create a virtual environment, activate it, and install your dependencies:

cd backend
python -m venv venv

# Activate on Mac/Linux:
source venv/bin/activate
# Activate on Windows (Command Prompt):
venv\Scripts\activate
# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
Create an active environment configuration file named .env in your backend/ directory based on the .env.template provided:

DATABASE_URL=sqlite:///./crm.db
LLM_PROVIDER=groq
GROQ_API_KEY=your_actual_groq_api_key_here

Note: On initialization, the backend automatically sets up a local SQLite file (crm.db) and seeds it with demo medical professionals (Dr. Smith, Dr. Sharma), clinical materials, and sample inventory tracking assets.

Launch your local development microservice API:

uvicorn main:app --reload
The server will boot up locally at http://127.0.0.1:8000.

2. Frontend Setup
Open a brand new separate terminal window, navigate into the frontend folder, install packages, and spin up Vite's local dev server:

cd frontend
npm install
npm run dev

Open your web browser to the specific port displayed in your terminal (usually http://localhost:5173) to view the interactive application dashboard.
