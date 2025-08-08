import logging
import usb.core
import usb.util
import os
import sys
from starlette.templating import Jinja2Templates
logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    templates_dir = os.path.join(sys._MEIPASS, 'templates')
else:
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

templates = Jinja2Templates(directory=templates_dir)

import usb.core
import usb.util
import logging

logger = logging.getLogger(__name__)

EPOS_PRINTERS = {
    0x0fe6: "RuGtek",         # May also be Xprinter
    0x04b8: "EPSON",
    0x1504: "BIXOLON",
    0x0416: "Winbond",
    0x1fc9: "POSBANK",
    0x0519: "Star Micronics",
}
import usb.core
import usb.util
import logging

logger = logging.getLogger(__name__)

EPOS_PRINTERS = {
    0x4b43: "Caysn OR Shreyans",
    0x0fe6: "RuGtek or Xprinter",         # May also be Xprinter
    0x04b8: "EPSON",
    0x1504: "BIXOLON",
    0x0416: "Winbond",
    0x1fc9: "POSBANK",
    0x0519: "Star Micronics",
}

KEYWORDS = ["printer", "thermal", "receipt", "pos", "rugtek", "xprinter"]
def list_known_epos_printers(known=True):
    devices = usb.core.find(find_all=True)
    printers = []

    for device in devices:
        try:
            vid = device.idVendor
            pid = device.idProduct

            # Flags
            is_known_vendor = vid in EPOS_PRINTERS
            is_printer_interface = False

            # Check interface class
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 0x07:
                        is_printer_interface = True
                        break
                if is_printer_interface:
                    break

            # Manufacturer/Product strings
            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"
            name_combined = f"{manufacturer} {product}".lower()

            has_keyword_match = any(keyword in name_combined for keyword in KEYWORDS)

            # Skip logic
            # if known and not is_known_vendor:
            #     continue
            # elif known and not (is_known_vendor or is_printer_interface or has_keyword_match):
            #     continue

            printers.append({
                "vendor_id": f"{vid:04x}",
                "product_id": f"{pid:04x}",
                "manufacturer": manufacturer,
                "vendor_name": EPOS_PRINTERS.get(vid, "Unknown"),
                "product": product,
                "matched_by": (
                    "No Filter Applied" if known == False else
                    "Vendor id" if is_known_vendor else
                    "Interface class" if is_printer_interface else
                    "Name keyword"
                ),
            })

        except usb.core.USBError:
            continue
        except Exception as e:
            logger.warning(f"Error reading device info: {e}")
            continue

    return printers



def printer_list_page(request):
    return templates.TemplateResponse("index.html", {"request": request, "printers": list_known_epos_printers(known=False)})
