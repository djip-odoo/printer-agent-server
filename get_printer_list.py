import usb.core
import usb.util
from fastapi.templating import Jinja2Templates
import os
import sys
from starlette.templating import Jinja2Templates

if getattr(sys, 'frozen', False):
    templates_dir = os.path.join(sys._MEIPASS, 'templates')
else:
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

templates = Jinja2Templates(directory=templates_dir)
import usb.core
import usb.util
import logging

logger = logging.getLogger(__name__)
import usb.core
import usb.util
import logging

logger = logging.getLogger(__name__)

EPOS_PRINTERS = {
    0x0fe6: "RuGtek",
    0x04b8: "EPSON",      # Epson
    0x1504: "BIXOLON",    # Bixolon
    0x0416: "Winbond",
    0x0fe6: "Xprinter",
    0x1fc9: "POSBANK",
    0x0519: "Star Micronics",
}

def list_known_epos_printers():
    devices = usb.core.find(find_all=True)
    printers = []

    for device in devices:
        try:
            vid = device.idVendor
            pid = device.idProduct

            if vid not in EPOS_PRINTERS:
                continue  # Skip non-EPOS vendors

            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"

            printers.append({
                "vendor_id": f"{vid:04x}",
                "product_id": f"{pid:04x}",
                "manufacturer": manufacturer,
                "product": product,
                "vendor_name": EPOS_PRINTERS[vid],
            })

        except usb.core.USBError:
            continue
        except Exception as e:
            logger.warning(f"Error reading device info: {e}")
            continue

    return printers


def printer_list_page(request):
    return templates.TemplateResponse("index.html", {"request": request, "printers": list_usb_printers()})
