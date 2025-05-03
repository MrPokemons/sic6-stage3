import json
import requests
import streamlit as st
from typing import List
from pymongo import MongoClient
from src.services.pawpal.schemas.document import ConversationDoc


if "deviceId" not in st.session_state:
    st.session_state.deviceId = False

chatConfig = []
# dummyMsg = []
dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]

st.title("🤖 Percakapan Saat Ini 🧒")

if not st.session_state.deviceId:
    placeholder = st.empty()
    with placeholder.form("device_id_form"):
        deviceIdInput = st.text_input("No. ID Perangkat", "")
        saveDeviceId = st.form_submit_button("Cari percakapan terakhir")
        if saveDeviceId:
            st.session_state.deviceId = deviceIdInput
            placeholder.empty()

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId

    list_conversation = None
    try:
        resp = requests.get(
            f"http://localhost:11080/api/v1/pawpal/conversation/{deviceId}/live"
        )
        if resp.status_code == 200:
            list_conversation = resp.json()
    except Exception:
        pass

    # backend offline, connect to read-only demo purposes mongodb
    if list_conversation is None:
        _client = MongoClient(
            "mongodb+srv://pawpal-demo-user:p78Q4EsqPfLmnvtb@sic-cluster.hcqho.mongodb.net/?retryWrites=true&w=majority&appName=SIC-Cluster"
        )
        _db = _client["pawpal_v2"]
        _collection = _db["pawpal-conversation-2"]
        list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
        st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

    # last mode, use the static
    if list_conversation is None:
        try:
            with open("static/json/example.json", "r") as f:
                list_conversation = json.load(f)
        except FileNotFoundError:
            pass

    if list_conversation is None:
        st.error("No conversation ever recorded from the provided device id")
        st.info(
            "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `cincayla`"
        )
        st.stop()

    list_conversation: List[ConversationDoc] = [
        ConversationDoc.model_validate(convo) for convo in list_conversation
    ]

    st.json([i.model_dump(mode="json") for i in list_conversation])

    liveConversation = list_conversation[0]

    if not liveConversation.sessions:
        st.error("Sesi belum dimulai")
        st.stop()

    lastSession = liveConversation.sessions[-1]

    messageResult = []
    for message in lastSession.messages:
        if message.type in ("ai",):
            sender = "ai"
            text = message.text()
        elif message.type in ("human",):
            sender = "user"
            text = message.text().strip()
            if not text:
                continue
        else:
            continue

        messageResult.append({"sender": sender, "text": text})

    # -------------------
    # st.subheader("Transkrip")
    with st.container(border=True, height=500):
        for msg in messageResult:
            with st.chat_message(msg["sender"]):
                st.write(msg["text"])

st.markdown(
    """
    <style>

    button:hover{
        border-color: #1e5677 !important;
        color: #1e5677 !important;
    }

    button:active{
        background-color: #1e5677 !important;
        color: white !important;
    }

    button:focus:not(:active) {
        border-color: #1e5677 !important;
        color: #1e5677 !important;
    }

    /* Geser avatar user ke kanan */
    div[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarUser"] {
        order: 2; /* Biar muncul setelah pesan */
        margin-left: auto;
        margin-right: 0;
        background-color: #fcc06b;
    }

    div[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarAssistant"] {
        padding: 1rem;
        background-color: #1e5677;
    }

    /* Geser konten pesan ke kiri */
    div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"] {
        order: 1;
    }

    /* Buat layout flex horizontal (jika belum) */
    div[data-testid="stChatMessage"] {
        gap: 1rem;
    }

    div[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarUser"] svg {
        color: #976216;
    }


    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) p {
        text-align: right;
            color: white;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        margin-left: 6rem;
        background-color: #1e5677;
    }

    div[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarAssistant"] svg {
        color: white;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        margin-right: 6rem;
        background-color: #ededed;
        padding: 1rem;
    }

    @media (prefers-color-scheme: dark) {
        div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) p {
            color: white;
        }
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) p {

    }

    </style>
""",
    unsafe_allow_html=True,
)
