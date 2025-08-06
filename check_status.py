import usb.core
import usb.util
from usb.util import endpoint_direction, ENDPOINT_IN, ENDPOINT_OUT

STATUS_COMMANDS = {
    'Printer Status': b'\x10\x04\x01',
    'Offline Status': b'\x10\x04\x02',
    'Error Status': b'\x10\x04\x03',
    'Paper Status': b'\x10\x04\x04',
}

def decode_status(name, byte_val):
    b = byte_val[0]
    messages = []

    if name == 'Printer Status':
        if b & 0x80: messages.append("Printer is busy")
        if b & 0x40: messages.append("FEED button is pressed")
        if b & 0x20: messages.append("An error occurred")
        if b & 0x08: messages.append("Drawer pin 3 is high")
        if not messages: messages.append("Printer status OK")

    elif name == 'Offline Status':
        if b & 0x08: messages.append("Cover is open")
        if b & 0x04: messages.append("Paper is out")
        if b & 0x01: messages.append("Printer is offline")
        if not messages: messages.append("Printer is online and cover closed")

    elif name == 'Error Status':
        if b & 0x40: messages.append("Auto-cutter error")
        if b & 0x08: messages.append("Unrecoverable error")
        if b & 0x04: messages.append("Recoverable error")
        if not messages: messages.append("No printer errors")

    elif name == 'Paper Status':
        paper_bits = b & 0x60
        if paper_bits == 0x00:
            messages.append("Paper adequate")
        elif paper_bits == 0x20:
            messages.append("Paper near end")
        elif paper_bits == 0x60:
            messages.append("Paper end")
        else:
            messages.append("Unknown paper status")

    return messages


def check_printer_status(vendor_id, product_id):
    device = None 
    try:
        # Convert hex strings (if needed)
        if isinstance(vendor_id, str): vendor_id = int(vendor_id, 16)
        if isinstance(product_id, str): product_id = int(product_id, 16)

        device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if not device:
            return {"status": "error", "message": "Printer not found"}
        try:
            if device.is_kernel_driver_active(0):
                device.detach_kernel_driver(0)
        except:
            pass

        device.set_configuration()
        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]

        ep_out = usb.util.find_descriptor(
            intf, custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT
        )
        ep_in = usb.util.find_descriptor(
            intf, custom_match=lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
        )

        if not ep_out or not ep_in:
            return {"status": "error", "message": "Could not find printer endpoints."}

        errors = {}
        for name, cmd in STATUS_COMMANDS.items():
            ep_out.write(cmd)
            response = ep_in.read(ep_in.wMaxPacketSize, timeout=2000)
            decoded = decode_status(name, response)
            for msg in decoded:
                if "OK" not in msg and "adequate" not in msg and "online" not in msg and "No printer errors" not in msg:
                    errors.setdefault(name, []).append(msg)

        if errors:
            flat_errors = "".join(
                f"{k}: {', '.join(v)}\n" for k, v in errors.items()
            )
            return {
                "status": "error",
                "message": flat_errors
            }
        else:
            return {
                "status": "success",
                "message": "Printer is ready"
            }

    except usb.core.USBError as e:
        return {"status": "error", "message": f"USB communication failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            usb.util.dispose_resources(device)
            usb.util.release_interface(device, 0)
        except Exception as e:
            print(e)
