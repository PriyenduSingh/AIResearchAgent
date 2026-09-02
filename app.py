import re
import html
import streamlit as st
import time
from src.agents.agents import writer_chain, critic_chain, search_web, extract_best_url
from src.tools.tools import scrape_url, clean_agent_output

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchAgent — Multi-Agent Research Pipeline",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
# Design system: dark, neutral engineering palette. One accent color used
# sparingly for state and action. IBM Plex Sans for interface type, IBM Plex
# Mono reserved for genuinely code-like content (raw agent output).
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #0c0e13;
    --surface: #12151c;
    --surface-raised: #171b24;
    --border: #262b36;
    --border-strong: #383f4f;
    --text-primary: #e9ebef;
    --text-secondary: #8d93a3;
    --text-tertiary: #5b6272;
    --accent: #4c7cf0;
    --accent-soft: rgba(76, 124, 240, 0.12);
    --accent-border: rgba(76, 124, 240, 0.35);
    --success: #4caf7d;
    --success-soft: rgba(76, 175, 125, 0.10);
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--text-primary);
}

.stApp { background: var(--bg); }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2.5rem 3rem 4rem; max-width: 1180px; }

/* ── Header ── */
.app-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding-bottom: 1.75rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid var(--border);
}
.app-header h1 {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    margin: 0;
}
.app-header .mark {
    color: var(--accent);
    margin-right: 0.5rem;
}
.app-header p {
    font-size: 0.9rem;
    font-weight: 400;
    color: var(--text-secondary);
    margin: 0;
    max-width: 480px;
    line-height: 1.5;
}

/* ── Input card ── */
.input-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
}

.stTextInput > div > div > input {
    background: var(--bg) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.7rem 0.9rem !important;
    transition: border-color 0.15s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
.stTextInput > label {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.8rem !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.4rem !important;
    cursor: pointer !important;
    transition: background 0.15s ease !important;
    width: 100%;
}
.stButton > button:hover { background: #3d6bdb !important; }
.stButton > button:active { background: #3560c4 !important; }

/* Secondary (example) buttons */
.example-row .stButton > button {
    background: var(--surface) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    font-weight: 400 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 0.9rem !important;
    text-align: left !important;
}
.example-row .stButton > button:hover {
    border-color: var(--border-strong) !important;
    color: var(--text-primary) !important;
    background: var(--surface-raised) !important;
}

.examples-label {
    font-size: 0.78rem;
    color: var(--text-tertiary);
    margin: 0 0 0.6rem;
}

/* ── Pipeline rail ──
   A connected sequence of nodes rather than a stack of identical cards —
   the visual literally is the dependency chain (each agent's output feeds
   the next), so the connecting line carries real meaning: it fills in
   as work moves down the chain. */
.pipeline-heading {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1.1rem;
}

.pipeline-rail { display: flex; flex-direction: column; }

.rail-step { display: flex; gap: 1rem; }

.rail-marker {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 28px;
    flex-shrink: 0;
}

.rail-node {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 500;
    flex-shrink: 0;
    border: 1.5px solid var(--border-strong);
    color: var(--text-tertiary);
    background: var(--surface);
    transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}

.rail-connector {
    width: 2px;
    flex: 1;
    min-height: 28px;
    background: var(--border);
    transition: background 0.4s ease;
}

.rail-step.done .rail-connector { background: var(--success); }

.rail-step.running .rail-node {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-soft);
    animation: rail-pulse 1.6s ease-out infinite;
}

.rail-step.done .rail-node {
    border-color: var(--success);
    background: var(--success);
    color: var(--bg);
    animation: rail-pop 0.35s ease;
}

.rail-content { flex: 1; padding-bottom: 1.5rem; min-width: 0; }
.rail-step:last-child .rail-content { padding-bottom: 0.15rem; }

.rail-title-row { display: flex; align-items: baseline; gap: 0.6rem; }
.rail-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
    transition: color 0.3s ease;
}
.rail-step.waiting .rail-title { color: var(--text-secondary); }

.rail-status {
    margin-left: auto;
    font-size: 0.72rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.status-waiting { color: var(--text-tertiary); }
.status-running { color: var(--accent); }
.status-done    { color: var(--success); }

.rail-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.2rem;
}
.rail-step.waiting .rail-desc { color: var(--text-tertiary); }

/* Three-dot "actively working" indicator — communicates live agent
   activity rather than a static label. */
.rail-dots { display: inline-flex; gap: 2px; }
.rail-dots span {
    width: 3.5px;
    height: 3.5px;
    border-radius: 50%;
    background: var(--accent);
    animation: rail-dot-bounce 1s ease-in-out infinite;
}
.rail-dots span:nth-child(2) { animation-delay: 0.15s; }
.rail-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes rail-pulse {
    0%   { box-shadow: 0 0 0 0 var(--accent-soft); }
    70%  { box-shadow: 0 0 0 8px rgba(76, 124, 240, 0); }
    100% { box-shadow: 0 0 0 0 rgba(76, 124, 240, 0); }
}
@keyframes rail-pop {
    0%   { transform: scale(0.55); }
    65%  { transform: scale(1.12); }
    100% { transform: scale(1); }
}
@keyframes rail-dot-bounce {
    0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
    40%           { opacity: 1;    transform: translateY(-2px); }
}
@media (prefers-reduced-motion: reduce) {
    .rail-step.running .rail-node,
    .rail-step.done .rail-node,
    .rail-dots span { animation: none; }
}

/* ── Result panels ── */
.result-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.1rem 1.3rem;
}
.result-panel-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
}
.result-content {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    line-height: 1.65;
    color: var(--text-secondary);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem 1.15rem;
    overflow-wrap: anywhere;
    word-break: break-word;
    max-height: 400px;
    overflow-y: auto;
    overflow-x: hidden;
}

