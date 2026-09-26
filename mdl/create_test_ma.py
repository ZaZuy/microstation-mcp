import os

src_ma = r"C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\MicroStation\mdlapps\runmacro.ma"
dst_ma = r"mdl\MsNativePipe.ma"

with open(src_ma, "rb") as f:
    data = bytearray(f.read())

# Verify target offsets
assert data[0x154:0x154+8] == b"RUNMACRO", f"Unexpected at 0x154: {data[0x154:0x154+8]}"
assert data[0x165:0x165+8] == b"runmacro", f"Unexpected at 0x165: {data[0x165:0x165+8]}"

# Clear old strings with zeros
data[0x154:0x165] = b"\x00" * (0x165 - 0x154)
data[0x165:0x180] = b"\x00" * (0x180 - 0x165)

# Insert new strings
task_id = b"MSNATIVEPIPE\x00"
dll_name = b"MsNativePipe\x00"

data[0x154:0x154+len(task_id)] = task_id
data[0x165:0x165+len(dll_name)] = dll_name

with open(dst_ma, "wb") as f:
    f.write(data)

print(f"Created {dst_ma} ({len(data)} bytes)")
print("0x140..0x180:", bytes(data[0x140:0x180]))
