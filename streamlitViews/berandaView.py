import json
import pandas as pd
import plotly.express as px
from typing import List
from pathlib import Path
from dateutil import parser

import requests
import streamlit as st
from pymongo import MongoClient
from src.services.pawpal.schemas.document import ConversationDoc

ROOT_PATH = Path(__file__).parents[1]

if "deviceId" not in st.session_state:
    st.session_state.deviceId = None

if "page" not in st.session_state:
    st.session_state.page = 0


# analytics data declaration here
bulan = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

title_map = {
    "talk_to_me": ("👄", "Talk To Me"),
    "math_games": ("🖐️", "Math Adventure"),
    "guess_the_sound": ("🔊", "Guess The Sound"),
    "would_you_rather": ("❓", "Would You Rather"),
}

emotion_map = {
    "Happy": "😄 Bahagia",
    "Sad": "😢 Sedih",
    "Angry": "😠 Marah",
    "Afraid": "😨 Takut",
    "Embarrassed": "",
    "Loving": "😍 Sayang",
    "Confused": "😕 Bingung",
    "Frustrated": "😣 Frustrasi",
    "Confident": "😎 Percaya Diri",
    "Proud": "😇 Bangga",
    "Jealous": "😤 Cemburu",
    "Relieved": "😌 Lega",
    "Tired": "😫 Lelah",
    "Excited": "🤗 Semangat",
    "Nervous": "😬 Gugup",
    "Disappointed": "🥺 Kecewa",
    "Amazed": "🤩 Kagum",
    "Bored": "😐 Bosan",
    "Doubtful": "🫤 Ragu",
}

color_map = {"Benar": "green", "Salah": "red", "Tidak Menjawab": "gray"}


# st.title("PawPal 🐾")
st.image(ROOT_PATH / "streamlitViews" / "image" / "logo.png")

