"""
bts_schemas.py — BUILD-3. Typed, validated schemas for the BTS bus (contract v1.2).

SGH's GitHub mine ranked Pydantic #2: "Pydantic models auto-generate clean, validated
tool schemas." That is the actual payoff here — these models are the single source of
truth for BOTH runtime validation AND the JSON-Schema that bts_mcp.py hands to the
nodes. Define the envelope once; the tool schema falls out of it.

bts_bus.py already hand-validates. This does not replace it — bts_bus stays pure-stdlib
so it can never break. This module is the strict, typed layer on top:
  - Signal      : the {type, path, note, ts} envelope, with the REQUIRE_PATH rule enforced
  - HandoffHeader: the 3-field SUMMARY / OPEN_QUESTIONS / CONFIDENCE header
  - json_schema(): emits JSON Schema for the MCP layer

Graceful: if pydantic is somehow absent, falls back to bts_bus's stdlib validation so
nothing in the mesh hard-fails on an import.
"""
from __future__ import annotations

import datetime
import re
from typing import List, Literal, Optional

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    _HAVE_PYDANTIC = True
except ImportError:  # pragma: no cover - mesh must never hard-fail on a missing dep
    _HAVE_PYDANTIC = False


SignalType = Literal[
    "NEW_OUTPUT_READY",   # producer staged content at `path`
    "QUESTION_FOR_YOU",   # producer needs consumer input
    "NEEDS_INPUT",        # blocked; needs a HUMAN decision -> surface to Keith
    "TASK_COMPLETE",      # batch done
    "ACK",                # consumer processed a prior signal
    "SPAWN_SESSION",      # orchestrator: launch + seed a new session
    "STATUS",             # non-blocking progress
    "ERROR",              # node error -> dead-letter
]

# Only these two carry a payload the consumer must go read.
REQUIRE_PATH = {"NEW_OUTPUT_READY", "QUESTION_FOR_YOU"}

AGENTS = ("COWORK", "SGH", "GBW", "GEM", "COPILOT", "CLA")

Confidence = Literal["[V]", "[G]", "[P]"]  # verified / good-but-unverified / provisional


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if _HAVE_PYDANTIC:

    class Signal(BaseModel):
        """One line on the BTS bus. Serialises to exactly the contract envelope."""

        type: SignalType
        note: str = Field(min_length=1, description="One sentence, human-readable.")
        path: Optional[str] = Field(
            default=None,
            description="ROLD-relative path to the payload. Required for "
                        "NEW_OUTPUT_READY and QUESTION_FOR_YOU. No drive letters.",
        )
        ts: str = Field(default_factory=utc_now, description="ISO-8601 UTC.")

        @field_validator("path")
        @classmethod
        def _no_absolute_paths(cls, v: Optional[str]) -> Optional[str]:
            # Contract: paths are ROLD-relative. An absolute path means the producer
            # is leaking its own filesystem layout into the bus.
            if v and (re.match(r"^[A-Za-z]:[\\/]", v) or v.startswith(("/", "\\"))):
                raise ValueError(f"path must be ROLD-relative, got absolute: {v!r}")
            return v

        @field_validator("ts")
        @classmethod
        def _iso_utc(cls, v: str) -> str:
            try:
                datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"ts must be ISO-8601 UTC, got {v!r}")
            return v

        @model_validator(mode="after")
        def _path_required(self):
            if self.type in REQUIRE_PATH and not self.path:
                raise ValueError(f"type {self.type} requires a `path`")
            return self

        def to_line(self, agent: str) -> str:
            """Render the author-prefixed append-only log line."""
            agent = (agent or "?").upper()[:8]
            return f"{agent}|{self.model_dump_json()}\n"

    class HandoffHeader(BaseModel):
        """The 3-field header every deliverable must start with (contract v1.2)."""

        summary: str = Field(min_length=1)
        open_questions: List[str] = Field(default_factory=list, max_length=3)
        confidence: Confidence = "[G]"

        def render(self) -> str:
            q = "\n".join(f"- {x}" for x in self.open_questions) or "- None"
            return (
                "<!-- HANDOFF HEADER -->\n"
                f"**SUMMARY:** {self.summary}\n"
                "**OPEN_QUESTIONS:**\n"
                f"{q}\n"
                f"**CONFIDENCE:** {self.confidence}\n"
                "---\n"
            )

        @staticmethod
        def present_in(content: str) -> bool:
            """R5: check the START of the file, not a substring anywhere in it.
            A plain `in content` test misreads any doc that merely MENTIONS the marker."""
            return content.lstrip().startswith("<!-- HANDOFF HEADER -->")

    def json_schema() -> dict:
        """JSON Schema for the Signal envelope — consumed by bts_mcp.py."""
        return Signal.model_json_schema()

    def validate(env: dict) -> "Signal":
        return Signal(**env)

else:  # pragma: no cover

    def validate(env: dict):
        from bts_bus import validate_envelope
        validate_envelope(env)
        return env

    def json_schema() -> dict:
        return {"type": "object", "note": "pydantic unavailable; stdlib validation only"}
