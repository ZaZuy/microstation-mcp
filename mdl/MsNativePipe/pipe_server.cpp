/*===========================================================================
 * pipe_server.cpp  -  Named Pipe Server implementation
 *
 * Muc dich: Implement pipe server thread su dung Overlapped I/O de ho tro
 *           dung server cleanly khi MDL app unload.
 *
 * Luong hoat dong:
 *   1. PipeServer_Start() -> CreateThread(PipeServerThread)
 *   2. PipeServerThread:
 *        a. CreateNamedPipe (overlapped mode)
 *        b. ConnectNamedPipe (overlapped) + WaitForMultipleObjects
 *        c. ReadFrame: doc [4-byte len][data]
 *        d. Copy vao g_requestMsg, EnterCriticalSection
 *        e. SetEvent(g_hRequestEvent) -> bao MDL timer co request
 *        f. WaitForSingleObject(g_hResponseEvent, timeout)
 *        g. WriteFrame: ghi [4-byte len][data] response
 *        h. DisconnectNamedPipe -> quay lai buoc (b)
 *   3. MDL Timer Callback (main thread):
 *        a. WaitForSingleObject(g_hRequestEvent, 0) == WAIT_OBJECT_0
 *        b. Doc g_requestMsg, goi HandleRequest()
 *        c. Ghi g_responseMsg, SetEvent(g_hResponseEvent)
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/

#include "pipe_server.h"
#include "handlers.h"

#include <cstdio>
#include <cstring>

// -----------------------------------------------------------------------
// Dinh nghia bien toan cuc
// -----------------------------------------------------------------------

HANDLE          g_hRequestEvent  = NULL;
HANDLE          g_hResponseEvent = NULL;
HANDLE          g_hStopEvent     = NULL;
HANDLE          g_hPipeThread    = NULL;
SharedMessage   g_requestMsg;
SharedMessage   g_responseMsg;
CRITICAL_SECTION g_cs;

// -----------------------------------------------------------------------
// Ham tiep nhan noi bo: log loi don gian ra debug output
// -----------------------------------------------------------------------
static void PipeLog(const char* fmt, ...)
{
    char buf[512];
    va_list args;
    va_start(args, fmt);
    _vsnprintf(buf, sizeof(buf) - 1, fmt, args);
    buf[sizeof(buf) - 1] = '\0';
    va_end(args);

    // Ghi ra debug output (xem bang DebugView cua Sysinternals)
    OutputDebugStringA("[MsNativePipe] ");
    OutputDebugStringA(buf);
    OutputDebugStringA("\n");
}

// -----------------------------------------------------------------------
// ReadFrame - doc mot frame tu pipe (4-byte length + data)
//
// Su dung ReadFile blocking tren pipe co overlapped, voi WaitForMultipleObjects
// de kiem tra dong thoi stop event.
//
// @param hPipe       Handle pipe da ket noi
// @param hStopEv     Stop event de thoat vong lap
// @param outBuf      Buffer nhan du lieu
// @param outLen      [out] So byte nhan duoc
// @return            TRUE neu thanh cong, FALSE neu loi hoac dung
// -----------------------------------------------------------------------
static BOOL ReadFrame(HANDLE hPipe, HANDLE hStopEv,
                      char* outBuf, DWORD* outLen)
{
    OVERLAPPED ov;
    ZeroMemory(&ov, sizeof(ov));
    ov.hEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!ov.hEvent) return FALSE;

    BOOL    ok    = FALSE;
    HANDLE  evArr[2] = { ov.hEvent, hStopEv };

    // --- Doc 4 byte length ---
    DWORD   lenRaw = 0;
    DWORD   bytesRead = 0;

    ReadFile(hPipe, &lenRaw, 4, &bytesRead, &ov);
    DWORD waitRes = WaitForMultipleObjects(2, evArr, FALSE, INFINITE);
    if (waitRes != WAIT_OBJECT_0)
    {
        // Stop event hoac loi
        CancelIo(hPipe);
        CloseHandle(ov.hEvent);
        return FALSE;
    }

    if (!GetOverlappedResult(hPipe, &ov, &bytesRead, FALSE) || bytesRead != 4)
    {
        CloseHandle(ov.hEvent);
        return FALSE;
    }

    // Chuyen tu LE sang host byte order (Windows la LE nen khong can swap)
    DWORD dataLen = lenRaw;

    // Kiem tra gioi han
    if (dataLen == 0 || dataLen > PIPE_BUFFER_SIZE - 1)
    {
        PipeLog("ReadFrame: dataLen khong hop le: %lu", dataLen);
        CloseHandle(ov.hEvent);
        return FALSE;
    }

    // --- Doc phan du lieu ---
    ResetEvent(ov.hEvent);
    DWORD totalRead = 0;

    while (totalRead < dataLen)
    {
        DWORD toRead = dataLen - totalRead;
        DWORD got    = 0;

        ReadFile(hPipe, outBuf + totalRead, toRead, &got, &ov);
        waitRes = WaitForMultipleObjects(2, evArr, FALSE, INFINITE);
        if (waitRes != WAIT_OBJECT_0)
        {
            CancelIo(hPipe);
            CloseHandle(ov.hEvent);
            return FALSE;
        }
        if (!GetOverlappedResult(hPipe, &ov, &got, FALSE) || got == 0)
        {
            CloseHandle(ov.hEvent);
            return FALSE;
        }
        totalRead += got;
        ResetEvent(ov.hEvent);
    }

    outBuf[dataLen] = '\0'; // Null-terminate
    *outLen = dataLen;
    ok = TRUE;

    CloseHandle(ov.hEvent);
    return ok;
}

// -----------------------------------------------------------------------
// WriteFrame - ghi mot frame vao pipe (4-byte length + data)
//
// @param hPipe    Handle pipe da ket noi
// @param buf      Du lieu can ghi
// @param len      So byte can ghi
// @return         TRUE neu thanh cong
// -----------------------------------------------------------------------
static BOOL WriteFrame(HANDLE hPipe, const char* buf, DWORD len)
{
    OVERLAPPED ov;
    ZeroMemory(&ov, sizeof(ov));
    ov.hEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!ov.hEvent) return FALSE;

    BOOL  ok = FALSE;
    DWORD written = 0;

    // Ghi 4 byte length truoc (LE)
    DWORD lenLE = len; // Windows la LE
    WriteFile(hPipe, &lenLE, 4, &written, &ov);
    WaitForSingleObject(ov.hEvent, 10000);
    if (!GetOverlappedResult(hPipe, &ov, &written, FALSE) || written != 4)
    {
        CloseHandle(ov.hEvent);
        return FALSE;
    }

    // Ghi phan du lieu
    ResetEvent(ov.hEvent);
    DWORD totalWritten = 0;

    while (totalWritten < len)
    {
        DWORD toWrite = len - totalWritten;
        DWORD w       = 0;

        WriteFile(hPipe, buf + totalWritten, toWrite, &w, &ov);
        WaitForSingleObject(ov.hEvent, 10000);
        if (!GetOverlappedResult(hPipe, &ov, &w, FALSE) || w == 0)
        {
            CloseHandle(ov.hEvent);
            return FALSE;
        }
        totalWritten += w;
        ResetEvent(ov.hEvent);
    }

    ok = TRUE;
    CloseHandle(ov.hEvent);
    return ok;
}

// -----------------------------------------------------------------------
// PipeServerThread - ham thread chinh cua pipe server
//
// Chay trong background thread, lap lai vong: tao pipe -> ket noi ->
// doc request -> doi MDL xu ly -> ghi response -> disconnect.
// -----------------------------------------------------------------------
DWORD WINAPI PipeServerThread(LPVOID /*lpParam*/)
{
    PipeLog("PipeServerThread bat dau.");

    while (true)
    {
        // Kiem tra stop event truoc khi tao pipe moi
        if (WaitForSingleObject(g_hStopEvent, 0) == WAIT_OBJECT_0)
        {
            PipeLog("PipeServerThread: nhan duoc stop event, thoat.");
            break;
        }

        // --- Tao named pipe ---
        HANDLE hPipe = CreateNamedPipeA(
            PIPE_NAME,
            PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED, // Overlapped I/O
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            PIPE_MAX_INSTANCES,
            PIPE_BUFFER_SIZE,   // Output buffer
            PIPE_BUFFER_SIZE,   // Input buffer
            0,                  // Default timeout
            NULL                // Default security
        );

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            DWORD err = GetLastError();
            PipeLog("CreateNamedPipe that bai, loi: %lu. Thu lai sau 1 giay.", err);
            // Doi 1 giay truoc khi thu lai, kiem tra stop event
            if (WaitForSingleObject(g_hStopEvent, 1000) == WAIT_OBJECT_0)
                break;
            continue;
        }

        PipeLog("Pipe tao thanh cong, cho ket noi client...");

        // --- ConnectNamedPipe (overlapped) ---
        OVERLAPPED ovConnect;
        ZeroMemory(&ovConnect, sizeof(ovConnect));
        ovConnect.hEvent = CreateEvent(NULL, TRUE, FALSE, NULL);

        BOOL connected = ConnectNamedPipe(hPipe, &ovConnect);
        DWORD connectErr = GetLastError();

        if (!connected)
        {
            if (connectErr == ERROR_IO_PENDING)
            {
                // Doi client ket noi hoac stop event
                HANDLE evArr[2] = { ovConnect.hEvent, g_hStopEvent };
                DWORD waitRes = WaitForMultipleObjects(2, evArr, FALSE, INFINITE);

                if (waitRes != WAIT_OBJECT_0)
                {
                    // Stop hoac loi
                    PipeLog("ConnectNamedPipe: stop event hoac loi, thoat vong lap.");
                    CancelIo(hPipe);
                    CloseHandle(ovConnect.hEvent);
                    CloseHandle(hPipe);
                    break;
                }

                DWORD dummy;
                if (!GetOverlappedResult(hPipe, &ovConnect, &dummy, FALSE))
                {
                    PipeLog("GetOverlappedResult ConnectNamedPipe that bai: %lu",
                            GetLastError());
                    CloseHandle(ovConnect.hEvent);
                    CloseHandle(hPipe);
                    continue;
                }
            }
            else if (connectErr == ERROR_PIPE_CONNECTED)
            {
                // Client da ket noi truoc khi goi ConnectNamedPipe
            }
            else
            {
                PipeLog("ConnectNamedPipe loi: %lu", connectErr);
                CloseHandle(ovConnect.hEvent);
                CloseHandle(hPipe);
                continue;
            }
        }

        CloseHandle(ovConnect.hEvent);
        PipeLog("Client da ket noi.");

        // --- Vong lap xu ly request/response tren ket noi nay ---
        while (true)
        {
            // Kiem tra stop truoc khi doc
            if (WaitForSingleObject(g_hStopEvent, 0) == WAIT_OBJECT_0)
            {
                PipeLog("Stop event trong vong lap xu ly.");
                goto done;
            }

            // Doc frame request
            char  reqBuf[PIPE_BUFFER_SIZE];
            DWORD reqLen = 0;

            if (!ReadFrame(hPipe, g_hStopEvent, reqBuf, &reqLen))
            {
                PipeLog("ReadFrame that bai (client ngat ket noi hoac stop).");
                break; // Ngat ket noi, quay lai vong lap tao pipe moi
            }

            PipeLog("Nhan request: %lu bytes.", reqLen);

            // --- Push vao shared buffer va bao MDL thread ---
            EnterCriticalSection(&g_cs);
            memcpy(g_requestMsg.data, reqBuf, reqLen);
            g_requestMsg.data[reqLen] = '\0';
            g_requestMsg.length       = reqLen;
            LeaveCriticalSection(&g_cs);

            // Reset response event truoc khi signal request
            ResetEvent(g_hResponseEvent);
            SetEvent(g_hRequestEvent);

            // Doi MDL timer xu ly va ghi response
            DWORD waitRes = WaitForSingleObject(g_hResponseEvent,
                                                PIPE_RESPONSE_TIMEOUT_MS);

            if (waitRes != WAIT_OBJECT_0)
            {
                // Timeout hoac loi
                PipeLog("Timeout cho response tu MDL thread (%d ms).",
                        PIPE_RESPONSE_TIMEOUT_MS);
                // Ghi response loi
                const char* errResp = "{\"id\":0,\"success\":false,\"data\":null,"
                                      "\"message\":\"MDL thread timeout\"}";
                DWORD errLen = (DWORD)strlen(errResp);
                WriteFrame(hPipe, errResp, errLen);
                break;
            }

            // Doc response da duoc ghi boi MDL thread
            EnterCriticalSection(&g_cs);
            char  resBuf[PIPE_BUFFER_SIZE];
            DWORD resLen = g_responseMsg.length;
            memcpy(resBuf, g_responseMsg.data, resLen);
            LeaveCriticalSection(&g_cs);

            PipeLog("Gui response: %lu bytes.", resLen);

            // Ghi response ve client
            if (!WriteFrame(hPipe, resBuf, resLen))
            {
                PipeLog("WriteFrame that bai.");
                break;
            }
        }

        // Ngat ket noi voi client hien tai
        FlushFileBuffers(hPipe);
        DisconnectNamedPipe(hPipe);
        CloseHandle(hPipe);
        PipeLog("Client ngat ket noi, cho ket noi moi...");
    }

