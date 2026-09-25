/*  DOA5LR-JoinFix v0.1  (25/09/2026) — correctifs de jonction des salons (DOA5LR PC, mode Lobby du pack).
 *
 *  Analyse (voir DOA5LR-JoinDiag) :
 *   - le jeu ignore P2PSessionConnectFail (gestionnaire vide `ret 4`) : si la liaison avec l'hote echoue,
 *     l'etape JoinRoom attend son delai (90 s) sans rien dire ;
 *   - le jeu n'accepte les demandes de liaison P2P que tant que son objet CLobby existe ;
 *   - sur une invitation (GameLobbyJoinRequested), le jeu demande les donnees du salon et ne lance la
 *     jonction qu'a l'arrivee de LobbyDataUpdate pour ce salon : si elle se perd, rien ne se passe.
 *
 *  Correctifs (chacun desactivable dans DOA5LR-JoinFix.ini, section [JoinFix]) :
 *   AcceptMembers=1 : accepte la liaison P2P d'un joueur s'il est membre du salon courant (ou en cours de jonction).
 *   FastFail=1      : pendant JoinRoom, si Steam signale la liaison avec l'HOTE impossible (callback 1203 ou
 *                     etat de session en erreur), l'etape echoue comme le jeu le fait lui-meme
 *                     (+0xC/+0xD = 0x100, code affiche 5) -> message et retour immediat au lieu de 90 s.
 *   InviteRetry=1   : apres une invitation acceptee, redemande les donnees du salon toutes les 3 s (5 fois max)
 *                     tant que LobbyDataUpdate / LobbyEnter n'est pas arrive.
 *   KeyFix=1        : (0.2, CAUSE TROUVEE le 25/09) l'hote publie ses cles de chiffrement P2P dans les donnees
 *                     du salon Steam comme du TEXTE ("cryptSeed" 16 octets, "sigKey" 8 octets, contexte global
 *                     RVA 0x20924B8 -> +0x1C / +0x2C). Si un octet aleatoire vaut 0, Steam coupe la valeur : le
 *                     joueur qui rejoint derive une mauvaise cle, l'hote ignore sa JoinRequest et il repart apres
 *                     30 s (~1 salon sur 11). Correctif cote HOTE : juste avant la publication, les octets nuls de la
 *                     cle sont remplaces dans le contexte du jeu ET dans la valeur publiee (le jeu relit ces cles a
 *                     chaque paquet, donc tout reste coherent). Sans effet si la cle ne contient pas de zero.
 *   CopyLinkKey=118 : (0.3) touche (code virtuel Windows, 118 = F7, 0 = aucune) qui copie dans le presse-papiers le lien
 *                     steam://joinlobby/311730/<salon>/<hote> du salon ou l'on se trouve (les salons prives n'ont pas
 *                     de bouton "Rejoindre la partie" dans Steam). Bip aigu = copie, bip grave = pas de salon.
 *   Log=1           : journal DOA5LR-JoinFix.log (actions seulement).
 *
 *  Tous les appels Steam se font sur le thread du jeu (tic = SteamAPI_RunCallbacks, via la table d'imports).
 *  Compilation : build.cmd (LLVM-MinGW, 32 bits).
 */
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <share.h>

#define FIX_VER "0.3"
typedef uint64_t CSteamID;

static CRITICAL_SECTION g_cs; static int g_logOn = 1;
#ifndef NO_LOG
static FILE *g_log;
#endif
#ifdef NO_LOG
#define L(...) ((void)0)
#else
static void L(const char *fmt, ...)
{
    if (!g_log || !g_logOn) return;
    SYSTEMTIME t; GetLocalTime(&t);
    va_list ap; va_start(ap, fmt);
    EnterCriticalSection(&g_cs);
    fprintf(g_log, "%02u/%02u %02u:%02u:%02u.%03u ", t.wDay, t.wMonth, t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
    vfprintf(g_log, fmt, ap); fputc('\n', g_log); fflush(g_log);
    LeaveCriticalSection(&g_cs);
    va_end(ap);
}
#endif
static int patch_ptr(void **slot, void *hook, void **orig)
{
    DWORD old;
    if (!VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old)) return 0;
    *orig = *slot;
    InterlockedExchange((volatile LONG *)slot, (LONG)(uintptr_t)hook);
    VirtualProtect(slot, sizeof(void *), old, &old);
    return 1;
}

