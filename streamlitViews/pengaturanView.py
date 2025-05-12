import requests
import streamlit as st
from typing import List, Annotated
from pydantic import BaseModel, PositiveInt
from src.services.pawpal.schemas.user import UserData
from src.services.pawpal.schemas.topic import TopicParams
from src.services.pawpal.schemas.topic_flow import TopicFlowType


class StartConversationInput(BaseModel):
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt

def normalize(value):
    return value if value not in ["", None] else None

if "configuration" not in st.session_state:
    st.session_state.configuration = False
if "deviceId" not in st.session_state:
    st.session_state.deviceId = False

chatConfig = []
# dummyMsg = []
dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]

st.title("⚙️ Pengaturan Percakapan")

with st.form("child_profile_form"):
    st.subheader("Biodata Anak")
    st.write("Opsional — nilai default akan digunakan jika tidak diisi")
    nameInput = st.text_input("🧒 Nama")
    ageInput = st.number_input("🎂 Umur", min_value=4, max_value=8, step=1, value=6)
    genderInput = st.selectbox(
        "🚻 Jenis Kelamin", ["Pilih Jenis Kelamin", "Laki-laki", "Perempuan"]
    )
    descriptionInput = st.text_area("🚲 Deskripsi Anak (hobi dan minat, kepribadian)")

    st.subheader("Konfigurasi Percakapan")
    if not st.session_state.deviceId:
        deviceIdInput = st.text_input("⚙️ No. ID Perangkat", "")
    else:
        deviceIdInput = st.text_input("⚙️ No. ID Perangkat", st.session_state.deviceId)
    st.session_state.deviceId = deviceIdInput
    sessionsInput = st.number_input("🗣️ Jumlah Sesi", min_value=1, step=1)

    featureOptions = [
        "👄 Talk To Me",
        "🖐️ Math Adventures",
        "🔊 Guess The Sound",
        "❓ Would You Rather",
    ]
    selectedFeatures = st.pills(
        "💬 Jenis Interaksi", featureOptions, selection_mode="multi"
    )

    saveConfiguration = st.form_submit_button("Simpan")
    if saveConfiguration:
        st.session_state.configuration = True  

if st.session_state.configuration:
    if not (
        nameInput
        and ageInput
        and descriptionInput
    ) or genderInput == "Pilih Jenis Kelamin":
        st.info("Field kosong akan diisi dengan nilai default")

    if not (
        deviceIdInput
    ):
        st.error("No ID perangkat harus diisi")
        st.stop()

    if not nameInput:
        nameInput = "Adik"

    genderInput = normalize(genderInput)
    ageInput = normalize(ageInput)
    descriptionInput = normalize(descriptionInput)

    if not (selectedFeatures):
        st.error("Pilih setidaknya salah satu interaksi")
        st.stop()

    topic_map = {
        "👄 Talk To Me": "talk_to_me",
        "🖐️ Math Adventures": "math_games",
        "🔊 Guess The Sound": "guess_the_sound",
        "❓ Would You Rather": "would_you_rather",
    }
    selectedFeatures = [topic_map.get(feature) for feature in selectedFeatures]

    durationInput = 0
    questionInput = 0
    with st.form("duration_and_total_question"):
        if "talk_to_me" in selectedFeatures or "would_you_rather" in selectedFeatures:
            durationInput = st.select_slider(
                "⏰ Durasi Interaksi dalam Menit (Talk To Me, Would You Rather)",
                options=range(1, 31),
                value=1,
            )
        if "math_games" in selectedFeatures or "guess_the_sound" in selectedFeatures:
            questionInput = st.select_slider(
                "🙋‍♂️ Jumlah Pertanyaan (Math Adventure, Guess The Sound)",
                options=range(1, 31),
                value=1,
            )

        startConvo = st.form_submit_button("Mulai Percakapan")

    durationTalkToMe = durationWouldYouRather = 0
    questionMathGames = questionGuessTheSound = 0
    if "talk_to_me" in selectedFeatures:
        durationTalkToMe = durationInput
    if "would_you_rather" in selectedFeatures:
        durationWouldYouRather = durationInput
    if "math_games" in selectedFeatures:
        questionMathGames = questionInput
    if "guess_the_sound" in selectedFeatures:
        questionGuessTheSound = questionInput

    if startConvo:
        st.success("Percakapan dimulai!")
    else:
        st.info("Konfigurasi sudah sesuai? Klik tombol mulai percakapan!")

    if startConvo:
        gender_map = {"Laki-laki": "male", "Perempuan": "female"}
        try:
            user_data = UserData(
                name=nameInput,
                gender=gender_map.get(genderInput),
                age=ageInput,
                description=descriptionInput,
                language="Indonesian",
            )

            topic_param = TopicParams(
                talk_to_me=TopicParams.TalkToMeParam(
                    duration=durationTalkToMe * 60
                ),
                math_game=TopicParams.MathGameParam(
                    total_question=questionMathGames
                ),
                guess_the_sound=TopicParams.GuessTheSoundParam(
                    total_question=questionGuessTheSound
                ),
                would_you_rather=TopicParams.WouldYouRatherParam(
                    duration=durationWouldYouRather * 60
                ),
            )

            convo_input = StartConversationInput(
                device_id=deviceIdInput,
                user=user_data,
                feature_params=topic_param,
                selected_features=selectedFeatures,
                total_sessions=sessionsInput,
            )

            st.json(convo_input.model_dump())  # show for debugging
            resp = requests.post(
                "http://localhost:11080/api/v1/pawpal/conversation/start",
                json=convo_input.model_dump(),
            )
            if resp.status_code != 200:
                resp.raise_for_status()
            st.success("Berhasil menginput konfigurasi percakapan baru!!")
        except Exception:
            st.warning("Jika Backend tidak berjalan, fitur ini tidak dapat dipakai.")
            st.error("Backend tidak aktif, fitur ini tidak dapat digunakan, mohon untuk menyalakan servernya dengan mengikuti panduan.")


# -------------------
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

    </style>
""",
    unsafe_allow_html=True,
)
