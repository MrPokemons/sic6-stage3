import streamlit as st

pages = [
    st.Page("streamlitViews/berandaView.py", title="🏡 Beranda"),
    # st.Page("streamlitViews/dataDiriView.py", title="🧒 Data Anak"),
    st.Page("streamlitViews/pengaturanView.py", title="⚙️ Pengaturan Percakapan"),
    st.Page("streamlitViews/percakapanView.py", title="🤖 Percakapan Saat Ini 🧒"),
]


pg = st.navigation(pages)
pg.run()