static int g_acceptMembers = 1, g_fastFail = 1, g_inviteRetry = 1, g_keyFix = 1;
static int g_copyKey = 0x76;
static int g_keyTest = 0; static char g_ini[MAX_PATH];   /* TEST : 1 = met un octet nul dans cryptSeed SANS corriger (reproduit le bug), 2 = octet nul PUIS KeyFix */
static uint8_t *g_base;

/* ---- adresses du jeu (game.exe Ver.1.10C, RVA) */
#define RVA_KTOL_PRINTF     0x846010
static const uint8_t KTOL_PRINTF_BYTES[] = {0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x04, 0x02, 0x00, 0x00};
#define RVA_ERRDLG          0x2080320   /* code d'erreur affiche (ecrit par sub_745810) */
#define RVA_IAT_RUNCALLBACKS 0x9663DC
#define RVA_JOINROOM_VT     0xBE35B0
#define RVA_JOINROOM_UPD    0x52EC60
#define RVA_CRYPT_CTX       0x20924B8   /* pointeur global : +0x1C cryptSeed[16], +0x2C sigKey[8] */

/* ---- Steam */
static void *g_mm, *g_net;
typedef uint8_t (__thiscall *AcceptP2P_t)(void *self, CSteamID id);
typedef struct { uint8_t active, connecting, error, relay; int32_t bytesQueued, packetsQueued; uint32_t ip; uint16_t port; } P2PSessionState_t;
typedef uint8_t (__thiscall *GetP2PSessionState_t)(void *self, CSteamID id, P2PSessionState_t *st);
typedef int (__thiscall *GetNumLobbyMembers_t)(void *self, CSteamID lobby);
typedef CSteamID *(__thiscall *GetLobbyMemberByIndex_t)(void *self, CSteamID *ret, CSteamID lobby, int i);
typedef CSteamID *(__thiscall *GetLobbyOwner_t)(void *self, CSteamID *ret, CSteamID lobby);
typedef uint8_t (__thiscall *RequestLobbyData_t)(void *self, CSteamID lobby);

static CSteamID g_lobby;            /* salon courant (LobbyEnter OK) */
static CSteamID g_inviteLobby;      /* invitation acceptee, en attente des donnees */
static DWORD g_inviteTick; static int g_inviteTries;

static int is_member(CSteamID lobby, CSteamID who)
{
    if (!g_mm || !lobby || !who) return 0;
    void **vt = *(void ***)g_mm;
    int n = ((GetNumLobbyMembers_t)vt[17])(g_mm, lobby);
    for (int i = 0; i < n && i < 32; i++) { CSteamID m = 0; ((GetLobbyMemberByIndex_t)vt[18])(g_mm, &m, lobby, i); if (m == who) return 1; }
    return 0;
}
static CSteamID owner_of(CSteamID lobby)
{
    if (!g_mm || !lobby) return 0;
    CSteamID o = 0; ((GetLobbyOwner_t)(*(void ***)g_mm)[35])(g_mm, &o, lobby); return o;
}

