import os
from typing import Annotated, Sequence, TypedDict, List, Dict, Any, Literal, Optional, Union
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator

from backend.config import settings
from backend.models import HCP, Material, Sample

# Define the state of the agent
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    form_data: Dict[str, Any]
    last_updated_fields: List[str]
    hcp_suggestions: List[Dict[str, Any]]
    submitted: bool

# Define Pydantic inputs for the tools to ensure strict validation

def _coerce_list_to_str(v):
    """Convert any list/array value to a comma-separated string. Groq rejects arrays where str is expected."""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x)
    if v is None:
        return None
    return str(v)

class LogInteractionInput(BaseModel):
    hcp_name: Optional[str] = Field(default=None, description="Name of the healthcare professional (e.g. Dr. Smith)")
    interaction_type: Optional[str] = Field(default=None, description="Type of interaction, e.g., Meeting, Call, Email, Event, Webcast")
    date: Optional[str] = Field(default=None, description="Date of interaction. Format: YYYY-MM-DD")
    time: Optional[str] = Field(default=None, description="Time of interaction. Format: HH:MM (24-hour)")
    attendees: Optional[str] = Field(default=None, description="Names of attendees, separated by commas")
    topics_discussed: Optional[str] = Field(default=None, description="Key discussion points or topics covered")
    materials_shared: Optional[str] = Field(default=None, description="Comma-separated materials shared (e.g. 'OncoBoost Phase III PDF, Product X Brochure'). Must be a string, not a list.")
    samples_distributed: Optional[str] = Field(default=None, description="Comma-separated samples distributed (e.g. 'Product X Sample Pack'). Must be a string, not a list.")
    sentiment: Optional[str] = Field(default=None, description="Sentiment of the HCP. Options: Positive, Neutral, Negative")
    outcomes: Optional[str] = Field(default=None, description="Key outcomes, decisions, or agreements")
    follow_up_actions: Optional[str] = Field(default=None, description="Immediate follow-up actions or tasks")

    @field_validator('materials_shared', 'samples_distributed', 'attendees', mode='before')
    @classmethod
    def coerce_lists_to_str(cls, v):
        return _coerce_list_to_str(v)

class EditInteractionInput(BaseModel):
    hcp_name: Optional[str] = Field(default=None, description="Updated name of the HCP")
    interaction_type: Optional[str] = Field(default=None, description="Updated type of interaction")
    date: Optional[str] = Field(default=None, description="Updated date of interaction. Format: YYYY-MM-DD")
    time: Optional[str] = Field(default=None, description="Updated time of interaction")
    attendees: Optional[str] = Field(default=None, description="Updated attendees list")
    topics_discussed: Optional[str] = Field(default=None, description="Updated topics discussed")
    materials_shared: Optional[str] = Field(default=None, description="Updated materials shared (comma-separated string, not a list)")
    samples_distributed: Optional[str] = Field(default=None, description="Updated samples distributed (comma-separated string, not a list)")
    sentiment: Optional[str] = Field(default=None, description="Updated sentiment (Positive, Neutral, Negative)")
    outcomes: Optional[str] = Field(default=None, description="Updated outcomes")
    follow_up_actions: Optional[str] = Field(default=None, description="Updated follow-up actions")

    @field_validator('materials_shared', 'samples_distributed', 'attendees', mode='before')
    @classmethod
    def coerce_lists_to_str(cls, v):
        return _coerce_list_to_str(v)

class SearchHCPInput(BaseModel):
    name_query: str = Field(..., description="Name or partial name of the HCP to search in the database")

class SuggestFollowUpsInput(BaseModel):
    topics_discussed: Optional[str] = Field(default=None, description="The topics discussed during the meeting")
    sentiment: Optional[str] = Field(default=None, description="The inferred sentiment of the HCP")

class SubmitInteractionInput(BaseModel):
    confirm: Any = Field(True, description="Confirm submission of the current interaction details to the database")

