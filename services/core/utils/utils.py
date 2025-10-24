import socket
import struct

def mac_to_ofctl_hex(mac_address):
    """Converts a MAC address string (AA:BB:...) to 0x<hex> format matching ovs-ofctl output (no leading zero after 0x)."""
    if not isinstance(mac_address, str):
        return None # Or raise TypeError
    try:
        mac_no_colon = mac_address.replace(':', '')
        mac_int = int(mac_no_colon, 16)
        # Use hex() to get standard hex representation (e.g., 0xeb4... not 0x0eb4...)
        return hex(mac_int).lower()
    except ValueError:
        print(f"Warning: Invalid MAC format for conversion: {mac_address}")
        return None

def ipv4_to_ofctl_hex(ip_address):
    """Converts an IPv4 address string (A.B.C.D) to 0x<hex> format for ofctl actions."""
    if not isinstance(ip_address, str):
        return None # Or raise TypeError
    try:
        # Pack the IP address into a 4-byte binary representation (big-endian)
        packed_ip = socket.inet_aton(ip_address)
        # Unpack as an unsigned integer (big-endian) and format as hex
        hex_ip = struct.unpack('!I', packed_ip)[0]
        return hex(hex_ip) # Returns '0x...' format directly
    except OSError: # Handle invalid IP format (e.g., not a valid IPv4 string)
        print(f"Warning: Invalid IP format for conversion: {ip_address}")
        return None # Or raise ValueError 