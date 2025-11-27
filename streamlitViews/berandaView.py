import json
import pandas as pd
import pytz
import plotly.express as px
from typing import List
from pathlib import Path
from dateutil import parser
from urllib.parse import urljoin
import requests
import streamlit as st
from pymongo import MongoClient

from src.services.pawpal.schemas.document import ConversationDoc
from config.settings import SETTINGS
from streamlitViews.language_utils import render_language_toggle, get_current_language
from streamlitViews.translations import get_text, get_month, get_emotion, get_answer_category


USER_TIMEZONE = pytz.timezone("Asia/Bangkok")

ROOT_PATH = Path(__file__).parents[1]

# Render language toggle in sidebar
render_language_toggle()

# Get current language
lang = get_current_language()

if "deviceId" not in st.session_state:
    st.session_state.deviceId = None

if "page" not in st.session_state:
    st.session_state.page = 0


title_map = {
    "talk_to_me": ("👄", "Talk To Me"),
    "math_games": ("🖐️", "Math Adventure"),
    "guess_the_sound": ("🔊", "Guess The Sound"),
    "would_you_rather": ("❓", "Would You Rather"),
}

# Create color map based on current language
color_map = {
    get_answer_category("Benar", lang): "green",
    get_answer_category("Salah", lang): "red",
    get_answer_category("Tidak Menjawab", lang): "gray"
}


# st.title("PawPal 🐾")
st.image(ROOT_PATH / "streamlitViews" / "image" / "logo.png")

