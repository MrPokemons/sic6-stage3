import streamlit as st

pages = [
    st.Page("streamlitViews/berandaView.py", title="🏡 Beranda"),
    # st.Page("streamlitViews/dataDiriView.py", title="🧒 Data Anak"),
    st.Page("streamlitViews/percakapanView.py", title="🤖 Mulai Percakapan 🐾"),
]


pg = st.navigation(pages)
pg.run()
