// DOA5LR-Borderless.asi 1.1 — plein ecran sans bordures SANS passer par les options du jeu.
// 1.1 : scripts\DOA5LR-Borderless.ini [Borderless] Mode=  2 = sans bordures (defaut : SCREEN_TYPE=WINDOW est impose
//       dans Documents\KoeiTecmo\DOA5LR\DOA5LR.ini AVANT que le jeu ne le lise, puis les bordures sont retirees),
//       1 = fenetre classique imposee (WINDOW, bordures conservees), 0 = le plugin ne touche a rien (reglage du jeu).
//       IniPath= (tests) : chemin du DOA5LR.ini a modifier au lieu de Documents\KoeiTecmo\DOA5LR\DOA5LR.ini.
//       ToggleKey=F11 (0 = desactivee) : en jeu, fait tourner Sans bordures (1 bip) -> Fenetre (2 bips) -> Plein ecran (3 bips,
//       applique au prochain lancement : SCREEN_TYPE=FULLSCREEN, Mode=0) -> Sans bordures... ; Mode= est memorise dans l'ini du plugin.
//       Le jeu re-ecrit son ini quand on change l'option en jeu : au lancement suivant le plugin re-impose le mode.
// Historique : 1.0 = attendait la fenetre principale puis retirait caption/cadre et la calait sur le moniteur.
#define DOA5LR_INI_MODE 1
#include <shlobj.h>
// Charge par Ultimate ASI Loader (dinput8.dll). Aucun hook : on attend la
// fenetre principale du processus puis on retire caption/cadre/liseré et on
// la cale sur le moniteur ou elle se trouve. Re-applique si le jeu recree ou
// redimensionne sa fenetre (changement de resolution dans les options).
#include <windows.h>
#include <stdio.h>

static HWND g_hwnd = NULL;
static int g_mode = 2;                     /* 0 = inactif, 1 = fenetre, 2 = sans bordures */
static int g_toggleKey = VK_F11;
static WCHAR g_pluginIni[MAX_PATH], g_gameIni[MAX_PATH];
static LONG g_origStyle = 0, g_origEx = 0; static RECT g_origRect; static int g_origSaved = 0;
/* 1.0.1 : -DNO_LOG = build release sans journal ni stdio (faux positifs antivirus) */
#ifdef NO_LOG
#define logf_(...) ((void)0)
#define LOG_OPEN() ((void)0)
#else
static FILE *g_log = NULL;
#define LOG_OPEN() (g_log = fopen("DOA5LR-Borderless.log", "w"))

static void logf_(const char *fmt, ...)
{
    if (!g_log) return;
    SYSTEMTIME st; GetLocalTime(&st);
    fprintf(g_log, "%02d:%02d:%02d ", st.wHour, st.wMinute, st.wSecond);
    va_list ap; va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
    fputc('\n', g_log); fflush(g_log);
}
#endif

static BOOL CALLBACK find_main_window(HWND h, LPARAM lp)
{
    DWORD pid = 0;
    GetWindowThreadProcessId(h, &pid);
    if (pid != GetCurrentProcessId()) return TRUE;
    if (!IsWindowVisible(h) || GetParent(h) != NULL) return TRUE;
    if (GetWindowLongW(h, GWL_EXSTYLE) & WS_EX_TOOLWINDOW) return TRUE;
    RECT c; GetClientRect(h, &c);
    if (c.right < 320 || c.bottom < 240) return TRUE; // splash / fenetres utilitaires
    *(HWND *)lp = h;
    return FALSE;
}

static const LONG kStrip   = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME;
static const LONG kStripEx = WS_EX_CLIENTEDGE | WS_EX_DLGMODALFRAME | WS_EX_STATICEDGE | WS_EX_WINDOWEDGE;

