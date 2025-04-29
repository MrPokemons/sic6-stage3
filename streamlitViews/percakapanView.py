import streamlit as st
import requests
import pandas as pd
from dateutil import parser
from datetime import datetime
from pymongo import MongoClient

if 'deviceId' not in st.session_state:
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
    with st.form("device_id_form"):
        deviceIdInput = st.text_input("No. ID Perangkat", "")
        st.session_state.deviceId = deviceIdInput
        saveDeviceId = st.form_submit_button("Cari percakapan terakhir")

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId

    st.subheader("Transkrip")
    with st.container(border=True):
        st.chat_message("user").write("test")
        st.chat_message("ai").write("test")

        list_conversation = None
        try:
            resp = requests.get(
                f"http://localhost:11080/api/v1/pawpal/conversation/{deviceId}"
            )
            if resp.status_code == 200:
                list_conversation = resp.json()
        except Exception:
            pass

        if (
            list_conversation is None
        ):  # backend offline, connect to read-only demo purposes mongodb
            _client = MongoClient(
                "mongodb+srv://pawpal-demo-user:p78Q4EsqPfLmnvtb@sic-cluster.hcqho.mongodb.net/?retryWrites=true&w=majority&appName=SIC-Cluster"
            )
            _db = _client["pawpal_v2"]
            _collection = _db["pawpal-conversation"]
            list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
            st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

        if not list_conversation:
            st.error("No conversation ever recorded from the provided device id")
            st.info(
                "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `2b129436-1a2d-11f0-9045-6ac49b7e4ceb`"
            )
            st.stop()

        list_conversation = sorted(
            list_conversation, key=lambda x: x["created_datetime"], reverse=True
        )
        lastConversation = list_conversation[0]
        # print(lastConversation)
        # print("SESSIONNN ?? ", lastConversation["sessions"])

        for session in lastConversation["sessions"]:
            dummyMsg.clear()
            for message in session["messages"]:
                # Check message type and handle accordingly
                if isinstance(message, dict):
                    if message["type"] == "ai":
                        sender = "bot"
                        text = message["content"]
                    elif message["type"] == "human":
                        sender = "user"
                        # Assuming content is a list
                        if (
                            isinstance(message["content"], list)
                            and len(message["content"]) > 0
                        ):
                            text = message["content"][0]["text"]
                        else:
                            text = message["content"]
                    else:
                        continue  # Skip other types of messages

                    # Append formatted message to the dummyMsg list
                    dummyMsg.append({"sender": sender, "text": text})

        # -------------------
        convoStartTime = lastConversation["sessions"][0]["messages"][2][
            "response_metadata"
        ]["created_at"]
        convoStartTime = parser.isoparse(convoStartTime)
        convoStartTimeDate = convoStartTime.strftime("%d %B %Y")
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = datetime.now()
        for message in reversed(lastConversation["sessions"][0]["messages"]):
            if (
                "response_metadata" in message
                and "created_at" in message["response_metadata"]
            ):
                convoEndTime = message["response_metadata"]["created_at"]
                break

        convoEndTime = parser.isoparse(convoEndTime)
        convoEndTimeHour = convoEndTime.strftime("%H:%M")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Percakapan Terakhir")
            st.markdown(
                f"""
            <div style="
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                font-family: 'Helvetica', sans-serif;
                line-height: 1.6;
                padding-bottom: 20px;
            ">
                <div style="margin-bottom: 6px">
                    <span style="margin-right: 20px;">🗓️ {convoStartTimeDate}</span>
                    <span>⏰ {convoStartTimeHour} - {convoEndTimeHour}</span>
                    </div>
            </div>
        """,
                unsafe_allow_html=True,
            )
        with col2:
            st.subheader("Perasaan")
            st.markdown(
                """
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
            """,
                unsafe_allow_html=True,
            )

# with st.expander("💬 Transkrip Percakapan"):
    # if dummyMsg:
    #     for msg in dummyMsg:
    #         with st.chat_message(msg["sender"]):
    #             st.write(msg["text"])
    # else:
    #     st.write("Belum ada percakapan yang dimulai!")