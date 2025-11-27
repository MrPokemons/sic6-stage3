import streamlit as st
from streamlitViews.language_utils import render_language_toggle, get_current_language
from streamlitViews.translations import get_text

# Render language toggle in sidebar
render_language_toggle()

# Get current language
lang = get_current_language()

st.title(get_text("tentang.title", lang))
st.subheader(get_text("tentang.subtitle", lang))

with st.container():
    st.write(get_text("tentang.description", lang))

with st.container():
    st.subheader(get_text("tentang.main_features", lang))
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("👄 Talk To Me"):
            st.write(get_text("tentang.talk_to_me_desc", lang))
        with st.expander("🖐️ Math Adventures"):
            st.write(get_text("tentang.math_adventures_desc", lang))
    with col2:
        with st.expander("🔊 Guess The Sound"):
            st.write(get_text("tentang.guess_the_sound_desc", lang))
        with st.expander("❓ Would you Rather"):
            st.write(get_text("tentang.would_you_rather_desc", lang))

with st.container():
    st.subheader(get_text("tentang.target_users", lang))
    st.write(get_text("tentang.target_users_desc", lang))

with st.container():
    st.subheader(get_text("tentang.duration_function", lang))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, height=110):
            st.write(get_text("tentang.duration_desc1", lang))
    with col2:
        with st.container(border=True, height=110):
            st.write(get_text("tentang.duration_desc2", lang))

with st.container():
    st.subheader(get_text("tentang.session_function", lang))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, height=160):
            st.write(get_text("tentang.session_desc1", lang))
    with col2:
        with st.container(border=True, height=160):
            st.markdown(
                get_text("tentang.session_desc2", lang),
                unsafe_allow_html=True,
            )
    st.write(get_text("tentang.session_desc3", lang))

with st.container():
    st.subheader(get_text("tentang.customizable", lang))
    st.write(get_text("tentang.customizable_desc", lang))


st.markdown(
    """
    <style>
        div[data-testid="stExpander"] details {
            background-color: #1e5677 !important;
            border: 0;
        }

        div[data-testid="stExpanderDetails"] {
            background-color: #ededed;
            padding-top: 1rem;
        }

        div[data-testid="stExpanderDetails"] p {
            color: black !important;
        }

        summary, summary svg {
            color: white !important;
        }

        summary:hover span{
            color: white !important;
        }

        summary:hover svg{
            fill: white !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)
