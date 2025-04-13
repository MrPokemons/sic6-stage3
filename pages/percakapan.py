import streamlit as st
import requests

chatConfig = []
dummyMsg = []
# dummyMsg = [
#     {"sender": "user", "text": "Hai, kamu lagi apa?"},
#     {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
#     {"sender": "user", "text": "Oke siap~"},
# ]

st.title("Mulai Percakapan 🤖")

st.subheader("Konfigurasi Percakapan")
with st.form("child_profile_form"):
    duration = st.number_input("⏰ Durasi", min_value=5, max_value=12, step=1)
    topic = st.text_area("💬 Topik Percakapan")

    startConvo = st.form_submit_button("Mulai")

if startConvo:
    print("convo started")

# -------------------
st.subheader("Transkrip")
with st.expander("💬 Transkrip Percakapan Terakhir"):
    if(dummyMsg):
        for msg in dummyMsg:
            with st.chat_message(msg["sender"]):
                st.write(msg["text"])
    else:
        st.write("Belum ada percakapan yang dimulai!")