done:
    PipeLog("PipeServerThread ket thuc.");
    return 0;
}

// -----------------------------------------------------------------------
// PipeServer_Start - khoi dong pipe server thread
// -----------------------------------------------------------------------
void PipeServer_Start()
{
    // Khoi tao Critical Section
    InitializeCriticalSection(&g_cs);
    ZeroMemory(&g_requestMsg,  sizeof(g_requestMsg));
    ZeroMemory(&g_responseMsg, sizeof(g_responseMsg));

    // Tao cac synchronization events
    // g_hRequestEvent: manual-reset, initially not signaled
    g_hRequestEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!g_hRequestEvent)
    {
        PipeLog("PipeServer_Start: khong tao duoc g_hRequestEvent, loi: %lu",
                GetLastError());
        return;
    }

    // g_hResponseEvent: manual-reset, initially not signaled
    g_hResponseEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!g_hResponseEvent)
    {
        PipeLog("PipeServer_Start: khong tao duoc g_hResponseEvent, loi: %lu",
                GetLastError());
        CloseHandle(g_hRequestEvent);
        g_hRequestEvent = NULL;
        return;
    }

    // g_hStopEvent: manual-reset, initially not signaled
    g_hStopEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!g_hStopEvent)
    {
        PipeLog("PipeServer_Start: khong tao duoc g_hStopEvent, loi: %lu",
                GetLastError());
        CloseHandle(g_hRequestEvent);
        CloseHandle(g_hResponseEvent);
        g_hRequestEvent = g_hResponseEvent = NULL;
        return;
    }

    // Tao thread
    DWORD threadId = 0;
    g_hPipeThread = CreateThread(
        NULL,               // Default security
        0,                  // Default stack size
        PipeServerThread,   // Ham thread
        NULL,               // Tham so (khong dung)
        0,                  // Bat dau ngay
        &threadId
    );

    if (!g_hPipeThread)
    {
        PipeLog("PipeServer_Start: khong tao duoc thread, loi: %lu",
                GetLastError());
        CloseHandle(g_hRequestEvent);
        CloseHandle(g_hResponseEvent);
        CloseHandle(g_hStopEvent);
        g_hRequestEvent = g_hResponseEvent = g_hStopEvent = NULL;
        return;
    }

    PipeLog("PipeServer_Start: thread tao thanh cong, ID=%lu.", threadId);
}

