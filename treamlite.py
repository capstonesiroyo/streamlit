import streamlit as st
from pymongo import MongoClient
from collections import Counter
import pandas as pd
import re

# Koneksi MongoDB
client = MongoClient("mongodb+srv://sagitarius:22090017@cluster0.dabaqxm.mongodb.net/")
db = client["gym"]
collection = db["gymData"]

# Judul Aplikasi
st.title("Visualisasi Data Kompas - Olahraga")

# Fungsi pencarian
keyword = st.text_input("Cari kata di isi berita:")

if keyword:
    query = {"isi_berita": {"$regex": keyword, "$options": "i"}}
    search_results = list(collection.find(query))
    st.subheader(f"Hasil pencarian untuk '{keyword}'")
    for article in search_results:
        st.markdown(f"**{article.get('judul', '')}** - {article.get('tanggal', '')}")
        st.markdown(f"[Buka Artikel]({article.get('link', '#')})")
else:
    search_results = list(collection.find())

# Statistik dasar
all_articles = list(collection.find())
total_artikel = len(all_articles)
st.metric("Total Artikel", total_artikel)

# --- Grafik: Artikel per tanggal ---
tanggal_counts = {}
for article in all_articles:
    tgl = article.get("scraped_at", "Unknown")
    tanggal_counts[tgl] = tanggal_counts.get(tgl, 0) + 1

if tanggal_counts:
    df_tanggal = pd.DataFrame(list(tanggal_counts.items()), columns=["Tanggal", "Jumlah"])
    df_tanggal = df_tanggal.sort_values(by="Tanggal")
    st.subheader("Grafik Jumlah Artikel per Tanggal")
    st.bar_chart(df_tanggal.set_index("Tanggal"))

# --- Pie Chart: Kata Paling Umum di Judul ---
title_word_counter = Counter()
for article in all_articles:
    title = article.get("judul", "").lower()
    words = re.findall(r'\b\w+\b', title)
    title_word_counter.update(words)

top_words = title_word_counter.most_common(6)
if top_words:
    df_pie = pd.DataFrame(top_words, columns=["Kata", "Frekuensi"])
    st.subheader("Kata Paling Sering di Judul")
    st.bar_chart(df_pie.set_index("Kata"))  # Streamlit belum mendukung pie chart native

# --- Tabel Artikel Terbaru ---
st.subheader("10 Artikel Terbaru")
latest_articles = list(collection.find().sort("scraped_at", -1).limit(10))
for article in latest_articles:
    st.markdown(f"- **{article.get('judul', '')}** ({article.get('tanggal', '')}) - [Link]({article.get('link', '#')})")
