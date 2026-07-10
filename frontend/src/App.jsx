import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  MessageSquare,
  User,
  Calendar,
  Clock,
  Users,
  FileText,
  Bookmark,
  Smile,
  CheckCircle,
  Plus,
  Search,
  Mic,
  Send,
  Trash2,
  AlertCircle,
  FolderOpen,
  Bot,
  Sparkles
} from 'lucide-react';
import {
  updateField,
  updateFormData,
  resetForm,
  addMessage,
  setMessages,
  setLastUpdatedFields,
  clearLastUpdatedFields,
  setHcpSuggestions,
  setTyping,
  setLoading,
  setError,
  setSubmitSuccess
} from './store';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const dispatch = useDispatch();
  const {
    messages,
    formData,
    lastUpdatedFields,
    hcpSuggestions,
    isTyping,
    isLoading,
    error,
    submitSuccess
  } = useSelector((state) => state.interaction);

  // Local state for modals & search
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  const [showSampleModal, setShowSampleModal] = useState(false);
  const [materialsList, setMaterialsList] = useState([]);
  const [samplesList, setSamplesList] = useState([]);
  const [allHcps, setAllHcps] = useState([]);
  
  // Voice note simulation state
  const [isRecording, setIsRecording] = useState(false);
  const [recordTimer, setRecordTimer] = useState(0);
  const recordInterval = useRef(null);

  // Chat input
  const [chatInput, setChatInput] = useState('');
  const chatBottomRef = useRef(null);

  // Fetch initial data from FastAPI backend
  useEffect(() => {
    fetchMaterials();
    fetchSamples();
    fetchHcps();
  }, []);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Handle fading out highlighted fields
  useEffect(() => {
    if (lastUpdatedFields.length > 0) {
      const timer = setTimeout(() => {
        dispatch(clearLastUpdatedFields());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [lastUpdatedFields, dispatch]);

  const fetchMaterials = async () => {
    try {
      const res = await fetch(`${API_BASE}/materials`);
      if (res.ok) {
        const data = await res.json();
        setMaterialsList(data);
      }
    } catch (e) {
      console.error('Error fetching materials:', e);
    }
  };

  const fetchSamples = async () => {
    try {
      const res = await fetch(`${API_BASE}/samples`);
      if (res.ok) {
        const data = await res.json();
        setSamplesList(data);
      }
    } catch (e) {
      console.error('Error fetching samples:', e);
    }
  };

  const fetchHcps = async () => {
    try {
      const res = await fetch(`${API_BASE}/hcps`);
      if (res.ok) {
        const data = await res.json();
        setAllHcps(data);
      }
    } catch (e) {
      console.error('Error fetching HCPs:', e);
    }
  };

  // Input changes
  const handleInputChange = (field, value) => {
    dispatch(updateField({ field, value }));
  };

  // Add / remove materials & samples
  const addMaterial = (materialName) => {
    if (!formData.materials_shared.includes(materialName)) {
      handleInputChange('materials_shared', [...formData.materials_shared, materialName]);
    }
    setShowMaterialModal(false);
  };

  const removeMaterial = (materialName) => {
    handleInputChange(
      'materials_shared',
      formData.materials_shared.filter((m) => m !== materialName)
    );
  };

  const addSample = (sampleName) => {
    if (!formData.samples_distributed.includes(sampleName)) {
      handleInputChange('samples_distributed', [...formData.samples_distributed, sampleName]);
    }
    setShowSampleModal(false);
  };

  const removeSample = (sampleName) => {
    handleInputChange(
      'samples_distributed',
      formData.samples_distributed.filter((s) => s !== sampleName)
    );
  };

  // AI Suggested follow-ups click
  const handleSuggestionClick = (suggestion) => {
    const currentActions = formData.follow_up_actions;
    const separator = currentActions ? '\n' : '';
    handleInputChange('follow_up_actions', currentActions + separator + `- ${suggestion}`);
  };

  // Submit via API
  const handleFormSubmit = async () => {
    if (!formData.hcp_name) {
      dispatch(setError('HCP Name is required to log an interaction.'));
      return;
    }
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            ...messages,
            { role: 'user', content: 'Submit and save this interaction details form to the database.' }
          ],
          form_data: formData
        })
      });
      if (response.ok) {
        const data = await response.json();
        if (data.submitted) {
          dispatch(setSubmitSuccess(true));
          dispatch(
            addMessage({
              role: 'assistant',
              content: '✅ The interaction details have been successfully committed to the database.'
            })
          );
        } else {
          dispatch(setError('Could not submit form. Make sure all required fields are filled.'));
        }
      } else {
        dispatch(setError('Server error during form submission.'));
      }
    } catch (e) {
      dispatch(setError('Network error. Failed to reach the server.'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  // Conversational message submission
  const sendMessage = async (messageText) => {
    const text = messageText || chatInput;
    if (!text.trim()) return;

    // Add user message to history
    dispatch(addMessage({ role: 'user', content: text }));
    if (!messageText) setChatInput('');
    dispatch(setTyping(true));
    dispatch(setError(null));

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: text }],
          form_data: formData
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log("FRONTEND RECEIVED FORM DATA:", data.form_data);
        
        // Update Form state returned by Agent
        dispatch(updateFormData(data.form_data));
        
        // Highlight updated fields
        if (data.last_updated_fields && data.last_updated_fields.length > 0) {
          dispatch(setLastUpdatedFields(data.last_updated_fields));
        }

        // Set HCP suggestions if query returned multiple
        if (data.hcp_suggestions) {
          dispatch(setHcpSuggestions(data.hcp_suggestions));
        }

        // Append only the newly generated assistant replies to the chat history
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach((msg) => {
            dispatch(addMessage(msg));
          });
        }
        
        if (data.submitted) {
          dispatch(setSubmitSuccess(true));
        }
      } else {
        dispatch(setError('Failed to get a response from the AI assistant.'));
      }
    } catch (e) {
      dispatch(setError('Failed to reach backend agent. Is uvicorn running?'));
    } finally {
      dispatch(setTyping(false));
    }
  };

  // Simulate dictation recording
  const handleVoiceNoteClick = () => {
    if (isRecording) {
      // Stop recording
      clearInterval(recordInterval.current);
      setIsRecording(false);
      setRecordTimer(0);
      
      // Simulate transcribing a high-fidelity pharmaceutical rep update
      const simulatedTranscript = "Met with Dr. Sharma today at 14:00 to discuss the NeuroVibe Product Manual efficacy. The sentiment was positive, and I shared the NeuroVibe Product Manual and distributed the NeuroVibe Dosage Guide.";
      
      // Load the transcription directly into the text input box for user review
      setInput(simulatedTranscript);
    } else {
      // Start recording
      setIsRecording(true);
      setRecordTimer(0);
      recordInterval.current = setInterval(() => {
        setRecordTimer((prev) => prev + 1);
      }, 1000);
    }
  };

  // Pre-created prompts
  const samplePrompts = [
    "Today I met with Dr. Smith and discussed Product X efficacy. The sentiment was positive, and I shared the brochures.",
    "Actually the name is Dr. John and the sentiment was negative.",
    "Submit the interaction details."
  ];

  return (
    <div className="app-container">
      {/* LEFT PANEL - Form Details */}
      <div className="left-panel">
        <div className="header-bar">
          <h1 className="header-title">
            <FolderOpen className="text-indigo-600" size={24} />
            Log HCP Interaction
          </h1>
          <button className="action-btn secondary" onClick={() => dispatch(resetForm())}>
            Reset Form
          </button>
        </div>

        {submitSuccess && (
          <div style={{ padding: '0 32px', marginTop: '24px' }}>
            <div className="success-banner">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle size={20} />
                <span><strong>Success!</strong> The interaction has been saved to the database.</span>
              </div>
              <button
                className="action-btn primary"
                onClick={() => dispatch(resetForm())}
              >
                Log New Interaction
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '0 32px', marginTop: '24px' }}>
            <div style={{
              backgroundColor: 'var(--accent-negative-light)',
              border: '1.5px solid var(--accent-negative)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--accent-negative)'
            }}>
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          </div>
        )}

        <div className="form-content">
          {/* Row 1: HCP Name & Interaction Type */}
          <div className="form-row">
            <div className={`form-group ${lastUpdatedFields.includes('hcp_name') ? 'field-highlighted' : ''}`}>
              <label>HCP Name</label>
              <input
                type="text"
                placeholder="Search or select HCP..."
                value={formData.hcp_name || ''}
                onChange={(e) => handleInputChange('hcp_name', e.target.value)}
                readOnly /* Read-only to enforce AI assistant rule, but user can clear */
              />
              {hcpSuggestions.length > 0 && (
                <div style={{
                  border: '1.5px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'white',
                  marginTop: '4px',
                  maxHeight: '120px',
                  overflowY: 'auto'
                }}>
                  {hcpSuggestions.map((hcp) => (
                    <div
                      key={hcp.id}
                      onClick={() => {
                        dispatch(updateFormData({
                          hcp_name: hcp.name,
                          attendees: hcp.name
                        }));
                        dispatch(setHcpSuggestions([]));
                      }}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        borderBottom: '1px solid #f1f5f9'
                      }}
                      hover-bg="true"
                    >
                      <strong>{hcp.name}</strong> - {hcp.specialty}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className={`form-group ${lastUpdatedFields.includes('interaction_type') ? 'field-highlighted' : ''}`}>
              <label>Interaction Type</label>
              <select
                value={formData.interaction_type || 'Meeting'}
                onChange={(e) => handleInputChange('interaction_type', e.target.value)}
                disabled
              >
                <option value="Meeting">Meeting</option>
                <option value="Call">Call</option>
                <option value="Email">Email</option>
                <option value="Event">Event</option>
                <option value="Webcast">Webcast</option>
              </select>
            </div>
          </div>

          {/* Row 2: Date & Time */}
          <div className="form-row">
            <div className={`form-group ${lastUpdatedFields.includes('date') ? 'field-highlighted' : ''}`}>
              <label>Date</label>
              <input
                type="date"
                value={formData.date && formData.date !== 'null' && formData.date !== 'None' ? formData.date : ''}
                onChange={(e) => handleInputChange('date', e.target.value)}
                readOnly
              />
            </div>

            <div className={`form-group ${lastUpdatedFields.includes('time') ? 'field-highlighted' : ''}`}>
              <label>Time</label>
              <input
                type="time"
                value={formData.time && formData.time !== 'null' && formData.time !== 'None' ? formData.time : ''}
                onChange={(e) => handleInputChange('time', e.target.value)}
                readOnly
              />
            </div>
          </div>

          {/* Row 3: Attendees */}
          <div className={`form-group full-width ${lastUpdatedFields.includes('attendees') ? 'field-highlighted' : ''}`}>
            <label>Attendees</label>
            <input
              type="text"
              placeholder="Enter names or search..."
              value={formData.attendees || ''}
              onChange={(e) => handleInputChange('attendees', e.target.value)}
              readOnly
            />
          </div>

          {/* Row 4: Topics Discussed */}
          <div className={`form-group full-width ${lastUpdatedFields.includes('topics_discussed') ? 'field-highlighted' : ''}`}>
            <label>Topics Discussed</label>
            <textarea
              rows={4}
              placeholder="Enter key discussion points..."
              value={formData.topics_discussed || ''}
              onChange={(e) => handleInputChange('topics_discussed', e.target.value)}
              readOnly
            />
            <div className="voice-note-container">
              <button
                className={`voice-btn ${isRecording ? 'recording' : ''}`}
                onClick={handleVoiceNoteClick}
              >
                <Mic size={16} />
                {isRecording 
                  ? `Recording Voice Note (${recordTimer}s) - Click to Stop & Transcribe` 
                  : 'Summarize from Voice Note (Requires Consent)'}
              </button>
            </div>
          </div>

          {/* Row 5: Materials Shared & Samples Distributed */}
          <div className="form-row">
            <div className={`form-group ${lastUpdatedFields.includes('materials_shared') ? 'field-highlighted' : ''}`}>
              <label>Materials Shared</label>
              <div className="badge-list">
                {formData.materials_shared && formData.materials_shared.length > 0 ? (
                  formData.materials_shared.map((material) => (
                    <span key={material} className="badge-item">
                      {material}
                      <button onClick={() => removeMaterial(material)}>&times;</button>
                    </span>
                  ))
                ) : (
                  <span className="empty-badge-text">No materials added.</span>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <button className="add-item-btn" onClick={() => setShowMaterialModal(true)}>
                  <Plus size={14} /> Search/Add Material
                </button>
              </div>
            </div>

            <div className={`form-group ${lastUpdatedFields.includes('samples_distributed') ? 'field-highlighted' : ''}`}>
              <label>Samples Distributed</label>
              <div className="badge-list">
                {formData.samples_distributed && formData.samples_distributed.length > 0 ? (
                  formData.samples_distributed.map((sample) => (
                    <span key={sample} className="badge-item">
                      {sample}
                      <button onClick={() => removeSample(sample)}>&times;</button>
                    </span>
                  ))
                ) : (
                  <span className="empty-badge-text">No samples added.</span>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <button className="add-item-btn" onClick={() => setShowSampleModal(true)}>
                  <Plus size={14} /> Add Sample
                </button>
              </div>
            </div>
          </div>

          {/* Row 6: Inferred HCP Sentiment */}
          <div className={`form-group full-width ${lastUpdatedFields.includes('sentiment') ? 'field-highlighted' : ''}`}>
            <label>Observed/Inferred HCP Sentiment</label>
            <div className="sentiment-group">
              {['Positive', 'Neutral', 'Negative'].map((sent) => (
                <label key={sent} className={`sentiment-option ${sent.toLowerCase()}`}>
                  <input
                    type="radio"
                    name="sentiment"
                    value={sent}
                    checked={formData.sentiment === sent}
                    onChange={() => {}} /* Read-only to enforce AI assistant control */
                  />
                  <span>
                    {sent === 'Positive' && '😊 '}
                    {sent === 'Neutral' && '😐 '}
                    {sent === 'Negative' && '😡 '}
                    {sent}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Row 7: Outcomes */}
          <div className={`form-group full-width ${lastUpdatedFields.includes('outcomes') ? 'field-highlighted' : ''}`}>
            <label>Outcomes</label>
            <textarea
              rows={3}
              placeholder="Key outcomes or agreements..."
              value={formData.outcomes || ''}
              onChange={(e) => handleInputChange('outcomes', e.target.value)}
              readOnly
            />
          </div>

          {/* Row 8: Follow-up Actions */}
          <div className={`form-group full-width ${lastUpdatedFields.includes('follow_up_actions') ? 'field-highlighted' : ''}`}>
            <label>Follow-up Actions</label>
            <textarea
              rows={3}
              placeholder="Enter next steps or tasks..."
              value={formData.follow_up_actions || ''}
              onChange={(e) => handleInputChange('follow_up_actions', e.target.value)}
              readOnly
            />
          </div>

          {/* Row 9: AI Suggested Follow-ups */}
          {formData.ai_suggested_follow_ups && formData.ai_suggested_follow_ups.length > 0 && (
            <div className="form-group full-width">
              <label>AI Suggested Follow-ups (Click to Apply)</label>
              <div className="suggestions-box">
                {formData.ai_suggested_follow_ups.map((s, idx) => (
                  <div key={idx} className="suggestion-chip" onClick={() => handleSuggestionClick(s)}>
                    <CheckCircle size={14} className="text-indigo-600" />
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Actions */}
          <div style={{ marginTop: '12px' }}>
            <button
              className="action-btn primary"
              style={{ width: '100%', padding: '14px' }}
              onClick={handleFormSubmit}
              disabled={isLoading}
            >
              {isLoading ? 'Submitting...' : 'Log and Save Interaction'}
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL - AI Assistant Chat */}
      <div className="right-panel">
        <div className="chat-header">
          <div className="chat-header-title">
            <MessageSquare size={20} className="text-indigo-600" />
            AI Assistant
          </div>
          <div className="chat-header-subtitle">Log interaction details here via chat</div>
        </div>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`chat-bubble ${msg.role === 'assistant' ? 'assistant' : 'user'}`}
            >
              {msg.content}
            </div>
          ))}
          {isTyping && (
            <div className="typing-indicator">
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
            </div>
          )}
          <div ref={chatBottomRef} />
        </div>

        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <input
              type="text"
              placeholder="Describe interaction..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            />
          </div>
          <button className="chat-send-btn" onClick={() => sendMessage()}>
            <Bot size={16} /> Log
          </button>
        </div>
      </div>

      {/* Materials Selection Modal */}
      {showMaterialModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Select Material Shared</h3>
              <button className="modal-close-btn" onClick={() => setShowMaterialModal(false)}>
                &times;
              </button>
            </div>
            <div className="modal-list">
              {materialsList.length > 0 ? (
                materialsList.map((mat) => (
                  <div
                    key={mat.id}
                    className="modal-list-item"
                    onClick={() => addMaterial(mat.name)}
                  >
                    <div>
                      <strong>{mat.name}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {mat.description}
                      </div>
                    </div>
                    <Plus size={16} />
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.9rem', color: 'var(--text-light)', textAlign: 'center' }}>
                  No materials available
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Samples Selection Modal */}
      {showSampleModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Select Sample Distributed</h3>
              <button className="modal-close-btn" onClick={() => setShowSampleModal(false)}>
                &times;
              </button>
            </div>
            <div className="modal-list">
              {samplesList.length > 0 ? (
                samplesList.map((samp) => (
                  <div
                    key={samp.id}
                    className="modal-list-item"
                    onClick={() => addSample(samp.name)}
                  >
                    <div>
                      <strong>{samp.name}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {samp.description}
                      </div>
                    </div>
                    <Plus size={16} />
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.9rem', color: 'var(--text-light)', textAlign: 'center' }}>
                  No samples available
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
