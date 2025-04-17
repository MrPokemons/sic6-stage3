import streamlit as st
import requests
import pandas as pd
from dateutil import parser
from datetime import datetime

# analytics data declaration here

wordDictionary = {
    "Kata Asli": ["Adel", "Data 2", "Data 3"],
    "Pelafalan Anak": ["Value 1", "Value 2", "Value 3"],
}

mathDictionary = {
    "Pertanyaan": ["Data 1", "Data 2", "Data 3"],
    "Jawaban Anak": ["Value 1", "Value 2", "Value 3"],
}

dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]


st.title("PawPal 🐾")

deviceId = st.text_input("No. ID Perangkat", "")
if st.button("Cari percakapan terakhir", type="primary"):
    resp = requests.get(f"http://localhost:11080/api/v1/pawpal/conversation/{deviceId}")
    list_conversation = resp.json()
    if not list_conversation:
        st.error("No conversation ever recorded from the provided device id")
        st.stop()

    lastConversation = list_conversation[0]
    print(lastConversation)

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

    # -------------------
    st.subheader("Transkrip")
    with st.expander("💬 Transkrip Percakapan Terakhir"):
        for msg in dummyMsg:
            with st.chat_message(msg["sender"]):
                st.write(msg["text"])

    # -------------------
    # hard coded values
    # karena belum setup backend logic & endpoints for retrieving these kinds of data
    st.subheader("Analytic")
    # dictionary columns
    # declare tables and columns
    wdt = pd.DataFrame(wordDictionary)
    wdt.index += 1
    mdt = pd.DataFrame(mathDictionary)
    mdt.index += 1

    col1, col2 = st.columns(2)
    with col1:
        st.table(wdt)
    with col2:
        st.table(mdt)
