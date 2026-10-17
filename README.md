# Tool Buff TikTok View (Mobile & PC)

Công cụ tăng lượt xem video TikTok tự động, hỗ trợ chạy trực tiếp trên Điện thoại Android / Ugphone (qua Termux) hoặc trên Máy tính (Windows).

---

## 📱 HƯỚNG DẪN CHẠY TRÊN ĐIỆN THOẠI / UGPHONE (4G)

### 1. Cài đặt Termux
Tải và cài đặt Termux APK: [Tải tại đây](https://github.com/termux/termux-app/releases/download/v0.118.1/termux-app_v0.118.1+github-debug_arm64-v8a.apk)

### 2. Cài môi trường (Chạy 1 lần duy nhất)
Mở Termux và dán dòng lệnh sau:
```bash
pkg update -y && pkg install python git -y && pip install httpx colorama
```

### 3. Tải và chạy Tool
```bash
git clone https://github.com/nq28/buff-tiktok.git
cd buff-tiktok
python buff.py
```

> **Mẹo tăng tốc & chống lọc IP:** Cứ sau mỗi đợt gửi (50 - 100 views), hãy vuốt thanh thông báo điện thoại **BẬT rồi TẮT Chế độ máy bay (Airplane Mode)** trong 2 giây để đổi dải IP 4G mới toanh!

Từ các lần sau, bạn chỉ cần mở Termux và gõ:
```bash
cd buff-tiktok && python buff.py
```

---

## 💻 HƯỚNG DẪN CHẠY TRÊN MÁY TÍNH (WINDOWS)

1. Cài đặt Python 3.10+ trên máy tính (nhớ tích chọn *Add Python to PATH*).
2. Tải repository này về máy:
   ```bash
   git clone https://github.com/nq28/buff-tiktok.git
   cd buff-tiktok
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Khởi chạy bằng cách nhấp đúp vào các file `.bat`:
   - **`Chay_Embed.bat`**: Bản chạy qua TikTok Embed Player V2 (Siêu nhẹ, tải ~500KB/view, tiết kiệm 80% RAM, xem stream video thật).
   - **`Chay_Browser.bat`**: Bản chạy Headless Browser đầy đủ.
   - **`Chay_Tool.bat`**: Bản Turbo API tự động kết hợp xoay Proxy.
