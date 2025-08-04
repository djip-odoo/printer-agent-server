import os
import sys
import socket
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from escpos.printer import Usb

app = FastAPI(
    title="Local Print Agent API",
    description="A FastAPI server to communicate with ESC/POS thermal printers over raw sockets.",
    version="1.0.0"
)

# Allow all CORS for testing purposes. In production, restrict this!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Printer server is working!"}

@app.get("/test")
def test_endpoint():
    return {"status": "Test successful"}

# BaseModel for printing request
class PrintRequest(BaseModel):
    raster_base64: str
    width: int
    height: int
    nw_printer_ip: str  # Expected format: "ip:port"
    cash_drawer: bool = False

# ESC/POS status commands
STATUS_COMMANDS = {
    'Printer Status': b'\x10\x04\x01',
    'Offline Status': b'\x10\x04\x02',
    'Error Status': b'\x10\x04\x03',
    'Paper Status': b'\x10\x04\x04',
}

@app.post("/pos/print/")
def print_receipt(data: PrintRequest):
    try:
        raster_bytes = base64.b64decode(data.raster_base64)

        VENDOR_ID = 0x0fe6  # Example: Epson
        PRODUCT_ID = 0x811e  # Example: TM-T20
        printer = Usb(VENDOR_ID, PRODUCT_ID, timeout=0, in_ep=0x82, out_ep=0x01)

        printer._raw(b'\x1b@')
        bytes_per_row = (data.width + 7) // 8

        header = b'\x1d' + b'v' + b'0' + b'\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([data.height % 256, data.height // 256])
        printer._raw(header + raster_bytes)

        printer._raw(b'\x1b\x64\x03')
        printer._raw(b'\x1dV\x00')

        if data.cash_drawer:
            printer.cashdraw(0)

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Decode status byte for human-readable messages
def decode_status(name, byte_val):
    b = byte_val[0]
    messages = []

    if name == 'Printer Status':
        if b & 0x80: messages.append("Printer is busy")
        if b & 0x40: messages.append("Feeding paper using FEED button")
        if b & 0x20: messages.append("An error has occurred")
        if b & 0x08: messages.append("Cash drawer pin 3 is high")
        if not messages: messages.append("Printer status OK")

    elif name == 'Offline Status':
        if b & 0x80: messages.append("Cover is open")
        if b & 0x40: messages.append("Paper is feeding")
        if b & 0x20: messages.append("Printer is offline")
        if b & 0x08: messages.append("Waiting for recovery")
        if not messages: messages.append("Printer is online and ready")

    elif name == 'Error Status':
        if b & 0x20: messages.append("Auto-recoverable error")
        if b & 0x08: messages.append("Unrecoverable error")
        if b & 0x04: messages.append("Auto-cutter error")
        if not messages: messages.append("No printer errors")

    elif name == 'Paper Status':
        if b & 0x08: messages.append("Paper end")
        if b & 0x04: messages.append("Paper near-end warning")
        if not messages: messages.append("Paper status OK")

    return messages

# Check printer status using socket commands
def check_printer_status(host, port):
    try:
        errors = {}
        with socket.create_connection((host, port), timeout=3) as sock:
            for name, cmd in STATUS_COMMANDS.items():
                sock.sendall(cmd)
                response = sock.recv(1)
                decoded = decode_status(name, response)
                for msg in decoded:
                    if "OK" not in msg and "ready" not in msg and "No printer errors" not in msg:
                        errors.setdefault(name, []).append(msg)

        return errors if errors else None

    except socket.timeout:
        return {"Connection Error": ["Connection timed out."]}
    except socket.error as e:
        return {"Socket Error": [str(e)]}
    except Exception as e:
        return {"Unexpected Error": [str(e)]}


def resource_path(filename: str) -> str:
    """Get absolute path to resource, works for PyInstaller and dev."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.abspath(filename)

if __name__ == "__main__":
    import uvicorn
    ssl_dir = resource_path("ssl")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080, 
        ssl_certfile=os.path.join(ssl_dir, "cert.pem"),
        ssl_keyfile=os.path.join(ssl_dir, "key.pem"),
    )
