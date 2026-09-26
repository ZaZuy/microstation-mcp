/*===========================================================================
 * pipe_server.h  -  Named Pipe Server cho MicroStation MDL
 *
 * Muc dich: Khai bao cac ham quan ly pipe server, cac bien chia se giua
 *           pipe thread va MDL main thread.
 *
 * Kien truc luong:
 *   - Pipe Thread (background): ConnectNamedPipe -> doc request -> SetEvent
 *                               -> WaitForSingleObject(response) -> ghi response
 *   - MDL Timer  (main thread): WaitForSingleObject(request, 0) ->
 *                               xu ly -> SetEvent(response)
 *
 * Wire format: [4-byte uint32 LE length][JSON UTF-8 bytes]
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/
#pragma once

#include <windows.h>
#include <string>

// -----------------------------------------------------------------------
// Hang so cau hinh
// -----------------------------------------------------------------------

/// Kich thuoc buffer toi da cho moi message (512 KB)
#define PIPE_BUFFER_SIZE        (512 * 1024)

/// Ten pipe Windows
#define PIPE_NAME               "\\\\.\\pipe\\MsNativeMCP"

/// Chu ky MDL timer (ms)
#define PIPE_TIMER_INTERVAL     50

/// Timeout cho response tu MDL main thread (ms)
#define PIPE_RESPONSE_TIMEOUT_MS  30000

/// So instance pipe toi da dong thoi
#define PIPE_MAX_INSTANCES      1

// -----------------------------------------------------------------------
// SharedMessage - buffer chia se giua Pipe Thread va MDL Main Thread
// -----------------------------------------------------------------------

/**
 * Buffer chia se giua Pipe Thread va MDL Main Thread.
 * Pipe Thread ghi request vao, MDL Thread doc va ghi response.
 * Bao ve boi g_cs (CRITICAL_SECTION).
 */
struct SharedMessage
{
    char  data[PIPE_BUFFER_SIZE]; ///< Du lieu JSON (UTF-8)
    DWORD length;                 ///< So byte thuc te trong data
};

// -----------------------------------------------------------------------
// Bien toan cuc chia se
// -----------------------------------------------------------------------

/// Event bao hieu co request moi tu pipe thread -> MDL thread
extern HANDLE        g_hRequestEvent;

/// Event bao hieu response san sang tu MDL thread -> pipe thread
extern HANDLE        g_hResponseEvent;

/// Event bao hieu yeu cau dung pipe server
extern HANDLE        g_hStopEvent;

/// Buffer request tu client
extern SharedMessage g_requestMsg;

/// Buffer response gui ve client
extern SharedMessage g_responseMsg;

/// Critical section bao ve truy cap vao shared buffers
extern CRITICAL_SECTION g_cs;

/// Handle cua pipe server thread
extern HANDLE        g_hPipeThread;

// -----------------------------------------------------------------------
// Ham public
// -----------------------------------------------------------------------

/**
 * Khoi dong pipe server thread.
 * Tao synchronization objects va bat dau PipeServerThread.
 * Goi tu MdlMain() khi MDL application load.
 */
void PipeServer_Start();

/**
 * Dung pipe server thread mot cach an toan.
 * SetEvent(g_hStopEvent) roi WaitForSingleObject(thread, 5000ms).
 * Goi khi MDL application unload.
 */
void PipeServer_Stop();

/**
 * Kiem tra va xu ly pending request tu pipe thread.
 * Duoc goi tu MDL timer callback (main thread) moi 50ms.
 * Neu co request pending:
 *   1. Doc g_requestMsg
 *   2. Goi HandleRequest() de xu ly
 *   3. Ghi ket qua vao g_responseMsg
 *   4. SetEvent(g_hResponseEvent)
 */
void PipeServer_ProcessPending();

/**
 * Ham thread cua pipe server (DWORD WINAPI).
 * Vong lap: CreateNamedPipe -> ConnectNamedPipe -> Read/Write -> Disconnect.
 *
 * @param lpParam  Khong su dung (NULL)
 * @return         0 khi ket thuc binh thuong
 */
DWORD WINAPI PipeServerThread(LPVOID lpParam);
