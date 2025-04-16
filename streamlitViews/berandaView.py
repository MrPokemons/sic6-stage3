import streamlit as st
import requests
import pandas as pd

# analytics data declaration here

wordDictionary = {
    "Kata Asli": ['Adel', 'Data 2', 'Data 3'],
    "Pelafalan Anak": ['Value 1', 'Value 2', 'Value 3']
}

mathDictionary = {
    "Pertanyaan": ['Data 1', 'Data 2', 'Data 3'],
    "Jawaban Anak": ['Value 1', 'Value 2', 'Value 3']
}

dummyMsg = [
    {"sender": "user", 
     "text": "Hai, kamu lagi apa?"},
    {"sender": "bot", 
     "text": "Halo! Aku lagi standby nunggu kamu 😄"},
    {"sender": "user", 
     "text": "Oke siap~"},
]

# messages: [
#         {
        #   content: "Halo Cindy, selamat datang kembali ke sesi 'Berbicara'. Senyummu menunjukkan bahwa hari ini pasti penuh dengan kesenangan, kan? Bagaimana kabarmu hari ini? Ada yang lucu atau serius yang mau kita bicarakan?",
        #   additional_kwargs: {},
        #   type: 'ai',
        #   name: null,
        #   id: 'run-e8ddba46-0a2b-4230-af92-d6975601bbb3-0'
        # },
        # {
        #   content: [
        #     {
        #       type: 'text',
        #       text: 'Iya kak, hari ini saya berkunjung ke taman yang penuh dengan bunga dan banyak yang mekar.'
        #     }
        #   ],
        #   additional_kwargs: {},
        #   response_metadata: {},
        #   type: 'human',
        #   name: null,
        #   id: null
        # },
# ]

# view starts here
st.title("PawPal 🐾")

# input device ID
deviceId = st.text_input("No. ID Perangkat", "")
if st.button("Cari percakapan terakhir", type="primary"):
    lastConversation = requests.get(f"http://localhost:8899/api/v1/pawpal/conversation/{deviceId}").json()

    for session in lastConversation['sessions']:
        dummyMsg.clear()
        for message in session['messages']:
            # Check message type and handle accordingly
            if isinstance(message, dict):
                if message['type'] == 'ai':
                    sender = 'bot'
                    text = message['content']
                elif message['type'] == 'human':
                    sender = 'user'
                    # Assuming content is a list
                    if isinstance(message['content'], list) and len(message['content']) > 0:
                        text = message['content'][0]['text']
                    else:
                        text = message['content']
                else:
                    continue  # Skip other types of messages

                # Append formatted message to the dummyMsg list
                dummyMsg.append({"sender": sender, "text": text})

    # -------------------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Percakapan Terakhir")
        st.markdown("""
        <div style="
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            font-family: 'Helvetica', sans-serif;
            line-height: 1.6;
            padding-bottom: 20px;
        ">        
            <div style="margin-bottom: 6px">
                <span style="margin-right: 20px;">🗓️ 12 April 2015</span>
                <span>⏰ 17:10 - 17:15</span>
                </div>
        </div>
    """, unsafe_allow_html=True)
    with col2:
        st.subheader("Perasaan")
        st.markdown("""
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
        """, unsafe_allow_html=True)

    # -------------------
    st.subheader("Transkrip")
    with st.expander("💬 Transkrip Percakapan Terakhir"):
        for msg in dummyMsg:
            with st.chat_message(msg["sender"]):
                st.write(msg["text"])


    # -------------------
    # hard coded values
    # karena belum setup backend logic & endpoints for retrieving these kinds of data
    st.subheader("Analitik")
    # dictionary columns
    # declare tables and columns
    wordDictTable = pd.DataFrame(wordDictionary)
    mathDictTable = pd.DataFrame(mathDictionary)

    wdt = pd.DataFrame(wordDictTable)
    wdt.index += 1
    mdt = pd.DataFrame(mathDictTable)
    mdt.index += 1

    col1, col2 = st.columns(2)
    with col1:
        st.table(wdt)
    with col2:
        st.table(mdt)