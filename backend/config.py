import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables into os.environ
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./crm.db"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"  # 'groq' or 'gemini'
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
