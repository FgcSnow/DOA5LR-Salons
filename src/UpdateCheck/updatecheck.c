/*  DOA5LR-UpdateCheck 1.1  (21/09/2026) — part of the DOA5LR-Salons community pack
 *
 *  What it does, and nothing else:
 *    1. a few seconds after the game starts, it downloads ONE public text file (version.txt on GitHub) with
 *       a plain HTTPS GET — no cookie, no id, no data about you or your game is sent;
 *    2. it compares the "version=" line with DOA5LR-Salons-VERSION.txt in the game folder;
 *    3. if a newer pack exists, when you CLOSE the game it starts DOA5LR-Salons-Installer.exe --update,
 *       which asks "Update now / Later". Nothing is installed without your click.
 *  1.1: when a newer pack exists it also shows a small banner on screen for a few seconds (layered window,
 *       no D3D hook: visible in borderless / window mode, invisible in exclusive fullscreen).
 *  It writes no file (no log), opens no socket besides that single GET, and changes nothing in the game.
 *
 *  scripts\DOA5LR-UpdateCheck.ini :  Enabled=1  UpdatePrompt=1  DelaySeconds=20  Banner=1  BannerSeconds=8  VersionUrl=<https url>
 *  If DOA5LR-Telemetry.asi (testers build) is loaded, this plugin stays idle: the telemetry plugin does the same check.
 *
 *  Build (llvm-mingw) : build.cmd   ->  i686-w64-mingw32-gcc -O2 -s -shared -static -o DOA5LR-UpdateCheck.asi updatecheck.c version.res -lwinhttp -lgdi32
 */
#include <windows.h>
#include <winhttp.h>
#include <stdio.h>
#include <string.h>

#define UVER "1.1"
#ifndef DEFAULT_VERSION_URL
#define DEFAULT_VERSION_URL "https://raw.githubusercontent.com/FgcSnow/DOA5LR-Salons/main/version.txt"
#endif

static char g_dir[MAX_PATH], g_game[MAX_PATH], g_url[512], g_installed[24], g_latest[24];
static int g_enabled = 1, g_prompt = 1, g_delay = 20, g_outdated = 0, g_banner = 1, g_bannerSec = 8;
static volatile LONG g_launched = 0;
typedef void (WINAPI *ExitProcess_t)(UINT);
static ExitProcess_t o_ExitProcess;

