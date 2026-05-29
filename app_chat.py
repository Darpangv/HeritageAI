from __future__ import annotations

import subprocess
import sys
import uuid
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from map_views import research_map_config  # noqa: E402

LAST_ANSWER = PROJECT_ROOT / "data" / "extracted" / "last_answer.md"
MAP_EMBED_RE = re.compile(r"<!--MAP_EMBED_URL:(.*?)-->")
RESEARCH_MAP_RE = re.compile(r"<!--RESEARCH_MAP_SITE:(.*?)-->")


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


def research_map_html(site_id: str) -> str:
    site = research_map_config(site_id) or research_map_config("hampi")
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        html, body, #map {{ height: 100%; margin: 0; }}
        .panel {{
          background: rgba(255, 255, 255, 0.94);
          border: 1px solid #bbb;
          border-radius: 6px;
          box-shadow: 0 1px 8px rgba(0,0,0,.18);
          color: #222;
          font: 13px/1.35 system-ui, -apple-system, Segoe UI, sans-serif;
          max-width: 310px;
          padding: 10px 12px;
        }}
        .panel h3 {{ font-size: 14px; margin: 0 0 6px; }}
        .panel ul {{ margin: 6px 0 0 18px; padding: 0; }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script>
        const map = L.map('map').setView([{site["lat"]}, {site["lon"]}], {site["zoom"]});
        const satellite = L.tileLayer(
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
          {{ attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics, and contributors' }}
        );
        const osm = L.tileLayer(
          'https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
          {{ attribution: '&copy; OpenStreetMap contributors' }}
        );
        const topo = L.tileLayer(
          'https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png',
          {{ attribution: 'Map data &copy; OpenStreetMap contributors, SRTM | OpenTopoMap' }}
        );
        satellite.addTo(map);

        const marker = L.marker([{site["lat"]}, {site["lon"]}]).bindPopup('{site["name"]}');
        const studyArea = L.circle([{site["lat"]}, {site["lon"]}], {{
          radius: {site["study_radius_m"]},
          color: '#b3261e',
          fillColor: '#ffcc00',
          fillOpacity: 0.12,
          weight: 2
        }}).bindPopup('Approximate research study area for contextual landscape review');
        marker.addTo(map);
        studyArea.addTo(map);

        L.control.layers(
          {{ 'Satellite imagery': satellite, 'OpenStreetMap basemap': osm, 'Topographic basemap': topo }},
          {{ 'Public site marker': marker, 'Approximate study area': studyArea }},
          {{ collapsed: false }}
        ).addTo(map);

        const info = L.control({{ position: 'bottomleft' }});
        info.onAdd = function () {{
          const div = L.DomUtil.create('div', 'panel');
          div.innerHTML = `
            <h3>Research Map: {site["name"]}</h3>
            <div>Use this as a visual workspace, then confirm evidence through official GIS/satellite portals and published archaeology sources.</div>
            <ul>
              <li>Satellite context</li>
              <li>Topographic context</li>
              <li>Approximate study area</li>
              <li>Public site marker</li>
            </ul>
          `;
          return div;
        }};
        info.addTo(map);
      </script>
    </body>
    </html>
    """


def render_answer(answer: str) -> None:
    match = MAP_EMBED_RE.search(answer)
    research_match = RESEARCH_MAP_RE.search(answer)
    cleaned_answer = RESEARCH_MAP_RE.sub("", MAP_EMBED_RE.sub("", answer)).strip()
    st.markdown(cleaned_answer)
    if research_match:
        components.html(research_map_html(research_match.group(1).strip()), height=540)
    elif match:
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
