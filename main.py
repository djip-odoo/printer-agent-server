import os
import sys
import socket
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from escpos.printer import Usb
from queue import Queue
from threading import Thread

app = FastAPI(
    title="Local Print Agent API",
    description="A FastAPI server to communicate with ESC/POS thermal printers over raw sockets.",
    version="1.0.0"
)

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

print_queue = Queue()

def printer_worker():
    while True:
        data = print_queue.get()
        if data is None:
            break
        try:
            handle_print_job(data)
        except Exception as e:
            print(f"[ERROR] Print job failed: {e}")
        finally:
            print_queue.task_done()

def handle_print_job(data: PrintRequest):
    raster_bytes = base64.b64decode(data.raster_base64)

    VENDOR_ID = "0x" + data.vendor_id #0fe6
    PRODUCT_ID = "0x" + data.product_id #811e

    printer = Usb(VENDOR_ID, PRODUCT_ID, timeout=0, in_ep=0x82, out_ep=0x01)
    
    if printer.device.is_kernel_driver_active(0):
        printer.device.detach_kernel_driver(0)

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

# Start the worker thread on boot
worker_thread = Thread(target=printer_worker, daemon=True)
worker_thread.start()

# ==================== ✅ PRINT ENDPOINT MODIFIED ====================

@app.post("/pos/print/")
def print_receipt(data: PrintRequest):
    try:
        print_queue.put(data)
        return {"status": "queued", "message": "Print job added to queue"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
