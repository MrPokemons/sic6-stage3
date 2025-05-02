import streamlit as st
import requests
from pathlib import Path
import pandas as pd
from bson.json_util import dumps
from dateutil import parser
from datetime import datetime
from pymongo import MongoClient
from streamlitViews.utils.session import Session


ROOT_PATH = Path(__file__).parents[1]


if 'deviceId' not in st.session_state:
    st.session_state.deviceId = False
if 'page' not in st.session_state:
    st.session_state.page = 0

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


# st.title("PawPal 🐾")
st.image(ROOT_PATH / "streamlitViews" / "image" / "logo.png")

if not st.session_state.deviceId:
    with st.form("device_id_form"):
        deviceIdInput = st.text_input("No. ID Perangkat", "")
        st.session_state.deviceId = deviceIdInput
        saveDeviceId = st.form_submit_button("Cari percakapan terakhir")

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId
    page = st.session_state.page

    print("\ndevice id ", deviceId)
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
        _collection = _db["pawpal-conversation-2"]
        list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
        st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

    if not list_conversation:
        st.error("No conversation ever recorded from the provided device id")
        st.info(
            "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `cincayla`"
        )
        st.stop()

    
    # st.json(dumps(list_conversation))  
    current_conversastion = list_conversation[-page-1]
    # print(current_conversastion)
    
    # sessionTitle = []
    # messageResult = []
    # session = Session()
    listSession = []
    for session in current_conversastion["sessions"]:
        # dummyMsg.clear()
        title = session["type"]
        result = session["result"]

        convoStartTime = result["start_datetime"]
        convoStartTime = parser.isoparse(convoStartTime)
        convoStartTimeDate = convoStartTime.strftime("%d %B %Y")
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = result["modified_datetime"]
        convoEndTime = parser.isoparse(convoEndTime)
        convoEndTimeHour = convoStartTime.strftime("%H:%M")

        # convoEndTime = datetime.now()
        # for message in reversed(current_conversastion["sessions"][0]["messages"]):
        #     if (
        #         "response_metadata" in message
        #         and "created_at" in message["response_metadata"]
        #     ):
        #         convoEndTime = message["response_metadata"]["created_at"]
        #         break

        #     convoEndTime = parser.isoparse(convoEndTime)
        #     convoEndTimeHour = convoEndTime.strftime("%H:%M")
        #     # convoEndTimeHour = 0

        #     emotion = current_conversastion["sessions"][0]["result"]["emotion"]
        # convoEndTimeHour = 0

        messageResult = []
        for message in session["messages"]:
            # Check message type and handle accordingly
            if isinstance(message, dict):
                if message["type"] == "ai":
                    sender = "ai"
                    text = message["content"]
                elif message["type"] == "human":
                    sender = "user"
                    # Assuming content is a list
                    # if (
                    #     isinstance(message["content"], list)
                    #     and len(message["content"]) > 0
                    # ):
                    text = message["content"][0]["text"]
                    # else:
                    #     text = message["content"]
                else:
                    continue  # Skip other types of messages

                # Append formatted message to the dummyMsg list
                messageResult.append({"sender": sender, "text": text})

        overview = result["extraction"]["overview"]
        emotion = result["extraction"]["emotion"]
        keypoints = result["extraction"]["keypoints"]

        

        newSession = Session(title, convoStartTimeDate, convoStartTimeHour, convoEndTimeHour, messageResult, overview, emotion, keypoints)
        listSession.append(newSession)

    print(listSession)

    
    # -------------------
    



    with st.container():
        pageCol1, pageCol2, pageCol3 = st.columns([1, 14, 1])
        with pageCol1:
            if st.button("←", disabled=st.session_state.page <= 0):
                st.session_state.page -= 1
                st.rerun()

        with pageCol2:
            st.subheader("Riwayat Percakapan")
                
        with pageCol3:
            if st.button("→", disabled=st.session_state.page >= len(list_conversation)-1):
                st.session_state.page += 1
                st.rerun()

    # -------------------
    # st.subheader("Transkrip")
    # with st.expander("💬 Transkrip Percakapan Terakhir"):
    #     for msg in messageResult:
    #         with st.chat_message(msg["sender"]):
    #             st.write(msg["text"])

    

    startDate = listSession[0].date
    endDate = listSession[-1].date
    startTime = listSession[0].startTime
    endTime = listSession[-1].endTime

    if startDate == endDate:
        st.markdown(f"""
        <h3 style="text-align: center; padding-top: 0; padding-bottom: 0.2rem; font-weight:650;">
            🗓️ {startDate}
        </h3>
        <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; font-size: 1.1rem; ">
            ⏰ {startTime} - {endTime} WIB
        </h5>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <h5 style="text-align: center; padding: 0.5rem 0px 1.2rem; ">
            {startDate} {startTime} - {endDate} {endTime}
        </h5>
        """, unsafe_allow_html=True)

    for n, session in enumerate(listSession):
        title_map =  { "talk_to_me" : ("👄", "Talk To Me"), "math_games" : ("🖐️", "Math Adventure"), "spelling_games" : ("🔤", "Spelling Game"),  "would_you_rather" : ("❓", "Would You Rather")}
        _icon, _title = title_map.get(session.title)
        title_modified = "Sesi " + str((n+1)) + " - " + _title

        with st.expander(title_modified, icon=_icon):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Tanggal dan Waktu")
                with st.container(border=True):
                    st.write(f"🗓️ {session.date}  ⏰ {session.startTime} - {session.endTime} WIB")
                    # st.write(f"⏰ {convoStartTimeHour} - {convoEndTimeHour} WIB")
                    # col3, col4 = st.columns(2)
                    # with col3:
                    #     st.write(f"🗓️ {convoStartTimeDate}")
                    # with col4:
                    #     st.write(f"⏰ {convoStartTimeHour} - {convoEndTimeHour} WIB")
            with col2:
                st.subheader("Perasaan")
                emotion_map = {"Happy": "😄 Bahagia", "Sad": "😢 Sedih", "Angry": "😠 Marah", "Afraid": "😨 Takut", "Embarrassed": "", "Loving": "😍 Sayang", "Confused": "😕 Bingung", "Frustrated": "😣 Frustrasi", "Confident": "😎 Percaya Diri", "Proud": "😇 Bangga", "Jealous": "😤 Cemburu", "Relieved": "😌 Lega", "Tired": "😫 Lelah", "Excited": "🤗 Semangat", "Nervous": "😬 Gugup", "Disappointed": "🥺 Kecewa", "Amazed": "🤩 Kagum", "Bored": "😐 Bosan", "Doubtful": "🫤 Ragu"}
                with st.container(border=True):
                    st.write(emotion_map.get(session.emotion.title()))

            st.subheader("Transkrip Percakapan")
            with st.container(height=500):
                
                for msg in session.message: 
                    with st.chat_message(msg["sender"]):
                        st.write(msg["text"])
            
            st.subheader("Ringkasan")
            st.write(session.overview)

            with st.container():
                st.subheader("Poin Utama")
                for keypoint in session.keypoints:
                    st.write("✨ ", keypoint)

    # --------------------
    # custom styling
st.markdown("""
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
        border-color: #31333f33;
        background-color: transparent;
        color: #31333f66;
        cursor: not-allowed;
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
""", unsafe_allow_html=True)
    # -------------------
    # hard coded values
    # karena belum setup backend logic & endpoints for retrieving these kinds of data
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
