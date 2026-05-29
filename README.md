# Indian Heritage AI

Explore Indian heritage with AI. Search, learn, and discover history, archaeology, architecture, and cultural knowledge from trusted sources.

Starter MVP for an AI + Heritage research and storytelling agent.

The first version focuses on building a reliable source database before adding RAG, embeddings, or chatbot logic.

## Project Structure

```text
Indian-Heritage-AI/
├── app.py
├── metadata/
│   └── heritage_links.csv
├── scripts/
│   ├── link_collector.py
│   └── validate_links.py
├── data/
├── docs/
└── requirements.txt
```

## Run The Link Collector

```bash
cd Indian-Heritage-AI
python scripts/link_collector.py --list
```

Add a source:

```bash
python scripts/link_collector.py --title "Example Source" --category "Archive" --region "India" --source "Example" --link "https://example.com"
```

## Validate Links

```bash
run_validate_links.bat
```

For a quick test:

```bash
run_validate_links.bat --mode pending --limit 5
```

By default validation is incremental:

```text
run_validate_links.bat
```

checks pending links plus links not checked in the last 30 days.

Modes:

```bash
run_validate_links.bat --mode pending --limit 25
run_validate_links.bat --mode stale --stale-days 30 --limit 25
run_validate_links.bat --mode broken --limit 25 --add-replacements
run_validate_links.bat --mode redirect --limit 25 --add-replacements
run_validate_links.bat --mode all
```

Run a focused repair pass for both broken and redirected links:

```bash
run_repair_links.bat
```

Broken and redirected link checks now store repair metadata in the CSV:

```text
final_url
replacement_link
replacement_status
replacement_checked
```

With `--add-replacements`, redirect targets and discovered replacement candidates are added as new `pending` rows, so the validator can verify them in a later pass without deleting the original historical link.

Validation logs are saved to:

```text
data/logs/link_validation.log
```

Install automatic daily validation on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_link_validator_schedule.ps1
```

This creates a scheduled task named `IndianHeritageAI-LinkValidation` that runs daily at 09:00 and validates up to 25 pending/stale links.
The scheduled task also uses `--add-replacements`, so redirect targets and obvious replacement candidates can be added automatically as pending rows.

Remove the schedule:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_link_validator_schedule.ps1
```

## Add Indian Archaeology Sources

Add the curated pack of Indian archaeology blogs, articles, journals, research papers, reports, and mapping projects:

```bash
run_add_indian_archaeology_sources.bat
```

The script skips links already present in `metadata/heritage_links.csv`, marks new links as `pending`, and applies source quality fields automatically. Pending links are picked up by the regular validator.

Add the curated GIS, satellite, remote-sensing, and mapping source pack:

```bash
run_add_gis_satellite_sources.bat
```

This includes Indian official geospatial portals such as Bhuvan, Bhoonidhi, VEDAS, MOSDAC, IIRS, NRSC, ISRO earth observation pages, state archaeology mapping, and global satellite datasets useful for archaeological landscape research.

Add the focused Vijayanagara / named-person knowledge pack:

```bash
run_add_vijayanagara_sources.bat
```

This adds official and scholarly sources for Hampi, Vijayanagara, Shri Krishnadevaraya, Krishna Deva Raya, Vijayanagara Research Project material, Hampi monument pages, and inscription-related sources.

Add the broader Indian dynasty/ruler knowledge pack:

```bash
run_add_dynasty_sources.bat
```

This adds source coverage and router vocabulary for major dynasties and rulers including Maurya/Ashoka, Gupta, Chola, Pallava, Chalukya, Rashtrakuta, Pandya, Satavahana, Kakatiya, Hoysala, Mughal, Maratha/Shivaji, and related monuments.

## Ask A Question

This runs your architecture:

```text
Question
-> Search heritage links database
-> Open relevant PDF URL
-> Extract relevant pages
-> GPT answer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python scripts/heritage_agent.py "Explain the architecture of Halebidu temple"
```

For the GPT step, set an API key first:

```bash
set OPENAI_API_KEY=your_api_key_here
```

Optional:

```bash
set OPENAI_MODEL=gpt-5.5
```

If `OPENAI_API_KEY` is not set, the script still searches, opens PDFs, extracts relevant pages, and prints the extracted context instead of calling GPT.

## Connect ChatGPT Brain

Set a fresh OpenAI API key locally. Do not paste it into chat or commit it to files.

PowerShell:

```powershell
$env:OPENAI_API_KEY="your_new_rotated_key_here"
$env:HERITAGE_CHAT_MODEL="gpt-5-mini"
```

Command Prompt:

```bat
set OPENAI_API_KEY=your_new_rotated_key_here
set HERITAGE_CHAT_MODEL=gpt-5-mini
```

Test only the brain connection:

```bash
run_brain_test.bat "Say hello as the Indian Heritage AI brain"
```

