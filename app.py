from __future__ import annotations

import csv
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from admin_auth import change_password, ensure_auth_file, verify_login  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"
VECTOR_DB = PROJECT_ROOT / "data" / "vector_store" / "heritage_vectors.sqlite"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
ACCESSIBILITY_RULES = PROJECT_ROOT / "docs" / "end_user_accessibility_rules.md"
BACKUP_DIR = PROJECT_ROOT / "metadata" / "backups"


st.set_page_config(page_title="Indian Heritage AI Admin", page_icon="IH", layout="wide")


def require_login() -> None:
    auth = ensure_auth_file()
    st.session_state.setdefault("admin_authenticated", False)
    st.session_state.setdefault("admin_username", "")

    if st.session_state["admin_authenticated"]:
        with st.sidebar:
            st.caption(f"Signed in as `{st.session_state['admin_username']}`")
            if st.button("Logout"):
                st.session_state["admin_authenticated"] = False
                st.session_state["admin_username"] = ""
                st.rerun()
        return

    st.title("Indian Heritage AI Admin")
    st.subheader("Admin Login")
    if auth.get("must_change_password"):
        st.warning("Default admin password is active. Sign in with admin/admin and change it from the Admin tab.")

    with st.form("admin_login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if verify_login(username, password):
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_username"] = username
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.info("Password reset is local: run `run_reset_admin_password.bat` to reset back to admin/admin.")
    st.stop()


require_login()


def load_links() -> pd.DataFrame:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    df = pd.DataFrame(rows)
    for column in ["is_new", "added_at", "discovered_from"]:
        if column not in df.columns:
            df[column] = ""
    if not df.empty:
        df["_new_rank"] = df["is_new"].fillna("").astype(str).str.lower().eq("yes").astype(int)
        df["_added_rank"] = pd.to_datetime(df["added_at"], errors="coerce", utc=True)
        df = df.sort_values(["_new_rank", "_added_rank"], ascending=[False, False], na_position="last")
        df = df.drop(columns=["_new_rank", "_added_rank"])
    return df


@st.cache_data
def load_vector_stats() -> dict:
    if not VECTOR_DB.exists():
        return {"exists": False, "chunks": 0, "models": {}, "sources": {}}

    connection = sqlite3.connect(VECTOR_DB)
    connection.row_factory = sqlite3.Row
    chunks = connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"]
    models = {
        row["embedding_model"]: row["count"]
        for row in connection.execute(
            """
            SELECT embedding_model, COUNT(*) AS count
            FROM chunks
            GROUP BY embedding_model
            ORDER BY count DESC
            """
        )
    }
    sources = {
        row["title"]: row["count"]
        for row in connection.execute(
            """
            SELECT title, COUNT(*) AS count
            FROM chunks
            GROUP BY title
            ORDER BY count DESC
            LIMIT 20
            """
        )
    }
    connection.close()
    return {"exists": True, "chunks": chunks, "models": models, "sources": sources}


def run_script(args: list[str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def show_result(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0:
        st.success("Command completed.")
    else:
        st.error(f"Command failed with exit code {result.returncode}.")

    output = "\n".join(part for part in [result.stdout, result.stderr] if part.strip())
    if output:
        st.code(output[-8000:], language="text")

    load_vector_stats.clear()


def counter_for(df: pd.DataFrame, column: str) -> Counter:
    if column not in df.columns or df.empty:
        return Counter()
    return Counter(value or "blank" for value in df[column].fillna("").astype(str))


def read_log(name: str, lines: int = 80) -> str:
    path = LOG_DIR / name
    if not path.exists():
        return "Log file not found yet."
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:])


def read_rules() -> str:
    if not ACCESSIBILITY_RULES.exists():
        return "Accessibility rules file not found."
    return ACCESSIBILITY_RULES.read_text(encoding="utf-8")


def list_csv_backups() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("heritage_links_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)


def filtered_links(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.header("Filters")
        query = st.text_input("Search", placeholder="ASI, Hampi, manuscript, GIS...")

        def options(column: str) -> list[str]:
            if column not in df.columns:
                return []
            return sorted(value for value in df[column].dropna().astype(str).unique() if value)

        statuses = st.multiselect("Status", options("status"))
        priorities = st.multiselect("Priority", options("priority"))
        source_types = st.multiselect("Source type", options("source_type"))
        document_categories = st.multiselect("Document category", options("document_category"))
        usable = st.multiselect("Usable for RAG", options("usable_for_rag"))
        new_only = st.checkbox("New sources only")

    filtered = df.copy()
    if query:
        q = query.lower()
        searchable_columns = [
            "title",
            "category",
            "region",
            "source",
            "link",
            "notes",
            "source_type",
            "document_category",
            "priority",
        ]
        available = [column for column in searchable_columns if column in filtered.columns]
        mask = filtered[available].fillna("").astype(str).agg(" ".join, axis=1).str.lower().str.contains(q)
        filtered = filtered[mask]

    for column, selected in [
        ("status", statuses),
        ("priority", priorities),
        ("source_type", source_types),
        ("document_category", document_categories),
        ("usable_for_rag", usable),
    ]:
        if selected and column in filtered.columns:
            filtered = filtered[filtered[column].isin(selected)]

    if new_only and "is_new" in filtered.columns:
        filtered = filtered[filtered["is_new"].fillna("").astype(str).str.lower() == "yes"]

    return filtered


df = load_links()
vector_stats = load_vector_stats()

st.title("Indian Heritage AI Admin")
st.caption("Manage links, validation, source quality, PDF ingestion, embeddings, and retrieval memory.")

if df.empty:
    st.warning("No links found in metadata/heritage_links.csv.")
    st.stop()

filtered = filtered_links(df)

status_counts = counter_for(df, "status")
quality_counts = counter_for(df, "usable_for_rag")
priority_counts = counter_for(df, "priority")
document_category_counts = counter_for(df, "document_category")
new_count = int((df["is_new"].fillna("").astype(str).str.lower() == "yes").sum()) if "is_new" in df.columns else 0

gis_terms = "gis|map|mapping|geospatial|satellite|remote sensing|earth observation|bhuvan|bhoonidhi|vedas|mosdac|nrsc|isro|earthdata|copernicus|opentopography|sentinel|landsat|uav"
gis_scan_columns = [column for column in ["title", "category", "source", "link", "notes", "source_type"] if column in df.columns]
gis_mask = df[gis_scan_columns].fillna("").astype(str).agg(" ".join, axis=1).str.contains(
    gis_terms,
    case=False,
    regex=True,
)
gis_count = int(gis_mask.sum())

metric_cols = st.columns(9)
metric_cols[0].metric("Links", len(df))
metric_cols[1].metric("Visible", len(filtered))
metric_cols[2].metric("Pending", status_counts.get("pending", 0))
metric_cols[3].metric("Verified/PDF", status_counts.get("verified", 0) + status_counts.get("pdf", 0))
metric_cols[4].metric("Usable RAG", quality_counts.get("yes", 0))
metric_cols[5].metric("GIS/Sat", gis_count)
metric_cols[6].metric("Doc Categories", len(document_category_counts))
metric_cols[7].metric("New", new_count)
metric_cols[8].metric("Vector Chunks", vector_stats["chunks"])

tabs = st.tabs(["Overview", "Links", "Categories", "GIS/Satellite", "Rules", "Actions", "Vector DB", "Logs", "Admin"])

with tabs[0]:
    left, middle, right = st.columns(3)
    with left:
        st.subheader("Validation Status")
        st.bar_chart(pd.DataFrame(status_counts.items(), columns=["status", "count"]), x="status", y="count")
    with middle:
        st.subheader("RAG Usability")
        st.bar_chart(pd.DataFrame(quality_counts.items(), columns=["usable_for_rag", "count"]), x="usable_for_rag", y="count")
    with right:
        st.subheader("Priority")
        st.bar_chart(pd.DataFrame(priority_counts.items(), columns=["priority", "count"]), x="priority", y="count")

    st.subheader("Document Categories")
    category_df = pd.DataFrame(document_category_counts.items(), columns=["document_category", "count"])
    if not category_df.empty:
        category_df = category_df.sort_values("count", ascending=False)
        st.bar_chart(category_df, x="document_category", y="count")

    if new_count:
        st.subheader("New Sources")
        new_df = df[df["is_new"].fillna("").astype(str).str.lower() == "yes"].head(25)
        new_columns = [
            column
            for column in [
                "is_new",
                "added_at",
                "title",
                "source",
                "category",
                "document_category",
                "status",
                "link",
                "discovered_from",
            ]
            if column in new_df.columns
        ]
        st.dataframe(
            new_df[new_columns],
            use_container_width=True,
            hide_index=True,
            column_config={"link": st.column_config.LinkColumn("link")},
        )

with tabs[1]:
    st.subheader("Source Database")
    display_columns = [
        column
        for column in [
            "title",
            "is_new",
            "added_at",
            "category",
            "region",
            "source",
            "status",
            "source_type",
            "document_category",
            "category_confidence",
            "trust_score",
            "usable_for_rag",
            "priority",
            "last_checked",
            "final_url",
            "replacement_link",
            "replacement_status",
            "replacement_checked",
            "discovered_from",
            "link",
            "notes",
        ]
        if column in filtered.columns
    ]
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("link")},
    )
    st.download_button(
        "Download filtered CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        "heritage_links_filtered.csv",
        "text/csv",
    )

with tabs[2]:
    st.subheader("Document Categories")
    category_df = pd.DataFrame(document_category_counts.items(), columns=["document_category", "count"])
    if category_df.empty:
        st.info("Document categories have not been generated yet.")
    else:
        category_df = category_df.sort_values("count", ascending=False)
        st.dataframe(category_df, use_container_width=True, hide_index=True)

    selected_category = st.selectbox(
        "Inspect category",
        ["All", *category_df["document_category"].tolist()] if not category_df.empty else ["All"],
    )
    category_rows = df if selected_category == "All" else df[df["document_category"] == selected_category]
    category_display_columns = [
        column
        for column in [
            "title",
            "document_category",
            "category_confidence",
            "category",
            "region",
            "source",
            "status",
            "link",
            "notes",
        ]
        if column in category_rows.columns
    ]
    st.dataframe(
        category_rows[category_display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("link")},
    )

with tabs[3]:
    st.subheader("GIS, Satellite, Remote Sensing, and Mapping Sources")
    gis_df = df[gis_mask].copy()
    st.metric("GIS/Satellite Sources", len(gis_df))

    gis_display_columns = [
        column
        for column in [
            "title",
            "category",
            "region",
            "source",
            "status",
            "source_type",
            "document_category",
            "trust_score",
            "usable_for_rag",
            "priority",
            "final_url",
            "replacement_link",
            "replacement_status",
            "link",
            "notes",
        ]
        if column in gis_df.columns
    ]
    st.dataframe(
        gis_df[gis_display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("link")},
    )

    st.download_button(
        "Download GIS/Satellite CSV",
        gis_df.to_csv(index=False).encode("utf-8"),
        "heritage_gis_satellite_links.csv",
        "text/csv",
    )

with tabs[4]:
    st.subheader("End User Accessibility And Usage Rules")
    st.markdown(read_rules())

with tabs[5]:
    st.subheader("Operations")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Validate Links**")
        validate_limit = st.number_input("Validation limit", min_value=1, max_value=500, value=25)
        validate_mode = st.selectbox("Validation mode", ["pending", "stale", "broken", "redirect", "all"], index=1)
        add_replacements = st.checkbox("Add redirect/replacement rows", value=True)
        if st.button("Run Validation"):
            args = [
                "scripts/validate_links.py",
                "--mode",
                validate_mode,
                "--limit",
                str(validate_limit),
            ]
            if add_replacements:
                args.append("--add-replacements")
            show_result(
                run_script(args)
            )

    with col2:
        st.markdown("**Quality + Discovery**")
        source_limit = st.number_input("Source pages", min_value=1, max_value=200, value=10)
        pdf_limit = st.number_input("PDFs per source", min_value=1, max_value=50, value=5)
        if st.button("Update Source Quality"):
            show_result(run_script(["scripts/update_source_quality.py"]))
        if st.button("Update Document Categories"):
            show_result(run_script(["scripts/update_document_categories.py"]))
        if st.button("Repair Broken/Redirects"):
            show_result(
                run_script(
                    [
                        "scripts/validate_links.py",
                        "--mode",
                        "broken",
                        "--limit",
                        str(source_limit),
                        "--add-replacements",
                    ]
                )
            )
            show_result(
                run_script(
                    [
                        "scripts/validate_links.py",
                        "--mode",
                        "redirect",
                        "--limit",
                        str(source_limit),
                        "--add-replacements",
                    ]
                )
            )
        if st.button("Discover PDFs"):
            show_result(
                run_script(
                    [
                        "scripts/discover_pdfs.py",
                        "--source-limit",
                        str(source_limit),
                        "--pdf-limit-per-source",
                        str(pdf_limit),
                    ]
                )
            )
        new_source_limit = st.number_input("New links per source", min_value=1, max_value=100, value=10)
        if st.button("Discover New Online Sources"):
            show_result(
                run_script(
                    [
                        "scripts/discover_new_sources.py",
                        "--per-seed-limit",
                        str(new_source_limit),
                    ]
                )
            )
        if st.button("Add Archaeology Sources"):
            show_result(run_script(["scripts/add_indian_archaeology_sources.py"]))
        if st.button("Add GIS/Satellite Sources"):
            show_result(run_script(["scripts/add_gis_satellite_sources.py"]))

    with col3:
        st.markdown("**Embeddings + Pipeline**")
        embed_limit = st.number_input("PDF embed limit", min_value=1, max_value=100, value=10)
        append_embeddings = st.checkbox("Append/update embeddings", value=True)
        if st.button("Build Embeddings"):
            args = ["scripts/build_embeddings.py", "--limit", str(embed_limit)]
            if append_embeddings:
                args.append("--append")
            show_result(run_script(args, timeout=1800))
        if st.button("Run Auto-Ingest"):
            show_result(
                run_script(
                    [
                        "scripts/auto_ingest_pipeline.py",
                        "--validate-limit",
                        str(validate_limit),
                        "--source-limit",
                        str(source_limit),
                        "--pdf-limit-per-source",
                        str(pdf_limit),
                        "--embed-limit",
                        str(embed_limit),
                    ],
                    timeout=2400,
                )
            )

with tabs[6]:
    st.subheader("Vector Memory")
    if not vector_stats["exists"]:
        st.info("Vector DB has not been built yet.")
    else:
        left, right = st.columns(2)
        with left:
            st.metric("Chunks", vector_stats["chunks"])
            st.write("Embedding models")
            st.dataframe(
                pd.DataFrame(vector_stats["models"].items(), columns=["model", "chunks"]),
                hide_index=True,
                use_container_width=True,
            )
        with right:
            st.write("Top embedded sources")
            st.dataframe(
                pd.DataFrame(vector_stats["sources"].items(), columns=["source", "chunks"]),
                hide_index=True,
                use_container_width=True,
            )

        st.markdown("**Test Search**")
        question = st.text_input("Search vector DB", placeholder="What monuments survive at Hampi?")
        top_k = st.number_input("Top K", min_value=1, max_value=20, value=5)
        if st.button("Search Memory") and question:
            result = run_script(["scripts/search_embeddings.py", question, "--top-k", str(top_k)])
            show_result(result)
            st.caption("Search results use webpage/PDF ingestion plus auto-reranking: semantic score + source quality + keyword match + document category fit + source diversity.")

with tabs[7]:
    st.subheader("Recent Logs")
    log_name = st.selectbox(
        "Log file",
        ["link_validation.log", "pdf_discovery.log", "auto_ingest.log"],
    )
    st.code(read_log(log_name), language="text")

with tabs[8]:
    st.subheader("Admin Account")
    st.write("Use this section to change the dashboard password.")
    with st.form("change_admin_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        change_submitted = st.form_submit_button("Change Password")

    if change_submitted:
        if not new_password or new_password != confirm_password:
            st.error("New passwords do not match.")
        else:
            ok, message = change_password(current_password, new_password)
            if ok:
                st.success(message)
            else:
                st.error(message)

    st.markdown("**Reset Password**")
    st.code("run_reset_admin_password.bat", language="bat")
    st.caption("This resets the local admin account to username `admin` and password `admin`.")

    st.subheader("Source Database Recovery")
    backups = list_csv_backups()
    st.metric("CSV Backups", len(backups))
    if backups:
        backup_labels = [f"{backup.name} ({backup.stat().st_size} bytes)" for backup in backups]
        selected_backup = st.selectbox("Available backups", backup_labels)
        selected_path = backups[backup_labels.index(selected_backup)]
        st.code(str(selected_path), language="text")
        if st.button("Restore Selected CSV Backup"):
            show_result(run_script(["scripts/restore_csv_backup.py", "--backup", str(selected_path)]))
            st.warning("Backup restored. Refresh the dashboard to reload source data.")
    else:
        st.info("No CSV backups found yet.")
