from typing import Literal

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class SourceCreate(BaseModel):
    collection_id: str
    title: str = Field(min_length=1, max_length=200)
    source_type: str = Field(default="text", max_length=30)
    content: str = Field(min_length=1)


class NoteCreate(BaseModel):
    collection_id: str
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    note_type: Literal["note", "concept", "question", "method", "flashcard"] = "note"


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    collection_id: str | None = None
    conversation_id: str | None = None


class LearningGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    target_date: str | None = None


class TaskUpdate(BaseModel):
    completed: bool


class ReviewRequest(BaseModel):
    period: Literal["daily", "weekly", "topic"] = "weekly"


class ReportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=2000)
    collection_id: str | None = None

