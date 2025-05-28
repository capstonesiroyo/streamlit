import requests
from bs4 import BeautifulSoup
import time
import re
from pymongo import MongoClient
from datetime import datetime
import schedule
import pytz
from collections import Counter
import string
import nltk

#pastikan nltk stopwords sudah tersedia
nltk.download('stopwords')
from nltk.corpus import stopwords
stop_words = set(stopwords.words('indonesian'))

# Fungsi scraping berita dari Kompas tag "olahraga"
def scrape_kompas_crime():
    url_artikel = "https://www.kompas.com/tag/olahraga"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    all_data = []
    article_titles = []
    page = 1
    max_pages = 10

    # Tanggal scraping (format WIB)
    scrape_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")

    # Koneksi ke MongoDB untuk memeriksa data yang sudah ada
    client = MongoClient("mongodb+srv://sagitarius:22090017@cluster0.dabaqxm.mongodb.net/gym?retryWrites=true&w=majority&appName=Cluster0")
    db = client["gym"]
    collection = db["gymData"]

    # Ambil semua artikel yang sudah ada untuk mencegah duplikasi
    existing_links = set(item["link"] for item in collection.find({"scraped_at": scrape_time}))

    while True:
        print(f"Mengambil halaman {page}...")
        url = f"{url_artikel}?page={page}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Gagal mengambil halaman {page}")
            break

        soup = BeautifulSoup(response.text, "html.parser")

        if soup.find("div", class_="searchContent --emptyAlart"):
            print("Halaman kosong ditemukan, scraping dihentikan.")
            break

        article_list = soup.find("div", class_="articleList -list")
        if not article_list:
            print("Daftar artikel tidak ditemukan.")
            break

        articles = article_list.find_all("div", class_="articleItem")
        if not articles:
            print("Tidak ada artikel pada halaman ini.")
            break

        for article in articles:
            try:
                link_tag = article.find("a", class_="article-link")
                if not link_tag:
                    continue
                link = link_tag["href"]

                # Cek apakah artikel sudah ada berdasarkan link
                if link in existing_links:
                    continue

                title_tag = article.find("h2", class_="articleTitle")
                title = title_tag.get_text(strip=True) if title_tag else "Tidak ada judul"

                date_tag = article.find("div", class_="articlePost-date")
                date = date_tag.get_text(strip=True) if date_tag else "Tidak ada tanggal"

                # ambil isi berita
                article_response = requests.get(link, headers=headers)
                if article_response.status_code == 200:
                    article_soup = BeautifulSoup(article_response.text, "html.parser")
                    content_tags = article_soup.find_all("p")
                    full_content = " ".join(p.get_text(strip=True) for p in content_tags)
                else:
                    full_content=" "
                
                article_titles.append(title)
             

                #simpan ke list
                all_data.append({
                    "judul": title,
                    "tanggal": date,
                    "link": link,
                    "isi_berita": full_content,
                
                })

                time.sleep(1)

            except Exception as e:
                print(f"Error parsing article: {e}")

        if page >= max_pages:
            print("Batas maksimal halaman tercapai.")
            break

        pagination_next = soup.find("a", class_="paging__link--next")
        if not pagination_next:
            print("Tidak ada halaman berikutnya.")
            break

        page += 1
        time.sleep(1)

        #analisis kata terbanyak
        if article_titles:
            all_titles = " ".join(article_titles)
            cleaned_titles = full_content.lower().translate(str.maketrans('', '', string.punctuation))
            words = cleaned_titles.split()
            filtered_words = [w for w in words if w not in stop_words]
            common_words = Counter(filtered_words).most_common(5)
        else:
            common_words = []

        for item in all_data:
            item["kata_terbanyak"] = common_words

        return all_data

# Simpan data ke MongoDB
def save_to_mongodb(data, db_name="gym", collection_name="gymData"):
    try:
        client = MongoClient("mongodb+srv://sagitarius:22090017@cluster0.dabaqxm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        db = client[db_name]
        collection = db[collection_name]

        inserted = 0
        for item in data:
            result = collection.update_one(
                {"link": item["link"]},
                {"$set": item},
                upsert=True  # Upsert artikel jika belum ada
            )
            if result.upserted_id:
                inserted += 1

        print(f"{inserted} data baru berhasil ditambahkan")
    except Exception as e:
        print(f"Error saat menyimpan ke MongoDB: {e}")

# Fungsi utama yang dijadwalkan
def job():
    print("Menjalankan scraping jam:", datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S'))
    berita = scrape_kompas_crime()
    save_to_mongodb(berita)

# Penjadwalan scraping setiap jam WIB
schedule.every().day.at("13:40").do(job)

print("Menunggu penjadwalan scraping setiap jamWIB...")

while True:
    schedule.run_pending()
    time.sleep(1)
