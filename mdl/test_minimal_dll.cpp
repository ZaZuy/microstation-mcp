#include <windows.h>

extern "C" __declspec(dllexport) int MdlMain(int argc, char *argv[])
{
    OutputDebugStringA("=== MsNativePipe MdlMain CALLED SUCCESSFULLY! ===\n");
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    return TRUE;
}
