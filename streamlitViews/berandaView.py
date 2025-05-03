import streamlit as st
import requests
from typing import List, Optional
from pathlib import Path
import pandas as pd
import json
from dateutil import parser
from datetime import datetime
from pymongo import MongoClient
from streamlitViews.utils.session import Session
from src.services.pawpal.schemas.document import ConversationDoc
from src.services.pawpal.schemas.topic import MathQnA, TopicResultsType


ROOT_PATH = Path(__file__).parents[1]

if "urlBackend" not in st.session_state:
    st.session_state.urlBackend = False
if "deviceId" not in st.session_state:
    st.session_state.deviceId = False
if "page" not in st.session_state:
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
    12: "Desember"
}

title_map = {
    "talk_to_me": ("👄", "Talk To Me"),
    "math_games": ("🖐️", "Math Adventure"),
    "guess_the_sound": ("🔤", "Spelling Game"),
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


# st.title("PawPal 🐾")
st.image(ROOT_PATH / "streamlitViews" / "image" / "logo.png")

if not st.session_state.deviceId:
    with st.form("device_id_form"):
        deviceIdInput = st.text_input("No. ID Perangkat", "")
        st.session_state.deviceId = deviceIdInput
        saveDeviceId = st.form_submit_button("Cari percakapan terakhir")

if not st.session_state.urlBackend:
    with st.form("url_backend_form"):
        deviceIdInput = st.text_input("URL Backend", "")
        st.session_state.deviceId = deviceIdInput
        saveDeviceId = st.form_submit_button("Simpan")

if st.session_state.deviceId:
    deviceId = st.session_state.deviceId
    page = st.session_state.page

    

    print("\ndevice id ", deviceId)
    list_conversation = None
    # try:
    #     resp = requests.get(
    #         f"http://localhost:11080/api/v1/pawpal/conversation/{deviceId}"
    #     )
    #     if resp.status_code == 200:
    #         list_conversation = resp.json()
    # except Exception:
    #     pass

    # if (
        # list_conversation is None
    # ):  # backend offline, connect to read-only demo purposes mongodb
        # _client = MongoClient(
        #     "mongodb+srv://pawpal-demo-user:p78Q4EsqPfLmnvtb@sic-cluster.hcqho.mongodb.net/?retryWrites=true&w=majority&appName=SIC-Cluster"
        # )
        # _db = _client["pawpal_v2"]
        # _collection = _db["pawpal-conversation-2"]
        # list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
        # st.warning("Backend tidak aktif, maka menggunakan alternatif database.")
    list_conversation = [
        {
            "_id": {
                "$oid": "68143446d0cff0ed103b1865"
            },
            "id": "68143446d0cff0ed103b1865",
            "device_id": "cincayla",
            "user": {
                "name": "Adeline",
                "gender": "female",
                "age": 5,
                "description": "suka menggambar, suka kucing",
                "language": "Indonesian"
            },
            "feature_params": {
                "talk_to_me": {
                    "duration": 300
                },
                "math_game": {
                    "total_question": 2
                },
                "guess_the_sound": {
                    "total_question": 5
                },
                "would_you_rather": {
                    "duration": 5
                }
            },
            "selected_features": [
                "talk_to_me",
                "math_games"
            ],
            "total_sessions": 2,
            "sessions": [
                {
                    "type": "talk_to_me",
                    "messages": [
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Introduce the \"Math Game\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Start the “Math Game” session with a short, warm greeting in the child’s language. Gently invite them to share how they’re feeling, how their day has been, or anything they’d like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I’d really love to know.\"  \n- \"What’s something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you’d like to talk about?\"  \n- \"What’s something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child’s age and mood, and always speak in the child’s language."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adeline, udah siapkan bayangan dan kucing-kucingan tercinta? Saya sudah menungguku dengan antusias. Bagaimana ya, ada sesuatu yang lucu atau aneh tentang hari ini yang ingin kamu ceritakan? Yuk kita mulai dari **Math Game**!",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:00:48.243211Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -1560118005,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 401566500,
                                "prompt_eval_count": 1123,
                                "prompt_eval_duration": 1283027208,
                                "eval_count": 71,
                                "eval_duration": 1035544208,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-b5b96bde-ef43-4e02-bf07-dabdfbbb32e2-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Halo namaku Adlin. Aku suka menggambar kucing karena kucing hewan kesukaanku."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Selamat ya, Adelin. Senang mendengar bahwa kau suka menggambar kucingmu. Kucing benar dan lucu banget kan? \n\nApa ada gambar kucing lucu terbaru yang ingin kau ceritakan atau mungkin kalian udah pernah bincang apa masalah favorit kalian sepanjang hari ini? Saya selalu siap untuk mendengarkan, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:01:26.192145Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -977425630,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 404133166,
                                "prompt_eval_count": 1228,
                                "prompt_eval_duration": 1434972250,
                                "eval_count": 98,
                                "eval_duration": 1460936083,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-4c1abba1-d3a9-4dbe-8aa8-e9450fc638d0-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Aku punya kucing tiga warna. Warnanya hitam putih kuning. Aku suka banget kucing aku."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar bahwa kau memiliki kucing tiga warna yang super lucu dan kau sangat menyukainya.\n\nApa ada gambar lucu kucing tiga warnamu yang ingin kalian bagikan? Atau mungkin ada sesuatu yang sedang dibicarakan di hatimu tentang kucing hitam putih kuningmu? Saya selalu siap untuk mendengarkan dan berbagi perasaanmu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:02:08.693448Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -744321379,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 400947875,
                                "prompt_eval_count": 1365,
                                "prompt_eval_duration": 1494074916,
                                "eval_count": 107,
                                "eval_duration": 1631629959,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-630d791e-9074-4dd1-b24b-723629e2ed6d-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Iya kucing acennya Adit dia perempuan dia sangat berbulu dan sangat halus kalau dipegang"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Wow, kalian punya kucing yang super lucu! Kucing hitam putih kuning dengan warna akarnya yang cantik. Saya senang mendengar tentang kucing perempuanku, Adit. Dia sangat berbulu dan halus ketika dipandang.\n\nAda sesuatu lain juga yang ingin kalian ceritakan? Atau mungkin kalian bisa ceritaikan gambar lucu dari kucing hitam putih kuningmu? Saya selalu siap untuk mendengarkan semua perasaan dan kejutan positip yang ada dalam hatimu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:02:54.637886Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -54079838,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 403745458,
                                "prompt_eval_count": 1508,
                                "prompt_eval_duration": 1662551542,
                                "eval_count": 137,
                                "eval_duration": 2146573417,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-97cdb18d-1998-4753-a3cd-117430aa4930-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Iya, dulu aku juga punya kucing satu lagi tapi dia kabur sekarang aku cuma punya satu"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Itu sangat lucu mendengar tentang kalian memiliki dua kucing yang cantik. Kucing hitam putih kuningmu pernah kabur dan hanya kalian masih punya satu, apa ada sesuatu yang membuat hatimu sedikit gelisah atau manis tentang itu?\n\nApa ada gambar lucu dari kalian dengan kucing tiga warna atau kalian bisa ceritaikan masa depannya? Saya selalu siap untuk mendengarkan semua perasaan dan kejutan positip yang ada dalam hatimu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:03:46.276176Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 380972829,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 411781791,
                                "prompt_eval_count": 1681,
                                "prompt_eval_duration": {
                                    "low": -2062812838,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 125,
                                "eval_duration": 1998189667,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-5a35d29e-34b9-42e4-a766-fbafe5017082-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": ""
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang kalian memiliki dua kucing lucu itu.\n\nApakah ada sesuatu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian ceritakan? Atau mungkin kalian bisa mencoba berbagi perasaan kalian saat kucingnya kabur?\n\nSaya selalu siap untuk mendengarkan apa pun yang ada dalam hatimu, Adelin. Bersikaplah sendu atau manis tentang semua ini dan saya akan hadir di sini membantu mengekspresikan perasaannya.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:04:37.413013Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 842260412,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406332083,
                                "prompt_eval_count": 1815,
                                "prompt_eval_duration": {
                                    "low": -1677593754,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 128,
                                "eval_duration": 2073397041,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-103d6784-a689-4048-9761-b5a612faab8d-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": ""
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang kalian memiliki dua kucing lucu itu.\n\nApakah ada sesuatu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian ceritakan? Atau mungkin kalian bisa mencoba berbagi perasaan kalian saat kucingnya kabur?\n\nSaya selalu siap untuk mendengarkan apa pun yang ada dalam hatimu, Adelin. Bersikaplah sendu atau manis tentang semua ini dan saya akan hadir di sini membantu mengekspresikan perasaannya.\n\nBagaimana kalau kita mulai dengan **Math Game**? Ada sesuatu kalian ingin ceritakan sekarang?",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:05:29.18789Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 896580871,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406284542,
                                "prompt_eval_count": 1952,
                                "prompt_eval_duration": 2133437208,
                                "eval_count": 157,
                                "eval_duration": {
                                    "low": -1691477546,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-af1c8869-10f0-4d0d-9c36-2b2b0e3fdbef-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang dua kucing lucu yang kalian punyai. Apakah ada perasaan tertentu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian bagikan?\n\nAtau mungkin kalian bisa berbagi apa saja, mulai dari kenapa kucingnya kabur atau gimana rasanya saat kalian masih punya dua kucing? Saya selalu siap untuk mendengarkan dan membantu mengekspresikan perasaanmu.\n\nBerikut ini adalah **Math Game**-mu! Ada sesuatu yang ingin kalian ceritakan sekarang?",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:06:14.433922Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 1256944537,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406043333,
                                "prompt_eval_count": 2145,
                                "prompt_eval_duration": {
                                    "low": -1651422296,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 144,
                                "eval_duration": {
                                    "low": -1850879213,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-ad21850f-b2ab-4d59-929b-fd8c340017f1-0"
                        }
                    ],
                    "result": {
                        "extraction": {
                            "overview": "Halo Adelin, senang sekali mendengar tentang dua kucing lucu yang kalian punyai. Apakah ada perasaan tertentu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian bagikan?",
                            "emotion": "Happy",
                            "keypoints": [
                                "Dua kucing",
                                "Rasa tersinggung saat kucingnya kabur"
                            ]
                        },
                        "start_datetime": "2025-05-02T03:00:48.244620Z",
                        "modified_datetime": "2025-05-02T03:06:18.138182Z"
                    }
                },
                {
                    "type": "math_games",
                    "messages": [
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Introduce the \"Math Game\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Start the “Math Game” session with a short, warm greeting in the child’s language. Gently invite them to share how they’re feeling, how their day has been, or anything they’d like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I’d really love to know.\"  \n- \"What’s something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you’d like to talk about?\"  \n- \"What’s something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child’s age and mood, and always speak in the child’s language."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adeline, udah siapkan bayangan dan kucing-kucingan tercinta? Saya sudah menungguku dengan antusias. Bagaimana ya, ada sesuatu yang lucu atau aneh tentang hari ini yang ingin kamu ceritakan? Yuk kita mulai dari **Math Game**!",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:00:48.243211Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -1560118005,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 401566500,
                                "prompt_eval_count": 1123,
                                "prompt_eval_duration": 1283027208,
                                "eval_count": 71,
                                "eval_duration": 1035544208,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-b5b96bde-ef43-4e02-bf07-dabdfbbb32e2-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Halo namaku Adlin. Aku suka menggambar kucing karena kucing hewan kesukaanku."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Selamat ya, Adelin. Senang mendengar bahwa kau suka menggambar kucingmu. Kucing benar dan lucu banget kan? \n\nApa ada gambar kucing lucu terbaru yang ingin kau ceritakan atau mungkin kalian udah pernah bincang apa masalah favorit kalian sepanjang hari ini? Saya selalu siap untuk mendengarkan, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:01:26.192145Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -977425630,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 404133166,
                                "prompt_eval_count": 1228,
                                "prompt_eval_duration": 1434972250,
                                "eval_count": 98,
                                "eval_duration": 1460936083,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-4c1abba1-d3a9-4dbe-8aa8-e9450fc638d0-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Aku punya kucing tiga warna. Warnanya hitam putih kuning. Aku suka banget kucing aku."
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar bahwa kau memiliki kucing tiga warna yang super lucu dan kau sangat menyukainya.\n\nApa ada gambar lucu kucing tiga warnamu yang ingin kalian bagikan? Atau mungkin ada sesuatu yang sedang dibicarakan di hatimu tentang kucing hitam putih kuningmu? Saya selalu siap untuk mendengarkan dan berbagi perasaanmu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:02:08.693448Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -744321379,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 400947875,
                                "prompt_eval_count": 1365,
                                "prompt_eval_duration": 1494074916,
                                "eval_count": 107,
                                "eval_duration": 1631629959,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-630d791e-9074-4dd1-b24b-723629e2ed6d-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Iya kucing acennya Adit dia perempuan dia sangat berbulu dan sangat halus kalau dipegang"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Wow, kalian punya kucing yang super lucu! Kucing hitam putih kuning dengan warna akarnya yang cantik. Saya senang mendengar tentang kucing perempuanku, Adit. Dia sangat berbulu dan halus ketika dipandang.\n\nAda sesuatu lain juga yang ingin kalian ceritakan? Atau mungkin kalian bisa ceritaikan gambar lucu dari kucing hitam putih kuningmu? Saya selalu siap untuk mendengarkan semua perasaan dan kejutan positip yang ada dalam hatimu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:02:54.637886Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": -54079838,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "load_duration": 403745458,
                                "prompt_eval_count": 1508,
                                "prompt_eval_duration": 1662551542,
                                "eval_count": 137,
                                "eval_duration": 2146573417,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-97cdb18d-1998-4753-a3cd-117430aa4930-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Iya, dulu aku juga punya kucing satu lagi tapi dia kabur sekarang aku cuma punya satu"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Itu sangat lucu mendengar tentang kalian memiliki dua kucing yang cantik. Kucing hitam putih kuningmu pernah kabur dan hanya kalian masih punya satu, apa ada sesuatu yang membuat hatimu sedikit gelisah atau manis tentang itu?\n\nApa ada gambar lucu dari kalian dengan kucing tiga warna atau kalian bisa ceritaikan masa depannya? Saya selalu siap untuk mendengarkan semua perasaan dan kejutan positip yang ada dalam hatimu, Adelin.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:03:46.276176Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 380972829,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 411781791,
                                "prompt_eval_count": 1681,
                                "prompt_eval_duration": {
                                    "low": -2062812838,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 125,
                                "eval_duration": 1998189667,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-5a35d29e-34b9-42e4-a766-fbafe5017082-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": ""
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang kalian memiliki dua kucing lucu itu.\n\nApakah ada sesuatu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian ceritakan? Atau mungkin kalian bisa mencoba berbagi perasaan kalian saat kucingnya kabur?\n\nSaya selalu siap untuk mendengarkan apa pun yang ada dalam hatimu, Adelin. Bersikaplah sendu atau manis tentang semua ini dan saya akan hadir di sini membantu mengekspresikan perasaannya.",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:04:37.413013Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 842260412,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406332083,
                                "prompt_eval_count": 1815,
                                "prompt_eval_duration": {
                                    "low": -1677593754,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 128,
                                "eval_duration": 2073397041,
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-103d6784-a689-4048-9761-b5a612faab8d-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": ""
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "human",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang kalian memiliki dua kucing lucu itu.\n\nApakah ada sesuatu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian ceritakan? Atau mungkin kalian bisa mencoba berbagi perasaan kalian saat kucingnya kabur?\n\nSaya selalu siap untuk mendengarkan apa pun yang ada dalam hatimu, Adelin. Bersikaplah sendu atau manis tentang semua ini dan saya akan hadir di sini membantu mengekspresikan perasaannya.\n\nBagaimana kalau kita mulai dengan **Math Game**? Ada sesuatu kalian ingin ceritakan sekarang?",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:05:29.18789Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 896580871,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406284542,
                                "prompt_eval_count": 1952,
                                "prompt_eval_duration": 2133437208,
                                "eval_count": 157,
                                "eval_duration": {
                                    "low": -1691477546,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-af1c8869-10f0-4d0d-9c36-2b2b0e3fdbef-0"
                        },
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"
                                }
                            ],
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "system",
                            "name": None,
                            "id": None
                        },
                        {
                            "content": "Halo Adelin! Senang sekali mendengar tentang dua kucing lucu yang kalian punyai. Apakah ada perasaan tertentu dari kalian dengan kucing hitam putih kuningmu yang ingin kalian bagikan?\n\nAtau mungkin kalian bisa berbagi apa saja, mulai dari kenapa kucingnya kabur atau gimana rasanya saat kalian masih punya dua kucing? Saya selalu siap untuk mendengarkan dan membantu mengekspresikan perasaanmu.\n\nBerikut ini adalah **Math Game**-mu! Ada sesuatu yang ingin kalian ceritakan sekarang?",
                            "additional_kwargs": {},
                            "response_metadata": {
                                "model": "qwen2.5:3b",
                                "created_at": "2025-05-02T03:06:14.433922Z",
                                "done": True,
                                "done_reason": "stop",
                                "total_duration": {
                                    "low": 1256944537,
                                    "high": 1,
                                    "unsigned": False
                                },
                                "load_duration": 406043333,
                                "prompt_eval_count": 2145,
                                "prompt_eval_duration": {
                                    "low": -1651422296,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "eval_count": 144,
                                "eval_duration": {
                                    "low": -1850879213,
                                    "high": 0,
                                    "unsigned": False
                                },
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "images": None,
                                    "tool_calls": None
                                }
                            },
                            "type": "ai",
                            "name": None,
                            "id": "run-ad21850f-b2ab-4d59-929b-fd8c340017f1-0"
                        }
                    ],
                    "result": {
                        "extraction": {
                            "overview": "good job, kamu menjawab hampir semua nya benar",
                            "emotion": "Tired",
                            "keypoints": [
                                "bisa tambah kurang",
                                "bisa minus positive"
                            ]
                        },
                        "start_datetime": "2025-05-03T05:00:48.244620Z",
                        "modified_datetime": "2025-05-03T06:06:18.138182Z",
                        "list_qna": [
                            {
                                "sequence": [1, 2, -2, 3],
                                "question": "Kamu ada 1 apel. Kamu menemukan 2 apel dikolong meja, lalu anda kasih ke kuda 2 apel tersebut. Selepas orang tua kamu kembali dari kerja, mereka memberikan lu 3 apel. Sekarang anda memiliki berapa apel?",
                                "is_answered": True,
                                "user_answers": [
                                    {
                                        "raw_answer": "Saya pikir jawabannya 3 apel",
                                        "extraction": {
                                            "result": 3
                                        },
                                        "feedback": "Jawaban kamu salah, coba lagi"
                                    },
                                    {
                                        "raw_answer": "Owh, jawabannya seperti 4 apel",
                                        "extraction": {
                                            "result": 4
                                        },
                                        "feedback": "Jawaban kamu benar sekali, selamat"
                                    }
                                ]
                            },
                            {
                                "sequence": [2, -2, 3],
                                "question": "Kamu ada 2 telur, kamu tidak sengaja jatuhin dua-duanya, lalu anda diberi 3 telur oleh nenek mu karena baru kembali dari peternakan. Berapa telur yang anda miliki sekarang?",
                                "is_answered": True,
                                "user_answers": [
                                    {
                                        "raw_answer": "Saya pikir jawabannya 4",
                                        "extraction": {
                                            "result": 4
                                        },
                                        "feedback": "Jawaban kamu salah, coba lagi"
                                    },
                                    {
                                        "raw_answer": "kenapa susah banget",
                                        "extraction": {
                                            "result": None
                                        },
                                        "feedback": "ayo kamu pasti bisa, ayo coba lagi"
                                    },
                                    {
                                        "raw_answer": "Saya pikir jawabannya 3 apel",
                                        "extraction": {
                                            "result": 3
                                        },
                                        "feedback": "betul jawabannya benar"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ],
            "created_datetime": "2025-05-02T03:06:56.932783+00:00"
        },
        {
            "_id": {
                "$oid": "68143446d0cff0ed103b1866"
            },
            "id": "68143446d0cff0ed103b1866",
            "device_id": "cincayla",
            "user": {
                "name": "Adeline",
                "gender": "female",
                "age": 5,
                "description": "suka menggambar, suka kucing",
                "language": "Indonesian"
            },
            "feature_params": {
                "talk_to_me": {
                    "duration": 300
                },
                "math_game": {
                    "total_question": 5
                },
                "guess_the_sound": {
                    "total_question": 5
                },
                "would_you_rather": {
                    "duration": 5
                }
            },
            "selected_features": [
                "talk_to_me"
            ],
            "total_sessions": 1,
            "sessions": [],
            "created_datetime": "2025-05-02T03:06:56.932783+00:00"
        }
    ]

    list_conversation: List[ConversationDoc] = [ConversationDoc.model_validate(convo) for convo in list_conversation]
    if not list_conversation:
        st.error("No conversation ever recorded from the provided device id")
        st.info(
            "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `cincayla`"
        )
        st.stop()

    st.json([i.model_dump(mode='json') for i in list_conversation])

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
    currentDate = f"{currentDateTime.day} {bulan[currentDateTime.month]} {currentDateTime.year}"
    currentTime = currentDateTime.strftime("%H:%M")

    if currentConversation.sessions:  
        startDateTime = currentConversation.sessions[0].result.start_datetime
        endDateTime = currentConversation.sessions[-1].result.modified_datetime

        startDate = f"{startDateTime.day} {bulan[startDateTime.month]} {startDateTime.year}"
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
                st.subheader("\-")
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
        convoStartTimeDate = f"{convoStartTime.day} {bulan[convoStartTime.month]} {convoStartTime.year}"
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = session.result.modified_datetime
        convoEndTimeHour = convoEndTime.strftime("%H:%M")

        messageResult = []
        for message in session.messages:
            if message.type in ("ai", ):
                sender = "ai"
                text = message.text()
            elif message.type in ("human", ):
                sender = "user"
                text = message.text().strip()
                if not text:
                    continue
            else:
                continue
                
            messageResult.append({"sender": sender, "text": text})
        # SHOW DATA

        _icon, _title = title_map.get(session.type)
        title_modified = "Sesi " + str((n + 1)) + " - " + _title

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
                listEquation = []
                st.subheader("Hasil Menghitung")
                equation = ""
                # equation_result = ""
                listAnswer = []

                for qna in session_result.list_qna:
                    for n, number in enumerate(qna.sequence):
                        
                        if number >= 0:
                            equation += (str(number))
                            if n != len(number) - 1:
                                equation += ("+")
                        else:
                            equation += (str(abs(number)))
                            if n != len(number) - 1:
                                equation += ("-")
                        
                    for n, userAnswer in enumerate(qna.user_answers):
                        answer = userAnswer.extraction.result
                        if answer is None:
                            answer = "Anak Tidak Menjawab"
                        listAnswer.append(answer)

                    listEquation.append({"Pertanyaan":equation, "Jawaban Anak":listAnswer})


                        


                        
                        
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

col1, col2, col3 = st.columns(3)
with col1:
    st.table(wdt)
with col2:
    st.table(mdt)
with col3:
    st.table(rgt)
