import streamlit as st

st.set_page_config(
    page_icon="streamlitViews/image/logo_only.png",  # Bisa juga emoji seperti "🐾"
    layout="centered",
)

st.sidebar.image("streamlitViews/image/logo.png")
pages = [
    st.Page("streamlitViews/berandaView.py", title="🏡 Beranda"),
    # st.Page("streamlitViews/dataDiriView.py", title="🧒 Data Anak"),
    st.Page("streamlitViews/pengaturanView.py", title="⚙️ Pengaturan Percakapan"),
    st.Page("streamlitViews/tentangView.py", title="🐾 Tentang PawPal"),
    st.Page("streamlitViews/percakapanView.py", title="🤖 Percakapan Saat Ini 🧒"),
]

pg = st.navigation(pages)
pg.run()
