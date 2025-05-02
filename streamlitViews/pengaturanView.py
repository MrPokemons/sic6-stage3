import streamlit as st
import requests
from src.services.pawpal.schemas.user import UserData
from src.controllers.pawpal import StartConversationInput, TopicParams

if 'configuration' not in st.session_state:
    st.session_state.configuration = False
if 'deviceId' not in st.session_state:
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
    nameInput = st.text_input("🧒 Nama")
    ageInput = st.number_input("🎂 Umur", min_value=4, max_value=8, step=1)
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
    # durationInput = st.number_input("⏰ Durasi", min_value=3, step=2)
    sessionsInput = st.number_input("🗣️ Jumlah Sesi", min_value=1, step=1)
    
    featureOptions = ["👄 Talk To Me", "🖐️ Math Adventures", "🔤 Spelling Games", "❓ Would You Rather"]
    selectedFeatures = st.pills("💬 Jenis Interaksi", featureOptions, selection_mode="multi")

    # untuk styling nya nanti lagi
    # st.markdown(
    #     """<style>
    #         button[data-testid="stBaseButton-pills"]{
    #             height:200px;
                
    #         }
    #     </style>""",
    #     unsafe_allow_html=True,
    # )
    saveConfiguration = st.form_submit_button("Simpan")
    if saveConfiguration:
        st.session_state.configuration = True  # Menampilkan form kedua
# print("testtt => ", st.session_state.durationQuestion)

if st.session_state.configuration:
# if saveConfiguration:
    if not (
        nameInput
        and ageInput
        # and genderInput
        and descriptionInput
        and deviceIdInput
        # and durationInput
        and sessionsInput
    ):
        st.error("Semua kolom wajib diisi! Mohon dicek kembali.")
        st.stop()
    
    if genderInput == "Pilih Jenis Kelamin":
        st.error("Pilih salah satu jenis kelamin")
        st.stop()

    if not (
        selectedFeatures
    ):
        st.error("Pilih setidaknya salah satu interaksi")
        st.stop()

    topic_map = {"👄 Talk To Me": "talk_to_me", "🖐️ Math Adventures": "math_games", "🔤 Spelling Games": "spelling_games", "❓ Would You Rather": "would_you_rather"}
    selectedFeatures = [topic_map.get(feature) for feature in selectedFeatures]

    durationInput = 0
    questionInput = 0
    with st.form("duration_and_total_question"):
        if "talk_to_me" in selectedFeatures or "would_you_rather" in selectedFeatures:
            # range = range(1, 31)
            durationInput = st.select_slider(
                "⏰ Durasi Interaksi (Talk To Me, Would You Rather)",
                options=range(1, 31), value=1)
            # st.write("You selected wavelengths between", start_color, "and", end_color)
        if "math_games" in selectedFeatures or "spelling_games" in selectedFeatures:
            # range = range(1, 31)
            questionInput = st.select_slider(
                "🙋‍♂️ Jumlah Pertanyaan (Math Adventure, Spelling Game)",
                options=range(1, 31), value=1)
        startConvo = st.form_submit_button("Mulai Percakapan")
    
    if startConvo:
        st.success("Percakapan dimulai!")
    else:
        st.info("Konfigurasi sudah sesuai? Klik tombol mulai percakapan!")
    # print(startConvo)

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
                talk_to_me=TopicParams.TalkToMeParam(duration=durationInput*60),
                math_game=TopicParams.MathGameParam(total_question=questionInput),
                spelling_game=TopicParams.SpellingGameParam(total_question=questionInput),
                would_you_rather=TopicParams.WouldYouRatherParam(duration=durationInput*60  ),
            )

            convo_input = StartConversationInput(
                device_id=deviceIdInput,
                user=user_data,
                feature_params=topic_param,
                selected_features=selectedFeatures,
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
            resp = requests.post(
                "http://localhost:11080/api/v1/pawpal/conversation/start",
                json=convo_input.model_dump(),
            )
            if resp.status_code != 200:
                resp.raise_for_status()
            st.success("Berhasil menginput konfigurasi percakapan baru!!")
        except Exception as e:
            st.warning("Jika Backend tidak berjalan, fitur ini tidak dapat dipakai.")
            st.error(f"Terjadi kesalahan: {e}")

        print("convo started")

# -------------------


# import streamlit as st
# options = ["North", "East", "South", "West"]
# selection = st.pills("Directions", options, selection_mode="multi")
# st.markdown(f"Your selected options: {selection}.")
st.markdown("""
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
""", unsafe_allow_html=True)