static const char *pack_path(char *buf, size_t cap, const char *name)   /* next to the plugin if present, else game root */
{
    snprintf(buf, cap, "%s%s", g_dir, name); if (GetFileAttributesA(buf) != INVALID_FILE_ATTRIBUTES) return buf;
    snprintf(buf, cap, "%s%s", g_game, name); return buf;
}
static int version_cmp(const char *a, const char *b)
{
    int x[4] = { 0 }, y[4] = { 0 }; sscanf(a, "%d.%d.%d.%d", &x[0], &x[1], &x[2], &x[3]); sscanf(b, "%d.%d.%d.%d", &y[0], &y[1], &y[2], &y[3]);
    for (int i = 0; i < 4; i++) if (x[i] != y[i]) return x[i] < y[i] ? -1 : 1;
    return 0;
}
static int read_installed(void)
{
    char path[MAX_PATH]; pack_path(path, sizeof path, "DOA5LR-Salons-VERSION.txt");
    HANDLE h = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    char buf[64] = ""; DWORD n = 0; ReadFile(h, buf, sizeof buf - 1, &n, NULL); CloseHandle(h); buf[n] = 0;
    return sscanf(buf, "%23s", g_installed) == 1 && g_installed[0] >= '0' && g_installed[0] <= '9';
}
/* single HTTPS GET of a small text file; returns HTTP status (200 = ok) */
static int http_get_text(const char *url, char *out, size_t cap)
{
    WCHAR wurl[1024]; MultiByteToWideChar(CP_UTF8, 0, url, -1, wurl, 1024);
    URL_COMPONENTS uc; memset(&uc, 0, sizeof uc); uc.dwStructSize = sizeof uc;
    WCHAR host[256], path[1024]; uc.lpszHostName = host; uc.dwHostNameLength = 256; uc.lpszUrlPath = path; uc.dwUrlPathLength = 1024;
    if (!WinHttpCrackUrl(wurl, 0, 0, &uc) || uc.nScheme != INTERNET_SCHEME_HTTPS) return -1;
    HINTERNET s = WinHttpOpen(L"DOA5LR-UpdateCheck/" UVER, WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0); if (!s) return -2;
    WinHttpSetTimeouts(s, 5000, 5000, 5000, 5000);
    int status = -3; size_t n = 0;
    HINTERNET c = WinHttpConnect(s, host, uc.nPort, 0);
    if (c) {
        HINTERNET r = WinHttpOpenRequest(c, L"GET", path, NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
        if (r) {
            if (WinHttpSendRequest(r, WINHTTP_NO_ADDITIONAL_HEADERS, 0, NULL, 0, 0, 0) && WinHttpReceiveResponse(r, NULL)) {
                DWORD st = 0, sz = sizeof st; WinHttpQueryHeaders(r, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX, &st, &sz, WINHTTP_NO_HEADER_INDEX); status = (int)st;
                DWORD got = 0;
                while (n + 1 < cap && WinHttpReadData(r, out + n, (DWORD)(cap - 1 - n), &got) && got > 0) n += got;
            }
            WinHttpCloseHandle(r);
        }
        WinHttpCloseHandle(c);
    }
    WinHttpCloseHandle(s);
    out[n] = 0;
    return status;
}
static void launch_installer(void)
{
    if (!g_outdated || !g_prompt || InterlockedExchange(&g_launched, 1)) return;
    char exe[MAX_PATH]; pack_path(exe, sizeof exe, "DOA5LR-Salons-Installer.exe");
    if (GetFileAttributesA(exe) == INVALID_FILE_ATTRIBUTES) return;
    char cmd[MAX_PATH + 16]; snprintf(cmd, sizeof cmd, "\"%s\" --update", exe);
    STARTUPINFOA si = { sizeof si }; PROCESS_INFORMATION pi;
    if (CreateProcessA(exe, cmd, NULL, NULL, FALSE, DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, NULL, g_game, &si, &pi)) { CloseHandle(pi.hThread); CloseHandle(pi.hProcess); }
}
/* Banner (1.1): a layered, non-activating, click-through window on top of the game for a few seconds. */
static WCHAR g_bannerText[160];
static LRESULT CALLBACK banner_proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(w, &ps); RECT r; GetClientRect(w, &r);
        HBRUSH bg = CreateSolidBrush(RGB(20, 24, 34)); FillRect(dc, &r, bg); DeleteObject(bg);
        HBRUSH acc = CreateSolidBrush(RGB(226, 55, 68)); RECT bar = r; bar.right = bar.left + 6; FillRect(dc, &bar, acc); DeleteObject(acc);
        HFONT f = CreateFontW(-24, 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
        HGDIOBJ of = SelectObject(dc, f); SetBkMode(dc, TRANSPARENT); SetTextColor(dc, RGB(240, 244, 250));
        RECT t = r; t.left += 22; t.right -= 12; DrawTextW(dc, g_bannerText, -1, &t, DT_SINGLELINE | DT_VCENTER | DT_LEFT | DT_END_ELLIPSIS);
        SelectObject(dc, of); DeleteObject(f); EndPaint(w, &ps); return 0;
    }
    if (m == WM_TIMER) { DestroyWindow(w); return 0; }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProcW(w, m, wp, lp);
}
static BOOL CALLBACK find_game_window(HWND h, LPARAM out)
{
    DWORD pid = 0; GetWindowThreadProcessId(h, &pid);
    if (pid == GetCurrentProcessId() && IsWindowVisible(h) && !GetWindow(h, GW_OWNER)) { *(HWND *)out = h; return FALSE; }
    return TRUE;
}
static DWORD WINAPI banner_thread(LPVOID unused)
{
    (void)unused;
    HINSTANCE hi = GetModuleHandleW(NULL);
    WNDCLASSW wc = { 0 }; wc.lpfnWndProc = banner_proc; wc.hInstance = hi; wc.lpszClassName = L"DOA5LR_UpdateCheck_Banner"; wc.hCursor = LoadCursor(NULL, IDC_ARROW); RegisterClassW(&wc);
    HWND game = NULL; EnumWindows(find_game_window, (LPARAM)&game);
    HMONITOR mon = MonitorFromWindow(game ? game : GetForegroundWindow(), MONITOR_DEFAULTTOPRIMARY);
    MONITORINFO mi = { sizeof mi }; GetMonitorInfoW(mon, &mi);
    int w = 980, h = 60; if (w > mi.rcMonitor.right - mi.rcMonitor.left - 40) w = mi.rcMonitor.right - mi.rcMonitor.left - 40;
    int x = mi.rcMonitor.left + (mi.rcMonitor.right - mi.rcMonitor.left - w) / 2, y = mi.rcMonitor.top + 40;
    HWND t = CreateWindowExW(WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
                             L"DOA5LR_UpdateCheck_Banner", L"", WS_POPUP, x, y, w, h, NULL, NULL, hi, NULL);
    if (!t) return 0;
    SetLayeredWindowAttributes(t, 0, 235, LWA_ALPHA);
    ShowWindow(t, SW_SHOWNOACTIVATE); UpdateWindow(t); SetTimer(t, 1, (UINT)g_bannerSec * 1000, NULL);
    MSG msg; while (GetMessageW(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    return 0;
}
static void show_banner(void)
{
    if (!g_banner) return;
    WCHAR latest[24]; MultiByteToWideChar(CP_ACP, 0, g_latest, -1, latest, 24);
    wsprintfW(g_bannerText, L"DOA5LR-Salons %s is available — the installer opens when you close the game", latest);
    HANDLE th = CreateThread(NULL, 0, banner_thread, NULL, 0, NULL); if (th) CloseHandle(th);
}

static void WINAPI hk_ExitProcess(UINT code) { launch_installer(); o_ExitProcess(code); }

static void **iat_find(HMODULE mod, const char *dll, const char *func)
{
    BYTE *b = (BYTE *)mod; IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)b; if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(b + dos->e_lfanew); if (nt->Signature != IMAGE_NT_SIGNATURE) return NULL;
    IMAGE_DATA_DIRECTORY d = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT]; if (!d.VirtualAddress) return NULL;
    IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(b + d.VirtualAddress);
    for (; imp->Name; imp++) {
        if (_stricmp((char *)(b + imp->Name), dll) || !imp->OriginalFirstThunk) continue;
        IMAGE_THUNK_DATA *orig = (IMAGE_THUNK_DATA *)(b + imp->OriginalFirstThunk), *th = (IMAGE_THUNK_DATA *)(b + imp->FirstThunk);
        for (; orig->u1.AddressOfData; orig++, th++) {
            if (orig->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            IMAGE_IMPORT_BY_NAME *nm = (IMAGE_IMPORT_BY_NAME *)(b + orig->u1.AddressOfData);
            if (!strcmp((char *)nm->Name, func)) return (void **)&th->u1.Function;
        }
    }
    return NULL;
}
static void hook_exit(void)      /* only when an update exists: the game's ExitProcess import -> hk_ExitProcess */
{
    void **slot = iat_find(GetModuleHandleA(NULL), "KERNEL32.dll", "ExitProcess");
    if (!slot) return;
    DWORD old; if (VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old)) { o_ExitProcess = (ExitProcess_t)*slot; *slot = (void *)hk_ExitProcess; VirtualProtect(slot, sizeof(void *), old, &old); }
}

