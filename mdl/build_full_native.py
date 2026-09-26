import subprocess
import os

vcvars = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
src_dir = r"mdl\MsNativePipe"

for cpp in ["pipe_server.cpp", "handlers.cpp", "batch.cpp", "geometry.cpp", "MsNativePipe.cpp"]:
    fpath = os.path.join(src_dir, cpp)
    cmd = f'call "{vcvars}" && cl /nologo /c /MD /O2 /EHsc /I"{src_dir}" "{fpath}"'
    res = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
    print(f"--- Compiling {cpp} ---")
    if res.returncode == 0:
        print(f"[OK] {cpp} compiled successfully.")
    else:
        print(f"[ERR] {cpp} failed:")
        print(res.stdout[:500] if res.stdout else "")
        print(res.stderr[:500] if res.stderr else "")