with st.form("device_id_form"):
    deviceIdInput = st.text_input(
        get_text("common.device_id", lang), value=st.session_state.deviceId or ""
    )
    st.session_state.deviceId = deviceIdInput
    saveDeviceId = st.form_submit_button(get_text("common.search_last_conversation", lang))

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId
    page = st.session_state.page

    list_conversation = None
    try:
        resp = requests.get(urljoin(SETTINGS.APP.DOMAIN, f"/api/v1/pawpal/conversation/{deviceId}"))
        if resp.status_code == 200:
            list_conversation = resp.json()
    except Exception:
        pass

    # backend offline, connect to read-only demo purposes mongodb
    if list_conversation is None and SETTINGS.MONGODB.MOCK_CONN_URI:
        _client = MongoClient(SETTINGS.MONGODB.MOCK_CONN_URI)
        _db = _client["pawpal_v2"]
        _collection = _db["pawpal-conversation-2_1"]
        list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
        # st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

    # last mode, use the static
    if list_conversation is None:
        try:
            with open("data/json/example.json", "r") as f:
                list_conversation = json.load(f)
        except FileNotFoundError:
            pass

    if not list_conversation:
        st.error(get_text("beranda.no_conversation", lang))
        st.info(get_text("beranda.demo_info", lang))
        st.stop()

    list_conversation: List[ConversationDoc] = [
        ConversationDoc.model_validate(convo) for convo in list_conversation
    ]

    list_conversation = sorted(
        list_conversation,
        key=lambda x: x.created_datetime,
        reverse=True,
    )

    with st.container():
        pageCol1, pageCol2, pageCol3 = st.columns([1, 14, 1])
        with pageCol1:
            if st.button("←", disabled=st.session_state.page <= 0):
                st.session_state.page -= 1
                st.session_state.page = max(st.session_state.page, 0)
                st.rerun()

        with pageCol2:
            st.subheader(get_text("beranda.conversation_history", lang))

        with pageCol3:
            if st.button(
                "→", disabled=st.session_state.page >= len(list_conversation) - 1
            ):
                st.session_state.page += 1
                st.session_state.page = min(st.session_state.page, len(list_conversation) - 1)
                st.rerun()

    currentConversation: ConversationDoc = list_conversation[page]
    currentDateTime = parser.isoparse(currentConversation.created_datetime).astimezone(USER_TIMEZONE)
    currentDate = (
        f"{currentDateTime.day} {get_month(currentDateTime.month, lang)} {currentDateTime.year}"
    )
    currentTime = currentDateTime.strftime("%H:%M")

    if currentConversation.sessions:
        startDateTime = currentConversation.sessions[0].result.start_datetime.astimezone(USER_TIMEZONE)
        endDateTime = next(_ses for _ses in currentConversation.sessions[::-1] if _ses.result).result.modified_datetime.astimezone(USER_TIMEZONE)

        startDate = (
            f"{startDateTime.day} {get_month(startDateTime.month, lang)} {startDateTime.year}"
        )
        startTime = startDateTime.strftime("%H:%M")

        endDate = f"{endDateTime.day} {get_month(endDateTime.month, lang)} {endDateTime.year}"
        endTime = endDateTime.strftime("%H:%M")

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
                    <h3 class="date-header" style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                        🗓️ {startDate}
                    </h3>
                    <h5 class="time-header" style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
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
                    <h3 class="date-header" style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
                        🗓️ {endDate}
                    </h3>
                    <h5 class="time-header" style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
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
        st.error(get_text("beranda.session_not_started", lang))

    for n, session in enumerate(currentConversation.sessions):
        if session.result is None:
            continue

        convoStartTime = session.result.start_datetime.astimezone(USER_TIMEZONE)
        convoStartTimeDate = (
            f"{convoStartTime.day} {get_month(convoStartTime.month, lang)} {convoStartTime.year}"
        )
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = session.result.modified_datetime.astimezone(USER_TIMEZONE)
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
        title_modified = get_text("beranda.session", lang) + " " + str(n + 1) + " - " + _title

        with st.expander(title_modified, icon=_icon):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader(get_text("beranda.date_and_time", lang))
                with st.container(border=True):
                    st.write(
                        f"🗓️ {convoStartTimeDate}  ⏰ {convoStartTimeHour} - {convoEndTimeHour} WIB"
                    )
            with col2:
                st.subheader(get_text("beranda.feeling", lang))
                with st.container(border=True):
                    st.write(get_emotion(session.result.extraction.emotion, lang))

            st.subheader(get_text("beranda.conversation_transcript", lang))
            with st.container(height=500):
                for msg in messageResult:
                    with st.chat_message(msg["sender"]):
                        st.write(msg["text"])

            session_result = session.result
            if session_result is None:
                continue

            st.subheader(get_text("beranda.summary", lang))
            st.write(session_result.extraction.overview)

            with st.container():
                st.subheader(get_text("beranda.key_points", lang))
                for keypoint in session_result.extraction.keypoints:
                    st.write("✨ ", keypoint)

            if session.type == "math_games":
                totalCorrect = 0
                totalWrong = 0
                totalBlank = 0

                listEquation = []
                listAttemp = []
                st.subheader(get_text("beranda.math_results", lang))

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
                        correction = (
                            "✅" if correction else ("⚪" if answer is None else "❌")
                        )
                        if answer is None:
                            answer = get_answer_category("Tidak Menjawab", lang)
                        listAnswer.append(answer)
                        listCorrection.append(correction)

                    equation_fmt = " ".join(equation).strip(
                        " +"
                    )  # clear the front if its either space or +

                    listAnswer_fmt = ", ".join(map(str, listAnswer)).strip()
                    listCorrection_fmt = ", ".join(map(str, listCorrection)).strip()
                    listEquation.append(
                        {
                            get_text("beranda.question", lang): equation_fmt,
                            get_text("beranda.child_answer", lang): listAnswer_fmt,
                            get_text("beranda.correction", lang): listCorrection_fmt,
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
                            get_text("beranda.attempt", lang): get_text("beranda.question", lang) + " " + str(i + 1),
                            get_answer_category("Benar", lang): listCorrection.count("✅"),
                            get_answer_category("Salah", lang): listCorrection.count("❌"),
                            get_answer_category("Tidak Menjawab", lang): listCorrection.count("⚪"),
                        }
                    )
                    # st.write(listCorrection)
                    # st.write(listAttemp)

                # Show Pie Chart
                equationResultTable = pd.DataFrame(listEquation)
                equationResultTable.index += 1
                st.table(equationResultTable)

                data = {
                    get_text("beranda.category", lang): [
                        get_answer_category("Benar", lang),
                        get_answer_category("Salah", lang),
                        get_answer_category("Tidak Menjawab", lang)
                    ],
                    get_text("beranda.total", lang): [totalCorrect, totalWrong, totalBlank],
                }
                fig = px.pie(
                    data,
                    names=get_text("beranda.category", lang),
                    values=get_text("beranda.total", lang),
                    title=get_text("beranda.accuracy_percentage", lang),
                    color=get_text("beranda.category", lang),
                    color_discrete_map=color_map,
                )
                st.plotly_chart(fig, key="math_games-pie_chart")

                # Show Bar Chart
                df = pd.DataFrame(listAttemp)
                df_long = df.melt(
                    id_vars=get_text("beranda.attempt", lang),
                    value_vars=[
                        get_answer_category("Benar", lang),
                        get_answer_category("Salah", lang),
                        get_answer_category("Tidak Menjawab", lang)
                    ],
                    var_name=get_text("beranda.category", lang),
                    value_name=get_text("beranda.total_questions", lang),
                )
                fig = px.bar(
                    df_long,
                    x=get_text("beranda.attempt", lang),
                    y=get_text("beranda.total_questions", lang),
                    color=get_text("beranda.category", lang),
                    color_discrete_map=color_map,
                    title=get_text("beranda.accuracy_per_attempt", lang),
                )
                st.plotly_chart(fig, key="math_games-bar_chart")

            elif session.type == "guess_the_sound":
                totalCorrect = 0
                totalWrong = 0
                totalBlank = 0

                listSound = []  # i guess assuming the sound is fixed?
                listAttemp = []
                listGuessSound = []
                st.subheader(get_text("beranda.guess_results", lang))

                for i, qna in enumerate(session_result.list_qna):
                    listAnswer = []
                    listCorrection = []
                    for n, userAnswer in enumerate(qna.user_answers):
                        answer = userAnswer.extraction.result
                        correction = qna.is_correct(index=n)
                        correction = (
                            "✅" if correction else ("⚪" if answer is None else "❌")
                        )
                        if answer is None:
                            answer = get_answer_category("Tidak Menjawab", lang)
                        listAnswer.append(answer)
                        listCorrection.append(correction)

                    listSound.append(qna.sound_path)

                    listAnswer_fmt = ", ".join(map(str, listAnswer)).strip()
                    listCorrection_fmt = ", ".join(map(str, listCorrection)).strip()
                    listGuessSound.append(
                        {
                            get_text("beranda.sound", lang): qna.sound_path,
                            get_text("beranda.child_answer", lang): listAnswer_fmt,
                            get_text("beranda.correction", lang): listCorrection_fmt,
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
                            get_text("beranda.attempt", lang): get_text("beranda.sound", lang) + " " + str(i + 1),
                            get_answer_category("Benar", lang): listCorrection.count("✅"),
                            get_answer_category("Salah", lang): listCorrection.count("❌"),
                            get_answer_category("Tidak Menjawab", lang): listCorrection.count("⚪"),
                        }
                    )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"###### {get_text('beranda.sound', lang)}")
                    for guessSound in listGuessSound:
                        st.audio(guessSound[get_text("beranda.sound", lang)])
                with col2:
                    st.write(f"###### {get_text('beranda.child_answer', lang)}")
                    for guessSound in listGuessSound:
                        st.markdown(
                            f"""
                            <div style="border:1px solid #ccc; padding:10px; border-radius:5px; ">
                                {guessSound[get_text("beranda.child_answer", lang)]}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                with col3:
                    st.write(f"###### {get_text('beranda.correction', lang)}")
                    for guessSound in listGuessSound:
                        st.markdown(
                            f"""
                            <div style="border:1px solid #ccc; padding:10px; border-radius:5px; ">
                                {guessSound[get_text("beranda.correction", lang)]}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                # show pie chart
                data = {
                    get_text("beranda.category", lang): [
                        get_answer_category("Benar", lang),
                        get_answer_category("Salah", lang),
                        get_answer_category("Tidak Menjawab", lang)
                    ],
                    get_text("beranda.total", lang): [totalCorrect, totalWrong, totalBlank],
                }
                fig = px.pie(
                    data,
                    names=get_text("beranda.category", lang),
                    values=get_text("beranda.total", lang),
                    title=get_text("beranda.accuracy_percentage", lang),
                    color=get_text("beranda.category", lang),
                    color_discrete_map=color_map,
                )
                st.plotly_chart(fig, key="guess_the_sound-pie_chart")

                # Show Bar Chart
                df = pd.DataFrame(listAttemp)
                df_long = df.melt(
                    id_vars=get_text("beranda.attempt", lang),
                    value_vars=[
                        get_answer_category("Benar", lang),
                        get_answer_category("Salah", lang),
                        get_answer_category("Tidak Menjawab", lang)
                    ],
                    var_name=get_text("beranda.category", lang),
                    value_name=get_text("beranda.total_questions", lang),
                )
                fig = px.bar(
                    df_long,
                    x=get_text("beranda.attempt", lang),
                    y=get_text("beranda.total_questions", lang),
                    color=get_text("beranda.category", lang),
                    color_discrete_map=color_map,
                    title=get_text("beranda.accuracy_per_sound", lang),
                )
                st.plotly_chart(fig, key="guess_the_sound-bar_chart")

    # --------------------
    # custom styling
st.markdown(
    """
<style>
    @media (max-width: 768px) {

        div[data-testid="stHorizontalBlock"]:has(h3#riwayat-percakapan) div[data-testid="stColumn"]{
            min-width: 0 !important;
        }

        div[data-testid="stHorizontalBlock"]:has(h3#riwayat-percakapan) div[data-testid="stColumn"]:has(h3#riwayat-percakapan){
            width: auto !important;
            flex: auto;
        }

        div[data-testid="stHorizontalBlock"]:has(h3#riwayat-percakapan) div[data-testid="stColumn"]:has(h3#riwayat-percakapan) span[data-testid="stHeaderActionElements"]{
            display: none;
        }


        div[data-testid="stColumn"]:has(.date-header) {
            width: 10vw;
            min-width: 0;
        }

        div[data-testid="stColumn"]:has(.date-header) span{
            display: none;
        }

        div[data-testid="stHorizontalBlock"]:has(.date-header) div[data-testid="stColumn"]:nth-of-type(3){
            width: 20px;
            min-width: 0;
            flex: 0;
        }

        div[data-testid="stHorizontalBlock"]:has(.date-header) div[data-testid="stColumn"]:nth-of-type(3) h3{
            width: 10px;
            line-height: 0.1;
        }

        .date-header {
            font-size: 1.4rem !important;
            width: 40vw !important;
        }

        .time-header {
            font-size: 1rem !important;
            width: 35vw !important;
        }

        div[data-testid="stHorizontalBlock"]:has(h3#riwayat-percakapan){
            gap: 0;
        }

        div[data-testid="stHorizontalBlock"]:has(h3#riwayat-percakapan) div[data-testid="stColumn"] div[data-testid="stVerticalBlock"]:has(h3#riwayat-percakapan){
            width: auto;
        }

        .date-header, .time-header {
            width: 60vw;
        }

        h3#riwayat-percakapan {

        }
    }

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