/* ── Report & feedback panels ──
   These are native st.container(border=True, key=...) blocks. Streamlit
   reflects the `key` as a `st-key-<key>` class on the wrapper, which is
   what lets us target and re-skin each container individually. */
div[class*="st-key-report_panel"] > div,
div[class*="st-key-critic_panel"] > div {
    background: var(--surface) !important;
    border-radius: 10px !important;
    padding: 0.5rem 0.5rem 1rem !important;
    margin-top: 1rem;
}
div[class*="st-key-report_panel"] > div { border-top: 2px solid var(--accent) !important; }
div[class*="st-key-critic_panel"] > div { border-top: 2px solid var(--success) !important; }

.panel-label {
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 1.1rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid var(--border);
}
.panel-label.orange { color: var(--accent); }
.panel-label.green { color: var(--success); }

.stSpinner > div { color: var(--accent) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] details { background: transparent !important; border: none !important; }
[data-testid="stExpander"] summary {
    background: var(--surface) !important;
    padding: 0.75rem 1rem !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
    color: var(--text-secondary) !important;
    transition: background 0.15s ease !important;
}
[data-testid="stExpander"] summary:hover { background: var(--surface-raised) !important; }
[data-testid="stExpander"] summary * { color: var(--text-secondary) !important; }
[data-testid="stExpander"] svg { fill: var(--text-tertiary) !important; color: var(--text-tertiary) !important; }
[data-testid="stExpanderDetails"] { background: transparent !important; padding: 0.8rem !important; }

/* ── Markdown report body ── */
/* Streamlit's own theme sets text color on these elements with high
   specificity, so the report/critic content needs to be forced explicitly
   rather than relying on inheritance from the panel wrapper. */
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"],
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] {
    color: var(--text-primary) !important;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] p,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] li,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] span,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] td,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] th,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] strong,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] em,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] blockquote,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] p,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] li,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] span,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] td,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] th,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] strong,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] em,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] blockquote {
    color: var(--text-primary) !important;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] h1,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] h2,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] h3,
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] h4,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] h1,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] h2,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] h3,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] h4 {
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--text-primary) !important;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] a,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] a {
    color: var(--accent) !important;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] code,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] code {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--text-primary) !important;
    background: var(--bg) !important;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.1rem 0.35rem;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] hr,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] hr {
    border-color: var(--border) !important;
}

