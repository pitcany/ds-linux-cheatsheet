"""Pydantic data models for command entries."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Example(BaseModel):
    """A concrete, runnable example for a command entry."""

    description: str = Field(..., min_length=1)
    command: str = Field(..., min_length=1)


class CommandEntry(BaseModel):
    """A single cheat sheet entry."""

    id: str = Field(..., min_length=1, description="Stable unique identifier.")
    title: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    command: str = Field(..., min_length=1, description="Canonical command template.")
    explanation: str = Field(..., min_length=1)
    flags: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)
    gotchas: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    dangerous: bool = False

    @field_validator("tags", "flags", "gotchas")
    @classmethod
    def _strip_strings(cls, value: list[str]) -> list[str]:
        return [v.strip() for v in value if v and v.strip()]

    @property
    def search_text(self) -> str:
        """Flat haystack for keyword matching."""
        parts = [
            self.title,
            self.category,
            self.command,
            self.explanation,
            " ".join(self.tags),
            " ".join(self.flags),
            " ".join(e.description for e in self.examples),
            " ".join(e.command for e in self.examples),
        ]
        return " ".join(parts).lower()


class CommandFile(BaseModel):
    """Top-level YAML file model."""

    category: str = Field(..., min_length=1)
    commands: list[CommandEntry] = Field(default_factory=list)