Run full RAG:

```bash
run_agent.bat "What monuments and structures survive at Hampi?"
```

Every agent answer uses RAG citations. Retrieved chunks are labeled as `[S1]`, `[S2]`, and so on, and the answer is instructed to cite factual claims inline, such as `[S1, page 4]`. The result also ends with a `Sources` section mapping each citation ID to the source title, page, and link.

## Answer Quality Guard

Generated RAG answers now pass through `scripts/answer_quality_guard.py` before they are saved or shown.

The guard checks:

```text
inline citation presence
unknown or invalid source IDs
factual-looking sentences without citations
short or weak retrieved context
source IDs that do not appear in retrieved context labels
citation/source text overlap
page references that do not match retrieved pages
```

It does not reject sources because of old scans, bad OCR, unknown language, damaged pages, maps, images, or archaeology-specific document quality issues. Those materials can still be valuable. When the guard finds a problem, it appends an `Answer Quality Guard` warning block to the answer so the user knows the response needs review.

Check a saved answer manually:

```bash
run_check_answer_quality.bat data/extracted/last_answer.md --source "- [S1] Example source: https://example.com"
```

Run only the citation verifier:

```bash
run_verify_citations.bat data/extracted/last_answer.md --context-file data/extracted/retrieved_context.txt --source "- [S1] Example source page 1: https://example.com"
```

The same result is saved to:

```text
data/extracted/last_answer.md
```

The brain uses `scripts/chatgpt_brain.py`, which calls the OpenAI Responses API and saves the last raw model response to:

```text
data/brain/last_brain_response.json
```

## Build Embeddings

Build a local vector store from PDF and webpage links in `metadata/heritage_links.csv`:

```bash
run_build_embeddings.bat --query "Hampi"
```

This creates:

```text
data/vector_store/heritage_chunks.jsonl
data/vector_store/heritage_vectors.sqlite
```

Search the embeddings:

```bash
run_search_embeddings.bat "What is important about Hampi heritage?"
```

Embedding search uses auto-reranking. The first pass retrieves semantically similar chunks, then reranking combines:

```text
semantic similarity
source quality score
question/source keyword overlap
document category fit
source diversity
```

Search output shows the rerank reason for each hit.

Webpage ingestion extracts cleaner text from titles, descriptions, headings, paragraphs, lists, table cells, and captions while filtering common boilerplate such as cookie/privacy/footer text. Direct PDF links are still downloaded and extracted page by page.

To keep the older PDF-only behavior:

```bash
run_build_embeddings.bat --pdf-only --limit 10
```

After the vector store exists, `run_agent.bat` will use embedding search first. If no vector store exists, it falls back to webpage/PDF search and extraction.

## Question Router

The agent routes each question before retrieval. It detects whether the question is mainly about:

```text
source inventory
GIS / satellite / maps
excavation reports
ASI annual reviews
manuscripts / inscriptions
research literature
monuments / site records
general heritage RAG
```

The route influences document-category preference, reranking, and CSV/PDF fallback search. Source inventory questions, such as link counts or broken/pending status, are answered directly from `metadata/heritage_links.csv`.

If a routed question asks for source links, for example GIS/satellite links, the agent returns a ranked source list directly from the CSV instead of forcing a PDF/vector answer.

For site feature questions such as `list out Hampi temples`, the router returns a direct monument list instead of confusing the word `list` with a request for source URLs. Source-link mode is still available when the question explicitly asks for links or sources.

Inspect a route without running the full agent:

```bash
run_inspect_question_route.bat "List GIS satellite mapping sources for archaeology"
```

## End User Accessibility Rules

End-user answer and usage constraints are defined in:

```text
docs/end_user_accessibility_rules.md
```

The rules require clear language, short scannable answers, inline citations, source links, uncertainty when evidence is weak, and careful handling of archaeology-sensitive content. The agent refuses requests involving illegal digging, artifact removal, trafficking, trespass, or exposing vulnerable site access details.

The Admin Dashboard includes a `Rules` tab showing the active rules.

## Admin Dashboard Login

The Admin Dashboard requires login.

Default credentials:

```text
username: admin
password: admin
```

After login, open the `Admin` tab to change the password. The password is stored locally as a salted hash in:

```text
data/config/admin_auth.json
```

Reset the password back to `admin/admin`:

```bash
run_reset_admin_password.bat
```

Set a specific reset password:

```bash
run_reset_admin_password.bat new_password_here
```

## Source Recovery / Backup System

Scripts that modify `metadata/heritage_links.csv` now create a timestamped backup first:

```text
metadata/backups/
```

List available backups:

```bash
run_list_csv_backups.bat
```

Restore the latest backup:

```bash
run_restore_latest_csv_backup.bat
```

The Admin Dashboard `Admin` tab also includes a Source Database Recovery section where you can inspect and restore backups.

## Local Chat UI