/* ---- etape JoinRoom : suivi de l'objet en cours (slot 1 de sa vtable) */
typedef void (__thiscall *ProcUpdate_t)(void *self);
static ProcUpdate_t o_joinUpd;
static void *volatile g_joinProc; static DWORD g_joinStart;
static void __thiscall hk_joinUpd(void *self)
{
    o_joinUpd(self);
    uint8_t run = ((uint8_t *)self)[0xC];
    if (run && g_joinProc != self) { g_joinProc = self; g_joinStart = GetTickCount(); }
    else if (!run && g_joinProc == self) g_joinProc = NULL;
}
static void join_fail(const char *why, CSteamID host)
{
    void *p = g_joinProc;
    if (!p || !((uint8_t *)p)[0xC]) return;
    /* meme chemin d'echec que le jeu (sub JoinRoom update) : word +0xC = 0x100 (fini, echec), code affiche 5 */
    *(volatile uint16_t *)((uint8_t *)p + 0xC) = 0x100;
    *(volatile uint32_t *)(g_base + RVA_ERRDLG) = 5;
    g_joinProc = NULL;
    L("FastFail : jonction abandonnee apres %lu ms (%s, hote %llu) -> message d'erreur du jeu, on peut reessayer",
      (unsigned long)(GetTickCount() - g_joinStart), why, (unsigned long long)host);
}

/* ---- callbacks Steam (CCallbackBase MSVC : [0] Run(pv,bIO,hCall) [1] Run(pv) [2] taille) */
typedef struct CB { void **vt; uint8_t flags; uint8_t pad[3]; int id; int size; } CB;
static CSteamID g_joinTarget;   /* salon vise par JoinLobby (le hook JoinLobby n'est pas pose : on prend LobbyEnter) */
static void on_callback(int id, void *pv)
{
    uint8_t *d = (uint8_t *)pv;
    switch (id) {
    case 333:   /* GameLobbyJoinRequested : lobby, friend */
        if (g_inviteRetry) { g_inviteLobby = *(uint64_t *)d; g_inviteTick = GetTickCount(); g_inviteTries = 0;
            L("Invitation acceptee : salon %llu, on surveille l'arrivee de ses donnees", (unsigned long long)g_inviteLobby); }
        break;
    case 505: { /* LobbyDataUpdate */
        CSteamID lobby = *(uint64_t *)d;
        if (g_inviteLobby && lobby == g_inviteLobby) { L("Invitation : donnees du salon recues (%d relance(s))", g_inviteTries); g_inviteLobby = 0; }
        break; }
    case 504: { /* LobbyEnter */
        CSteamID lobby = *(uint64_t *)d; uint32_t resp = *(uint32_t *)(d + 16);
        if (resp == 1) g_lobby = lobby;
        if (g_inviteLobby == lobby) g_inviteLobby = 0;
        g_joinTarget = lobby;
        break; }
    case 1202: { /* P2PSessionRequest */
        CSteamID u = *(uint64_t *)d;
        if (!g_acceptMembers || !g_net) break;
        CSteamID lobby = g_lobby ? g_lobby : g_joinTarget;
        if (lobby && is_member(lobby, u)) {
            uint8_t ok = ((AcceptP2P_t)(*(void ***)g_net)[3])(g_net, u) & 0xFF;
            L("AcceptMembers : liaison P2P acceptee pour %llu (membre du salon) -> %d", (unsigned long long)u, ok);
        }
        break; }
    case 1203: { /* P2PSessionConnectFail : le jeu l'ignore */
        CSteamID u = *(uint64_t *)d; int e = d[8];
        L("Steam : liaison P2P impossible avec %llu (erreur %d)", (unsigned long long)u, e);
        if (g_fastFail && g_joinProc && g_joinTarget && u == owner_of(g_joinTarget)) join_fail("P2PSessionConnectFail", u);
        break; }
    case 513: { int r = *(int *)d; if (r == 1) g_lobby = *(uint64_t *)(d + 8); break; }
    case 506: { /* LobbyChatUpdate : si c'est nous qui partons */
        break; }
    }
}
static void __thiscall cb_run_result(CB *self, void *pv, int io, uint64_t call) { (void)io; (void)call; on_callback(self->id, pv); }
static void __thiscall cb_run(CB *self, void *pv) { on_callback(self->id, pv); }
static int __thiscall cb_size(CB *self) { return self->size; }
static void *g_cbVt[3] = { (void *)cb_run_result, (void *)cb_run, (void *)cb_size };
static const int CB_IDS[][2] = { {333, 16}, {504, 24}, {505, 24}, {513, 16}, {1202, 8}, {1203, 16} };
#define NCB (sizeof CB_IDS / sizeof *CB_IDS)
static CB g_cbs[NCB];
typedef void (__cdecl *RegisterCallback_t)(CB *cb, int id);

