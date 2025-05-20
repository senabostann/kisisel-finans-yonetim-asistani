import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

# Veritabanı bağlantısı
conn = sqlite3.connect("finans.db")
cursor = conn.cursor()

# Tabloları oluştur
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    category TEXT,
    amount REAL,
    date TEXT
)
""")
conn.commit()

# Varsayılan kategoriler
varsayilan_kategoriler = ["maaş", "market", "fatura", "ulaşım", "yemek"]
for kategori in varsayilan_kategoriler:
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (kategori,))
    except sqlite3.IntegrityError:
        pass
conn.commit()

def kategori_listesini_al():
    cursor.execute("SELECT name FROM categories")
    return [row[0] for row in cursor.fetchall()]

def kayit_ekle():
    t_type = gelir_gider_var.get()
    category = kategori_combo.get()
    try:
        amount = float(tutar_entry.get())
    except ValueError:
        messagebox.showerror("Hata", "Lütfen geçerli bir tutar girin.")
        return
    date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)",
                   (t_type, category, amount, date))
    conn.commit()
    listeyi_guncelle()
    tutar_entry.delete(0, tk.END)

def kayit_sil():
    selected = liste.selection()
    if not selected:
        messagebox.showwarning("Uyarı", "Lütfen silmek için bir kayıt seçin.")
        return
    kayit_id = liste.item(selected[0])["values"][0]
    cursor.execute("DELETE FROM transactions WHERE id = ?", (kayit_id,))
    conn.commit()
    listeyi_guncelle()

def listeyi_guncelle():
    for item in liste.get_children():
        liste.delete(item)
    
    cursor.execute("SELECT id, type, category, amount, date FROM transactions ORDER BY date DESC")
    for row in cursor.fetchall():
        liste.insert("", tk.END, values=row)

    # Bakiye hesapla
    cursor.execute("SELECT type, amount FROM transactions")
    toplam = 0
    for t_type, amount in cursor.fetchall():
        toplam += amount if t_type == "gelir" else -amount
    bakiye_label.config(text=f"Bakiye: {toplam:.2f} TL")

def kategori_ekle_penceresi():
    def kategori_ekle():
        yeni_kategori = kategori_entry.get().strip().lower()
        if not yeni_kategori:
            messagebox.showerror("Hata", "Kategori boş olamaz.")
            return
        try:
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (yeni_kategori,))
            conn.commit()
            kategori_combo['values'] = kategori_listesini_al()
            kategori_entry.delete(0, tk.END)
            messagebox.showinfo("Başarılı", f"{yeni_kategori} kategorisi eklendi.")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Uyarı", "Bu kategori zaten var.")

    pencere_kategori = tk.Toplevel()
    pencere_kategori.title("Yeni Kategori Ekle")
    pencere_kategori.geometry("300x100")

    tk.Label(pencere_kategori, text="Kategori Adı:").pack(pady=5)
    kategori_entry = tk.Entry(pencere_kategori)
    kategori_entry.pack(pady=5)

    tk.Button(pencere_kategori, text="Ekle", command=kategori_ekle).pack(pady=5)

def kategori_sil():
    secili_kategori = kategori_combo.get()
    if not secili_kategori:
        messagebox.showwarning("Uyarı", "Silmek için bir kategori seçin.")
        return

    cevap = messagebox.askyesno("Onay", f"'{secili_kategori}' kategorisini ve ona bağlı tüm kayıtları silmek istediğinize emin misiniz?")
    if not cevap:
        return

    # Kategoriye bağlı işlemleri sil
    cursor.execute("DELETE FROM transactions WHERE category = ?", (secili_kategori,))
    # Kategoriyi sil
    cursor.execute("DELETE FROM categories WHERE name = ?", (secili_kategori,))
    conn.commit()

    # Kategori listesini güncelle
    yeni_kategoriler = kategori_listesini_al()
    kategori_combo['values'] = yeni_kategoriler
    if yeni_kategoriler:
        kategori_combo.set(yeni_kategoriler[0])
    else:
        kategori_combo.set('')

    listeyi_guncelle()
    messagebox.showinfo("Başarılı", f"'{secili_kategori}' kategorisi ve ilişkili kayıtlar silindi.")

def butce_tavsiyesi_goster():
    cursor.execute("SELECT type, amount FROM transactions")
    gelir = 0
    gider = 0
    for t_type, amount in cursor.fetchall():
        if t_type == "gelir":
            gelir += amount
        else:
            gider += amount
    bakiye = gelir - gider

    if gelir == 0:
        oran = 0
    else:
        oran = (gider / gelir) * 100

    mesaj = f"""
