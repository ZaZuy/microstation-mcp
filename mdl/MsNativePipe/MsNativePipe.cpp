/*===========================================================================
 * MsNativePipe.cpp  -  MDL Application Entry Point
 *
 * Muc dich: Entry point cua MDL application MsNativePipe.
 *           Khoi dong named pipe server va dang ky MDL timer callback
 *           de xu ly request tu MDL main thread.
 *
 * Luong hoat dong:
 *   1. MdlMain() duoc goi khi MDL app load
 *   2. PipeServer_Start() -> tao pipe server thread
 *   3. mdlSystem_startTimer() -> dang ky callback 50ms
 *   4. TimerCallback() -> PipeServer_ProcessPending() moi 50ms
 *   5. Khi MDL unload -> PipeServer_Stop()
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/

// MDL SDK headers - thu tu include quan trong
#include <mdl.h>
#include <mselems.h>
#include <msmodel.h>
#include <tcb.h>
#include <mssettng.h>

// C++ standard headers
#include <cstdio>
#include <cstring>
#include <string>

// Project headers
#include "pipe_server.h"
#include "handlers.h"

// -----------------------------------------------------------------------
// Hang so
// -----------------------------------------------------------------------

/// Ten hien thi cua MDL application trong MicroStation
#define APP_NAME    "MsNativePipe"
#define APP_VERSION "1.0.0"

// -----------------------------------------------------------------------
// Bien toan cuc noi bo
// -----------------------------------------------------------------------

/// Task ID cua timer
static int g_timerTaskId = 0;

/// Flag kiem tra da khoi dong chua
static bool g_initialized = false;

// -----------------------------------------------------------------------
// Ham log tien ich noi bo
// -----------------------------------------------------------------------
static void AppLog(const char* fmt, ...)
{
    char buf[512];
    va_list args;
    va_start(args, fmt);
    _vsnprintf(buf, sizeof(buf) - 1, fmt, args);
    buf[sizeof(buf) - 1] = '\0';
    va_end(args);

    OutputDebugStringA("[MsNativePipe] ");
    OutputDebugStringA(buf);
    OutputDebugStringA("\n");

    // Hien thi trong MicroStation message center
    mdlOutput_message(buf);
}

// -----------------------------------------------------------------------
// TimerCallback - MDL timer callback (main thread, moi 50ms)
//
// Ham nay duoc goi dinh ky tu MDL main thread. An toan de goi MDL API.
// -----------------------------------------------------------------------
static void TimerCallback(long taskId)
{
    (void)taskId; // Khong su dung

    // Kiem tra va xu ly pending request tu pipe thread
    PipeServer_ProcessPending();
}

// -----------------------------------------------------------------------
// AppCleanup - don dep khi MDL app unload
// -----------------------------------------------------------------------
static void AppCleanup()
{
    AppLog("MsNativePipe dang dung...");

    // Huy dang ky timer
    if (g_timerTaskId != 0)
    {
        mdlSystem_stopTimer(g_timerTaskId);
        g_timerTaskId = 0;
    }

    // Dung pipe server thread
    if (g_initialized)
    {
        PipeServer_Stop();
        g_initialized = false;
    }

    AppLog("MsNativePipe da dung thanh cong.");
}

// -----------------------------------------------------------------------
// MdlMain - Entry point cua MDL application
//
// Duoc goi tu MicroStation khi MDL app duoc load.
// Tuong duong ham main() trong ANSI C.
//
// @param argc  So tham so dong lenh
// @param argv  Mang tham so dong lenh
// -----------------------------------------------------------------------
extern "C" void MdlMain(int argc, char* argv[])
{
    AppLog("=================================================");
    AppLog("MsNativePipe v%s dang khoi dong...", APP_VERSION);
    AppLog("Pipe name: %s", PIPE_NAME);
    AppLog("Timer interval: %d ms", PIPE_TIMER_INTERVAL);
    AppLog("=================================================");

    // Kiem tra tham so dong lenh (hien tai khong dung)
    if (argc > 1)
    {
        AppLog("Tham so dong lenh: %s", argv[1]);
    }

    // --- Khoi dong Pipe Server Thread ---
    PipeServer_Start();
    if (!g_hPipeThread)
    {
        AppLog("LOI: Khong khoi dong duoc pipe server thread!");
        mdlOutput_error("MsNativePipe: Khong khoi dong duoc pipe server!");
        return;
    }
    g_initialized = true;
    AppLog("Pipe server thread da khoi dong.");

    // --- Dang ky MDL timer (main thread callback) ---
    // mdlSystem_startTimer(interval_ms, callback_func, param)
    // Tra ve task ID, 0 neu that bai
    g_timerTaskId = mdlSystem_startTimer(
        PIPE_TIMER_INTERVAL,    // Chu ky (ms)
        TimerCallback,          // Ham callback
        0                       // Tham so (khong dung)
    );

    if (g_timerTaskId == 0)
    {
        AppLog("LOI: Khong dang ky duoc MDL timer!");
        // Van chay nhung se khong xu ly request tu timer
        // Thu dang ky lai mot lan nua
        g_timerTaskId = mdlSystem_startTimer(
            PIPE_TIMER_INTERVAL, TimerCallback, 0);

        if (g_timerTaskId == 0)
        {
            AppLog("LOI: Thu lai van that bai. MsNativePipe co the khong hoat dong.");
        }
    }
    else
    {
        AppLog("MDL timer da dang ky (task ID=%d, interval=%d ms).",
               g_timerTaskId, PIPE_TIMER_INTERVAL);
    }

    // --- Dang ky ham cleanup khi MDL unload ---
    mdlSystem_registerUndoHook(NULL, NULL); // Khong dung undo hook

    // Dang ky ham cleanup
    mdlSystem_addExitHandler(AppCleanup);

    // --- Thong bao hoan thanh khoi dong ---
    AppLog("MsNativePipe da san sang. Dang lang nghe tren: %s", PIPE_NAME);
    mdlOutput_message("MsNativePipe: San sang nhan lenh qua named pipe.");
}
