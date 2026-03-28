"""Context bus for managing conversation state across model switches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Turn:
    """Single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    model: Optional[str] = None
    phase: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class ContextBus:
    """Manages conversation context across SDLC phases and model switches.
    
    Maintains a sliding window of recent turns (max_turns) and
    optionally tracks the current file and task context.
    """
    
    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
        self._turns: list[Turn] = []
        self._file_path: Optional[str] = None
        self._task: Optional[str] = None
    
    def set_file(self, path: str) -> None:
        """Set the current file context."""
        self._file_path = path
    
    def set_task(self, task: str) -> None:
        """Set the current task description."""
        self._task = task
    
    def push(
        self,
        role: str,
        content: str,
        model: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Add a new turn to the context."""
        turn = Turn(role=role, content=content, model=model, phase=phase)
        self._turns.append(turn)
        
        # Keep only the most recent turns
        if len(self._turns) > self.max_turns * 2:  # user + assistant pairs
            self._turns = self._turns[-self.max_turns * 2:]
    
    def to_messages(self) -> list[dict]:
        """Convert turns to message list for API calls."""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self._turns
        ]
    
    def to_system_prompt_suffix(self) -> str:
        """Generate context suffix for system prompt."""
        parts = []
        
        if self._file_path:
            parts.append(f"Current file: {self._file_path}")
        
        if self._task:
            parts.append(f"Task: {self._task}")
        
        if self._turns:
            # Summarize recent conversation
            recent = self._turns[-min(2, len(self._turns)):]
            if recent:
                parts.append("Recent context:")
                for turn in recent:
                    preview = turn.content[:100] + "..." if len(turn.content) > 100 else turn.content
                    parts.append(f"  [{turn.role}] {preview}")
        
        if parts:
            return "\n\nContext:\n" + "\n".join(parts)
        return ""
    
    def clear(self) -> None:
        """Clear all context."""
        self._turns = []
        self._file_path = None
        self._task = None
    
    def get_stats(self) -> dict:
        """Get context statistics."""
        return {
            "turns": len(self._turns),
            "max_turns": self.max_turns,
            "file": self._file_path,
            "task": self._task,
        }
