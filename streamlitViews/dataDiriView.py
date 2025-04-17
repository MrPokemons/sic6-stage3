import streamlit as st

st.title("Biodata Anak 🧒")
# st.header("One Voice, Many Stories, Endless Smiles!")
# st.header("Satu Suara, Seribu Cerita, Senyum Tiada Henti!")
child_profile = []

with st.form("child_profile_form"):
    name = st.text_input("🧒 Nama")
    age = st.number_input("🎂 Umur", min_value=5, max_value=12, step=1)
    gender = st.selectbox("🚻 Gender", ["Pilih Gender", "Laki-laki", "Perempuan"])
    description = st.text_area("🚲 Deskripsi Anak (hobi dan minat, kepribadian)")
    purpose = st.text_area("🌠 Harapan Orang Tua")
    grade = st.selectbox(
        "📚 Tingkatan",
        [
            "Pilih Tingkatan",
            "PAUD",
            "TK A",
            "TK B",
            "SD Kelas 1",
            "SD Kelas 2",
            "SD Kelas 3",
            "SD Kelas 4",
            "SD Kelas 5",
            "SD Kelas 6",
        ],
    )

    submitted = st.form_submit_button("Simpan Data")

if submitted:
    if name == "":
        st.warning("Nama harus diisi")
    elif gender == "Pilih Gender":
        st.warning("Pilih salah satu gender")
    elif description == "":
        st.warning("Deskripsi anak harus diisi")
    elif purpose == "":
        st.warning("Harapan orang tua harus diisi")
    elif grade == "Pilih Tingkatan":
        st.warning("Pilih salah satu tingkatan anak")
    else:
        st.success("✅ Data berhasil disimpan!")

        with st.container(border=True):
            st.subheader("🧒 Data Anak")
            st.write(f"**Nama:** {name}")
            st.write(f"**Umur:** {age} tahun")
            st.write(f"**Gender:** {gender}")
            st.write(f"**Deskripsi:** {description}")
            st.write(f"**Harapan:** {purpose}")
            st.write(f"**Tingkatan:** {grade}")

        # Optionally, you can store this in a dictionary or write to a file/db
        child_profile = {
            "nama": name,
            "umur": age,
            "gender": gender,
            "deskripsi": description,
            "harapan": purpose,
            "tingkatan": grade,
        }

        # Simpan ke session_state jika mau dipakai di page lain
        st.session_state["child_profile"] = child_profile
