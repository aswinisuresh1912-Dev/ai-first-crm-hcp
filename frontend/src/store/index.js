import { configureStore, createSlice } from '@reduxjs/toolkit';

const getLocalDateString = () => {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getLocalTimeString = () => {
  const d = new Date();
  return d.toTimeString().slice(0, 5);
};

const initialFormState = {
  hcp_name: '',
  interaction_type: 'Meeting',
  date: getLocalDateString(),
  time: getLocalTimeString(),
  attendees: '',
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  ai_suggested_follow_ups: []
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    messages: [
      {
        role: 'assistant',
        content: 'Hello! I am your AI CRM Assistant. You can describe your meeting here, and I will populate the form for you (e.g. "I met Dr. Smith today..."). Let me know how I can help!'
      }
    ],
    formData: initialFormState,
    lastUpdatedFields: [],
    hcpSuggestions: [],
    isTyping: false,
    isLoading: false,
    error: null,
    submitSuccess: false
  },
  reducers: {
    updateField: (state, action) => {
      const { field, value } = action.payload;
      state.formData[field] = value;
    },
    updateFormData: (state, action) => {
      state.formData = { ...state.formData, ...action.payload };
    },
    resetForm: (state) => {
      state.formData = {
        ...initialFormState,
        date: getLocalDateString(),
        time: getLocalTimeString()
      };
      state.lastUpdatedFields = [];
      state.hcpSuggestions = [];
      state.submitSuccess = false;
    },
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    setMessages: (state, action) => {
      state.messages = action.payload;
    },
    setLastUpdatedFields: (state, action) => {
      state.lastUpdatedFields = action.payload;
    },
    clearLastUpdatedFields: (state) => {
      state.lastUpdatedFields = [];
    },
    setHcpSuggestions: (state, action) => {
      state.hcpSuggestions = action.payload;
    },
    setTyping: (state, action) => {
      state.isTyping = action.payload;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    setSubmitSuccess: (state, action) => {
      state.submitSuccess = action.payload;
    }
  }
});

export const {
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
} = interactionSlice.actions;

export const store = configureStore({
  reducer: {
    interaction: interactionSlice.reducer
  }
});
export default store;
