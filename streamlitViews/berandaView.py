import streamlit as st
import requests
import pandas as pd
from dateutil import parser
from datetime import datetime
from pymongo import MongoClient

# analytics data declaration here

wordDictionary = {
    "Kata Asli": [
        "Kucing",
        "Mobil",
        "Makan",
        "Tidur",
        "Minum",
        "Sepeda",
        "Sekolah",
        "Buku",
        "Pensil",
        "Hujan",
    ],
    "Pelafalan Anak": [
        "Cicing",
        "Obil",
        "Maka",
        "Tiduh",
        "Minuh",
        "Sepeda",
        "Sekola",
        "Buku",
        "Pensel",
        "Ujan",
    ],
    "Koreksi": ["✅", "✅", "✅", "✅", "❌", "✅", "✅", "✅", "❌", "✅"],
}

mathDictionary = {
    "Pertanyaan": [
        "1 + 1?",
        "2 + 3?",
        "4 - 2?",
        "5 x 2?",
        "10 : 2?",
        "3 + 5?",
        "9 - 4?",
        "6 x 3?",
        "12 : 4?",
        "7 + 8?",
    ],
    "Jawaban Anak": ["2", "4", "2", "12", "5", "7", "5", "18", "2", "15"],
    "Koreksi": ["✅", "❌", "✅", "❌", "✅", "❌", "✅", "✅", "❌", "✅"],
}

reasoningGames = {
    "Pertanyaan": [
        "Kamu lebih suka hidup di dunia penuh dinosaurus atau penuh robot?",
        "Kalau bisa pilih satu hewan jadi hewan peliharaan, kamu pilih apa dan kenapa?",
        "Lebih enak liburan di pegunungan atau di kota besar? Kenapa?",
        "Kalau bisa mengulang waktu, kamu mau kembali ke masa kapan?",
        "Kalau kamu jadi presiden, hal pertama yang ingin kamu ubah apa?",
        "Kamu lebih suka bisa berbicara semua bahasa di dunia, atau bisa bermain semua alat musik?",
        "Kalau ada pintu ajaib, kamu mau pergi ke mana?",
        "Lebih suka punya taman bermain di rumah atau kolam renang pribadi?",
        "Kalau kamu bisa membuat mainan impianmu, mainan seperti apa yang kamu buat?",
        "Kamu lebih suka membaca pikiran orang lain, atau bisa melihat masa depan?",
    ],
    "Contoh Jawaban Anak": [
        "Dunia robot, karena keren dan canggih!",
        "Panda, karena gemesin dan lucu banget!",
        "",
        "Waktu ulang tahun aku, karena seru dan dapat kado",
        "Semua anak sekolah gratis!",
        "Main semua alat musik, bisa bikin band sendiri!",
        "",
        "Taman bermain! Biar bisa main sepuasnya tiap hari!",
        "",
        "Melihat masa depan, biar tahu nanti aku jadi apa",
    ],
    "Status": ["✅", "✅", "❌", "✅", "✅", "✅", "❌", "✅", "❌", "✅"],
}

dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]


st.title("PawPal 🐾")

deviceId = st.text_input("No. ID Perangkat", "")
if st.button("Cari percakapan terakhir", type="primary"):
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
    st.subheader("Spelling Games 🔤")
    # dictionary columns
    # declare tables and columns
    wordDictTable = pd.DataFrame(wordDictionary)
    mathDictTable = pd.DataFrame(mathDictionary)
    reasoningGamesTable = pd.DataFrame(reasoningGames)

    wdt = pd.DataFrame(wordDictTable)
    wdt.index += 1
    mdt = pd.DataFrame(mathDictionary)
    mdt.index += 1
    rgt = pd.DataFrame(reasoningGamesTable)
    rgt.index += 1

    st.table(wdt)

    st.subheader("Math Adventures 🖐️")
    st.table(mdt)

    st.subheader("Reasoning Games 🧠")
    st.dataframe(rgt)

    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     st.table(wdt)
    # with col2:
    #     st.table(mdt)
    # with col3:
    #     st.table(rgt)