static void apply(HWND h)
{
    LONG st = GetWindowLongW(h, GWL_STYLE);
    LONG ex = GetWindowLongW(h, GWL_EXSTYLE);
    HMONITOR mon = MonitorFromWindow(h, MONITOR_DEFAULTTOPRIMARY);
    MONITORINFO mi = { sizeof(mi) };
    GetMonitorInfoW(mon, &mi);
    RECT want = mi.rcMonitor, have; GetWindowRect(h, &have);

    BOOL styleOk = !(st & kStrip) && !(ex & kStripEx);
    BOOL rectOk  = EqualRect(&want, &have);
    if (styleOk && rectOk) return;

    if (!g_origSaved && (st & kStrip)) { g_origStyle = st; g_origEx = ex; g_origRect = have; g_origSaved = 1; }
    if (!styleOk) {
        SetWindowLongW(h, GWL_STYLE,   (st & ~kStrip) | WS_POPUP | WS_VISIBLE);
        SetWindowLongW(h, GWL_EXSTYLE,  ex & ~kStripEx);
    }
    SetWindowPos(h, NULL, want.left, want.top, want.right - want.left, want.bottom - want.top,
                 SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER);
    logf_("hwnd=%p style 0x%08lX->0x%08lX ex 0x%08lX->0x%08lX rect %ld,%ld %ldx%ld", h,
          st, GetWindowLongW(h, GWL_STYLE), ex, GetWindowLongW(h, GWL_EXSTYLE),
          want.left, want.top, want.right - want.left, want.bottom - want.top);
}