// -----------------------------------------------------------------------
// PipeServer_Stop - dung pipe server thread an toan
// -----------------------------------------------------------------------
void PipeServer_Stop()
{
    PipeLog("PipeServer_Stop: dang dung...");

    if (g_hStopEvent)
        SetEvent(g_hStopEvent);

    // Mo ket noi gia de thread thoat khoi WaitForMultipleObjects
    // (trong truong hop thread dang cho ConnectNamedPipe)
    HANDLE hDummy = CreateFileA(
        PIPE_NAME,
        GENERIC_READ | GENERIC_WRITE,
        0, NULL,
        OPEN_EXISTING,
        0, NULL
    );
    if (hDummy != INVALID_HANDLE_VALUE)
        CloseHandle(hDummy);

    // Cho thread ket thuc (toi da 5 giay)
    if (g_hPipeThread)
    {
        DWORD waitRes = WaitForSingleObject(g_hPipeThread, 5000);
        if (waitRes == WAIT_TIMEOUT)
        {
            PipeLog("PipeServer_Stop: thread khong ket thuc sau 5s, force terminate.");
            TerminateThread(g_hPipeThread, 1);
        }
        CloseHandle(g_hPipeThread);
        g_hPipeThread = NULL;
    }

    // Giai phong resources
    if (g_hRequestEvent)  { CloseHandle(g_hRequestEvent);  g_hRequestEvent  = NULL; }
    if (g_hResponseEvent) { CloseHandle(g_hResponseEvent); g_hResponseEvent = NULL; }
    if (g_hStopEvent)     { CloseHandle(g_hStopEvent);     g_hStopEvent     = NULL; }

    DeleteCriticalSection(&g_cs);
    PipeLog("PipeServer_Stop: hoan tat.");
}