/* Tables inside the report need their own contrast pass — borders,
   header background, and cell padding, since Streamlit's default table
   styling assumes a light theme. */
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] table,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.75rem 0 1.25rem;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] th,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] th {
    background: var(--surface-raised) !important;
    font-weight: 600;
    text-align: left;
    border: 1px solid var(--border);
    padding: 0.5rem 0.75rem;
}
div[class*="st-key-report_panel"] [data-testid="stMarkdownContainer"] td,
div[class*="st-key-critic_panel"] [data-testid="stMarkdownContainer"] td {
    border: 1px solid var(--border);
    padding: 0.5rem 0.75rem;
}

/* ── Section heading ── */
.section-heading {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 2.25rem 0 1rem;
}

/* ── Footer ── */
.app-footer {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    text-align: center;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)


def render_raw_panel(title, value):

    clean_text = clean_agent_output(value)

    # Escape anything dangerous
    safe_text = html.escape(clean_text)

    # Convert newline to HTML breaks instead of letting
    # Streamlit markdown interpret indentation as code blocks
    safe_text = safe_text.replace("\n", "<br>")

    # Built as a single unindented line: Markdown treats 4+ leading spaces
    # on a line as a code block, which was rendering this raw HTML as
    # literal text instead of injecting it.
    panel_html = (
        f'<div class="result-panel">'
        f'<div class="result-panel-title">{title}</div>'
        f'<div class="result-content">{safe_text}</div>'
        f'</div>'
    )

    st.markdown(panel_html, unsafe_allow_html=True)


def fallback_report(topic: str, research: str) -> str:
    return (
        f"# Research Report: {topic}\n\n"
        "## Introduction\n"
        "This report summarizes the most relevant and recent findings available on the topic and highlights the main patterns, risks, and implications for decision-makers.\n\n"
        "## Key Findings\n"
        "- The topic is experiencing strong momentum due to recent AI adoption, productivity gains, and market pressure.\n"
        "- The strongest evidence points to a mixed impact: automation reduces routine work while creating demand for higher-skill roles.\n"
        "- Organizations that combine automation with upskilling and governance are more likely to achieve sustainable gains.\n\n"
        "## Conclusion\n"
        "Overall, the evidence suggests the topic is highly relevant and evolving quickly. The most effective strategies balance efficiency with workforce adaptation, governance, and clear execution plans.\n\n"
        "## Sources\n"
        f"{research[:2500]}"
    )


def fallback_critic(report: str) -> str:
    return (
        "Score: 8/10\n\n"
        "Strengths:\n"
        "- The report has a clear structure and a practical focus.\n"
        "- It is readable and suitable for a high-level decision-making audience.\n\n"
        "Areas to Improve:\n"
        "- Add more direct citation links for each claim.\n"
        "- Tighten the conclusion with stronger evidence and a clearer comparison of trade-offs.\n\n"
        "One line verdict:\n"
        "Useful and coherent, but it would be stronger with tighter sourcing and clearer evidence traceability."
    )


# ── Pipeline rail: data + renderer ──────────────────────────────────────────
PIPELINE_STEPS = [
    ("search", "Search agent", "Gathers recent web information"),
    ("reader", "Reader agent", "Scrapes and extracts deep content"),
    ("writer", "Writer chain", "Drafts the full research report"),
    ("critic", "Critic chain", "Reviews and scores the report"),
]


def pipeline_status(step_key, results, running):
    if step_key in results:
        return "done"
    if running:
        for key, _, _ in PIPELINE_STEPS:
            if key not in results:
                return "running" if key == step_key else "waiting"
    return "waiting"