# Helper to get LLM instance based on provider
def get_llm():
    if settings.LLM_PROVIDER == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Use gemini-2.5-flash
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                api_key=settings.GEMINI_API_KEY,
                temperature=0.1,
                max_retries=2,
                timeout=15.0
            )
        except ImportError:
            raise ImportError("Please install langchain-google-genai to use Gemini provider.")
    else:
        try:
            from langchain_groq import ChatGroq
            # Use llama-3.1-8b-instant (which has high limits and is active)
            model_name = "llama-3.1-8b-instant"
            return ChatGroq(
                model=model_name,
                api_key=settings.GROQ_API_KEY,
                temperature=0.1,
                max_retries=2,
                timeout=15.0
            )
        except ImportError:
            raise ImportError("Please install langchain-groq to use Groq provider.")

# Node definitions for LangGraph

def run_agent(state: AgentState):
    llm = get_llm()
    
    from langchain_core.tools import StructuredTool
    
    tools = [
        StructuredTool(
            name="log_interaction",
            description="Log new interaction details from the natural language discussion details. Extract fields such as hcp_name, date, time, topics_discussed, materials_shared, samples_distributed, sentiment, outcomes, and follow_up_actions.",
            args_schema=LogInteractionInput,
            func=lambda **kwargs: kwargs
        ),
        StructuredTool(
            name="edit_interaction",
            description="Edit specific fields of the current interaction details. Use this tool when the user wants to correct or update details (e.g., changing names, sentiment, or adding discussion points) without clearing other fields.",
            args_schema=EditInteractionInput,
            func=lambda **kwargs: kwargs
        ),
        StructuredTool(
            name="search_hcp",
            description="Search the database for an HCP by name to verify profile, get specialty, email, and auto-select them.",
            args_schema=SearchHCPInput,
            func=lambda **kwargs: kwargs
        ),
        StructuredTool(
            name="suggest_follow_ups",
            description="Generate AI suggested next steps/follow-ups based on the discussed topics and sentiment.",
            args_schema=SuggestFollowUpsInput,
            func=lambda **kwargs: kwargs
        ),
        StructuredTool(
            name="submit_interaction",
            description="Submit and commit the completed interaction details to the database.",
            args_schema=SubmitInteractionInput,
            func=lambda **kwargs: kwargs
        )
    ]
    
    llm_with_tools = llm.bind_tools(tools)
    
    # Construction of a detailed system prompt
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    yesterday_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    system_prompt = f"""You are a premium AI CRM Assistant for pharmaceutical and medical device field representatives.
Your task is to help the rep manage and log interactions with Healthcare Professionals (HCPs) strictly through this chat panel.
The UI is a split-screen. The left panel shows the form, and the right panel is your chat.

Current Date (YYYY-MM-DD): {current_date}
Current Time (HH:MM): {current_time}

YOUR CAPABILITIES & RULES:
1. **Logging**: When the user describes a meeting (e.g. "I met Dr. Smith..."), call 'log_interaction' to extract and fill the form fields.
   - If the user implies the meeting just happened (e.g. "Just met", "just finished"), auto-populate the 'time' field with the Current Time: {current_time}.
   - Always extract and format dates as YYYY-MM-DD (e.g. {current_date}).
2. **Editing**: When the user requests a correction or update to the form (e.g. "Change date to yesterday"), call 'edit_interaction' to update only the specific fields specified.
   - If the user refers to relative dates like "yesterday", resolve it based on the Current Date context: {current_date} (yesterday was {yesterday_date}).
   - Always output dates in YYYY-MM-DD format.
   - If the user asks to modify a field not directly present in the form (like "duration"), append it to 'topics_discussed' or 'outcomes' and note it in your reply.
3. **Searching**: When a user mentions a name, or you need to find an HCP profile, call 'search_hcp' to verify them in the database.
4. **Suggestions**: Always suggest follow-ups after logging. Call 'suggest_follow_ups' to generate dynamic, contextual AI recommended steps.
5. **Submission**: When the rep wants to save or submit the interaction, verify the required fields (HCP name, type, date) are present. If they are, call 'submit_interaction'. If not, ask the user to provide them.
6. **Form Synchronization**: Whenever you update the form via 'log_interaction' or 'edit_interaction', explain clearly to the user what you have updated.
7. **Premium Response Style**: 
   - Do not print raw Python dictionaries, state dumps, or internal variables directly in your conversational text replies to the user.
   - Summarize the updates in clean, natural, human-friendly Markdown text.
   - Example reply after logging details:
     "**Interaction logged successfully!** The details (HCP Name, Date, Sentiment, and Materials) have been automatically populated based on your summary. Would you like me to suggest a specific follow-up action, such as scheduling a meeting?"
   - Example reply after correcting details:
     "I have updated the HCP Name to Dr. John and Sentiment to Negative. All other fields have been kept intact. Would you like to make any other changes or proceed with submitting?"

Always be polite, professional, and act as a life sciences consulting assistant. Do not ask the user to fill the form manually; remind them you can handle it!

Active form data state (for reference only, do not repeat): {state.get('form_data', {})}"""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

