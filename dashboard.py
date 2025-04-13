import streamlit as st
import requests

pages = [
    st.Page("pages/beranda.py", title="🏡 Beranda"),
    st.Page("pages/data_diri.py", title="🧒 Data Anak"),
    st.Page("pages/percakapan.py", title="🤖 Mulai Percakapan 🐾"),
]
    

pg = st.navigation(pages)
pg.run()

