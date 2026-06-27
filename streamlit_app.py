import os
import time

import requests
import streamlit as st

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, Exception):
    API_URL = os.environ.get("API_URL", "")


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.text_input("Password", type="password", key="pwd_input")
        if st.button("Login"):
            try:
                app_password = st.secrets["APP_PASSWORD"]
            except Exception:
                app_password = os.environ.get("APP_PASSWORD", "")
            if st.session_state.pwd_input == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()


check_password()

EXAMPLE_QUESTIONS = [
    "What was the primary endpoint result in the study?",
    "What were the most common adverse events reported?",
    "What Grade 3 or 4 adverse events occurred in more than 5% of patients?",
    "How many patients were enrolled in the study?",
    "What was the dosing regimen used in the study?",
    "What were the key inclusion and exclusion criteria?",
    "How were patients randomised in this study?",
    "What was the median progression-free survival?",
]

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Clinical Document Intelligence",
    page_icon="🔬",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #00c8ff;
        margin-bottom: 0;
    }
    .sub-title {
        font-size: 1rem;
        color: #888888;
        margin-top: 0.2rem;
        margin-bottom: 2rem;
    }
    .answer-box {
        background: #1a1d27;
        border-left: 4px solid #00c8ff;
        border-radius: 6px;
        padding: 1.2rem 1.5rem;
        font-size: 1rem;
        line-height: 1.7;
        color: #f0f0f0;
    }
    .source-card {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #00c8ff;
    }
    .pill {
        display: inline-block;
        background: #2a2d3a;
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.8rem;
        color: #aaaaaa;
        margin: 0.2rem;
        cursor: pointer;
    }
    div[data-testid="stButton"] button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown('<p class="main-title">🔬 Clinical Document Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Ask questions about ingested clinical documents — get answers with exact page citations.</p>', unsafe_allow_html=True)

st.divider()

# ── Input ──────────────────────────────────────────────────────────────────────

st.markdown("**Ask a clinical question**")

if "question_input" not in st.session_state:
    st.session_state.question_input = ""

question = st.text_area(
    label="question",
    value=st.session_state.question_input,
    placeholder="e.g. What were the most common adverse events reported?",
    height=90,
    label_visibility="collapsed",
    key="question_input",
)

st.markdown("**Example questions:**")
cols = st.columns(4)
for i, eq in enumerate(EXAMPLE_QUESTIONS):
    if cols[i % 4].button(eq[:45] + "…" if len(eq) > 45 else eq, key=f"eq_{i}", use_container_width=True):
        st.session_state.question_input = eq
        st.rerun()

st.markdown("")
ask_col, _ = st.columns([1, 5])
ask = ask_col.button("Ask", type="primary", use_container_width=True)

# ── Query ──────────────────────────────────────────────────────────────────────

if ask and question.strip():
    with st.spinner("Searching clinical documents…"):
        try:
            resp = requests.post(
                f"{API_URL}/query",
                json={"question": question.strip()},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            st.error("Request timed out. The service may be starting up — try again in 30 seconds.")
            st.stop()
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Check that the service is running.")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.divider()

    # Answer
    st.markdown("### Answer")
    st.markdown(f'<div class="answer-box">{data["answer"]}</div>', unsafe_allow_html=True)

    st.markdown("")

    # Sources + Metrics side by side
    src_col, metrics_col = st.columns([3, 2])

    with src_col:
        sources = data.get("sources", [])
        st.markdown(f"### Sources ({len(sources)})")
        if sources:
            for s in sources:
                score_pct = round(s.get("score", 0) * 100)
                st.markdown(f"""
                <div class="source-card">
                    <strong>📄 {s.get('file', '—')}</strong><br>
                    <span style="color:#888888; font-size:0.85rem;">
                        Page {int(s.get('page', 0)) + 1} &nbsp;·&nbsp; Relevance: {score_pct}%
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("_No sources returned._")

    with metrics_col:
        st.markdown("### Performance")
        latency = data.get("latency_ms", {})
        cost = data.get("cost_usd", 0)

        m1, m2 = st.columns(2)
        m1.metric("Total", f"{latency.get('total', 0):,} ms")
        m2.metric("Cost", f"${cost:.4f}")

        m3, m4 = st.columns(2)
        m3.metric("Retrieval", f"{latency.get('retrieval', 0)} ms")
        m4.metric("Reranking", f"{latency.get('reranking', 0)} ms")

        st.metric("Generation (LLM)", f"{latency.get('generation', 0):,} ms")

elif ask and not question.strip():
    st.warning("Please enter a question.")

# ── Footer ─────────────────────────────────────────────────────────────────────

st.divider()
st.markdown(
    "<p style='text-align:center; color:#444444; font-size:0.8rem;'>"
    "Powered by AWS Bedrock · Weaviate Hybrid Search · CrossEncoder Reranker"
    "</p>",
    unsafe_allow_html=True,
)
