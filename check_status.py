import socket

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