import datetime

def _generate_follow_up_suggestions(topics: str, sentiment: str, hcp_name: str = "") -> list:
    """
    Dynamically generates contextually relevant follow-up suggestions based on 
    the topics discussed, HCP sentiment, and HCP name. Works for any prompt,
    not just hardcoded keywords.
    """
    suggestions = []
    topics_lower = topics.lower() if topics else ""
    sentiment_lower = sentiment.lower() if sentiment else ""
    hcp_lower = hcp_name.lower() if hcp_name else ""

    # --- Meeting cadence based on sentiment ---
    if "negative" in sentiment_lower or "skeptical" in sentiment_lower:
        suggestions.append(f"Schedule urgent follow-up with {hcp_name or 'the HCP'} within 1 week")
    elif "positive" in sentiment_lower or "optimistic" in sentiment_lower:
        suggestions.append(f"Schedule follow-up meeting with {hcp_name or 'the HCP'} in 2 weeks")
    else:
        suggestions.append(f"Schedule follow-up touchpoint with {hcp_name or 'the HCP'} in 2-3 weeks")

    # --- Product-specific material suggestions ---
    if any(kw in topics_lower for kw in ["oncology", "oncoboost", "cancer", "tumor", "drug target"]):
        suggestions.append("Send OncoBoost Phase III PDF")
    if any(kw in topics_lower for kw in ["cardio", "heart", "cardioshield", "cardiovascular"]):
        suggestions.append("Send CardioShield Clinical Study PDF")
    if any(kw in topics_lower for kw in ["neuro", "neurovibe", "brain", "neurology"]):
        suggestions.append("Send NeuroVibe Product Manual")
    if any(kw in topics_lower for kw in ["product x", "prodo-x", "efficacy", "brochure"]):
        suggestions.append("Send Product X clinical data brochure")

    # --- Advisory board / engagement suggestion ---
    if "advisory" in topics_lower or "board" in topics_lower or "research" in topics_lower:
        suggestions.append(f"Add {hcp_name or 'HCP'} to advisory board invite list")

    # --- Generic material share if no specific product was mentioned ---
    if len(suggestions) < 2:
        suggestions.append("Send relevant product brochure and supporting clinical data")

    # Deduplicate and cap at 3 suggestions
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    return unique[:3]

