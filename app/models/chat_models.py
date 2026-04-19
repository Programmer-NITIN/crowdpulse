"""
models/chat_models.py
---------------------
Pydantic schemas for the Event Assistant chatbot API.

Security bounds:
- message: 1–500 chars, stripped of leading/trailing whitespace.
- user_id: 1–64 chars.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatHistoryItem(BaseModel):
    """A single turn in the conversation history."""

    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Inbound chatbot request from an attendee."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique user identifier",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The attendee's question (1–500 chars)",
    )
    history: Optional[List[ChatHistoryItem]] = Field(
        default_factory=list,
        description="Previous conversation turns for context (max 8).",
    )

    @field_validator("message", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Strip whitespace; reject empty-after-strip strings."""
        if isinstance(v, str):
            v = v.strip()
        return v


class ChatResponse(BaseModel):
    """Response from the Event Assistant."""

    reply: str = Field(..., description="The assistant's response text")
    intent: Optional[str] = Field(
        None, description="Detected intent label (e.g. 'prohibited', 'timing')"
    )
    grounded: bool = Field(
        True,
        description="Whether the response was based on structured venue data",
    )
