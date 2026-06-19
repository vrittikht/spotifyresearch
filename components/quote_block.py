"""Styled user quote with source badge."""

from __future__ import annotations

from typing import Any

import streamlit as st

from components.constants import SOURCE_LABELS


def render_quote_block(quote: str | dict[str, Any], source: str | None = None) -> None:
    if isinstance(quote, dict):
        text = str(quote.get("quote") or quote.get("text") or "")
        source = source or str(quote.get("source") or "")
    else:
        text = str(quote)

    if not text:
        return

    label = SOURCE_LABELS.get(source or "", source or "unknown")
    st.markdown(
        f'<div class="quote-block">"{text}"'
        f'<br><span class="source-badge">{label}</span></div>',
        unsafe_allow_html=True,
    )
