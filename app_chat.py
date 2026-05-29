from __future__ import annotations

import subprocess
import sys
import uuid
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parent
LAST_ANSWER = PROJECT_ROOT / "data" / "extracted" / "last_answer.md"
MAP_EMBED_RE = re.compile(r"<!--MAP_EMBED_URL:(.*?)-->")


st.set_page_config(
    page_title="Indian Heritage AI Chat",
    page_icon="IH",
    layout="wide",
)


def run_agent(question: str, page_limit: int, session_id: str, memory_enabled: bool) -> tuple[str, str]:
    command = [
        sys.executable,
        "scripts/heritage_agent.py",
        question,
        "--page-limit",
        str(page_limit),
        "--session-id",
        session_id,
    ]
    if not memory_enabled:
        command.append("--no-memory")

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=240,
    )
    output = "\n".join(part for part in [result.stdout, result.stderr] if part.strip())
    if result.returncode != 0:
        return (
            "The local agent could not complete the request.\n\n"
            f"```text\n{output[-4000:]}\n```",
            output,
        )

    marker = "\nAnswer:\n"
    if marker in output:
        answer = output.split(marker, 1)[1]
        answer = answer.split("\nSaved result to ", 1)[0].strip()
    elif LAST_ANSWER.exists():
        answer = LAST_ANSWER.read_text(encoding="utf-8", errors="replace")
    else:
        answer = output.strip()
    return answer, output


def reset_chat() -> None:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Ask a question about Indian archaeology, heritage sources, GIS/satellite links, "
                "excavation reports, manuscripts, monuments, or the source database."
            ),
        }
    ]


def clear_memory(session_id: str) -> str:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/manage_conversation_memory.py",
            "--session-id",
            session_id,
            "--clear",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return "\n".join(part for part in [result.stdout, result.stderr] if part.strip())


def render_answer(answer: str) -> None:
    match = MAP_EMBED_RE.search(answer)
    cleaned_answer = MAP_EMBED_RE.sub("", answer).strip()
    st.markdown(cleaned_answer)
    if match:
        embed_url = match.group(1).strip()
        components.html(
            f"""
            <iframe
              title="Interactive heritage map"
              src="{embed_url}"
              width="100%"
              height="460"
              style="border:1px solid #c9c9c9; border-radius:8px;"
              loading="lazy">
            </iframe>
            """,
            height=480,
        )


st.title("Indian Heritage AI Chat")
st.caption("Local RAG chat with question routing, conversation memory, citations, source links, and archaeology safety rules.")

if "session_id" not in st.session_state:
    st.session_state.session_id = f"chat-{uuid.uuid4().hex[:12]}"

with st.sidebar:
    st.header("Chat Settings")
    page_limit = st.slider("Retrieved chunks", min_value=1, max_value=10, value=5)
    memory_enabled = st.toggle("Conversation memory", value=True)
    show_debug = st.toggle("Show route/debug output", value=False)
    if st.button("Clear Chat"):
        reset_chat()
        st.rerun()
    if st.button("Clear Memory"):
        output = clear_memory(st.session_state.session_id)
        st.session_state.memory_notice = output or "Conversation memory cleared."
        reset_chat()
        st.rerun()
    st.divider()
    st.caption(f"Memory session: `{st.session_state.session_id}`")
    st.caption("Answers are generated from local sources and end with citations when sources are available.")

if "messages" not in st.session_state:
    reset_chat()

if st.session_state.get("memory_notice"):
    st.info(st.session_state.pop("memory_notice"))

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_answer(message["content"])
        else:
            st.markdown(message["content"])
        if show_debug and message.get("debug"):
            with st.expander("Route and retrieval output"):
                st.code(message["debug"][-6000:], language="text")

question = st.chat_input("Ask about Hampi, ASI reports, GIS maps, excavation evidence...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching sources and preparing answer..."):
            answer, debug = run_agent(
                question,
                page_limit=page_limit,
                session_id=st.session_state.session_id,
                memory_enabled=memory_enabled,
            )
        render_answer(answer)
        if show_debug:
            with st.expander("Route and retrieval output"):
                st.code(debug[-6000:], language="text")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "debug": debug,
        }
    )
