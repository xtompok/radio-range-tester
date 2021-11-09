import struct 

def decode_packet(buf):
    if buf[0] != 0x02 or buf[-1] != 0x03:
        raise ValueError("Packet flags incorrect")
    outbuf = []
    esc = False
    for b in buf[1:-1]:
        if b == 0x7D:
            esc = True
            continue
        if esc:
            b = b ^ 0x20
            esc = False
        outbuf.append(b)
    try:
        return struct.unpack('<HLff',bytes(outbuf))
    except struct.error as e:
        print(f"Buffer len: {len(outbuf)}")
        print(f"Buffer: {buf}")
        print(e)
        print(f"Error when decoding buffer {outbuf}")
        return None


def encode_packet(aid, timestamp, lon, lat):
    buf = struct.pack('<HLff',aid, timestamp, lon, lat)
    outbuf = [0x02]
    esc=False
    for b in buf:
        if b < 32:
            outbuf.append(0x7D)
            outbuf.append(b^0x20)
        else:
            outbuf.append(b)
    outbuf.append(0x03)
    return outbuf

def packet_fieldnames():
    return ("id","datetime","lon","lat")