static DWORD WINAPI worker(LPVOID unused)
{
    (void)unused;
    char ini[MAX_PATH]; snprintf(ini, sizeof ini, "%sDOA5LR-UpdateCheck.ini", g_dir);
    g_enabled = GetPrivateProfileIntA("UpdateCheck", "Enabled", 1, ini);
    g_prompt = GetPrivateProfileIntA("UpdateCheck", "UpdatePrompt", 1, ini);
    g_banner = GetPrivateProfileIntA("UpdateCheck", "Banner", 1, ini);
    g_bannerSec = GetPrivateProfileIntA("UpdateCheck", "BannerSeconds", 8, ini); if (g_bannerSec < 2) g_bannerSec = 2; if (g_bannerSec > 60) g_bannerSec = 60;
    g_delay = GetPrivateProfileIntA("UpdateCheck", "DelaySeconds", 20, ini); if (g_delay < 3) g_delay = 3; if (g_delay > 600) g_delay = 600;
    GetPrivateProfileStringA("UpdateCheck", "VersionUrl", DEFAULT_VERSION_URL, g_url, sizeof g_url, ini);
    if (!g_enabled || strncmp(g_url, "https://", 8)) return 0;
    Sleep((DWORD)g_delay * 1000);
    if (GetModuleHandleA("DOA5LR-Telemetry.asi")) return 0;          /* testers build: the telemetry plugin does this check */
    if (!read_installed()) return 0;
    static char body[16384]; if (http_get_text(g_url, body, sizeof body) != 200) return 0;
    for (char *ln = body; ln && *ln; ) {
        char *e = strpbrk(ln, "\r\n"); if (e) *e++ = 0;
        if (!strncmp(ln, "version=", 8)) { sscanf(ln + 8, "%23s", g_latest); break; }
        ln = e; while (ln && (*ln == '\r' || *ln == '\n')) ln++;
    }
    if (!g_latest[0]) return 0;
    g_outdated = version_cmp(g_installed, g_latest) < 0;
    if (g_outdated) { hook_exit(); show_banner(); }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        GetModuleFileNameA(h, g_dir, sizeof g_dir); char *s = strrchr(g_dir, '\\'); if (s) s[1] = 0;
        GetModuleFileNameA(NULL, g_game, sizeof g_game); s = strrchr(g_game, '\\'); if (s) s[1] = 0; else strcpy(g_game, g_dir);
        HANDLE t = CreateThread(NULL, 0, worker, NULL, 0, NULL); if (t) CloseHandle(t);
    } else if (reason == DLL_PROCESS_DETACH && reserved) {
        launch_installer();                                                /* exit path that bypassed ExitProcess */
    }
    return TRUE;
}