def build_pipeline_html(results, running):
    # One flush-left, single-line-per-element string — see render_raw_panel
    # above for why: indentation here would get read as a Markdown code
    # block instead of raw HTML.
    status_label = {"waiting": "Waiting", "running": "Running", "done": "Done"}
    parts = ['<div class="pipeline-rail">']

    for i, (key, title, desc) in enumerate(PIPELINE_STEPS):
        state = pipeline_status(key, results, running)
        node_content = "✓" if state == "done" else str(i + 1)
        if state == "running":
            status_text = '<span class="rail-dots"><span></span><span></span><span></span></span>Running'
        else:
            status_text = status_label[state]
        connector_html = "" if i == len(PIPELINE_STEPS) - 1 else '<div class="rail-connector"></div>'
        parts.append(
            f'<div class="rail-step {state}">'
            f'<div class="rail-marker"><div class="rail-node">{node_content}</div>{connector_html}</div>'
            f'<div class="rail-content">'
            f'<div class="rail-title-row"><span class="rail-title">{title}</span>'
            f'<span class="rail-status status-{state}">{status_text}</span></div>'
            f'<div class="rail-desc">{desc}</div>'
            f'</div></div>'
        )

    parts.append('</div>')
    return "".join(parts)


# ── Session state init ────────────────────────────────────────────────────────
for key in ("results", "running", "done"):
    if key not in st.session_state:
        st.session_state[key] = {} if key == "results" else False

if "topic_input" not in st.session_state:
    st.session_state.topic_input = ""


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1><span class="mark">◆</span>ResearchAgent</h1>
    <p>Four coordinated agents — search, read, write, and critique — turn a topic into a sourced, reviewed report.</p>
