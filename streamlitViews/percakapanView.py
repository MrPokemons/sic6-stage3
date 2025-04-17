import streamlit as st
import requests
from src.services.pawpal.schemas.user import UserData
from src.controllers.pawpal import StartConversationInput, TopicParams

chatConfig = []
# dummyMsg = []
dummyMsg = [
    {"sender": "user", "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", "text": "Oke siap~"},
]

st.title("Mulai Percakapan 🤖")

with st.form("child_profile_form"):
    st.subheader("Biodata Anak")
    nameInput = st.text_input("🧒 Nama")
    ageInput = st.number_input("🎂 Umur", min_value=3, max_value=8, step=1)
    genderInput = st.selectbox(
        "🚻 Jenis Kelamin", ["Pilih Jenis Kelamin", "Laki-laki", "Perempuan"]
    )
    descriptionInput = st.text_area("🚲 Deskripsi Anak (hobi dan minat, kepribadian)")

    st.subheader("Konfigurasi Percakapan")
    deviceIdInput = st.text_input("⚙️ No. ID Perangkat", "")
    durationInput = st.number_input("⏰ Durasi", min_value=3, step=2)
    sessionsInput = st.number_input("🗣️ Jumlah Sesi", min_value=1, step=1)
    # topic = st.text_area("💬 Topik Percakapan (Opsional)")

    startConvo = st.form_submit_button("Mulai")

if startConvo:

    if not (
        nameInput
        and ageInput
        and genderInput
        and descriptionInput
        and deviceIdInput
        and durationInput
        and sessionsInput
    ):
        st.error("Semua kolom wajib diisi! Mohon dicek kembali.")
        st.stop()

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
            talk_to_me=TopicParams.TalkToMeParam(duration=durationInput),
            math_game=TopicParams.MathGameParam(total_question=durationInput),
            spelling_game=TopicParams.SpellingGameParam(total_question=durationInput),
            would_you_rather=TopicParams.WouldYouRatherParam(duration=durationInput),
        )

        convo_input = StartConversationInput(
            device_id=deviceIdInput,
            user=user_data,
            feature_params=topic_param,
            selected_features=["talk_to_me"],
            total_sessions=sessionsInput,
        )

        # class TopicParams(TypedDict):
        # class TalkToMeParam(TypedDict):
        #     duration: Annotated[int, "in seconds"]

        # class MathGameParam(TypedDict):
        #     total_question: int

        # class SpellingGameParam(TypedDict):
        #     total_question: int

        # class WouldYouRatherParam(TypedDict):
        #     duration: Annotated[int, "in seconds"]

        # talk_to_me: TalkToMeParam
        # math_game: MathGameParam
        # spelling_game: SpellingGameParam
        # would_you_rather: WouldYouRatherParam

        st.json(convo_input.model_dump())  # show for debugging
        requests.post(
            "http://localhost:11080/api/v1/pawpal/conversation/start",
            json=convo_input.model_dump(),
        )
        st.success("Berhasil menginput konfigurasi percakapan baru!!")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

    print("convo started")

# -------------------
st.subheader("Transkrip")
with st.expander("💬 Transkrip Percakapan"):
    if dummyMsg:
        for msg in dummyMsg:
            with st.chat_message(msg["sender"]):
                st.write(msg["text"])
    else:
        st.write("Belum ada percakapan yang dimulai!")
