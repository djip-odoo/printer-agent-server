import os
import sys
import base64
import threading
import usb.core
import usb.util
import time
import atexit
import logging
from queue import Queue
from threading import Thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from escpos.printer import Usb
from usb.util import endpoint_direction, ENDPOINT_IN, ENDPOINT_OUT
from check_status import check_printer_status
from get_printer_list import list_known_epos_printers , printer_list_page
from fastapi.responses import HTMLResponse
import ctypes
import platform
from ddl_path import load_libusb_backend
from set_local_ip import setup_domain

# Load backend
backend = load_libusb_backend()

# Use backend to find devices
if backend is not None:
    devices = usb.core.find(find_all=True, backend=backend)
    for dev in devices:
        print(f"Found USB device: VID=0x{dev.idVendor:04x}, PID=0x{dev.idProduct:04x}")
else:
    print("[ERROR] libusb backend could not be initialized.")


# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("print-server")

# ========== App Setup ==========
app = FastAPI(
    title="Local Print Agent API",
    description="A FastAPI server to communicate with ESC/POS thermal printers over USB.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Models ==========
class PrintRequest(BaseModel):
    raster_base64: str
    width: int
    height: int
    vendor_id: str
    product_id: str
    cash_drawer: bool = False

class StatusCheckRequest(BaseModel):
    vendor_id: str
    product_id: str

# ========== Print Queue ==========
print_queue = Queue()

def shutdown():
    print_queue.put(None)
    worker_thread.join()

atexit.register(shutdown)

# ========== Utility ==========
def resource_path(filename: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.abspath(filename)

# ========== Health ==========
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return printer_list_page(request)

@app.get("/printer-list")
async def printer_list(request: Request):
    return {"status": "success", "message": list_known_epos_printers()}

# ========== USB Status ==========
@app.post("/printer/status-usb")
def check_usb_status(req: StatusCheckRequest):
    return check_printer_status(req.vendor_id, req.product_id)

# ========== Worker ==========
def printer_worker():
    while True:
        data = print_queue.get()
        if data is None:
            break
        try:
            handle_print_job(data)
        except Exception as e:
            logger.error(f"[ERROR] Print job failed: {e}")
        finally:
            print_queue.task_done()

def handle_print_job(data: PrintRequest):
    printer = None
    try:
        raster_bytes = base64.b64decode(data.raster_base64)
        vendor_id = int(data.vendor_id, 16)
        product_id = int(data.product_id, 16)

        logger.info(f"Connecting to printer {vendor_id:04x}:{product_id:04x}...")
        printer = Usb(vendor_id, product_id)

        printer._raw(b'\x1b@')
        bytes_per_row = (data.width + 7) // 8
        header = b'\x1dv0\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([data.height % 256, data.height // 256])
        printer._raw(header + raster_bytes)
        printer._raw(b'\n' * 1) 
        printer.cut()
        logger.info("Print job completed.")

    except Exception as e:
        logger.error(f"❌ Print job error: {e}")
    finally:
        if printer:
            printer.close()
            print("closed")
            logger.info("✅ USB resources released.")

# ========== Print Endpoint ==========
@app.post("/pos/print/")
def print_receipt(data: PrintRequest):
    print_queue.put(data)
    return {"status": "success", "message": "Print job queued."}

# ========== Start Worker Thread ==========
worker_thread = Thread(target=printer_worker, daemon=True)
worker_thread.start()

# ========== Main Entry ==========


def register_mdns_service():
    zeroconf, info, ip = setup_domain()

    # Store globally so we can close later
    app.state.zeroconf = zeroconf
    app.state.service_info = info
    print(f"📢 mDNS Service Published: https://printer-server.local:8088 (IP: {ip})")

@app.on_event("startup")
async def startup_event():
    # Run Zeroconf in its own thread
    thread = threading.Thread(target=register_mdns_service, daemon=True)
    thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "zeroconf"):
        app.state.zeroconf.unregister_service(app.state.service_info)
        app.state.zeroconf.close()
        print("❌ mDNS Service Unregistered")

if __name__ == "__main__":
    import uvicorn
    ssl_dir = resource_path("ssl")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8088,
        ssl_certfile=os.path.join(ssl_dir, "cert.pem"),
        ssl_keyfile=os.path.join(ssl_dir, "key.pem"),
    )
