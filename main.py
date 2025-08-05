import os
import sys
import base64
import usb.core
import usb.util
import time
import atexit
import logging
from queue import Queue
from threading import Thread
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from escpos.printer import Usb
from usb.util import endpoint_direction, ENDPOINT_IN, ENDPOINT_OUT
from check_status import decode_status

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
@app.get("/")
def read_root():
    return {"status": "success", "message": "Printer server is running."}

@app.get("/test")
def test():
    return {"status": "success", "message": "Test successful."}

# ========== USB Status ==========
@app.post("/printer/status-usb")
def check_usb_status(req: StatusCheckRequest):
    return _check_status(req.vendor_id, req.product_id)

def _check_status(vendor_id, product_id):
    device = None
    try:
        vendor_id = int(vendor_id, 16)
        product_id = int(product_id, 16)

        device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if device is None:
            return {"status": "error", "message": "Printer not found."}

        if device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)

        device.set_configuration()
        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]

        ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT)
        ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN)

        if not ep_out or not ep_in:
            return {"status": "error", "message": "Could not find printer endpoints."}

        ep_out.write(b'\x10\x04\x01')
        response = ep_in.read(ep_in.wMaxPacketSize, timeout=2000)

        decoded = decode_status("Printer Status", response)
        status_text = "success" if all("OK" in msg or "ready" in msg or "No printer errors" in msg for msg in decoded) else "warning"
        return {"status": status_text, "message": "; ".join(decoded)}

    except ValueError:
        return {"status": "error", "message": "Invalid vendor_id or product_id format."}
    except usb.core.USBError as e:
        return {"status": "error", "message": f"USB communication failed: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            if device:
                usb.util.dispose_resources(device)
                usb.util.release_interface(device, 0)
                device.reset()
        except Exception as cleanup_error:
            logger.warning(f"[CLEANUP ERROR] {cleanup_error}")

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

        # Init and print raster
        printer._raw(b'\x1b@')
        bytes_per_row = (data.width + 7) // 8
        header = b'\x1dv0\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([data.height % 256, data.height // 256])
        # printer._raw(header + raster_bytes)
        # printer._raw(b'\x1bd\x03')
        # printer._raw(b'\x1dV\x00')

        if data.cash_drawer:
            printer.cashdraw(0)

        logger.info("Print job completed.")

    except Exception as e:
        logger.error(f"❌ Print job error: {e}")
    finally:
        if printer:
            usb.util.dispose_resources(printer.device)
            logger.info("✅ USB resources released.")

# ========== Print Endpoint ==========
@app.post("/pos/print/")
def print_receipt(data: PrintRequest):
    status = _check_status(data.vendor_id, data.product_id)
    if status["status"] != "success":
        return status
    print_queue.put(data)
    return {"status": "success", "message": "Print job queued."}

# ========== Start Worker Thread ==========
worker_thread = Thread(target=printer_worker, daemon=True)
worker_thread.start()

# ========== Main Entry ==========
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
