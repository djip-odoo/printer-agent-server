
🔐 Local Print Agent API
==========================

A cross-platform FastAPI-based local print agent to communicate with ESC/POS thermal printers over raw sockets using base64 raster data.

---

🚀 Features
-----------
- ✅ FastAPI backend with HTTPS (SSL included)
- ✅ ESC/POS raster image printing
- ✅ Cash drawer pulse support
- ✅ Printer status reporting (cover open, paper error, etc.)
- ✅ Build as a standalone executable (Windows/Linux/macOS)
- ✅ CORS enabled for cross-origin access

---


🛠 Setup & Build Instructions
-----------------------------

### Linux / macOS:

```bash
chmod +x build.sh
./build.sh
```

### Windows:

```cmd
build_windows.bat
```

---

📦 Dependencies (frozen)
------------------------
- fastapi==0.115.12
- uvicorn==0.34.3
- pydantic==2.11.5
- pyinstaller==6.14.1
- python-escpos===3.1
- pyusb===25.2

---

🔐 SSL Certificates
--------------------

If not already present, generate with:

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=localhost"
```

---

📬 API Endpoints
----------------

### `GET /`
Check if the server is up.

**Response:**
```json
{ "message": "Printer server is working!" }
```

### `POST /pos/print/`
Send rasterized receipt data to the printer.

**Request Body:**
```json
{
  "raster_base64": "<base64-encoded-image>",
  "width": 576,
  "height": 100,
  "nw_printer_ip": "192.168.0.100:9100",
  "cash_drawer": true
}
```

**Success Response:**
```json
{ "status": "success" }
```

**Failure Response:**
```json
{ "status": "error", "message": { "Printer Status": ["Printer is busy"] } }
```

---

🖨️ Supported Status Checks
---------------------------
- Printer Status
- Offline Status
- Error Status
- Paper Status

Returned in human-readable form to help with diagnostics.

---

🧪 Running the Server After Build
---------------------------------

```bash
./dist/main          # Linux/macOS
dist\main.exe       # Windows
```

It runs on:

```
https://{your_device_ip_address}:8088/
```
