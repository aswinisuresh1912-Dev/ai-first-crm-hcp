from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.database import get_db, init_db
from backend.models import HCP, Material, Sample, Interaction
from backend.agent import compiled_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

app = FastAPI(title="AI-First CRM HCP Module Backend")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Initialize and seed database
    init_db()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Endpoint to handle conversation & state synchronization
@app.post("/api/chat")
async def chat_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Expects payload:
    {
      "messages": [
        {"role": "user", "content": "..."}
      ],
      "form_data": {
         "hcp_name": "...",
         ...
      }
    }
    """
    raw_messages = payload.get("messages", [])
    form_data = payload.get("form_data", {})
    
    # Extract the last user message from the payload to run the agent in a clean, focused state
    user_prompts = [msg for msg in raw_messages if msg.get("role") == "user"]
    lc_messages = []
    if user_prompts:
        lc_messages = [HumanMessage(content=user_prompts[-1].get("content", ""))]
            
    # Prepare initial state for LangGraph
    initial_state = {
        "messages": lc_messages,
        "form_data": form_data,
        "last_updated_fields": [],
        "hcp_suggestions": [],
        "submitted": False
    }
    
    try:
        # Execute LangGraph
        result_state = compiled_graph.invoke(initial_state)
        
        # Get only the final generated assistant reply to prevent duplicates
        output_messages = []
        if result_state["messages"]:
            final_msg = result_state["messages"][-1]
            if isinstance(final_msg, AIMessage) and final_msg.content:
                output_messages.append({"role": "assistant", "content": final_msg.content})
        
        # Return updated state
        print("\n=== BACKEND OUTBOUND FORM DATA ===")
        print(result_state["form_data"])
        print("===================================\n")
        return {
            "messages": output_messages,
            "form_data": result_state["form_data"],
            "last_updated_fields": result_state.get("last_updated_fields", []),
            "hcp_suggestions": result_state.get("hcp_suggestions", []),
            "submitted": result_state.get("submitted", False)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent invocation failed: {str(e)}")

# Get preloaded HCP profiles
@app.get("/api/hcps")
def get_hcps(query: str = "", db: Session = Depends(get_db)):
    if query:
        hcps = db.query(HCP).filter(HCP.name.ilike(f"%{query}%")).all()
    else:
        hcps = db.query(HCP).all()
    return [{"id": h.id, "name": h.name, "specialty": h.specialty, "email": h.email} for h in hcps]

# Get preloaded Materials
@app.get("/api/materials")
def get_materials(db: Session = Depends(get_db)):
    materials = db.query(Material).all()
    return [{"id": m.id, "name": m.name, "description": m.description} for m in materials]

# Get preloaded Samples
@app.get("/api/samples")
def get_samples(db: Session = Depends(get_db)):
    samples = db.query(Sample).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in samples]

# Get list of logged interactions
@app.get("/api/interactions")
def get_interactions(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
    return [
        {
            "id": i.id,
            "hcp_name": i.hcp_name,
            "interaction_type": i.interaction_type,
            "date": i.date,
            "time": i.time,
            "attendees": i.attendees,
            "topics_discussed": i.topics_discussed,
            "materials_shared": i.materials_shared,
            "samples_distributed": i.samples_distributed,
            "sentiment": i.sentiment,
            "outcomes": i.outcomes,
            "follow_up_actions": i.follow_up_actions,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in interactions
    ]

# Setup main running block
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
