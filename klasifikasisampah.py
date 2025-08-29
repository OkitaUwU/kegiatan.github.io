import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder

# ===============================
# 1. Dataset lebih realistis (seimbang)
# ===============================
data = {
    "jenis_bahan": [
        "makanan", "plastik", "daun", "botol plastik", "kertas", "besi",
        "kulit buah", "sisa nasi", "sayuran busuk", "buah busuk",
        "kaleng minuman", "styrofoam", "kaca", "daun kering", "tulang"
    ],
    "mudah_terurai": [
        "ya", "tidak", "ya", "tidak", "ya", "tidak",
        "ya", "ya", "ya", "ya",
        "tidak", "tidak", "tidak", "ya", "ya"
    ],
    "dapat_daur_ulang": [
        "tidak", "ya", "tidak", "ya", "ya", "ya",
        "tidak", "tidak", "tidak", "tidak",
        "ya", "tidak", "ya", "tidak", "tidak"
    ],
    "berbau": [
        "ya", "tidak", "ya", "tidak", "tidak", "tidak",
        "ya", "ya", "ya", "ya",
        "tidak", "tidak", "tidak", "tidak", "ya"
    ],
    "target": [
        "organik", "anorganik", "organik", "anorganik", "anorganik", "anorganik",
        "organik", "organik", "organik", "organik",
        "anorganik", "anorganik", "anorganik", "organik", "organik"
    ]
}
df = pd.DataFrame(data)

# Encode teks -> angka
encoders = {}
for col in df.columns:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le

# Split data
X = df.drop("target", axis=1)
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Latih model ML
model = DecisionTreeClassifier(criterion="entropy", random_state=42)
model.fit(X_train, y_train)

# ===============================
# 2. Rule-based system (diperluas)
# ===============================
sampah_organik = [
    "makanan", "daun", "kulit buah", "sisa nasi", "sayuran busuk",
    "buah busuk", "daun kering", "tulang", "kotoran"
]
sampah_anorganik = [
    "plastik", "botol plastik", "styrofoam", "besi", "kaleng minuman",
    "kertas", "kaca"
]

def rule_based(nama_sampah):
    nama_sampah = nama_sampah.lower().strip()
    if nama_sampah in sampah_organik:
        return "organik"
    elif nama_sampah in sampah_anorganik:
        return "anorganik"
    else:
        return None  # tidak ketemu, serahkan ke ML

# ===============================
# 3. Hybrid Klasifikasi
# ===============================
def klasifikasi_sampah(nama_sampah, mudah_terurai, dapat_daur_ulang, berbau):
    # 1. Cek Rule-Based
    hasil_rule = rule_based(nama_sampah)
    if hasil_rule is not None:
        print(f"\n🗑️ HASIL KLASIFIKASI (Rule-Based)")
        print(f"Sampah '{nama_sampah}' dikategorikan sebagai: **{hasil_rule.upper()}**")
        if hasil_rule == "organik":
            print("👉 Buang ke tempat sampah hijau (organik) atau dijadikan kompos 🌱")
        else:
            print("👉 Buang ke tempat sampah kuning (anorganik) untuk didaur ulang ♻️")
        return

    # 2. Jika tidak ada di Rule, pakai ML
    sample = pd.DataFrame({
        "jenis_bahan": [nama_sampah],
        "mudah_terurai": [mudah_terurai],
        "dapat_daur_ulang": [dapat_daur_ulang],
        "berbau": [berbau]
    })

    # Encode sesuai ML
    for col in sample.columns:
        if col in encoders:
            try:
                sample[col] = encoders[col].transform(sample[col])
            except ValueError:
                sample[col] = [0]  # default kalau value baru

    pred = model.predict(sample)[0]
    hasil = encoders["target"].inverse_transform([pred])[0]

    print(f"\n🗑️ HASIL KLASIFIKASI (Machine Learning)")
    print(f"Sampah '{nama_sampah}' dikategorikan sebagai: **{hasil.upper()}**")
    if hasil == "organik":
        print("👉 Buang ke tempat sampah hijau (organik) atau dijadikan kompos 🌱")
    else:
        print("👉 Buang ke tempat sampah kuning (anorganik) untuk didaur ulang ♻️")

# ===============================
# 4. Validasi Input
# ===============================
def get_input(prompt, allowed_values=None):
    while True:
        value = input(prompt).strip().lower()
        if value == "":
            print("⚠️ Input tidak boleh kosong. Silakan isi lagi.")
            continue
        if allowed_values and value not in allowed_values:
            print(f"⚠️ Input harus salah satu dari {allowed_values}. Silakan isi lagi.")
            continue
        return value

# ===============================
# 5. Program Utama
# ===============================
def main():
    print("=== SISTEM KLASIFIKASI SAMPAH (Hybrid Realistis) ===")
    print("Ketik 'keluar' untuk berhenti.\n")

    while True:
        jenis_bahan = get_input("Masukkan jenis sampah: ")
        if jenis_bahan.lower() == "keluar":
            break

        mudah_terurai = get_input("Mudah terurai? (ya/tidak): ", ["ya", "tidak"])
        dapat_daur_ulang = get_input("Dapat didaur ulang? (ya/tidak): ", ["ya", "tidak"])
        berbau = get_input("Berbau? (ya/tidak): ", ["ya", "tidak"])

        klasifikasi_sampah(jenis_bahan, mudah_terurai, dapat_daur_ulang, berbau)

if __name__ == "__main__":
    main()
