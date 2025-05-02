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
        _collection = _db["pawpal-conversation"]
        list_conversation: list = _collection.find({"device_id": deviceId}).to_list()
        # list_conversation = [{"_id":{"$oid":"68124d0b070ec2d9daa302f9"},"id":"68124d0b070ec2d9daa302f9","device_id":"b898d942-250d-11f0-bc0b-6ac49b7e4cec","user":{"name":"Antoni","gender":"male","age":10,"description":"Love soccer, been training since 5 years' old","language":"Indonesian"},"feature_params":{"talk_to_me":{"duration":20},"math_game":{"total_question":5},"spelling_game":{"total_question":5},"would_you_rather":{"duration":20}},"selected_features":["talk_to_me"],"total_sessions":1,"sessions":[{"type":"talk_to_me","messages":[{"content":[{"type":"text","text":"Introduce the \"Talk to Me\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":[{"type":"text","text":"Start the “Talk to Me” session with a short, warm greeting in the child's language. Gently invite them to share how they're feeling, how their day has been, or anything they'd like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I'd really love to know.\"  \n- \"What's something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you'd like to talk about?\"  \n- \"What's something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child's age and mood, and always speak in the child's language."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni! Saya senang bertemu denganmu lagi. Bagaimana kabarmu hari ini? Kita bisa mulainya 'Kisahku Sendiri' ya, nggak ada masalah kok. Setelahnya kita boleh main game sepak bola atau bahkan bercanda tentang sepak bola yang kamu sukai. Aku juga senang sekali mendengar kau sudah mulai berlatih sejak umur 5 tahun dan suka sepak bola. Sudah siap untuk 'Kisahku Sendiri'?","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:57:02.178686Z","done":True,"done_reason":"stop","total_duration":36052624292,"load_duration":717346584,"prompt_eval_count":4951,"prompt_eval_duration":25862118500,"eval_count":120,"eval_duration":9091492583,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-d0c2b662-7cc2-4435-9d19-af8b7543c23a-0"},{"content":[{"type":"text","text":"Halo, Jimmy, selamat datang kembali ke sesi berbicara. Senyumu menunjukkan bahwa hari ini pasti penuh dengan kesenangankan bagaimana kabarmu hari ini. Ada yang lucu atau serius yang mau kita bicarakan?"}],"additional_kwargs":{},"response_metadata":{},"type":"human","name":None,"id":None},{"content":"Halo Jimmy! Selamat datang kembali juga. Senyummu benar-benar menyampaikan kalau hari ini pasti penuh dengan senangnya, itu sangat menggembirakan! Adakah sesuatu lucu atau serius yang mau kita bicarakan? Aku siap nih untuk mendengarkan apa pun yang kamu inginkan.","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:58:49.152913Z","done":True,"done_reason":"stop","total_duration":36211149542,"load_duration":739995792,"prompt_eval_count":5140,"prompt_eval_duration":28778473708,"eval_count":81,"eval_duration":6279523917,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-035aa0e1-cce0-408f-a06c-9f9d9a570826-0"},{"content":[{"type":"text","text":"End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Jimmy! Selamat datang kembali juga. Senyummu menunjukkan kalau hari ini pasti penuh dengan kesenangan-kesenanganmu, itu sangat menggembirakan! Ada sesuatu lucu atau serius yang mau kita bicarakan? Aku siap untuk mendengarkan apa pun yang kamu inginkan.","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:59:29.027969Z","done":True,"done_reason":"stop","total_duration":35794522459,"load_duration":751293792,"prompt_eval_count":5257,"prompt_eval_duration":28490685125,"eval_count":78,"eval_duration":6085064375,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-a40d9cce-4bac-4ff8-8ef2-5c431cda862a-0"}],"result":{"overview":"Always respond using Indonesian only—this is the only language the child understands.","emotion":"happy","keypoints":["Senyummu menunjukkan kalau hari ini pasti penuh dengan kesenangan-kesenanganmu, itu sangat menggembirakan!"]}}],"created_datetime":"2025-04-29T15:59:41.246262+00:00"},{"_id":{"$oid":"68124d67070ec2d9daa302fa"},"id":"68124d67070ec2d9daa302fa","device_id":"b898d942-250d-11f0-bc0b-6ac49b7e4cec","user":{"name":"Antoni","gender":"male","age":10,"description":"Love soccer, been training since 5 years' old","language":"Indonesian"},"feature_params":{"talk_to_me":{"duration":20},"math_game":{"total_question":5},"spelling_game":{"total_question":5},"would_you_rather":{"duration":20}},"selected_features":["talk_to_me"],"total_sessions":2,"sessions":[{"type":"talk_to_me","messages":[{"content":[{"type":"text","text":"Introduce the \"Talk to Me\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":[{"type":"text","text":"Start the “Talk to Me” session with a short, warm greeting in the child's language. Gently invite them to share how they're feeling, how their day has been, or anything they'd like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I'd really love to know.\"  \n- \"What's something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you'd like to talk about?\"  \n- \"What's something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child's age and mood, and always speak in the child's language."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni, udah senang bertemu lagi kan? Saya kenal dengan sepakbolmu sudah sejak usia 5 tahun lho. Senang banget kalau kita bisa mengeksplorasi berbagai hal tentang sepakbola dan juga tentang dirimu sendiri. \n\nBagaimana kalau kita mulai dari sini? Apa ada sesuatu yang membuatmu tersenyum atau mengganggu dalam hari ini? Yang penting adalah kamu merasa nyaman untuk membahasnya denganku. Senang bisa mendengar ceritamu dan mengetahui apa saja yang pernah terjadi di sepanjang hari mu.","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:18:40.712705Z","done":True,"done_reason":"stop","total_duration":14205726500,"load_duration":714404375,"prompt_eval_count":1125,"prompt_eval_duration":6341776334,"eval_count":142,"eval_duration":7127181750,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-35664ac7-fac9-47f6-849b-0d2c22dcead7-0"},{"content":[{"type":"text","text":"Halo, Jimmy, selamat datang kembali ke sesi berbicara. Senyumu menunjukkan bahwa hari ini pasti penuh dengan kesenangankan bagaimana kabarmu hari ini. Ada yang lucu atau serius yang mau kita bicarakan?"}],"additional_kwargs":{},"response_metadata":{},"type":"human","name":None,"id":None},{"content":"Halo Antoni! Selamat datang kembali ke sesi berbicara. Senyumanmu menunjukkan bahwa hari ini pastilah penuh dengan kesenangan-kesenanganmu. Adakah sesuatu yang lucu atau serius yang mau kita bicarakan?","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:20:23.060722Z","done":True,"done_reason":"stop","total_duration":12655142833,"load_duration":997345125,"prompt_eval_count":1338,"prompt_eval_duration":8299956417,"eval_count":63,"eval_duration":3308305042,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-d04fb734-e16c-4443-b8e2-1e56cd1729da-0"},{"content":[{"type":"text","text":"End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni! Selamat datang kembali ke sesi berbicara. Senyumanmu menunjukkan bahwa hari ini pastilah penuh dengan kesenangan-kesenanganmu. Adakah sesuatu yang lucu atau serius yang mau kita bicarakan?","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:20:37.707445Z","done":True,"done_reason":"stop","total_duration":11533913125,"load_duration":763450709,"prompt_eval_count":1437,"prompt_eval_duration":7425859791,"eval_count":63,"eval_duration":3299628917,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-60a42e47-0ef7-4513-aab0-7c9b107e49e9-0"}],"result":{"overview":"This response warmly welcomes the child back to the ","emotion":": It acknowledges their positive mood and encourages them to share what's on their mind, setting a supportive tone for the session.","keypoints":["Warm welcome","Encouragement to talk","Supportive tone"]}},{"type":"talk_to_me","messages":[{"content":[{"type":"text","text":"Introduce the \"Talk to Me\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":[{"type":"text","text":"Start the “Talk to Me” session with a short, warm greeting in the child's language. Gently invite them to share how they're feeling, how their day has been, or anything they'd like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I'd really love to know.\"  \n- \"What's something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you'd like to talk about?\"  \n- \"What's something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child's age and mood, and always speak in the child's language."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni! Saya senang bertemu denganmu lagi. Bagaimana kabarmu hari ini? Kita bisa mulainya 'Kisahku Sendiri' ya, nggak ada masalah kok. Setelahnya kita boleh main game sepak bola atau bahkan bercanda tentang sepak bola yang kamu sukai. Aku juga senang sekali mendengar kau sudah mulai berlatih sejak umur 5 tahun dan suka sepak bola. Sudah siap untuk 'Kisahku Sendiri'?","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:57:02.178686Z","done":True,"done_reason":"stop","total_duration":36052624292,"load_duration":717346584,"prompt_eval_count":4951,"prompt_eval_duration":25862118500,"eval_count":120,"eval_duration":9091492583,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-d0c2b662-7cc2-4435-9d19-af8b7543c23a-0"},{"content":[{"type":"text","text":"Halo, Jimmy, selamat datang kembali ke sesi berbicara. Senyumu menunjukkan bahwa hari ini pasti penuh dengan kesenangankan bagaimana kabarmu hari ini. Ada yang lucu atau serius yang mau kita bicarakan?"}],"additional_kwargs":{},"response_metadata":{},"type":"human","name":None,"id":None},{"content":"Halo Jimmy! Selamat datang kembali juga. Senyummu benar-benar menyampaikan kalau hari ini pasti penuh dengan senangnya, itu sangat menggembirakan! Adakah sesuatu lucu atau serius yang mau kita bicarakan? Aku siap nih untuk mendengarkan apa pun yang kamu inginkan.","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:58:49.152913Z","done":True,"done_reason":"stop","total_duration":36211149542,"load_duration":739995792,"prompt_eval_count":5140,"prompt_eval_duration":28778473708,"eval_count":81,"eval_duration":6279523917,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-035aa0e1-cce0-408f-a06c-9f9d9a570826-0"},{"content":[{"type":"text","text":"End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Jimmy! Selamat datang kembali juga. Senyummu menunjukkan kalau hari ini pasti penuh dengan kesenangan-kesenanganmu, itu sangat menggembirakan! Ada sesuatu lucu atau serius yang mau kita bicarakan? Aku siap untuk mendengarkan apa pun yang kamu inginkan.","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T15:59:29.027969Z","done":True,"done_reason":"stop","total_duration":35794522459,"load_duration":751293792,"prompt_eval_count":5257,"prompt_eval_duration":28490685125,"eval_count":78,"eval_duration":6085064375,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-a40d9cce-4bac-4ff8-8ef2-5c431cda862a-0"}],"result":{"overview":"Always respond using Indonesian only—this is the only language the child understands.","emotion":"happy","keypoints":["Senyummu menunjukkan kalau hari ini pasti penuh dengan kesenangan-kesenanganmu, itu sangat menggembirakan!"]}}],"created_datetime":"2025-04-29T16:20:48.381927+00:00"},{"_id":{"$oid":"68124deb9c1c23ad02a644be"},"id":"6810f8ecf0d73195ecd8f979","device_id":"b898d942-250d-11f0-bc0b-6ac49b7e4cec","user":{"name":"Antoni","gender":"male","age":10,"description":"Love soccer, been training since 5 years' old","language":"Indonesian"},"feature_params":{"talk_to_me":{"duration":20},"math_game":{"total_question":5},"spelling_game":{"total_question":5},"would_you_rather":{"duration":20}},"selected_features":["talk_to_me"],"total_sessions":1,"sessions":[{"type":"talk_to_me","messages":[{"content":[{"type":"text","text":"Introduce the \"Talk to Me\" session warmly and naturally in the child's language. Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":[{"type":"text","text":"Start the “Talk to Me” session with a short, warm greeting in the child's language. Gently invite them to share how they're feeling, how their day has been, or anything they'd like to talk about—whether happy, silly, confusing, or a little tough. Always listen with kindness and without judgment. Keep the tone friendly, calm, and safe. Below are a few example questions you can ask:\n\n**Examples, you are freely to explore another question as long its relevant to the topic:**\n\n- \"How are you feeling right now? I'd really love to know.\"  \n- \"What's something that made you smile today?\"  \n- \"Did anything today feel a little weird or tricky?\"  \n- \"If your day was a song, what would it sound like?\"  \n- \"Is there something on your mind that you'd like to talk about?\"  \n- \"What's something fun or funny that happened lately?\"  \n- \"If your feelings could wear costumes, what would they look like today?\"  \n\nOnly ask one question at a time. Adjust your tone based on the child's age and mood, and always speak in the child's language."}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni, senang sekali bertemu denganmu lagi! Saya tahu kau suka sepak bola dan udah mulai melatih sejak usia 5 tahun. Bagaimana kabarmu hari ini? Jika ada sesuatu yang ingin kamu bagikan atau bicarakan, aku di sini untuk mendengarkanmu dengan teliti tanpa perasaan yang salah. Selalu dengar dan mendukungmu!","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:46:40.827065Z","done":True,"done_reason":"stop","total_duration":11576384917,"load_duration":729326625,"prompt_eval_count":1036,"prompt_eval_duration":5908424042,"eval_count":99,"eval_duration":4915807333,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-28fc4179-6a4e-4cf1-b9ce-5edfcd2a6f94-0"},{"content":[{"type":"text","text":"Halo, Jimmy, selamat datang kembali ke sesi berbicara. Senyumu menunjukkan bahwa hari ini pasti penuh dengan kesenangankan bagaimana kabarmu hari ini. Ada yang lucu atau serius yang mau kita bicarakan?"}],"additional_kwargs":{},"response_metadata":{},"type":"human","name":None,"id":None},{"content":"Halo Antoni! Selamat datang kembali ke sesi berbicara. Senyumanmu menunjukkan bahwa hari ini pasti penuh dengan kesenangan-kesenanganmu. Ada topik lucu atau serius apa yang ingin kamu bagikan hari ini? Saya senang bisa mendengarkan semuanya!","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:48:08.567176Z","done":True,"done_reason":"stop","total_duration":12221135250,"load_duration":750294666,"prompt_eval_count":1204,"prompt_eval_duration":7760247042,"eval_count":73,"eval_duration":3679945292,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-b4739d21-7a99-4585-8643-10666ffab388-0"},{"content":[{"type":"text","text":"End the Session, while saying thank you for participating for the session.\n## **Always respond using Indonesian only—this is the only language the child understands.**"}],"additional_kwargs":{},"response_metadata":{},"type":"system","name":None,"id":None},{"content":"Halo Antoni, selamat datang lagi ke sesi berbicara. Senyumanmu menunjukkan bahwa hari ini pastinya penuh dengan kesenangan-kesenanganmu sendiri. Ada topik lucu atau serius apa yang ingin kamu bagikan hari ini? Saya senang bisa mendengarkan semua hal yang ada di pikiranku!","additional_kwargs":{},"response_metadata":{"model":"qwen2.5:3b","created_at":"2025-04-29T16:48:24.650049Z","done":True,"done_reason":"stop","total_duration":11876259166,"load_duration":761063916,"prompt_eval_count":1313,"prompt_eval_duration":6995112541,"eval_count":80,"eval_duration":4080193709,"message":{"role":"assistant","content":"","images":None,"tool_calls":None}},"type":"ai","name":None,"id":"run-468c45c7-8290-4d70-9dd3-34983a6737f5-0"}],"result":{"overview":"Start the session by greeting warmly and naturally in the child's language, inviting them to share their day or anything they'd like to talk about. Show that you're there to listen fully without judgment, keep it short, kind, and encouraging.","emotion":"Kindness","keypoints":["Warm greeting","Inviting to share","Listen without judgment"]}}],"created_datetime":"2025-04-29T16:48:37.276170+00:00"}]
        st.warning("Backend tidak aktif, maka menggunakan alternatif database.")

    if not list_conversation:
        st.error("No conversation ever recorded from the provided device id")
        st.info(
            "Jika anda ingin melihat demo tampilan dan backend harus tidak berjalan, dapat menggunakan device_id `2b129436-1a2d-11f0-9045-6ac49b7e4ceb`"
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

        convoStartTime = session["messages"][2]["response_metadata"]["created_at"]
        convoStartTime = parser.isoparse(convoStartTime)
        convoStartTimeDate = convoStartTime.strftime("%d %B %Y")
        convoStartTimeHour = convoStartTime.strftime("%H:%M")

        convoEndTime = session["messages"][-1]["response_metadata"]["created_at"]
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
        
        result = session["result"]
        overview = result["overview"]
        emotion = result["emotion"]
        keypoints = result["keypoints"]

        

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
