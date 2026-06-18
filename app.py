"""Spotify Discovery Research Agent — Part 1 entry point."""

import streamlit as st

from services.config import load_secrets, secrets_configured
from services.connection_tests import run_all_tests

st.set_page_config(
    page_title="Spotify Discovery Research Agent",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Spotify Discovery Research Agent")
st.caption("Part 1 — AI-powered Review Discovery Engine for music discovery research")

st.markdown(
    """
    This tool analyzes public user feedback about Spotify discovery and recommendations,
    then surfaces research-ready insights for product teams.
    """
)

st.divider()

# Load secrets from Streamlit secrets (Cloud) or local secrets.toml
try:
    secrets = dict(st.secrets)
except (FileNotFoundError, AttributeError):
    secrets = load_secrets()

st.subheader("Connection Tests")
st.markdown("Verify external services before building the pipeline (Phase 0).")

if not secrets_configured() and not secrets:
    st.warning(
        "No secrets found. Copy `.streamlit/secrets.toml.example` to "
        "`.streamlit/secrets.toml` and add your API keys."
    )
else:
    if st.button("Run connection tests", type="primary"):
        with st.spinner("Testing connections..."):
            results = run_all_tests(
                supabase_url=str(secrets.get("SUPABASE_URL", "")),
                supabase_key=str(secrets.get("SUPABASE_SERVICE_KEY", "")),
                groq_api_key=str(secrets.get("GROQ_API_KEY", "")),
                groq_model=str(secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile")),
                reddit_user_agent=str(
                    secrets.get(
                        "REDDIT_USER_AGENT",
                        "spotify-research-collector/1.0 (PM case study; public pages only)",
                    )
                ),
            )

        for result in results:
            if result.ok:
                st.success(f"**{result.name}** — {result.message}")
            else:
                st.error(f"**{result.name}** — {result.message}")

st.divider()

st.subheader("Pipeline (coming in later phases)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Collect", "Phase 2", help="Reddit public pages + Play Store CSV")
col2.metric("Analyze", "Phase 3", help="Groq structured extraction")
col3.metric("Insights", "Phase 4", help="Theme synthesis + report")
col4.metric("Dashboard", "Phase 5", help="Themes, evidence, segments")

with st.expander("Setup checklist (Phase 0)"):
    st.markdown(
        """
        - [ ] Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
        - [ ] Create a [Supabase](https://supabase.com) project
        - [ ] Get a [Groq API key](https://console.groq.com/keys) (starts with `gsk_`)
        - [ ] Reddit: save public search pages as HTML → `data/reddit_html/` (no API)
        - [ ] Run connection tests above
        - [ ] Push repo to GitHub (for Streamlit Cloud deploy in Phase 7)
        """
    )
