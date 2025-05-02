import streamlit as st

st.title("🐾 Tentang PawPal")
st.subheader("Playful Adaptive IoT and AI Learning Companion")

with st.container():
    st.write(
        "PawPal adalah boneka pintar interaktif berbasis IoT dan AI yang dirancang untuk mengurangi screen time dan mendorong interaksi bermakna bagi anak-anak. Menggunakan teknologi speech-to-text, natural language understanding, dan text-to-speech, PawPal berkomunikasi secara alami dalam Bahasa Indonesia. Dengan fitur pembelajaran adaptif, percakapan interaktif, dan permainan edukatif, PawPal mendukung perkembangan kognitif dan emosional anak melalui pengalaman bermain sambil belajar yang aman dan menyenangkan. Semua interaksi diproses melalui server cloud yang andal dan aman."
    )

with st.container():
    st.subheader("🌟 Fitur Utama")
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("👄 Talk To Me"):
            st.write(
                "Percakapan natural yang membantu anak mengekspresikan diri dan mengembangkan keterampilan sosial-emosional."
            )
        with st.expander("🖐️ Math Adventures"):
            st.write(
                "Permainan pemecahan masalah interaktif yang membangun konsep dasar matematika melalui cerita yang seru."
            )
    with col2:
        with st.expander("🔤 Spelling Games"):
            st.write(
                "Latihan mengeja yang dipandu suara untuk memperkuat kosakata dan pengenalan huruf."
            )
        with st.expander("❓ Would you Rather"):
            st.write(
                "Pertanyaan ringan dan imajinatif yang mendorong pemikiran kritis dan kreativitas anak."
            )
    # st.write("PawPal menghadirkan berbagai aktivitas berbasis suara yang menarik untuk membuat proses belajar menjadi menyenangkan dan interaktif: \n1. Talk to Me \nPercakapan natural yang membantu anak mengekspresikan diri dan mengembangkan keterampilan sosial-emosional. \n2. Math Adventures Permainan pemecahan masalah interaktif yang membangun konsep dasar matematika melalui cerita yang seru. \n3. Spelling Games Latihan mengeja yang dipandu suara untuk memperkuat kosakata dan pengenalan huruf. \n4. Would you Rather Pertanyaan ringan dan imajinatif yang mendorong pemikiran kritis dan kreativitas anak.")

with st.container():
    st.subheader("🎯 Pengguna PawPal")
    st.write(
        "PawPal dirancang khusus untuk anak usia 4 hingga 8 tahun, dengan aktivitas yang sesuai usia untuk mendukung pembelajaran dan interaksi yang menyenangkan tanpa layar."
    )

with st.container():
    st.subheader('📥 Apa fungsi input "Durasi"?')
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, height=110):
            st.write("Durasi menentukan total waktu bermain anak bersama PawPal.")
    with col2:
        with st.container(border=True, height=110):
            st.write(
                "Misalnya, jika Anda mengatur durasi 30 menit, maka PawPal akan berinteraksi selama total 30 menit, terbagi dalam sesi yang Anda tentukan."
            )

with st.container():
    st.subheader('🧩 Apa fungsi input "Sesi"?')
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, height=160):
            # st.write("")
            st.write(
                "Sesi menentukan berapa jenis aktivitas berbeda yang akan dimainkan PawPal dalam satu periode."
            )
    with col2:
        with st.container(border=True, height=160):
            st.markdown(
                "Contoh, "
                "jika Anda memasukkan 2 sesi, maka PawPal bisa menjalankan:<br>"
                "📌 10 menit bermain \"Talk to Me\"<br>"
                "📌 7 pertanyaan untuk bermain \"Math Adventures\"",
                unsafe_allow_html=True
            )
    st.write(
        "Ini memberikan variasi agar anak tidak bosan dan tetap belajar secara menyenangkan."
    )

with st.container():
    st.subheader("💬 Apakah bisa dikustom sesuai kebutuhan anak?")
    st.write(
        "Tentu saja! Anda bisa memilih dan mengatur kombinasi fitur berdasarkan jumlah sesi yang diinginkan, sesuai mood, kebiasaan, atau perkembangan anak Anda."
    )


st.markdown(
    """
    <style>
        div[data-testid="stExpander"] details {
            background-color: #1e5677 !important;
            border: 0;
        }
        
        div[data-testid="stExpanderDetails"] {
            background-color: #ededed;
            padding-top: 1rem;
        }
            
        div[data-testid="stExpanderDetails"] p {
            color: black !important;
        }
            
            
        summary, summary svg {
            color: white !important;
        }
            
        summary:hover span{
            color: white !important;
        }
            
        summary:hover svg{
            fill: white !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)