Toplam Gelir: {gelir:.2f} TL
Toplam Gider: {gider:.2f} TL
Bakiye: {bakiye:.2f} TL
Gider/gelir oranı: %{oran:.2f}
"""

    if oran > 90:
        mesaj += "\n⚠️ Giderler gelirinize çok yakın. Tasarruf yapmalısınız."
    elif oran > 70:
        mesaj += "\nℹ️ Giderler yüksek. Harcamaları gözden geçirin."
    elif oran > 50:
        mesaj += "\n🙂 Fena değil ama daha az harcayabilirsiniz."
    else:
        mesaj += "\n✅ Harika! Gelirinizi verimli kullanıyorsunuz."

    # Para biriktirmek için öneriler
    mesaj += "\n\n💡 Para Biriktirmek İçin Öneriler:"
    if oran > 50:
        mesaj += """
- Giderlerinizi gelirinize göre %50'nin altına düşürmeye çalışın.
- Gereksiz harcamalardan kaçının.
- Aylık birikim hedefi belirleyin ve o hedefe sadık kalın.
- Harcama kalemlerinizi gözden geçirip tasarruf edebileceğiniz alanları bulun.
"""
    else:
        mesaj += "- Mevcut durumunuz iyi, birikim hedeflerinizi artırabilirsiniz."

    messagebox.showinfo("Bütçe Tavsiyesi", mesaj)

def grafik_goster():
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='gider' GROUP BY category")
    veriler = cursor.fetchall()
    
    if not veriler:
        messagebox.showinfo("Bilgi", "Henüz gider kaydı bulunamadı.")
        return

    kategoriler = [row[0] for row in veriler]
    tutarlar = [row[1] for row in veriler]

    plt.figure(figsize=(6,6))
    plt.pie(tutarlar, labels=kategoriler, autopct="%1.1f%%", startangle=90)
    plt.title("Gider Dağılımı (Kategori Bazında)")
    plt.axis("equal")
    plt.show()

# Ana pencere
pencere = tk.Tk()
pencere.title("Bütçe Takip Uygulaması")
pencere.geometry("900x800")

# Giriş alanları
frame = tk.Frame(pencere)
frame.pack(pady=10)

tk.Label(frame, text="Tür:").grid(row=0, column=0)
gelir_gider_var = tk.StringVar(value="gider")
tk.OptionMenu(frame, gelir_gider_var, "gelir", "gider").grid(row=0, column=1)

tk.Label(frame, text="Kategori:").grid(row=0, column=2)
kategori_combo = ttk.Combobox(frame, values=kategori_listesini_al(), state="readonly")
kategori_combo.grid(row=0, column=3)
kategori_combo.set("market")

tk.Label(frame, text="Tutar:").grid(row=0, column=4)
tutar_entry = tk.Entry(frame)
tutar_entry.grid(row=0, column=5)

tk.Button(frame, text="Ekle", command=kayit_ekle).grid(row=0, column=6, padx=5)

# Kayıt listesi
liste = ttk.Treeview(pencere, columns=("ID", "Tür", "Kategori", "Tutar", "Tarih"), show="headings")
liste.heading("ID", text="ID")
liste.heading("Tür", text="Tür")
liste.heading("Kategori", text="Kategori")
liste.heading("Tutar", text="Tutar")
liste.heading("Tarih", text="Tarih")
liste.pack(pady=10, fill="both", expand=True)

# İşlem butonları
tk.Button(pencere, text="Seçili Kaydı Sil", command=kayit_sil, bg="tomato").pack(pady=5)
tk.Button(pencere, text="Yeni Kategori Ekle", command=kategori_ekle_penceresi).pack(pady=5)
tk.Button(pencere, text="Seçili Kategoriyi Sil", command=kategori_sil, bg="orange").pack(pady=5)
tk.Button(pencere, text="Bütçe Tavsiyesi Al", command=butce_tavsiyesi_goster).pack(pady=5)
tk.Button(pencere, text="Gider Grafiğini Göster", command=grafik_goster).pack(pady=5)

# Bakiye göstergesi
bakiye_label = tk.Label(pencere, text="Bakiye: 0 TL", font=("Arial", 14, "bold"))
bakiye_label.pack(pady=5)

listeyi_guncelle()
pencere.mainloop()