Run the end-user chat interface:

```bash
run_chat_ui.bat
```

Open:

```text
http://localhost:8502
```

The chat UI does not show admin controls, logs, validation buttons, or source-management actions. It uses the same local agent pipeline as `run_agent.bat`, including question routing, conversation memory, RAG citations, source links, accessibility rules, and archaeology safety constraints.

## Conversation Memory

Conversation memory stores prior question/answer turns locally so follow-up questions can use earlier context.

Storage:

```text
data/conversation_memory/conversations.sqlite
```

This folder is ignored by Git because it can contain private user conversation data.

Run the agent with a specific memory session:

```bash
run_agent.bat "Tell me more about his temples" --session-id research-session-1
```

Disable memory for a run:

```bash
run_agent.bat "Explain Hampi" --no-memory
```

Inspect or clear memory:

```bash
run_memory.bat
run_memory.bat --session-id research-session-1 --list
run_memory.bat --session-id research-session-1 --query "Krishnadevaraya temples"
run_memory.bat --session-id research-session-1 --clear
```

Conversation memory is treated as session context, not source evidence. The agent should not cite memory as a RAG source; factual claims still need retrieved source citations.

## Source Quality Scoring

The CSV includes quality fields:

```text
source_type
trust_score
usable_for_rag
priority
```

Update all scores:

```bash
run_update_source_quality.bat
```

The scorer boosts official and high-value sources such as ASI, UNESCO, national archives, government data, and direct PDFs. It does not exclude sources merely because they are old scans, manuscripts, maps, OCR-heavy documents, unknown-language material, or visually poor archaeology records. Those are often valuable for this domain. It only excludes obvious non-knowledge items such as tools, placeholder/example URLs, and broken links.

Retrieval uses these scores as a boost, so trusted sources rank higher when embedding similarity is close.

Inspect the vector database:

```bash
run_vector_db_info.bat
```

## Document Categories

Normalize loose source categories into a stable `document_category` column:

```bash
run_update_document_categories.bat
```

Categories include excavation reports, annual reviews, research papers, journals, books, manuscripts, archives, museum collections, monument/site records, GIS/map/satellite sources, datasets, government/policy documents, conservation/management sources, articles/blogs, and tools/platforms.

The Admin Dashboard includes a `Categories` tab and a document-category filter.

The default embedding provider is local and free:

```text
HERITAGE_EMBEDDING_PROVIDER=local
```

`local` now uses a corpus-trained TF-IDF vectorizer stored inside SQLite. This is stronger than the earlier hash memory and does not need API credits.

For the older hash embedding fallback:

```bash
set HERITAGE_EMBEDDING_PROVIDER=hash
run_build_embeddings.bat --limit 10
```

To later rebuild with OpenAI embeddings, after your API quota works:

```bash
set HERITAGE_EMBEDDING_PROVIDER=openai
set OPENAI_EMBEDDING_MODEL=text-embedding-3-small
run_build_embeddings.bat --query "Hampi"
```

## Auto-Ingestion Pipeline

Run the self-growing knowledge-base pipeline:

```bash
run_auto_ingest.bat --validate-limit 25 --source-limit 10 --pdf-limit-per-source 5 --embed-limit 10
```

It performs:

```text
validate pending/stale links
-> discover PDF links from verified source pages
-> add discovered PDFs to heritage_links.csv
-> download/extract direct PDFs and ingest source webpages
-> update the SQLite vector database
```

Run only PDF discovery:

```bash
run_discover_pdfs.bat --source-limit 10 --pdf-limit-per-source 5
```

Logs:

```text
data/logs/auto_ingest.log
data/logs/pdf_discovery.log
```

Install weekly auto-ingestion on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_auto_ingest_schedule.ps1
```

This creates `IndianHeritageAI-AutoIngest`, running every Sunday at 10:00.

Remove it:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_auto_ingest_schedule.ps1
```

Statuses:

- `verified`: URL is reachable.
- `redirect`: URL works but redirects.
- `pdf`: URL is reachable and appears to be a PDF.
- `broken`: URL failed or returned an error.
- `pending`: Not checked yet.

## Run The UI

Open the dependency-free dashboard directly:

```text
index.html
```

Or run the Streamlit version:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Admin dashboard launcher:

```bash
run_admin_dashboard.bat
```

Open:

```text
http://localhost:8501
```

The admin dashboard includes:

```text
link/status metrics
source quality breakdown
searchable CSV table
validation actions
PDF discovery actions
embedding and auto-ingest actions
vector DB stats
recent logs
memory search test
```

## Next Build Steps

1. Run `validate_links.py` and review broken or redirected URLs.
2. Add `scripts/extract_text.py` for PDFs and HTML pages.
3. Add `scripts/chunk_text.py`.
4. Add embeddings and a local vector database.
5. Build the heritage chatbot on top of verified content.
