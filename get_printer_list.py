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

def list_usb_printers(request):
    devices = usb.core.find(find_all=True)
    printers = []

    for device in devices:
        try:
            vendor_id = device.idVendor
            product_id = device.idProduct

            if device.bDeviceClass not in (0, 7):
                continue

            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"

            printers.append({
                "vendor_id": f"{vendor_id:04x}",
                "product_id": f"{product_id:04x}",
                "manufacturer": manufacturer,
                "product": product,
            })

        except usb.core.USBError:
            continue
        except Exception as e:
            logger.warning(f"Error getting USB printer info: {e}")
            continue

    return templates.TemplateResponse("index.html", {"request": request, "printers": printers})
    # return printers
    # return {"status": "success", "printers": printers}
