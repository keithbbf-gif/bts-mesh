"""
bts_mcp.py — BUILD-4. MCP-style tool definitions for the mesh's actions.

SGH's mine ranked MCP #1 ("highest leverage"): "Standardized way to expose tools,
resources and prompts to LLMs with clear schemas. Foundation for reusable, discoverable
skills both SGH and COWORK can register and call."

THE PROBLEM THIS SOLVES. Right now every node learns what it can do from PROSE in a
seed file ("write a file into BTS_SGH_Handoff, prepend a header, append a signal
line..."). Prose is not checkable. It is exactly why GBW invented its own handoff header
and shipped a verify() that could never pass — nothing machine-readable told it the
shape. Tool definitions replace prose with schema:

    ONE definition  ->  runtime dispatch (call it)          [execute()]
                    ->  JSON Schema      (validate it)      [tool_schemas()]
                    ->  the node's brief  (describe it)     [render_brief()]

Add a capability once, and every node learns it, can call it, and gets validated.

The action surface (deliberately small — these are the mesh's real verbs):
    gdx_put            upload a deliverable to the shared Drive folder (atomic)
    gdx_verify         byte-compare an upload (the no-fake-DONE guard)
    signal_append      put one line on the bus
    signal_read        read new signals (per-reader cursor)
    gate_raise         NEEDS_INPUT: halt and surface to Keith
    gate_list          what is currently blocking the mesh
    handoff_header     render the mandatory 3-field header

Emits standard MCP `tools/list` shape, so this drops straight into a real MCP server
(or any function-calling API) without rework.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bts_bus  # noqa: E402

LOG_PATH = os.path.join(HERE, "BTS_SIGNAL.log")

# --------------------------------------------------------------------------
# TOOL DEFINITIONS — the single source of truth.
# --------------------------------------------------------------------------

TOOLS = [
    {
        "name": "gdx_put",
        "description": (
            "Upload a deliverable into the shared GDX Drive folder (BTS_SGH_Handoff). "
            "Atomic: uploads under a temp name then renames, so a reader never sees a "
            "half-written file. Prepends the 3-field handoff header if absent, and "
            "appends a NEW_OUTPUT_READY signal to the bus. Returns the Drive file id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "local_path": {"type": "string", "description": "Path to the file to upload."},
                "note": {
                    "type": "string",
                    "description": "One sentence. Becomes the header SUMMARY. "
                                   "You MUST pass the same note to gdx_verify.",
                },
            },
            "required": ["local_path", "note"],
        },
    },
    {
        "name": "gdx_verify",
        "description": (
            "Download an uploaded file and BYTE-COMPARE it against the expected bytes. "
            "This is the no-fake-DONE guard: a claim of success must be provable. "
            "`note` MUST match the note used with gdx_put or the compare will fail."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Drive file id returned by gdx_put."},
                "local_path": {"type": "string", "description": "The local source file."},
                "note": {"type": "string", "description": "The SAME note used with gdx_put."},
            },
            "required": ["file_id", "local_path", "note"],
        },
    },
    {
        "name": "signal_append",
        "description": (
            "Append one author-prefixed line to the append-only bus log. Heavy content "
            "never rides in a signal — write a file and point `path` at it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["COWORK", "SGH", "GBW", "GEM", "COPILOT", "CLA"]},
                "type": {
                    "type": "string",
                    "enum": sorted(bts_bus.VALID_TYPES),
                    "description": "NEW_OUTPUT_READY and QUESTION_FOR_YOU require `path`.",
                },
                "note": {"type": "string", "description": "One sentence."},
                "path": {
                    "type": "string",
                    "description": "ROLD-relative path to the payload. No drive letters.",
                },
            },
            "required": ["agent", "type", "note"],
        },
    },
    {
        "name": "signal_read",
        "description": (
            "Read signals appended since this reader last looked (per-reader cursor). "
            "Self-filtering: a node never consumes its own signals."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mine": {"type": "string", "description": "Your agent code, to filter out your own lines."},
            },
            "required": ["mine"],
        },
    },
    {
        "name": "gate_raise",
        "description": (
            "NEEDS_INPUT. Halt the mesh and surface a question to Keith. Use this when a "
            "decision is genuinely his (credentials, sharing, scope). Do NOT guess to "
            "appear helpful — a wrong guess costs more than a pause. Durable: survives a restart."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "question": {"type": "string", "description": "The decision only a human can make."},
            },
            "required": ["agent", "question"],
        },
    },
    {
        "name": "gate_list",
        "description": "List open gates — i.e. what is currently blocking the mesh.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "handoff_header",
        "description": (
            "Render the mandatory 3-field handoff header that EVERY deliverable must "
            "start with. Do not invent your own header format."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "One sentence: what was delivered."},
                "open_questions": {
                    "type": "array", "items": {"type": "string"}, "maxItems": 3,
                },
                "confidence": {
                    "type": "string", "enum": ["[V]", "[G]", "[P]"],
                    "description": "[V] verified / [G] good-but-unverified / [P] provisional",
                },
            },
            "required": ["summary"],
        },
    },
]


def tool_schemas() -> list:
    """Standard MCP `tools/list` payload."""
    return TOOLS


# --------------------------------------------------------------------------
# DISPATCH — the same definitions, executable.
# --------------------------------------------------------------------------

def execute(name: str, args: dict):
    if name == "gdx_put":
        import bts_gdx
        return {"file_id": bts_gdx.put(args["local_path"], args.get("note", ""))}

    if name == "gdx_verify":
        import bts_gdx
        ok = bts_gdx.verify(args["file_id"], args["local_path"], args.get("note", ""))
        return {"verified": bool(ok)}

    if name == "signal_append":
        env = bts_bus.make_envelope(args["type"], args["note"], args.get("path"))
        bts_bus.append_signal(LOG_PATH, args["agent"], env)
        return {"appended": env}

    if name == "signal_read":
        cur = os.path.join(HERE, f".cursor_{args['mine'].lower()}")
        return {"signals": bts_bus.read_new_signals(LOG_PATH, cur, mine=args["mine"])}

    if name == "gate_raise":
        import bts_gate
        return {"gate": bts_gate.raise_gate(args["agent"], args["question"])}

    if name == "gate_list":
        import bts_gate
        return {"open_gates": bts_gate.open_gates()}

    if name == "handoff_header":
        try:
            from bts_schemas import HandoffHeader
            return {"header": HandoffHeader(
                summary=args["summary"],
                open_questions=args.get("open_questions", []),
                confidence=args.get("confidence", "[G]"),
            ).render()}
        except ImportError:
            q = "\n".join(f"- {x}" for x in args.get("open_questions", [])) or "- None"
            return {"header": (
                "<!-- HANDOFF HEADER -->\n"
                f"**SUMMARY:** {args['summary']}\n"
                "**OPEN_QUESTIONS:**\n"
                f"{q}\n"
                f"**CONFIDENCE:** {args.get('confidence', '[G]')}\n---\n"
            )}

    raise KeyError(f"unknown tool {name!r}. Known: {[t['name'] for t in TOOLS]}")


# --------------------------------------------------------------------------
# The SAME definitions, rendered as a node's brief. Prose stops drifting from code.
# --------------------------------------------------------------------------

def render_brief(agent: str) -> str:
    lines = [
        f"You are {agent}, a node of Keith's BTS mesh.",
        "",
        "You have these tools. Use them instead of improvising your own conventions:",
        "",
    ]
    for t in TOOLS:
        req = t["inputSchema"].get("required", [])
        lines.append(f"* {t['name']}({', '.join(req)})")
        lines.append(f"    {t['description']}")
    lines += [
        "",
        "HARD RULES:",
        "  1. NO FAKE-DONE. Never claim done until gdx_verify has actually returned true.",
        "  2. If blocked on a human decision, call gate_raise and STOP. Do not guess.",
        "  3. Never invent a handoff header — call handoff_header.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "brief":
        print(render_brief(sys.argv[2] if len(sys.argv) > 2 else "NODE"))
    else:
        print(json.dumps({"tools": tool_schemas()}, indent=2))
