"""Consistent empty-state messaging across dashboard pages."""

from __future__ import annotations

import streamlit as st


def show_empty(title: str, message: str, action: str | None = None) -> None:
    st.warning(f"**{title}**")
    st.markdown(message)
    if action:
        st.code(action, language="bash")
