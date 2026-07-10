from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class HCP(Base):
    __tablename__ = "hcps"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    specialty = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    
    interactions = relationship("Interaction", back_populates="hcp")

class Material(Base):
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

class Sample(Base):
    __tablename__ = "samples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=True)
    hcp_name = Column(String(255), nullable=False)  # Stored text value of the form field
    interaction_type = Column(String(50), nullable=True)  # Meeting, Call, Email, etc.
    date = Column(String(50), nullable=True)  # String format (YYYY-MM-DD) or similar for form simplicity
    time = Column(String(50), nullable=True)  # String format (HH:MM)
    attendees = Column(Text, nullable=True)  # JSON or comma-separated list
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)  # JSON or comma-separated list
    samples_distributed = Column(Text, nullable=True)  # JSON or comma-separated list
    sentiment = Column(String(20), nullable=True)  # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    hcp = relationship("HCP", back_populates="interactions")