with st.form("device_id_form"):
    deviceIdInput = st.text_input(
        "No. ID Perangkat", value=st.session_state.deviceId or ""
    )
    st.session_state.deviceId = deviceIdInput
    saveDeviceId = st.form_submit_button("Cari percakapan terakhir")

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId
    page = st.session_state.page

    list_conversation = None
    # try:
    #     resp = requests.get(
    #         f"http://localhost:11080/api/v1/pawpal/conversation/{deviceId}"
    #     )
    #     if resp.status_code == 200:
    #         list_conversation = resp.json()
    # except Exception:
    #     pass

    # backend offline, connect to read-only demo purposes mongodb
    if list_conversation is None:
        _client = MongoClient(
            "mongodb+srv://pawpal-demo-user:p78Q4EsqPfLmnvtb@sic-cluster.hcqho.mongodb.net/?retryWrites=true&w=majority&appName=SIC-Cluster"
        )
        _db = _client["pawpal_v2"]
        _collection = _db["pawpal-conversation-2_1"]
        list_conversation: list = sorted(_collection.find({"device_id": deviceId}).to_list(), key=lambda x: x["created_datetime"], reverse=True)
        st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

    # last mode, use the static
    if list_conversation is None:
        try:
            with open("data/json/example.json", "r") as f:
                list_conversation = json.load(f)
                list_conversation = sorted(list_conversation, key=lambda x: x["created_datetime"], reverse=True)
        except FileNotFoundError:
            pass

    if not list_conversation:
        st.error("No conversation ever recorded from the provided device id")
        st.info(
            "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `cincayla`"
        )
        st.stop()

    list_conversation: List[ConversationDoc] = [
        ConversationDoc.model_validate(convo) for convo in list_conversation
    ]

    # st.json([i.model_dump(mode="json") for i in list_conversation])

    with st.container():
        pageCol1, pageCol2, pageCol3 = st.columns([1, 14, 1])
        with pageCol1:
            if st.button("←", disabled=st.session_state.page <= 0):
                st.session_state.page -= 1
                st.rerun()

        with pageCol2:
            st.subheader("Riwayat Percakapan")

        with pageCol3:
            if st.button(
                "→", disabled=st.session_state.page >= len(list_conversation) - 1
            ):
                st.session_state.page += 1
                st.rerun()

    currentConversation: ConversationDoc = list_conversation[-page - 1]
    currentDateTime = parser.isoparse(currentConversation.created_datetime)
    currentDate = (
        f"{currentDateTime.day} {bulan[currentDateTime.month]} {currentDateTime.year}"
    )
    currentTime = currentDateTime.strftime("%H:%M")

    if currentConversation.sessions:
        startDateTime = currentConversation.sessions[0].result.start_datetime
        endDateTime = currentConversation.sessions[-1].result.modified_datetime

        startDate = (
            f"{startDateTime.day} {bulan[startDateTime.month]} {startDateTime.year}"
        )
        startTime = startDateTime.strftime("%H:%M")

        endDate = f"{endDateTime.day} {bulan[endDateTime.month]} {endDateTime.year}"
        endTime = startDateTime.strftime("%H:%M")

        if startDate == endDate:
            st.markdown(
                f"""
            <h3 style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                🗓️ {startDate}
            </h3>
            <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
                ⏰ {startTime} - {endTime} WIB
            </h5>
            """,
                unsafe_allow_html=True,
            )
        else:
            col1, col2, col3, col4, col5 = st.columns([2, 5, 1, 5, 2])
            with col2:
                st.markdown(
                    f"""
                    <h3 style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                        🗓️ {startDate}
                    </h3>
                    <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
                        ⏰ {startTime} WIB
                    </h5>
                    """,
                    unsafe_allow_html=True,
                )
            with col3:
                st.subheader("-")
            with col4:
                st.markdown(
                    f"""
                    <h3 style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                        🗓️ {endDate}
                    </h3>
                    <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
                        ⏰ {endTime} WIB
                    </h5>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            f"""
            <h3 style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                🗓️ {currentDate}
            </h3>
            <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
                ⏰ {currentTime} WIB
            </h5>
            """,
            unsafe_allow_html=True,
        )
        st.error("Sesi belum dimulai")

    for n, session in enumerate(currentConversation.sessions):
        convoStartTime = session.result.start_datetime
        convoStartTimeDate = (
            f"{convoStartTime.day} {bulan[convoStartTime.month]} {convoStartTime.year}"
        )
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = session.result.modified_datetime
        convoEndTimeHour = convoEndTime.strftime("%H:%M")

        messageResult = []
        for message in session.messages:
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
        # SHOW DATA

        _icon, _title = title_map.get(session.type)
        title_modified = "Sesi " + str(n + 1) + " - " + _title

        with st.expander(title_modified, icon=_icon):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Tanggal dan Waktu")
                with st.container(border=True):
                    st.write(
                        f"🗓️ {convoStartTimeDate}  ⏰ {convoStartTimeHour} - {convoEndTimeHour} WIB"
                    )
            with col2:
                st.subheader("Perasaan")
                with st.container(border=True):
                    st.write(emotion_map.get(session.result.extraction.emotion))

            st.subheader("Transkrip Percakapan")
            with st.container(height=500):
                for msg in messageResult:
                    with st.chat_message(msg["sender"]):
                        st.write(msg["text"])

            session_result = session.result
            if session_result is None:
                continue

            st.subheader("Ringkasan")
            st.write(session_result.extraction.overview)

            with st.container():
                st.subheader("Poin Utama")
                for keypoint in session_result.extraction.keypoints:
                    st.write("✨ ", keypoint)

            if session.type == "math_games":
                totalCorrect = 0
                totalWrong = 0
                totalBlank = 0

                listEquation = []
                listAttemp = []
                st.subheader("Hasil Menghitung")

                for i, qna in enumerate(session_result.list_qna):
                    listAnswer = []
                    listCorrection = []
                    equation = []
                    for n, number in enumerate(qna.sequence):
                        equation.append(
                            "+" if number >= 0 else "-"
                        )  # order matters, if negative then infront
                        equation.append(str(abs(number)))

                    for n, userAnswer in enumerate(qna.user_answers):
                        answer = userAnswer.extraction.result
                        correction = qna.is_correct(index=n)
                        correction = "✅" if correction else ("⚪" if answer is None else "❌")
                        if answer is None:
                            answer = "Tidak Menjawab"
                        listAnswer.append(answer)
                        listCorrection.append(correction)

                    equation_fmt = " ".join(equation).strip(
                        " +"
                    )  # clear the front if its either space or +

                    listAnswer_fmt = ", ".join(map(str, listAnswer)).strip()
                    listCorrection_fmt = ", ".join(map(str, listCorrection)).strip()
                    listEquation.append(
                        {
                            "Pertanyaan": equation_fmt,
                            "Jawaban Anak": listAnswer_fmt,
                            "Koreksi": listCorrection_fmt,
                        }
                    )

                    if listCorrection[-1] == "✅":
                        totalCorrect += 1
                    elif listCorrection[-1] == "❌":
                        totalWrong += 1
                    else:
                        totalBlank += 1

                    listAttemp.append(
                        {
                            "Percobaan": "Pertanyaan " + str(i + 1),
                            "Benar": listCorrection.count("✅"),
                            "Salah": listCorrection.count("❌"),
                            "Tidak Menjawab": listCorrection.count("⚪"),
                        }
                    )
                    # st.write(listCorrection)
                    # st.write(listAttemp)

                # Show Pie Chart
                equationResultTable = pd.DataFrame(listEquation)
                equationResultTable.index += 1
                st.table(equationResultTable)

                data = {
                    "Kategori": ["Benar", "Salah", "Tidak Menjawab"],
                    "Jumlah": [totalCorrect, totalWrong, totalBlank],
                }
                fig = px.pie(
                    data,
                    names="Kategori",
                    values="Jumlah",
                    title="Persentase Akurasi",
                    color="Kategori",
                    color_discrete_map=color_map,
                )
                st.plotly_chart(fig, key="math_games-pie_chart")

                # Show Bar Chart
                df = pd.DataFrame(listAttemp)
                fig = px.bar(
                    df,
                    x="Percobaan",
                    y=["Benar", "Salah", "Tidak Menjawab"],
                    title="Akurasi Jawaban pada Setiap Percobaan Matematika"
                )
                st.plotly_chart(fig, key="math_games-bar_chart")

            elif session.type == "guess_the_sound":
                totalCorrect = 0
                totalWrong = 0
                totalBlank = 0

                listSound = []  # i guess assuming the sound is fixed?
                listAttemp = []
                listEquation = []
                st.subheader("Hasil Menebak")

                for i, qna in enumerate(session_result.list_qna):
                    listAnswer = []
                    listCorrection = []
                    for n, userAnswer in enumerate(qna.user_answers):
                        answer = userAnswer.extraction.result
                        correction = qna.is_correct(index=n)
                        correction = "✅" if correction else ("⚪" if answer is None else "❌")
                        if answer is None:
                            answer = "Tidak Menjawab"
                        listAnswer.append(answer)
                        listCorrection.append(correction)

                    listSound.append(qna.sound_path)

                    listAnswer_fmt = ", ".join(map(str, listAnswer)).strip()
                    listCorrection_fmt = ", ".join(map(str, listCorrection)).strip()
                    listEquation.append(
                        {
                            "Sound": qna.sound_path,
                            "Jawaban Anak": listAnswer_fmt,
                            "Koreksi": listCorrection_fmt,
                        }
                    )

                    if listCorrection[-1] == "✅":
                        totalCorrect += 1
                    elif listCorrection[-1] == "❌":
                        totalWrong += 1
                    else:
                        totalBlank += 1

                    listAttemp.append(
                        {
                            "Percobaan": "Suara " + str(i + 1),
                            "Benar": listCorrection.count("✅"),
                            "Salah": listCorrection.count("❌"),
                            "Tidak Menjawab": listCorrection.count("⚪"),
                        }
                    )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("#### Suara")
                    for guessSound in listEquation:
                        st.audio(guessSound["Sound"])
                with col2:
                    st.markdown("#### Jawaban Anak")
                    for guessSound in listEquation:
                        st.write(guessSound["Jawaban Anak"])
                with col3:
                    st.markdown("#### Koreksi")
                    for guessSound in listEquation:
                        st.write(guessSound["Koreksi"])

                # show pie chart
                data = {
                    "Kategori": ["Benar", "Salah", "Tidak Menjawab"],
                    "Jumlah": [totalCorrect, totalWrong, totalBlank],
                }
                fig = px.pie(
                    data,
                    names="Kategori",
                    values="Jumlah",
                    title="Persentase Akurasi",
                    color="Kategori",
                    color_discrete_map=color_map,
                )
                st.plotly_chart(fig, key="guess_the_sound-pie_chart")

                # Show Bar Chart
                df = pd.DataFrame(listAttemp)
                fig = px.bar(
                    df,
                    x="Percobaan",
                    y=["Benar", "Salah", "Tidak Menjawab"],
                    title="Akurasi Jawaban pada Setiap Percobaan Menebak Suara",
                )
                st.plotly_chart(fig, key="guess_the_sound-bar_chart")

    # --------------------
    # custom styling
st.markdown(
    """
<style>
    h3#riwayat-percakapan{
        text-align: center;
        padding: 0;
    }

    div[data-testid="stFullScreenFrame"] img {
        width: 20vw;
    }

    button:hover{
        border-color: #1e5677 !important;
        color: #1e5677 !important;
    }

    button:disabled:hover{
        border-color: #31333f33 !important;
        background-color: transparent !important;
        color: #31333f66 !important;
        cursor: not-allowed !important;
    }

    button:active{
        background-color: #1e5677 !important;
        color: white !important;
    }

    button:focus:not(:active) {
        border-color: #1e5677 !important;
        color: #1e5677 !important;
    }

    summary:hover {
        color: #1e5677 !important;
    }

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
        margin-left: 4rem;
        background-color: #1e5677;
    }

    div[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarAssistant"] svg {
        color: white;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        margin-right: 4rem;
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


# # -------------------
# # hard coded values
# # karena belum setup backend logic & endpoints for retrieving these kinds of data, below just temporary
# # -------------------

# wordDictionary = {
#     "Kata Asli": [
#         "Kucing",
#         "Mobil",
#         "Makan",
#         "Tidur",
#         "Minum",
#         "Sepeda",
#         "Sekolah",
#         "Buku",
#         "Pensil",
#         "Hujan",
#     ],
#     "Pelafalan Anak": [
#         "Cicing",
#         "Obil",
#         "Maka",
#         "Tiduh",
#         "Minuh",
#         "Sepeda",
#         "Sekola",
#         "Buku",
#         "Pensel",
#         "Ujan",
#     ],
#     "Koreksi": ["✅", "✅", "✅", "✅", "❌", "✅", "✅", "✅", "❌", "✅"],
# }

# mathDictionary = {
#     "Pertanyaan": [
#         "1 + 1?",
#         "2 + 3?",
#         "4 - 2?",
#         "5 x 2?",
#         "10 : 2?",
#         "3 + 5?",
#         "9 - 4?",
#         "6 x 3?",
#         "12 : 4?",
#         "7 + 8?",
#     ],
#     "Jawaban Anak": ["2", "4", "2", "12", "5", "7", "5", "18", "2", "15"],
#     "Koreksi": ["✅", "❌", "✅", "❌", "✅", "❌", "✅", "✅", "❌", "✅"],
# }

# reasoningGames = {
#     "Pertanyaan": [
#         "Kamu lebih suka hidup di dunia penuh dinosaurus atau penuh robot?",
#         "Kalau bisa pilih satu hewan jadi hewan peliharaan, kamu pilih apa dan kenapa?",
#         "Lebih enak liburan di pegunungan atau di kota besar? Kenapa?",
#         "Kalau bisa mengulang waktu, kamu mau kembali ke masa kapan?",
#         "Kalau kamu jadi presiden, hal pertama yang ingin kamu ubah apa?",
#         "Kamu lebih suka bisa berbicara semua bahasa di dunia, atau bisa bermain semua alat musik?",
#         "Kalau ada pintu ajaib, kamu mau pergi ke mana?",
#         "Lebih suka punya taman bermain di rumah atau kolam renang pribadi?",
#         "Kalau kamu bisa membuat mainan impianmu, mainan seperti apa yang kamu buat?",
#         "Kamu lebih suka membaca pikiran orang lain, atau bisa melihat masa depan?",
#     ],
#     "Contoh Jawaban Anak": [
#         "Dunia robot, karena keren dan canggih!",
#         "Panda, karena gemesin dan lucu banget!",
#         "",
#         "Waktu ulang tahun aku, karena seru dan dapat kado",
#         "Semua anak sekolah gratis!",
#         "Main semua alat musik, bisa bikin band sendiri!",
#         "",
#         "Taman bermain! Biar bisa main sepuasnya tiap hari!",
#         "",
#         "Melihat masa depan, biar tahu nanti aku jadi apa",
#     ],
#     "Status": ["✅", "✅", "❌", "✅", "✅", "✅", "❌", "✅", "❌", "✅"],
# }

# dummyMsg = [
#     {"sender": "user", "text": "Hai, kamu lagi apa?"},
#     {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
#     {"sender": "user", "text": "Oke siap~"},
# ]

# st.subheader("Spelling Games 🔤")
# # dictionary columns
# # declare tables and columns
# wordDictTable = pd.DataFrame(wordDictionary)
# mathDictTable = pd.DataFrame(mathDictionary)
# reasoningGamesTable = pd.DataFrame(reasoningGames)

# wdt = pd.DataFrame(wordDictTable)
# wdt.index += 1
# mdt = pd.DataFrame(mathDictionary)
# mdt.index += 1
# rgt = pd.DataFrame(reasoningGamesTable)
# rgt.index += 1

# st.table(wdt)

# st.subheader("Math Adventures 🖐️")
# st.table(mdt)

# st.subheader("Reasoning Games 🧠")
# st.dataframe(rgt)

# col1, col2, col3 = st.columns(3)
# with col1:
#     st.table(wdt)
# with col2:
#     st.table(mdt)
# with col3:
#     st.table(rgt)