/* Remplace la valeur de SCREEN_TYPE= dans DOA5LR.ini (ANSI ou UTF-16 LE, fins de ligne conservees). Rien d'autre n'est touche. */
static void force_screen_type(const WCHAR *ini, const char *want)
{
    HANDLE h = CreateFileW(ini, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    DWORD size = GetFileSize(h, NULL), got = 0;
    if (size == INVALID_FILE_SIZE || size > 65536) { CloseHandle(h); return; }
    BYTE *raw = (BYTE *)HeapAlloc(GetProcessHeap(), 0, size + 2); if (!raw) { CloseHandle(h); return; }
    ReadFile(h, raw, size, &got, NULL); CloseHandle(h); raw[got] = raw[got + 1] = 0;
    int wide = got >= 2 && raw[0] == 0xFF && raw[1] == 0xFE;
    /* on travaille en ANSI 8 bits : l'UTF-16 est converti, puis reconverti a l'ecriture */
    char *txt; DWORD n;
    if (wide) { n = (got - 2) / 2; txt = (char *)HeapAlloc(GetProcessHeap(), 0, n + 64); for (DWORD i = 0; i < n; i++) txt[i] = (char)raw[2 + 2 * i]; txt[n] = 0; }
    else { n = got; txt = (char *)HeapAlloc(GetProcessHeap(), 0, n + 64); memcpy(txt, raw, n); txt[n] = 0; }
    char *k = strstr(txt, "SCREEN_TYPE=");
    if (!k) { HeapFree(GetProcessHeap(), 0, txt); HeapFree(GetProcessHeap(), 0, raw); return; }
    char *v = k + 12, *e = v; while (*e && *e != '\r' && *e != '\n') e++;
    size_t wl = strlen(want);
    if ((size_t)(e - v) == wl && !memcmp(v, want, wl)) { HeapFree(GetProcessHeap(), 0, txt); HeapFree(GetProcessHeap(), 0, raw); return; }   /* deja bon */
    DWORD n2 = (DWORD)((v - txt) + wl + strlen(e));
    char *out = (char *)HeapAlloc(GetProcessHeap(), 0, n2 + 1);
    memcpy(out, txt, v - txt); memcpy(out + (v - txt), want, wl); strcpy(out + (v - txt) + wl, e);
    h = CreateFileW(ini, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h != INVALID_HANDLE_VALUE) {
        DWORD w;
        if (wide) { BYTE bom[2] = { 0xFF, 0xFE }; WriteFile(h, bom, 2, &w, NULL); for (DWORD i = 0; i < n2; i++) { WCHAR c = (unsigned char)out[i]; WriteFile(h, &c, 2, &w, NULL); } }
        else WriteFile(h, out, n2, &w, NULL);
        CloseHandle(h);
        logf_("DOA5LR.ini : SCREEN_TYPE=%s impose", want);
    }
    HeapFree(GetProcessHeap(), 0, out); HeapFree(GetProcessHeap(), 0, txt); HeapFree(GetProcessHeap(), 0, raw);
}
static void read_config_and_force(HINSTANCE inst)
{
    WCHAR ini[MAX_PATH], path[MAX_PATH];
    GetModuleFileNameW(inst, ini, MAX_PATH); WCHAR *sl = wcsrchr(ini, L'\\'); if (sl) sl[1] = 0;
    wcscat(ini, L"DOA5LR-Borderless.ini"); wcscpy(g_pluginIni, ini);
    g_mode = GetPrivateProfileIntW(L"Borderless", L"Mode", 2, ini);
    if (g_mode < 0 || g_mode > 2) g_mode = 2;
    WCHAR key[16]; GetPrivateProfileStringW(L"Borderless", L"ToggleKey", L"F11", key, 16, ini);
    if (key[0] == L'F' || key[0] == L'f') { int f = _wtoi(key + 1); g_toggleKey = (f >= 1 && f <= 24) ? VK_F1 + f - 1 : 0; } else g_toggleKey = _wtoi(key);
    GetPrivateProfileStringW(L"Borderless", L"IniPath", L"", path, MAX_PATH, ini);
    if (!path[0]) {
        if (SHGetFolderPathW(NULL, CSIDL_MYDOCUMENTS, NULL, SHGFP_TYPE_CURRENT, path) != S_OK) return;
        wcscat(path, L"\\KoeiTecmo\\DOA5LR\\DOA5LR.ini");
    }
    wcscpy(g_gameIni, path);
    if (g_mode >= 1) force_screen_type(path, "WINDOW");
}

/* Bandeau 2 s en haut de l'ecran du jeu : fenetre en couches, sans activation, sans focus. Pas de hook D3D :
 * visible en fenetre / sans bordures ; en plein ecran exclusif rien ne peut s'afficher (les bips restent). */
static const WCHAR *g_toastText = L"";
static LRESULT CALLBACK toast_proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(w, &ps); RECT r; GetClientRect(w, &r);
        HBRUSH bg = CreateSolidBrush(RGB(20, 24, 34)); FillRect(dc, &r, bg); DeleteObject(bg);
        HBRUSH acc = CreateSolidBrush(RGB(226, 55, 68)); RECT bar = r; bar.right = bar.left + 6; FillRect(dc, &bar, acc); DeleteObject(acc);
        HFONT f = CreateFontW(-28, 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
        HGDIOBJ of = SelectObject(dc, f); SetBkMode(dc, TRANSPARENT); SetTextColor(dc, RGB(240, 244, 250));
        RECT t = r; t.left += 22; DrawTextW(dc, g_toastText, -1, &t, DT_SINGLELINE | DT_VCENTER | DT_LEFT);
        SelectObject(dc, of); DeleteObject(f); EndPaint(w, &ps); return 0;
    }
    if (m == WM_TIMER) { DestroyWindow(w); return 0; }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProcW(w, m, wp, lp);
}
static DWORD WINAPI toast_thread(LPVOID text)
{
    g_toastText = (const WCHAR *)text;
    static int reg = 0; HINSTANCE hi = GetModuleHandleW(NULL);
    if (!reg) { WNDCLASSW wc = { 0 }; wc.lpfnWndProc = toast_proc; wc.hInstance = hi; wc.lpszClassName = L"DOA5LR_Borderless_Toast"; wc.hCursor = LoadCursor(NULL, IDC_ARROW); RegisterClassW(&wc); reg = 1; }
    HMONITOR mon = MonitorFromWindow(g_hwnd ? g_hwnd : GetForegroundWindow(), MONITOR_DEFAULTTOPRIMARY);
    MONITORINFO mi = { sizeof mi }; GetMonitorInfoW(mon, &mi);
    int w = 520, h = 64, x = mi.rcMonitor.left + (mi.rcMonitor.right - mi.rcMonitor.left - w) / 2, y = mi.rcMonitor.top + 40;
    HWND t = CreateWindowExW(WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
                             L"DOA5LR_Borderless_Toast", L"", WS_POPUP, x, y, w, h, NULL, NULL, hi, NULL);
    if (!t) return 0;
    SetLayeredWindowAttributes(t, 0, 235, LWA_ALPHA);
    ShowWindow(t, SW_SHOWNOACTIVATE); UpdateWindow(t); SetTimer(t, 1, 2000, NULL);
    MSG msg; while (GetMessageW(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    return 0;
}
static void toast(const WCHAR *text) { HANDLE th = CreateThread(NULL, 0, toast_thread, (LPVOID)text, 0, NULL); if (th) CloseHandle(th); }

static void restore_borders(HWND h)      /* Mode 1/0 : fenetre classique, taille d'origine (ou centree sur le moniteur) */
{
    if (!h || !g_origSaved) return;
    SetWindowLongW(h, GWL_STYLE, g_origStyle | WS_VISIBLE); SetWindowLongW(h, GWL_EXSTYLE, g_origEx);
    RECT r = g_origRect;
    SetWindowPos(h, NULL, r.left, r.top, r.right - r.left, r.bottom - r.top, SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER);
}
static void set_mode(int m)
{
    g_mode = m;
    WCHAR v[4]; wsprintfW(v, L"%d", m); WritePrivateProfileStringW(L"Borderless", L"Mode", v, g_pluginIni);
    force_screen_type(g_gameIni, m == 0 ? "FULLSCREEN" : "WINDOW");
    if (m == 2) { if (g_hwnd) apply(g_hwnd); } else restore_borders(g_hwnd);
    toast(m == 2 ? L"Borderless" : m == 1 ? L"Window" : L"Fullscreen \u2014 applied at next launch");
    for (int i = 0; i < (m == 2 ? 1 : m == 1 ? 2 : 3); i++) { MessageBeep(MB_OK); Sleep(120); }
    logf_("Mode=%d (%s)", m, m == 2 ? "sans bordures" : m == 1 ? "fenetre" : "plein ecran au prochain lancement");
}
static void poll_toggle_key(void)
{
    static int down = 0;
    if (!g_toggleKey) return;
    int now = (GetAsyncKeyState(g_toggleKey) & 0x8000) != 0;
    if (now && !down) {
        HWND fg = GetForegroundWindow(); DWORD pid = 0; if (fg) GetWindowThreadProcessId(fg, &pid);
        if (pid == GetCurrentProcessId()) set_mode(g_mode == 2 ? 1 : g_mode == 1 ? 0 : 2);
    }
    down = now;
}

static DWORD WINAPI worker(LPVOID p)
{
    (void)p;
    for (;;) {
        if (!g_hwnd || !IsWindow(g_hwnd)) {
            g_hwnd = NULL;
            EnumWindows(find_main_window, (LPARAM)&g_hwnd);
            if (g_hwnd) logf_("fenetre principale trouvee hwnd=%p", g_hwnd);
        }
        if (g_hwnd && g_mode == 2) apply(g_hwnd);
        for (int i = 0; i < (g_hwnd ? 8 : 2); i++) { Sleep(125); poll_toggle_key(); }
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        LOG_OPEN();
        read_config_and_force(inst);                 /* avant que le jeu ne lise DOA5LR.ini */
        logf_("DOA5LR Borderless 1.1 charge (Mode=%d)", g_mode);
        HANDLE t = CreateThread(NULL, 0, worker, NULL, 0, NULL); if (t) CloseHandle(t);   /* Mode 2 : bordures ; tous modes : touche */
    }
    return TRUE;
}
