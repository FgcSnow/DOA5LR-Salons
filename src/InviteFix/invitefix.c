/*  DOA5LR-InviteFix  v0.1.1  (20/09/2026 : build release sans journal + VERSIONINFO ; v0.1 du 19/09/2026)
 *
 *  Corrige le bouton "Inviter ami" du mod DOA5LR-Lobby 0.9.0 quand CreamAPI est installe.
 *
 *  Probleme : le steam_api.dll de CreamAPI exporte la fonction "plate"
 *  SteamAPI_ISteamFriends_ActivateGameOverlayInviteDialog, mais ne fait que la relayer vers
 *  l'original (steam_api_o.dll) qui, lui, ne l'a pas (vieux SDK). Le relais est donc un
 *  pointeur NUL -> "call 0" -> crash C0000005 eip=00000000 rattrape par le mod, fenetre
 *  Steam jamais ouverte.
 *
 *  Correctif : on retrouve le relais (motif  55 8B EC FF75 10 FF75 0C FF75 08 FF15 <ptr>),
 *  et si *ptr == NULL on y ecrit notre propre implementation, qui appelle
 *  ISteamFriends014::ActivateGameOverlayInviteDialog (slot 27 de la vtable).
 *  Sans CreamAPI (ou si le pointeur est deja rempli) : on ne touche a rien.
 *
 *  Compilation : i686-w64-mingw32-gcc -O2 -s -shared -static -o DOA5LR-InviteFix.asi invitefix.c
 */
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

/* v0.1.1 : build "release" compile avec -DNO_LOG = aucun journal, aucun appel stdio (moins de faux positifs
 * antivirus, cf. retour de la communaute) ; build "-debug" (sans NO_LOG) = journal DOA5LR-InviteFix.log. */
#ifdef NO_LOG
#define Log(...) ((void)0)
#define LOG_OPEN() ((void)0)
#define LOG_CLOSE() ((void)0)
#else
static FILE *g_log;
static void Log(const char *fmt, ...)
{
    if (!g_log) return;
    SYSTEMTIME t; GetLocalTime(&t);
    fprintf(g_log, "%02u:%02u:%02u.%03u ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
    va_list ap; va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
    fputc('\n', g_log); fflush(g_log);
}
#define LOG_OPEN() (g_log = fopen("DOA5LR-InviteFix.log", "a"))
#define LOG_CLOSE() do { if (g_log) fclose(g_log); } while (0)
#endif

typedef void *(*SteamFriends_t)(void);
typedef void (__thiscall *InviteDialog_t)(void *self, uint64_t lobby);

static SteamFriends_t g_SteamFriends;
static volatile LONG g_calls;

#define SLOT_ACTIVATE_INVITE_DIALOG 27   /* ISteamFriends014 */

/* Remplacant du relais CreamAPI. Meme signature que la fonction plate (cdecl) :
 * (ISteamFriends *self, uint32 lo, uint32 hi). */
static void __cdecl Fix_ActivateGameOverlayInviteDialog(void *self, uint32_t lo, uint32_t hi)
{
    uint64_t lobby = ((uint64_t)hi << 32) | lo;
    LONG n = InterlockedIncrement(&g_calls);
    Log("Appel #%ld : self=%p salon=%llu (universe=%u type=%u)", n, self,
        (unsigned long long)lobby, hi >> 24, (hi >> 20) & 0xF);

    if (!self && g_SteamFriends) {
        self = g_SteamFriends();
        Log("  self NUL -> SteamFriends() = %p", self);
    }
    if (!self) { Log("  ECHEC : pas d'interface ISteamFriends."); return; }

    void **vtbl = *(void ***)self;
    InviteDialog_t fn = (InviteDialog_t)vtbl[SLOT_ACTIVATE_INVITE_DIALOG];
    Log("  vtable=%p slot27=%p -> ouverture de la fenetre d'invitation Steam", vtbl, (void *)fn);
    if (!fn) { Log("  ECHEC : slot 27 vide."); return; }
    fn(self, lobby);
    Log("  OK, appel termine.");
}

static const char *ModName(HMODULE m)
{
    static char buf[MAX_PATH];
    GetModuleFileNameA(m, buf, sizeof buf);
    const char *p = strrchr(buf, 92);  /* '\' */
    return p ? p + 1 : buf;
}

static int Patch(void)
{
    HMODULE api = GetModuleHandleA("steam_api.dll");
    if (!api) return 0;   /* pas encore charge, on reessaiera */

    HMODULE orig = GetModuleHandleA("steam_api_o.dll");
    Log("steam_api.dll=%p  steam_api_o.dll=%p (%s)", api, orig, orig ? "CreamAPI detecte" : "pas de CreamAPI");

    g_SteamFriends = (SteamFriends_t)GetProcAddress(api, "SteamFriends");
    Log("SteamFriends() = %p", (void *)g_SteamFriends);

    uint8_t *flat = (uint8_t *)GetProcAddress(api, "SteamAPI_ISteamFriends_ActivateGameOverlayInviteDialog");
    if (!flat) {
        Log("La fonction plate n'est pas exportee : rien a corriger (le mod prendra son plan B).");
        return 1;
    }
    Log("Fonction plate exportee a %p (%s+0x%X)", flat, ModName(api), (unsigned)(flat - (uint8_t *)api));

    /* Motif du relais CreamAPI : push ebp / mov ebp,esp / push [ebp+10] / push [ebp+C] / push [ebp+8] / call [ptr] */
    static const uint8_t pat[] = { 0x55, 0x8B, 0xEC, 0xFF, 0x75, 0x10, 0xFF, 0x75, 0x0C, 0xFF, 0x75, 0x08, 0xFF, 0x15 };
    if (memcmp(flat, pat, sizeof pat) != 0) {
        Log("Le code ne ressemble pas au relais CreamAPI (%02X %02X %02X %02X ...) : on ne touche a rien.",
            flat[0], flat[1], flat[2], flat[3]);
        return 1;
    }
    void **slot = *(void ***)(flat + sizeof pat);
    Log("Pointeur de relais a %p, valeur actuelle = %p", (void *)slot, *slot);
    if (*slot) {
        Log("Le relais est deja rempli : la fonction plate est fonctionnelle, aucun correctif necessaire.");
        return 1;
    }

    DWORD old;
    if (!VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old)) {
        Log("ECHEC VirtualProtect (%lu).", GetLastError());
        return 1;
    }
    *slot = (void *)Fix_ActivateGameOverlayInviteDialog;
    VirtualProtect(slot, sizeof(void *), old, &old);
    Log("CORRECTIF POSE : le relais nul pointe maintenant sur notre implementation (%p).",
        (void *)Fix_ActivateGameOverlayInviteDialog);
    return 1;
}

static DWORD WINAPI Worker(LPVOID p)
{
    (void)p;
    for (int i = 0; i < 600; i++) {       /* jusqu'a 60 s */
        if (Patch()) return 0;
        Sleep(100);
    }
    Log("steam_api.dll jamais charge en 60 s : abandon.");
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        LOG_OPEN();
        Log("Chargement DOA5LR-InviteFix 0.1.1 - correctif bouton Inviter (CreamAPI).");
        HANDLE t = CreateThread(NULL, 0, Worker, NULL, 0, NULL);
        if (t) CloseHandle(t);
    } else if (reason == DLL_PROCESS_DETACH) {
        Log("Dechargement (%ld appel(s) d'invitation traites).", g_calls);
        LOG_CLOSE();
    }
    return TRUE;
}