/* ---- KeyFix : ISteamMatchmaking::SetLobbyData (slot 20) */
typedef uint8_t (__thiscall *SetLobbyData_t)(void *self, CSteamID lobby, const char *key, const char *value);
static SetLobbyData_t o_setLobbyData;
static int fix_zeros(uint8_t *k, int n)
{
    int fixed = 0;
    for (int i = 0; i < n; i++) if (k[i] == 0) { k[i] = (uint8_t)(0x5B + 37 * i) | 1; fixed++; }
    return fixed;
}
static uint8_t __thiscall hk_setLobbyData(void *self, CSteamID lobby, const char *key, const char *value)
{
    if (g_keyFix && key && value && g_base) {
        int seed = !strcmp(key, "cryptSeed"), sig = !strcmp(key, "sigKey");
        uint8_t *ctx = *(uint8_t **)(g_base + RVA_CRYPT_CTX);
        if ((seed || sig) && ctx) {
            uint8_t *k = ctx + (seed ? 0x1C : 0x2C); int n = seed ? 16 : 8;
            /* la valeur publiee doit etre la copie de la cle du jeu : sinon on ne touche a rien */
            if (!memcmp(value, k, n) || (strlen(value) < (size_t)n && !memcmp(value, k, strlen(value)))) {
#ifndef NO_LOG
                if (seed) g_keyTest = GetPrivateProfileIntA("JoinFix", "KeyTest", 0, g_ini);   /* relu a chaque salon : modifiable jeu ouvert */
#endif
#ifndef NO_LOG
                if (seed && g_keyTest) {   /* test (build -debug seulement) : 3e octet nul, dans la cle du jeu ET la valeur publiee */
                    k[2] = 0; ((uint8_t *)value)[2] = 0;
                    L("KeyTest=%d : octet nul force dans cryptSeed du salon %llu (%s)", g_keyTest, (unsigned long long)lobby,
                      g_keyTest == 1 ? "SANS correction : le joueur ne devrait PAS pouvoir entrer" : "puis KeyFix : le joueur devrait entrer");
                    if (g_keyTest == 1) return o_setLobbyData(self, lobby, key, value);
                }
#endif
                int f = fix_zeros(k, n);
                if (f) {
                    memcpy((void *)value, k, n);
                    L("KeyFix : %s du salon %llu contenait %d octet(s) nul(s) -> corrige (sinon les joueurs n'auraient pas pu rejoindre)",
                      key, (unsigned long long)lobby, f);
                }
            } else L("KeyFix : %s publie ne correspond pas a la cle du jeu, non modifie", key);
        }
    }
    return o_setLobbyData(self, lobby, key, value);
}

