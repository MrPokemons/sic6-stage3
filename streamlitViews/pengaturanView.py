import requests
import streamlit as st
from typing import List, Annotated
from pydantic import BaseModel, PositiveInt
from urllib.parse import urljoin
from src.services.pawpal.schemas.user import UserData
from src.services.pawpal.schemas.topic import TopicParams
from src.services.pawpal.schemas.topic_flow import TopicFlowType
from config.settings import SETTINGS
from streamlitViews.language_utils import render_language_toggle, get_current_language
from streamlitViews.translations import get_text

class StartConversationInput(BaseModel):
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt

def normalize(value):
    return value if value not in ["", None] else None

# Render language toggle in sidebar
render_language_toggle()

# Get current language
lang = get_current_language()

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

st.title(get_text("pengaturan.title", lang))

with st.form("child_profile_form"):
    st.subheader(get_text("pengaturan.child_profile", lang))
    st.write(get_text("pengaturan.optional_info", lang))
    nameInput = st.text_input(get_text("pengaturan.name", lang))
    ageInput = st.number_input(get_text("pengaturan.age", lang), min_value=4, max_value=8, step=1, value=6)
    genderInput = st.selectbox(
        get_text("pengaturan.gender", lang),
        [
            get_text("pengaturan.select_gender", lang),
            get_text("pengaturan.male", lang),
            get_text("pengaturan.female", lang)
        ]
    )
    descriptionInput = st.text_area(get_text("pengaturan.description", lang))

    st.subheader(get_text("pengaturan.conversation_config", lang))
    if not st.session_state.deviceId:
        deviceIdInput = st.text_input(get_text("common.device_id", lang), "")
    else:
        deviceIdInput = st.text_input(get_text("common.device_id", lang), st.session_state.deviceId)
    st.session_state.deviceId = deviceIdInput
    sessionsInput = st.number_input(get_text("pengaturan.total_sessions", lang), min_value=1, step=1)


    featureOptions = [
        "👄 Talk To Me",
        "🖐️ Math Adventures",
        "🔊 Guess The Sound",
        "❓ Would You Rather",
    ]
    selectedFeatures = st.pills(
        get_text("pengaturan.interaction_type", lang), featureOptions, selection_mode="multi"
    )

    saveConfiguration = st.form_submit_button(get_text("common.save", lang))
    if saveConfiguration:
        st.session_state.configuration = True

if st.session_state.configuration:
    if not (
        nameInput
        and ageInput
        and descriptionInput
    ) or genderInput == get_text("pengaturan.select_gender", lang):
        st.info(get_text("pengaturan.empty_fields_info", lang))

    if not (
        deviceIdInput
    ):
        st.error(get_text("pengaturan.device_id_required", lang))
        st.stop()

    if not nameInput:
        nameInput = "Adik"

    genderInput = normalize(genderInput)
    ageInput = normalize(ageInput)
    descriptionInput = normalize(descriptionInput)

    if not (selectedFeatures):
        st.error(get_text("pengaturan.select_interaction", lang))
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
                get_text("pengaturan.duration_label", lang),
                options=range(1, 31),
                value=1,
            )
        if "math_games" in selectedFeatures or "guess_the_sound" in selectedFeatures:
            questionInput = st.select_slider(
                get_text("pengaturan.questions_label", lang),
                options=range(1, 31),
                value=1,
            )

        consentInput = st.checkbox(get_text("pengaturan.consent_text", lang, name=nameInput))

        startConvo = st.form_submit_button(get_text("common.start_conversation", lang))

    if not (
        consentInput
    ):
        st.error(get_text("pengaturan.consent_required", lang))
        st.stop()

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
        st.success(get_text("pengaturan.conversation_started", lang))
    else:
        st.info(get_text("pengaturan.ready_to_start", lang))

    if startConvo:
        gender_map = {
            get_text("pengaturan.male", lang): "male",
            get_text("pengaturan.female", lang): "female"
        }
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

            # st.json(convo_input.model_dump())  # show for debugging
            resp = requests.post(
                urljoin(SETTINGS.APP.DOMAIN, "/api/v1/pawpal/conversation/start"),
                json=convo_input.model_dump(),
            )
            if resp.status_code != 200:
                resp.raise_for_status()
            st.success(get_text("pengaturan.success_message", lang))
        except Exception:
            st.warning(get_text("pengaturan.backend_offline_warning", lang))
            st.error(get_text("pengaturan.backend_offline_error", lang))


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
