"""
Language toggle utility for PawPal Streamlit application.
"""
import streamlit as st


def init_language():
    """Initialize language in session state if not present."""
    if "language" not in st.session_state:
        st.session_state.language = "en"  # Default to English


def get_current_language():
    """Get current language from session state."""
    init_language()
    return st.session_state.language


def set_language(lang: str):
    """Set language in session state."""
    st.session_state.language = lang


def render_language_toggle():
    """Render language toggle button in sidebar."""
    init_language()

    with st.sidebar:
        st.markdown("### 🌐 Language")

        current_lang = get_current_language()

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "🇬🇧 EN",
                use_container_width=True,
                type="primary" if current_lang == "en" else "secondary"
            ):
                set_language("en")
                st.rerun()

        with col2:
            if st.button(
                "🇮🇩 ID",
                use_container_width=True,
                type="primary" if current_lang == "id" else "secondary"
            ):
                set_language("id")
                st.rerun()

        st.markdown("---")
