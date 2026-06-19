"""Inject Spotify-adjacent dashboard styling."""

from __future__ import annotations

import streamlit as st


def apply_dashboard_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetric"] {
            background: #F0F2F6;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            border-left: 4px solid #1DB954;
        }
        .quote-block {
            background: #F6F6F6;
            border-left: 4px solid #1DB954;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 0 8px 8px 0;
            font-style: italic;
        }
        .source-badge {
            display: inline-block;
            background: #191414;
            color: #1DB954;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-style: normal;
            margin-top: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
