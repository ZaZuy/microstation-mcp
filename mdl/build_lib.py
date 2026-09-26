import subprocess
import os

vcvars = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
cmd = f'"{vcvars}" && lib /def:mdl\\lib\\ustation.def /machine:x86 /out:mdl\\lib\\ustation.lib'
res = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
print("STDOUT:", res.stdout[-300:] if res.stdout else "")
print("STDERR:", res.stderr[-300:] if res.stderr else "")
print("Exit code:", res.returncode)
print("ustation.lib exists:", os.path.exists("mdl/lib/ustation.lib"))
