import subprocess
import os

vcvars = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
cmd = f'call "{vcvars}" && cl /nologo /LD /MD /O2 /Fe:mdl\\MsNativePipe.dll mdl\\test_minimal_dll.cpp'
res = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
print("Exit code:", res.returncode)
print("MsNativePipe.dll exists:", os.path.exists("mdl/MsNativePipe.dll"))