/* ---- CopyLinkKey : lien steam://joinlobby du salon courant -> presse-papiers */
static int copy_text(const char *t)
{
    size_t n = strlen(t) + 1;
    HGLOBAL h = GlobalAlloc(GMEM_MOVEABLE, n * sizeof(WCHAR));
    if (!h) return 0;
    WCHAR *w = (WCHAR *)GlobalLock(h);
    MultiByteToWideChar(CP_ACP, 0, t, -1, w, (int)n);
    GlobalUnlock(h);
    if (!OpenClipboard(NULL)) { GlobalFree(h); return 0; }
    EmptyClipboard();
    int ok = SetClipboardData(CF_UNICODETEXT, h) != NULL;
    CloseClipboard();
    if (!ok) GlobalFree(h);
    return ok;
}
static int game_has_focus(void)
{
    DWORD pid = 0; HWND w = GetForegroundWindow();
    if (!w) return 0;
    GetWindowThreadProcessId(w, &pid);
    return pid == GetCurrentProcessId();
}
static void copy_link(void)
{
    CSteamID lobby = g_lobby;
    int n = (g_mm && lobby) ? ((GetNumLobbyMembers_t)(*(void ***)g_mm)[17])(g_mm, lobby) : 0;
    CSteamID owner = n > 0 ? owner_of(lobby) : 0;
    if (!owner) { MessageBeep(MB_ICONHAND); L("CopyLink : pas de salon en cours"); return; }
    char link[128];
    snprintf(link, sizeof link, "steam://joinlobby/311730/%llu/%llu", (unsigned long long)lobby, (unsigned long long)owner);
    if (copy_text(link)) { MessageBeep(MB_ICONASTERISK); L("CopyLink : %s copie", link); }
    else { MessageBeep(MB_ICONHAND); L("CopyLink : presse-papiers indisponible"); }
}

/* ---- tic sur le thread du jeu : SteamAPI_RunCallbacks (table d'imports de game.exe) */
typedef void (__cdecl *RunCallbacks_t)(void);
static RunCallbacks_t o_runCallbacks;
static DWORD g_lastTick;
static void __cdecl hk_runCallbacks(void)
{
    o_runCallbacks();
    if (g_copyKey) {   /* chaque image : front montant de la touche, fenetre du jeu au premier plan */
        static int was;
        int down = (GetAsyncKeyState(g_copyKey) & 0x8000) != 0;
        if (down && !was && game_has_focus()) copy_link();
        was = down;
    }
    DWORD now = GetTickCount();
    if (now - g_lastTick < 500) return;
    g_lastTick = now;
    /* InviteRetry */
    if (g_inviteRetry && g_inviteLobby && g_mm && now - g_inviteTick >= 3000) {
        if (g_inviteTries >= 5) { L("Invitation : toujours pas de donnees apres 5 relances, abandon de la surveillance"); g_inviteLobby = 0; }
        else {
            uint8_t ok = ((RequestLobbyData_t)(*(void ***)g_mm)[28])(g_mm, g_inviteLobby) & 0xFF;
            g_inviteTries++; g_inviteTick = now;
            L("Invitation : donnees du salon %llu pas encore recues -> nouvelle demande n.%d (%d)", (unsigned long long)g_inviteLobby, g_inviteTries, ok);
        }
    }
    /* FastFail par etat de session (si le callback 1203 n'arrive pas) : hote en erreur, plus en cours de connexion */
    if (g_fastFail && g_joinProc && g_joinTarget && g_net && now - g_joinStart > 8000) {
        CSteamID host = owner_of(g_joinTarget);
        P2PSessionState_t st; memset(&st, 0, sizeof st);
        static int bad;
        if (host && (((GetP2PSessionState_t)(*(void ***)g_net)[6])(g_net, host, &st) & 0xFF) && !st.active && !st.connecting && st.error) {
            if (++bad >= 2) { bad = 0; join_fail("session P2P de l'hote en erreur", host); }
        } else bad = 0;
    }
}

