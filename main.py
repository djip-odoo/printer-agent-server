import os
import sys
import base64
import usb.core
import usb.util
import socket
import atexit
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from queue import Queue
from threading import Thread
from escpos.printer import Usb
from fastapi.middleware.cors import CORSMiddleware
from usb.util import endpoint_direction, ENDPOINT_IN, ENDPOINT_OUT
from check_status import decode_status
import time

app = FastAPI(
    title="Local Print Agent API",
    description="A FastAPI server to communicate with ESC/POS thermal printers over USB.",
    version="1.0.0"
)

# ========== Graceful Shutdown Handler ==========
print_queue = Queue()

def shutdown():
    print_queue.put(None)
    worker_thread.join()

atexit.register(shutdown)

# ========== CORS Middleware ==========
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
    # nw_printer_ip: str 
    vendor_id: str
    product_id: str
    cash_drawer: bool = False

class StatusCheckRequest(BaseModel):
    vendor_id: str
    product_id: str

# ========== Health Endpoints ==========
@app.get("/")
def read_root():
    return {"message": "Printer server is working!"}

@app.get("/test")
def test_endpoint():
    return {"status": "Test successful"}

@app.post("/printer/status-usb")
def check_usb_status(req: StatusCheckRequest):
    device = None
    start_time = time.time()

    try:
        vendor_id = int(req.vendor_id, 16)
        product_id = int(req.product_id, 16)

        device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Printer not found")

        if device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)

        device.set_configuration()
        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]

        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT
        )
        ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
        )

        if ep_out is None or ep_in is None:
            raise HTTPException(status_code=500, detail="Could not find printer endpoints")

        # Send DLE EOT 1 to check printer status
        ep_out.write(b'\x10\x04\x01')
        # Wait for printer response
        response = ep_in.read(ep_in.wMaxPacketSize, timeout=2000)
        print(f"[JOB] Response received at {time.time() - start_time:.3f}s")

        decoded = decode_status("Printer Status", response)
        return {
            "status": "ok" if all("OK" in msg or "ready" in msg or "No printer errors" in msg for msg in decoded) else "warning",
            "details": decoded
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex format for vendor_id or product_id")
    except usb.core.USBError as e:
        raise HTTPException(status_code=500, detail=f"USB communication failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"USB Printer status check failed: {str(e)}")
    finally:
        try:
            if device:
                usb.util.dispose_resources(device)
                # Explicit release interface and reset
                usb.util.release_interface(device, 0)
                device.reset()
        except Exception as cleanup_error:
            print(f"[CLEANUP ERROR] {cleanup_error}")

# ========== Print Worker ==========

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
    printer = None

    try:
        print("⏳ Decoding raster...")
        raster_bytes = base64.b64decode(data.raster_base64)

        # vendor_id = 0x0fe6 #int(data.vendor_id, 16)
        # product_id = 0x811e #int(data.product_id, 16)
        
        vendor_id = int(data.vendor_id, 16)
        product_id = int(data.product_id, 16)

        print(f"🔍 Connecting to printer {vendor_id:04x}:{product_id:04x}...")
        printer = Usb(vendor_id, product_id)

        # Initialize
        printer._raw(b'\x1b@')

        # Construct raster header (bit image mode)
        bytes_per_row = (data.width + 7) // 8
        header = b'\x1dv0\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([data.height % 256, data.height // 256])

        print("🖨️ Sending raster image...")
        printer._raw(header + raster_bytes)

        printer._raw(b'\x1bd\x03')  # Feed 3 lines
        printer._raw(b'\x1dV\x00')  # Cut paper

        if data.cash_drawer:
            print("💵 Opening cash drawer...")
            printer.cashdraw(0)

    except Exception as e:
        print(f"❌ Print job failed: {e}")

    finally:
        if printer:
            usb.util.dispose_resources(printer.device)
            print("✅ Resources released")

# ========== Print Endpoint ==========
@app.post("/pos/print/")
def print_receipt(data: PrintRequest):
    try:
        print_queue.put(data)
        return {"status": "queued", "message": "Print job added to queue"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== Utility ==========
def resource_path(filename: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.abspath(filename)

# ========== Server Start ==========
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

# ========== Start Worker ==========
worker_thread = Thread(target=printer_worker, daemon=True)
worker_thread.start()
