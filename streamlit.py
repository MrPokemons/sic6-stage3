import streamlit as st
import requests

st.title("🐾 PawPal - One Voice, Many Stories, Endless Smiles! 🐾")

user_input = st.text_input("Masukkan teks:")

if st.button("Prediksi"):
    if user_input:
        try:
            response = requests.post(
                "http://localhost:6789/predict",
                json={"text": user_input}
            )
            if response.status_code == 200:
                result = response.json()
                st.success(f"Hasil: {result}")
            else:
                st.error(f"Error dari server: {response.status_code}")
        except Exception as e:
            st.error(f"Gagal terhubung ke backend: {e}")