// -----------------------------------------------------------------------
// PipeServer_ProcessPending - xu ly pending request tu MDL main thread
//
// Duoc goi tu MDL timer callback moi 50ms.
// -----------------------------------------------------------------------
void PipeServer_ProcessPending()
{
    // Kiem tra co request pending khong (non-blocking)
    if (!g_hRequestEvent) return;

    DWORD waitRes = WaitForSingleObject(g_hRequestEvent, 0);
    if (waitRes != WAIT_OBJECT_0) return; // Khong co request

    // Reset event ngay lap tuc
    ResetEvent(g_hRequestEvent);

    // Doc request tu shared buffer
    EnterCriticalSection(&g_cs);
    std::string requestStr(g_requestMsg.data, g_requestMsg.length);
    LeaveCriticalSection(&g_cs);

    // Goi handler (MDL API duoc phep goi tu day vi dang o main thread)
    std::string responseStr;
    try
    {
        responseStr = HandleRequest(requestStr);
    }
    catch (const std::exception& ex)
    {
        // Bat loi va tao error response
        responseStr  = "{\"id\":0,\"success\":false,\"data\":null,\"message\":";
        responseStr += "\"Exception: ";
        responseStr += ex.what();
        responseStr += "\"}";
    }
    catch (...)
    {
        responseStr = "{\"id\":0,\"success\":false,\"data\":null,"
                      "\"message\":\"Unknown exception trong HandleRequest\"}";
    }

    // Ghi response vao shared buffer
    EnterCriticalSection(&g_cs);
    DWORD resLen = (DWORD)responseStr.size();
    if (resLen > PIPE_BUFFER_SIZE - 1)
        resLen = PIPE_BUFFER_SIZE - 1;
    memcpy(g_responseMsg.data, responseStr.c_str(), resLen);
    g_responseMsg.data[resLen] = '\0';
    g_responseMsg.length       = resLen;
    LeaveCriticalSection(&g_cs);

    // Bao pipe thread response da san sang
    SetEvent(g_hResponseEvent);
}
