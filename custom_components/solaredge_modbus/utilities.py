def pack_bitstring(bits):
    """bits: iterable of 0/1 or False/True; returns bytes (LSB first in each byte)."""
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit_index, bit in enumerate(bits[i:i+8]):
            if bit:
                byte |= 1 << bit_index
        out.append(byte)
    return bytes(out)

def unpack_bitstring(data, count=None):
    """Inverse of pack_bitstring."""
    bits = []
    for byte in data:
        for i in range(8):
            bits.append(bool(byte & (1 << i)))
    return bits if count is None else bits[:count]
