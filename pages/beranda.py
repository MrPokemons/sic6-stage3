import streamlit as st
import requests

import pandas as pd

# analytics data declaration here

wordDictionary = {
    "Kata Asli": ['Adel', 'Data 2', 'Data 3'],
    "Pelafalan Anak": ['Value 1', 'Value 2', 'Value 3']
}

mathDictionary = {
    "Pertanyaan": ['Data 1', 'Data 2', 'Data 3'],
    "Jawaban Anak": ['Value 1', 'Value 2', 'Value 3']
}

dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]


# view starts here
st.title("PawPal 🐾")

# -------------------
col1, col2 = st.columns(2)
with col1:
    st.subheader("Percakapan Terakhir")
    st.markdown("""
    <div style="
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        font-family: 'Helvetica', sans-serif;
        line-height: 1.6;
        padding-bottom: 20px;
    ">        
        <div style="margin-bottom: 6px">
            <span style="margin-right: 20px;">🗓️ 12 April 2015</span>
            <span>⏰ 17:10 - 17:15</span>
            </div>
    </div>
""", unsafe_allow_html=True)
with col2:
    st.subheader("Perasaan")
    st.markdown("""
    <div style="
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        font-family: 'Helvetica', sans-serif;
        line-height: 1.6;
        padding-bottom: 20px;
    ">        
        <div style="margin-bottom: 6px">
            <span style="margin-right: 20px;">
                🤩 Senang
            </span>
    </div>
    """, unsafe_allow_html=True)

# -------------------
st.subheader("Transkrip")
with st.expander("💬 Transkrip Percakapan Terakhir"):
    st.markdown("""
    <style>
        .message-container {
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 10px;
            max-width: 70%;
            word-wrap: break-word;
        }
        .user {
            background-color: #3c77d6;
            align-self: flex-end;
            margin-left: auto;
        }
        .bot {
            background-color: #04123d;
            align-self: flex-start;
            margin-right: auto;
        }
        .chat-box {
            display: flex;
            flex-direction: column;
        }
    </style>
    """, unsafe_allow_html=True)
        # Render messages
    st.markdown('<div class="chat-box">', unsafe_allow_html=True)
    for msg in dummyMsg:
      role_class = "user" if msg["sender"] == "user" else "bot"
      st.markdown(
        f'<div class="message-container {role_class}">{msg["text"]}</div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------
st.subheader("Analitik")
# dictionary columns
# declare tables and columns
wordDictTable = pd.DataFrame(wordDictionary)
mathDictTable = pd.DataFrame(mathDictionary)

wdt = pd.DataFrame(wordDictTable)
wdt.index += 1
mdt = pd.DataFrame(mathDictTable)
mdt.index += 1

col1, col2 = st.columns(2)
with col1:
    st.table(wdt)
with col2:
    st.table(mdt)