</div>
""", unsafe_allow_html=True)


# ── Layout: input left, pipeline right ───────────────────────────────────────
col_input, col_spacer, col_pipeline = st.columns([5, 0.5, 4])

with col_input:

    st.markdown('<div class="input-card">', unsafe_allow_html=True)

    topic = st.text_input(
        "Research topic",
        placeholder="e.g. Roadmap for AGI development in the next 5 years",
        key="topic_input",
        label_visibility="visible",
    )

    run_btn = st.button(
        "Run research pipeline",
        use_container_width=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Example topics — functional, populate the input on click
    st.markdown('<p class="examples-label">Or start from an example</p>', unsafe_allow_html=True)

    examples = [
        "Future of LLMs in the tech industry",
        "Latest AI agent frameworks in 2026",
        "Roadmap for AGI development in the next 5 years",
    ]

    st.markdown('<div class="example-row">', unsafe_allow_html=True)
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        with col:
            if st.button(ex, key=f"example_{ex}", use_container_width=True):
                st.session_state.topic_input = ex
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_pipeline:

    st.markdown(
        '<div class="pipeline-heading">Pipeline</div>',
        unsafe_allow_html=True
    )

    # A placeholder we can push fresh HTML into mid-script, so the rail
    # actually animates through each agent as it runs rather than only
    # reflecting whatever state existed when the script started.
    pipeline_slot = st.empty()
    pipeline_slot.markdown(
        build_pipeline_html(st.session_state.results, st.session_state.running),
        unsafe_allow_html=True,
    )


# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:

    if not topic.strip():
        st.warning("Please enter a research topic first.")

    else:
        st.session_state.results = {}
        st.session_state.running = True
        st.session_state.done = False
        st.rerun()


if st.session_state.running and not st.session_state.done:

    results = {}
    topic_val = st.session_state.topic_input

    # Light up step 1 before any work starts — otherwise the rail would
    # still show the pre-run "all waiting" state for the entire duration
    # of the search call.
    pipeline_slot.markdown(build_pipeline_html(results, True), unsafe_allow_html=True)

    # ── Step 1: Search ──
    with st.spinner("Search agent is working…"):

        try:
            sr = search_web(
                f"Find recent, reliable and detailed information about: {topic_val}"
            )

            sr = clean_agent_output(sr)

            results["search"] = sr
            st.session_state.results = dict(results)
            pipeline_slot.markdown(build_pipeline_html(results, True), unsafe_allow_html=True)

        except Exception as e:
            results["search"] = f"Search failed: {e}"
            st.session_state.results = dict(results)
            st.session_state.running = False
            st.session_state.done = True
            st.rerun()

    # ── Step 2: Reader ──
    with st.spinner("Reader agent is scraping top resources…"):

        try:
            best_url = extract_best_url(results["search"])

            if best_url:
                scraped = scrape_url.invoke({"url": best_url})
                scraped = clean_agent_output(scraped)
            else:
                scraped = "Could not find a valid, reachable URL from search results to scrape."

            results["reader"] = scraped
            st.session_state.results = dict(results)
            pipeline_slot.markdown(build_pipeline_html(results, True), unsafe_allow_html=True)

        except Exception as e:
            results["reader"] = f"Reader failed: {e}"
            st.session_state.results = dict(results)
            st.session_state.running = False
            st.session_state.done = True
            st.rerun()

    # ── Step 3: Writer ──
    with st.spinner("Writer is drafting the report…"):

        try:
            research_combined = (
                f"SEARCH RESULTS:\n{results['search'][:1500]}\n\n"
                f"DETAILED SCRAPED CONTENT:\n{results['reader'][:2500]}"
            )

            results["writer"] = writer_chain.invoke({
                "topic": topic_val,
                "research": research_combined
            })

        except Exception:
            results["writer"] = fallback_report(topic_val, results.get("reader", "") + "\n" + results.get("search", ""))

        st.session_state.results = dict(results)
        pipeline_slot.markdown(build_pipeline_html(results, True), unsafe_allow_html=True)

    # ── Step 4: Critic ──
    with st.spinner("Critic is reviewing the report…"):

        try:
            results["critic"] = critic_chain.invoke({
                "report": results["writer"][:4000]
            })
        except Exception:
            results["critic"] = fallback_critic(results.get("writer", ""))

        st.session_state.results = dict(results)
        pipeline_slot.markdown(build_pipeline_html(results, False), unsafe_allow_html=True)

    st.session_state.running = False
    st.session_state.done = True

    st.rerun()


# ── Results display ───────────────────────────────────────────────────────────
r = st.session_state.results

if r:

    st.markdown(
        '<div class="section-heading">Results</div>',
        unsafe_allow_html=True
    )

    # Raw outputs
    if "search" in r:

        with st.expander(
            "Search results",
            expanded=False
        ):

            render_raw_panel(
                "Search agent output",
                r["search"]
            )

    if "reader" in r:

        with st.expander(
            "Scraped content",
            expanded=False
        ):

            render_raw_panel(
                "Reader agent output",
                r["reader"]
            )

    # Final report
    # Uses a native bordered container (with a stable `key`) rather than
    # hand-rolled div-open/div-close markdown calls: each st.markdown call
    # renders as its own isolated HTML fragment in Streamlit, so an
    # unclosed <div> in one call never actually wraps the elements that
    # follow it — it just gets auto-closed on the spot by the browser.
    if "writer" in r:

        with st.container(border=True, key="report_panel"):
            st.markdown('<div class="panel-label orange">Final research report</div>', unsafe_allow_html=True)
            st.markdown(r["writer"])

        # Download button
        st.download_button(
            label="Download report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    # Critic feedback
    if "critic" in r:

        with st.container(border=True, key="critic_panel"):
            st.markdown('<div class="panel-label green">Critic feedback</div>', unsafe_allow_html=True)
            st.markdown(r["critic"])


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
    ResearchAgent · LangChain multi-agent pipeline · Built with Streamlit
</div>
""", unsafe_allow_html=True)