static DWORD WINAPI worker(LPVOID arg)
{
    (void)arg;
    g_base = (uint8_t *)GetModuleHandleA(NULL);
    int okv = 0;
    for (int t = 0; t < 600 && !(okv = memcmp(g_base + RVA_KTOL_PRINTF, KTOL_PRINTF_BYTES, sizeof KTOL_PRINTF_BYTES) == 0); t++) Sleep(100);
    if (!okv) { L("version de game.exe inattendue : JoinFix inactif"); return 0; }
    Sleep(1500);   /* laisse DOA5LR-JoinDiag poser ses propres suivis d'abord (il verifie les vtables d'origine) */
    void **jvt = (void **)(g_base + RVA_JOINROOM_VT);
    /* JoinDiag peut deja enrober ce slot : on verifie l'original connu OU un enrobage deja pose */
    if (patch_ptr(&jvt[1], (void *)hk_joinUpd, (void **)&o_joinUpd)) L("suivi de l'etape JoinRoom pose");
    HMODULE sa = NULL;
    for (int t = 0; t < 1200 && !sa; t++) { sa = GetModuleHandleA("steam_api.dll"); if (!sa) Sleep(100); }
    if (!sa) { L("steam_api.dll absent"); return 0; }
    RegisterCallback_t reg = (RegisterCallback_t)GetProcAddress(sa, "SteamAPI_RegisterCallback");
    if (reg) for (size_t i = 0; i < NCB; i++) { g_cbs[i].vt = g_cbVt; g_cbs[i].id = CB_IDS[i][0]; g_cbs[i].size = CB_IDS[i][1]; reg(&g_cbs[i], CB_IDS[i][0]); }
    typedef void *(*Acc_t)(void);
    Acc_t aMM = (Acc_t)GetProcAddress(sa, "SteamMatchmaking"), aNet = (Acc_t)GetProcAddress(sa, "SteamNetworking");
    for (int t = 0; t < 1200 && !(g_mm && g_net); t++) { if (aMM && !g_mm) g_mm = aMM(); if (aNet && !g_net) g_net = aNet(); if (!(g_mm && g_net)) Sleep(250); }
    if (g_keyFix && g_mm && patch_ptr(&(*(void ***)g_mm)[20], (void *)hk_setLobbyData, (void **)&o_setLobbyData)) L("KeyFix pose (SetLobbyData)");
    void **iat = (void **)(g_base + RVA_IAT_RUNCALLBACKS);
    if (patch_ptr(iat, (void *)hk_runCallbacks, (void **)&o_runCallbacks)) L("tic sur SteamAPI_RunCallbacks pose");
    L("pret : KeyFix=%d AcceptMembers=%d FastFail=%d InviteRetry=%d CopyLinkKey=%d", g_keyFix, g_acceptMembers, g_fastFail, g_inviteRetry, g_copyKey);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        InitializeCriticalSection(&g_cs);
        char dir[MAX_PATH]; GetModuleFileNameA(h, dir, sizeof dir);
        char *s = strrchr(dir, '\\'); if (s) s[1] = 0;
        char *ini = g_ini; snprintf(g_ini, sizeof g_ini, "%sDOA5LR-JoinFix.ini", dir);
        g_acceptMembers = GetPrivateProfileIntA("JoinFix", "AcceptMembers", 1, ini);
        g_fastFail = GetPrivateProfileIntA("JoinFix", "FastFail", 1, ini);
        g_inviteRetry = GetPrivateProfileIntA("JoinFix", "InviteRetry", 1, ini);
        g_keyFix = GetPrivateProfileIntA("JoinFix", "KeyFix", 1, ini);
        g_copyKey = GetPrivateProfileIntA("JoinFix", "CopyLinkKey", 0x76, ini);
#ifndef NO_LOG
        g_keyTest = GetPrivateProfileIntA("JoinFix", "KeyTest", 0, ini);
#endif
        g_logOn = GetPrivateProfileIntA("JoinFix", "Log", 1, ini);
#ifndef NO_LOG
        if (g_logOn) {
            char exe[MAX_PATH]; GetModuleFileNameA(NULL, exe, sizeof exe);
            char *e = strrchr(exe, '\\'); if (e) e[1] = 0;
            char path[MAX_PATH]; snprintf(path, sizeof path, "%sDOA5LR-JoinFix.log", exe);
            g_log = _fsopen(path, "a", _SH_DENYNO);
            L("=== DOA5LR-JoinFix " FIX_VER " ===");
        }
#endif
        HANDLE t = CreateThread(NULL, 0, worker, NULL, 0, NULL); if (t) CloseHandle(t);
    }
    return TRUE;
}