def call_tools(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    new_messages = []
    form_data = dict(state.get("form_data", {}))
    last_updated_fields = []
    hcp_suggestions = list(state.get("hcp_suggestions", []))
    submitted = state.get("submitted", False)
    
    # Extract tool calls from both potential formats (LangChain tool_calls list or legacy function_call kwargs)
    tool_calls = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tc in last_message.tool_calls:
            tool_calls.append({
                "name": tc["name"],
                "args": tc["args"],
                "id": tc.get("id") or "call_id_placeholder"
            })
    elif hasattr(last_message, "additional_kwargs") and "function_call" in last_message.additional_kwargs:
        fn_call = last_message.additional_kwargs["function_call"]
        import json
        try:
            args = json.loads(fn_call["arguments"])
        except Exception:
            args = {}
        tool_calls.append({
            "name": fn_call["name"],
            "args": args,
            "id": last_message.id or "call_id_placeholder"
        })
        
    for tool_call in tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]
        
        if name == "log_interaction":
            updates = args
            updated_keys = []
            
            # Special handling for dates
            if updates.get("date"):
                date_str = str(updates.get("date")).lower()
                if "today" in date_str:
                    updates["date"] = datetime.date.today().strftime("%Y-%m-%d")
                elif "yesterday" in date_str:
                    updates["date"] = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
            for k, v in updates.items():
                if v is not None:
                    v_str = str(v).strip().lower()
                    if v_str in ["null", "none", ""]:
                        form_data[k] = ""
                        continue
                    if k in ["materials_shared", "samples_distributed"] and isinstance(v, str):
                        # Clean up brackets/quotes in case the LLM did some weird formatting
                        v_clean = v.strip().lstrip("[").rstrip("]").replace("'", "").replace('"', "")
                        form_data[k] = [x.strip() for x in v_clean.split(",") if x.strip()]
                    else:
                        form_data[k] = v
                    updated_keys.append(k)
            
            # Automatically generate suggestions on logging
            topics = form_data.get("topics_discussed", "")
            sentiment = form_data.get("sentiment", "")
            hcp_name_val = form_data.get("hcp_name", "")
            if topics or sentiment:
                form_data["ai_suggested_follow_ups"] = _generate_follow_up_suggestions(topics, sentiment, hcp_name_val)
            
            tool_msg = f"Successfully parsed and populated interaction. Fields filled: {', '.join(updated_keys)}"
            new_messages.append(ToolMessage(content=tool_msg, tool_call_id=call_id, name=name))
            last_updated_fields.extend(updated_keys)
            
            # Trigger search automatically if hcp_name is logged
            if updates.get("hcp_name"):
                from backend.database import SessionLocal
                db = SessionLocal()
                try:
                    results = db.query(HCP).filter(HCP.name.ilike(f"%{updates['hcp_name']}%")).all()
                    if font_data_temp := results: # just dummy ref
                        hcp_suggestions = [{"id": r.id, "name": r.name, "specialty": r.specialty, "email": r.email} for r in results]
                        if len(results) == 1:
                            form_data["hcp_name"] = results[0].name
                            if not form_data.get("attendees"):
                                form_data["attendees"] = results[0].name
                    else:
                        hcp_suggestions = []
                finally:
                    db.close()

        elif name == "edit_interaction":
            updates = args
            updated_keys = []
            
            # Special handling for dates
            if updates.get("date"):
                date_str = str(updates.get("date")).lower()
                if "today" in date_str:
                    updates["date"] = datetime.date.today().strftime("%Y-%m-%d")
                elif "yesterday" in date_str:
                    updates["date"] = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
            for k, v in updates.items():
                if v is not None:
                    v_str = str(v).strip().lower()
                    if v_str in ["null", "none", ""]:
                        form_data[k] = ""
                        continue
                    if k in ["materials_shared", "samples_distributed"] and isinstance(v, str):
                        v_clean = v.strip().lstrip("[").rstrip("]").replace("'", "").replace('"', "")
                        form_data[k] = [x.strip() for x in v_clean.split(",") if x.strip()]
                    else:
                        form_data[k] = v
                    updated_keys.append(k)
            
            # Automatically update suggestions on editing
            topics = form_data.get("topics_discussed", "")
            sentiment = form_data.get("sentiment", "")
            if topics or sentiment:
                form_data["ai_suggested_follow_ups"] = _generate_follow_up_suggestions(topics, sentiment)
            
            tool_msg = f"Updated form corrections. Modified fields: {', '.join(updated_keys)}"
            new_messages.append(ToolMessage(content=tool_msg, tool_call_id=call_id, name=name))
            last_updated_fields.extend(updated_keys)
            
            # Trigger search automatically if hcp_name is edited
            if updates.get("hcp_name"):
                from backend.database import SessionLocal
                db = SessionLocal()
                try:
                    results = db.query(HCP).filter(HCP.name.ilike(f"%{updates['hcp_name']}%")).all()
                    if results:
                        hcp_suggestions = [{"id": r.id, "name": r.name, "specialty": r.specialty, "email": r.email} for r in results]
                        if len(results) == 1:
                            form_data["hcp_name"] = results[0].name
                    else:
                        hcp_suggestions = []
                finally:
                    db.close()
            
        elif name == "suggest_follow_ups":
            topics = args.get("topics_discussed", "") or form_data.get("topics_discussed", "")
            sentiment = args.get("sentiment", "") or form_data.get("sentiment", "")
            hcp_name_val = args.get("hcp_name", "") or form_data.get("hcp_name", "")
            suggestions = _generate_follow_up_suggestions(topics, sentiment, hcp_name_val)
            form_data["ai_suggested_follow_ups"] = suggestions
            
            tool_msg = f"Suggested Follow-ups generated: {suggestions}"
            new_messages.append(ToolMessage(content=tool_msg, tool_call_id=call_id, name=name))
            
        elif name == "search_hcp":
            query = args.get("name_query", "")
            from backend.database import SessionLocal
            db = SessionLocal()
            try:
                results = db.query(HCP).filter(HCP.name.ilike(f"%{query}%")).all()
                hcp_suggestions = [{"id": r.id, "name": r.name, "specialty": r.specialty, "email": r.email} for r in results]
                
                if len(results) == 1:
                    form_data["hcp_name"] = results[0].name
                    if not form_data.get("attendees"):
                        form_data["attendees"] = results[0].name
                    tool_msg = f"Found and auto-selected HCP: {results[0].name} ({results[0].specialty})"
                elif len(results) > 1:
                    names = [r.name for r in results]
                    tool_msg = f"Found multiple matches: {', '.join(names)}. Please select one."
                else:
                    tool_msg = f"No HCP profile found matching '{query}' in the directory. You can still input their name manually."
            except Exception as e:
                tool_msg = f"Error searching HCP: {str(e)}"
            finally:
                db.close()
                
            new_messages.append(ToolMessage(content=tool_msg, tool_call_id=call_id, name=name))
            
        elif name == "submit_interaction":
            from backend.database import SessionLocal
            from backend.models import Interaction
            db = SessionLocal()
            try:
                # Basic validation
                hcp_name = form_data.get("hcp_name")
                if not hcp_name:
                    tool_msg = "Error: Cannot submit. HCP Name is required."
                else:
                    hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name)).first()
                    hcp_id = hcp.id if hcp else None
                    
                    # Convert list to comma-separated string for DB storage
                    m_shared = form_data.get("materials_shared", [])
                    if isinstance(m_shared, list):
                        m_shared = ", ".join(m_shared)
                    s_dist = form_data.get("samples_distributed", [])
                    if isinstance(s_dist, list):
                        s_dist = ", ".join(s_dist)
                    
                    interaction = Interaction(
                        hcp_id=hcp_id,
                        hcp_name=hcp_name,
                        interaction_type=form_data.get("interaction_type", "Meeting"),
                        date=form_data.get("date", datetime.date.today().strftime("%Y-%m-%d")),
                        time=form_data.get("time", datetime.datetime.now().strftime("%H:%M")),
                        attendees=form_data.get("attendees"),
                        topics_discussed=form_data.get("topics_discussed"),
                        materials_shared=m_shared,
                        samples_distributed=s_dist,
                        sentiment=form_data.get("sentiment", "Neutral"),
                        outcomes=form_data.get("outcomes"),
                        follow_up_actions=form_data.get("follow_up_actions")
                    )
                    db.add(interaction)
                    db.commit()
                    submitted = True
                    tool_msg = "Interaction logged successfully!"
            except Exception as e:
                db.rollback()
                tool_msg = f"Failed to submit: {str(e)}"
            finally:
                db.close()
                
            new_messages.append(ToolMessage(content=tool_msg, tool_call_id=call_id, name=name))
            
    return {
        "messages": new_messages,
        "form_data": form_data,
        "last_updated_fields": last_updated_fields,
        "hcp_suggestions": hcp_suggestions,
        "submitted": submitted
    }

# Conditional routing logic: check if tool call exists
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if (hasattr(last_message, "tool_calls") and last_message.tool_calls) or (
        hasattr(last_message, "additional_kwargs") and "function_call" in last_message.additional_kwargs
    ):
        return "tools"
    return END

# Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", run_agent)
workflow.add_node("tools", call_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})
workflow.add_edge("tools", "agent")

compiled_graph = workflow.compile()
