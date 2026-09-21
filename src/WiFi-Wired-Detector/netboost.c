// DOA5LR-WiFi-Wired-Detector.asi (ex-NetBoost) v0.8.8 — mouchard reseau P2P (statistiques, ping reel,
// 0.8.8 : LinkOverride=1 (forcer « cable ») N'EXISTE PLUS (decision Snow 21/09 : l'indicateur ne vaut que si personne
//         ne peut se declarer cable a la main). Valeurs : 0 = auto, 2 = forcer sans fil ; 1 ou autre = ignore (auto).
// 0.8.7 : AFFICHAGE DU PING RETIRE (decision Snow 21/09 : on veut seulement savoir cable / Wi-Fi). PingDisplay et
//         PingDisplaySelf ne sont plus lus (forces a 0) : aucun hook ISteamFriends, rien d'ecrit dans les fiches.
//         Le HELLO ping/pong reste (il transporte le type de lien ; le RTT ne sert plus qu'au journal du build debug).
// verdict relais, qualite), type de connexion dans le salon + REDONDANCE de paquets, pour DOA5LR PC.
// 0.8.6 : PING AFFICHE DANS LE SALON (PingDisplay=1 : " 45ms" ajoute au nom du pair dans sa fiche locale
//         NameCard, +0xE4 ; =2 : RTT ecrit dans le champ qualite +0x108 ; 0 = rien) pour les pairs equipes
//         0.8.5+ ; PingDisplaySelf=1 pour tester seul sur sa propre fiche ; la session P2P vers son propre
//         SteamID est marquee "(soi)" dans live.txt (ignoree par DOA5LR-Telemetry 0.3). A VALIDER EN JEU :
//         le salon relit-il le nom depuis la fiche a chaque image ?
// 0.8.5 : plus AUCUN appel Steam hors du thread du jeu (crash 20/09 01:57), pairs partis ignores,
//         ping RTT par HELLO v2, qualite NameCard par pair, live.txt enrichi pour DOA5LR-Telemetry.
//
// Redondance : entre deux joueurs qui ont TOUS LES DEUX ce plugin (poignee de main
// automatique sur un canal que le jeu n'utilise pas), chaque paquet non fiable
// envoye embarque aussi les N precedents (N = Redundancy). A la reception, le
// plugin deballe, rend au jeu le paquet courant et, si un precedent a ete perdu
// en route, le rend aussi (jamais de doublon : suivi par numero de sequence).
// Avec un joueur sans plugin : trafic 100 % d'origine.
//
// Options (DOA5LR-WiFi-Wired-Detector.ini, section [NetBoost]) :
//   Redundancy=2    0 = desactive (statistiques seules), 1..3 = paquets precedents embarques
//   AllowRelay=1    0 = demander a Steam une connexion directe (test)
//   LogPackets=0    1 = journaliser chaque paquet (verbeux, PacketLogMax)
//
// Compilation : i686-w64-mingw32-gcc -O2 -s -shared -static -o DOA5LR-NetBoost.asi netboost.c -liphlpapi
#include <winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

// Les methodes Steam renvoient un bool : seul AL est significatif (le reste d'EAX est
// indetermine) -> les pointeurs de fonction sont declares en uint8_t, jamais en int.
typedef uint64_t CSteamID;
typedef struct { uint8_t active, connecting, error, relay; int32_t bytesQueued, packetsQueued; uint32_t ip; uint16_t port; } P2PSessionState_t;

typedef uint8_t (__thiscall *SendP2PPacket_t)(void *self, CSteamID id, const void *data, uint32_t len, int sendType, int channel);
typedef uint8_t (__thiscall *IsP2PPacketAvailable_t)(void *self, uint32_t *outLen, int channel);
typedef uint8_t (__thiscall *ReadP2PPacket_t)(void *self, void *dest, uint32_t cap, uint32_t *outLen, CSteamID *outId, int channel);
typedef uint8_t (__thiscall *GetP2PSessionState_t)(void *self, CSteamID id, P2PSessionState_t *st);
typedef uint8_t (__thiscall *AllowP2PPacketRelay_t)(void *self, int allow);
typedef void *(*SteamNetworking_t)(void);
// ISteamMatchmaking (SteamMatchMaking009) : donnees de salon (cle/valeur) — sonde pour
// trouver ou le jeu annonce le type de connexion des joueurs.
typedef uint8_t     (__thiscall *SetLobbyData_t)(void *self, CSteamID lobby, const char *key, const char *value);
typedef void        (__thiscall *SetLobbyMemberData_t)(void *self, CSteamID lobby, const char *key, const char *value);
typedef const char *(__thiscall *GetLobbyMemberData_t)(void *self, CSteamID lobby, CSteamID user, const char *key);
typedef const char *(__thiscall *GetLobbyData_t)(void *self, CSteamID lobby, const char *key);
static SetLobbyData_t o_setLobbyData = NULL; static SetLobbyMemberData_t o_setMemberData = NULL;
static GetLobbyMemberData_t o_getMemberData = NULL; static GetLobbyData_t o_getLobbyData = NULL;
static int g_lobbyProbe = 1;
// --- Type de connexion affiche dans le salon ([n] cable / <n> sans fil) ---
// Le jeu PC ecrit toujours 1 (cable) dans la fiche joueur (NameCard) envoyee aux
// autres. Offsets (Ver.1.10C, base d'analyse 0xAB0000) : NameCardManager global
// RVA 0xF82950, 16 entrees de 0x10C octets a +0xDC, cle (index membre) a +0,
// nom ASCII a +0xE4, octet type de connexion a +0x107 (1 = cable, 2 = sans fil).
// Verifie par test en salon le 19/09/2026 (<2> affiche chez l'autre joueur).
#define NC_MGR_RVA   0xF82950
#define NC_CHECK_RVA 0x50C570   // debut de NameCardManager::Find (0xFBC570 - 0xAB0000)
static const uint8_t NC_CHECK[16] = { 0x55,0x8b,0xec,0x57,0x8b,0x7d,0x08,0x83,0xff,0xff,0x75,0x0b,0x8d,0x81,0x98,0x11 };
static int g_linkOverride = 0;       // ini LinkOverride : 0 = auto, 2 = forcer sans fil (0.8.8 : 1 = forcer cable n'existe plus -> auto)
static int g_pingDisplay = 0, g_pingDisplaySelf = 0;   // 0.8.7 : toujours 0 (affichage du ping retire) ; le code 0.8.6 reste mais n'est jamais atteint
static uint8_t *g_ncMgr = NULL; static char g_persona[64] = "";
static uint64_t g_ncPatched = 0;
static void namecard_fix(void);
static void namecard_ping_show(void);
// NameCardPacket (type 0x13) : vtable RVA 0xBE22E4 (0x16922E4 - 0xAB0000), slot 2 = Serialize(stream)
// = RVA 0x515540 ; octet type de connexion a +0x117 de l objet paquet (verifie en jeu).
#define NCP_VTABLE_RVA    0xBE22E4
#define NCP_SERIALIZE_RVA 0x515540
typedef uint8_t (__thiscall *NcSerialize_t)(void *self, void *stream);
static NcSerialize_t o_ncSerialize = NULL;
static uint8_t __thiscall hk_ncSerialize(void *self, void *stream);

static SendP2PPacket_t        o_send = NULL;
static IsP2PPacketAvailable_t o_avail = NULL;
static ReadP2PPacket_t        o_read = NULL;
static GetP2PSessionState_t   o_state = NULL;
static AllowP2PPacketRelay_t  o_relay = NULL;
static void *g_iface = NULL;

static FILE *g_log = NULL;
/* 0.8.6d : -DNO_LOG = build release sans journal ni live.txt (aucun fichier ecrit) ; la logique reseau est identique */
#ifdef NO_LOG
#define fopen(p, m) ((FILE *)0)
#endif
static char g_dir[MAX_PATH];
static int g_redundancy = 2, g_allowRelay = 1, g_logPackets = 0, g_packetLogMax = 3000, g_packetLogged = 0;
static CRITICAL_SECTION g_cs;

#define HELLO_CH   15
#define MAXPEER    16
#define MAXPKT     1400
#define HIST       3          // profondeur max de redondance
#define QUEUE      64         // paquets deballes en attente de lecture par le jeu
#define MAXCH      16

static const uint8_t MAGIC[8] = { 'D','5','N','B','v','1',0xA5,0x5A };
static const char HELLO[12]   = "D5NB-HELLO1";
// HELLO v2 (0.8.5) : [0..11] magic, [12] type de lien, [13] 0 = ping / 1 = pong, [14..17] horodatage
// ms de l'emetteur (renvoye tel quel dans le pong -> RTT), [18] version du plugin (5), [19] reserve.
// Les 0.8.3/0.8.4 ne lisent que [12] et ne repondent jamais : pas de ping mesure avec eux.
#define HELLO_V2_LEN 20
#define PLUGIN_VER_BYTE 7
static uint8_t g_linkType = 0;   // 0 inconnu, 1 cable (Ethernet), 2 Wi-Fi
static CSteamID g_selfId = 0;    // SteamID local (ISteamUser::GetSteamID), pour ignorer la session vers soi-meme
static const char *linkName(int t) { return t == 1 ? "CABLE" : t == 2 ? "WI-FI" : "?"; }
static void *g_friends = NULL;   // ISteamFriends (SteamFriends014) : slot 7 = GetFriendPersonaName(CSteamID)
typedef const char *(__thiscall *GetFriendPersonaName_t)(void *self, CSteamID id);
static GetFriendPersonaName_t o_personaName = NULL;   // 0.8.6b : hooke, le salon dessine les noms via cet appel (la fiche NameCard n'est pas relue)
#define GONE_MS 60000            // pair sans paquet ni session active depuis 60 s = parti : plus jamais interroge

typedef struct { uint8_t data[MAXPKT]; uint16_t len; uint32_t seq; int ch; } Pkt;

typedef struct {
    CSteamID id; int used;
    uint64_t txPk, txBy, rxPk, rxBy, txPk1, txBy1, rxPk1, rxBy1;
    uint32_t txMax, rxMax; uint64_t txType[4], chan[MAXCH];
    int lastRelay, lastActive; uint32_t lastIp; uint8_t lastErr;
    // detecteur de cause du relais : classes d'adresses vues pour ce pair
    int sawPrivate, sawCgnat, sawPublic, sawRelay, verdict;
    DWORD firstSeen, lastSeen;
    // etat de session Steam, lu UNIQUEMENT sur le thread du jeu (steam_tick) et mis en cache ici :
    // le thread stats ne doit plus jamais appeler Steam (crash 20/09 01:57, use-after-free steamclient)
    P2PSessionState_t st; int stOk; DWORD stTick; int gone;
    // fiche joueur du jeu (NameCard) : nom Steam du pair -> qualite mesuree par le jeu (+0x108), lien (+0x107)
    char name[33]; int nameTried; int quality, qualityMin, qualityMax; uint8_t ncLink;
    int self, pingShown; DWORD pingShownAt; uint32_t pingShownMs;   // 0.8.6 : (soi) ; ping ecrit dans la fiche
    // ping reel via HELLO v2 (ms)
    uint32_t rttMin, rttMax, rttLast, rttN; uint64_t rttSum; uint8_t peerVer;
    // redondance
    int boosted; DWORD lastHello; uint8_t linkType;
    uint32_t txSeq[MAXCH]; Pkt hist[MAXCH][HIST]; int histN[MAXCH];
    uint32_t rxLastSeq[MAXCH]; int rxInit[MAXCH];
    uint64_t recovered, bundlesTx, bundlesRx, dupDropped;
} Peer;
static Peer g_peers[MAXPEER];
static volatile LONG g_pollCount = 0;   // appels du jeu passes par nos hooks (sondages) depuis la derniere seconde

// File des paquets deballes, rendus au jeu par IsP2PPacketAvailable/ReadP2PPacket.
typedef struct { CSteamID id; Pkt p; } QEntry;
static QEntry g_q[QUEUE]; static int g_qHead = 0, g_qCount = 0;

static void logf_(const char *fmt, ...)
{
#ifdef NO_LOG
    return;
#endif
    if (!g_log) return;
    SYSTEMTIME st; GetLocalTime(&st);
    fprintf(g_log, "%02d:%02d:%02d.%03d ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
    va_list ap; va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
    fputc('\n', g_log); fflush(g_log);
}

static Peer *peer(CSteamID id)
{
    int i, freeIdx = -1;
    for (i = 0; i < MAXPEER; i++) {
        if (g_peers[i].used && g_peers[i].id == id) return &g_peers[i];
        if (!g_peers[i].used && freeIdx < 0) freeIdx = i;
    }
    if (freeIdx < 0) return NULL;
    Peer *p = &g_peers[freeIdx]; memset(p, 0, sizeof *p);
    p->used = 1; p->id = id; p->firstSeen = p->lastSeen = GetTickCount(); p->lastRelay = p->lastActive = -1;
    p->quality = -1; p->qualityMin = 999; p->qualityMax = -1; p->rttMin = 0xFFFFFFFFu;
    logf_("nouveau pair %llu", (unsigned long long)id);
    return p;
}
static Peer *peer_find(CSteamID id) { for (int i = 0; i < MAXPEER; i++) if (g_peers[i].used && g_peers[i].id == id) return &g_peers[i]; return NULL; }

static int q_push(CSteamID id, const uint8_t *data, uint32_t len, uint32_t seq, int ch)
{
    if (g_qCount >= QUEUE || len > MAXPKT) return 0;
    QEntry *e = &g_q[(g_qHead + g_qCount) % QUEUE];
    e->id = id; memcpy(e->p.data, data, len); e->p.len = (uint16_t)len; e->p.seq = seq; e->p.ch = ch;
    g_qCount++; return 1;
}
static QEntry *q_peek(int ch)
{
    // premier paquet en file pour ce canal (les canaux se melangent rarement : on
    // n'extrait que la tete si elle est du bon canal, sinon on cherche plus loin)
    for (int i = 0; i < g_qCount; i++) { QEntry *e = &g_q[(g_qHead + i) % QUEUE]; if (e->p.ch == ch) return e; }
    return NULL;
}
static void q_remove(QEntry *e)
{
    int idx = (int)(e - g_q); int pos = (idx - g_qHead + QUEUE) % QUEUE;
    for (int i = pos; i < g_qCount - 1; i++) g_q[(g_qHead + i) % QUEUE] = g_q[(g_qHead + i + 1) % QUEUE];
    g_qCount--;
}

// TOUT appel a Steam se fait sur le thread du jeu, a l'interieur de nos hooks (Send/Read/Avail).
// steamclient n'est pas thread-safe pour le P2P legacy : le 20/09 01:57 un GetP2PSessionState
// lance depuis le thread stats (pair parti 54 min plus tot) a saute dans un objet libere.
static void hello_send(void *self, Peer *p, uint8_t kind, uint32_t stamp)
{
    uint8_t hb[HELLO_V2_LEN]; memset(hb, 0, sizeof hb);
    memcpy(hb, HELLO, 12); hb[12] = g_linkType; hb[13] = kind; memcpy(hb + 14, &stamp, 4); hb[18] = PLUGIN_VER_BYTE;
    o_send(self, p->id, hb, sizeof hb, 0, HELLO_CH);
}
// Vide le canal HELLO a CHAQUE passage du jeu (pas 1x/s) : le pong part tout de suite, le RTT
// mesure n'inclut que la latence reseau + au plus une image de jeu.
static DWORD g_lastDrainTick = 0;
static void hello_drain(void *self)
{
    uint32_t sz; uint8_t buf[64]; uint32_t len; CSteamID id; DWORD now = GetTickCount();
    if (now == g_lastDrainTick) return;   // au plus un passage par tick systeme (~16 ms) : le jeu sonde ~1000 fois/s
    g_lastDrainTick = now;
    for (int guard = 0; guard < 32 && (o_avail(self, &sz, HELLO_CH) & 0xFF); guard++) {
        if (!(o_read(self, buf, sizeof buf, &len, &id, HELLO_CH) & 0xFF)) break;
        if (len < sizeof HELLO || memcmp(buf, HELLO, sizeof HELLO) != 0) continue;
        Peer *p = peer(id); if (!p) continue;
        uint8_t lt = len >= 13 ? buf[12] : 0;
        if (!p->boosted || lt != p->linkType) logf_("pair %llu a le plugin (connexion %s)%s", (unsigned long long)id, linkName(lt), g_redundancy > 0 ? " -> redondance ACTIVEE" : "");
        p->boosted = 1; p->linkType = lt; p->lastHello = now; p->gone = 0;
        if (len < HELLO_V2_LEN) continue;               // 0.8.3 / 0.8.4 : pas de RTT
        uint32_t stamp; memcpy(&stamp, buf + 14, 4);
        if (buf[18] && buf[18] != p->peerVer) { p->peerVer = buf[18]; logf_("pair %llu : plugin version %u (HELLO v2, ping mesurable)", (unsigned long long)id, buf[18]); }
        if (buf[13] == 0) hello_send(self, p, 1, stamp);   // ping -> pong immediat, horodatage renvoye
        else {                                               // pong -> RTT
            uint32_t rtt = now - stamp; if (rtt > 5000) continue;
            p->rttLast = rtt; p->rttN++; p->rttSum += rtt; if (rtt < p->rttMin) p->rttMin = rtt; if (rtt > p->rttMax) p->rttMax = rtt;
        }
    }
}
// 1x/s sur le thread du jeu : etat de session (cache pour le thread stats), nom Steam du pair,
// ping HELLO vers les sessions actives, detection des pairs partis.
static DWORD g_lastSteamTick = 0;
static void steam_tick(void *self)
{
    InterlockedIncrement(&g_pollCount);
    hello_drain(self);
    DWORD now = GetTickCount();
    if (now - g_lastSteamTick < 1000) return;
    g_lastSteamTick = now;
    for (int i = 0; i < MAXPEER; i++) {
        Peer *p = &g_peers[i]; if (!p->used || p->gone) continue;
        P2PSessionState_t st; memset(&st, 0, sizeof st);
        int ok = o_state ? (o_state(self, p->id, &st) & 0xFF) : 0;
        p->st = st; p->stOk = ok; p->stTick = now;
        if (ok && st.active) p->lastActive = 1; else if (ok) p->lastActive = 0;
        if (!p->name[0] && !p->nameTried && g_friends) {
            const char *n = (o_personaName ? o_personaName : (GetFriendPersonaName_t)(*(void ***)g_friends)[7])(g_friends, p->id);
            if (n && n[0] && strcmp(n, "[unknown]")) { strncpy(p->name, n, 32); p->name[32] = 0; if (g_persona[0] && !strcmp(p->name, g_persona)) { p->self = 1; logf_("pair %llu : c'est notre propre session (nom Steam identique) -> (soi)", (unsigned long long)p->id); } }
            else if (now - p->firstSeen > 30000) p->nameTried = 1;
        }
        if (!(ok && st.active)) {
            if (now - p->lastSeen > GONE_MS && !(ok && st.connecting)) { p->gone = 1; p->boosted = 0; logf_("pair %llu parti (aucun paquet depuis %lu s, session inactive) : plus interroge", (unsigned long long)p->id, (unsigned long)((now - p->lastSeen) / 1000)); }
            continue;
        }
        // La poignee de main (type de connexion + ping) est toujours envoyee ; seule la
        // redondance depend du reglage Redundancy.
        hello_send(self, p, 0, now);
        if (p->boosted && now - p->lastHello > 6000) { p->boosted = 0; logf_("pair %llu : plus de HELLO, redondance coupee", (unsigned long long)p->id); }
    }
}

// ---- envoi ----------------------------------------------------------------
static int g_firstSend = 0, g_firstAvail = 0;
static int __thiscall hk_send(void *self, CSteamID id, const void *data, uint32_t len, int sendType, int channel)
{
    int r;
    EnterCriticalSection(&g_cs);
    if (!g_firstSend) { g_firstSend = 1; logf_("premier SendP2PPacket (self=%p ch%d type%d %u o)", self, channel, sendType, len); }
    if (sendType >= 2) namecard_fix();   // fiche corrigee AVANT tout envoi fiable (NameCard part a l'entree du salon)
    if (channel != HELLO_CH) steam_tick(self);
    Peer *p = peer(id);
    int bundle = p && p->boosted && g_redundancy > 0 && (sendType == 0 || sendType == 1) && channel >= 0 && channel < MAXCH && len <= 700;
    if (bundle) {
        static uint8_t buf[8 + 4 + 2 + 2 + 2 + MAXPKT + HIST * (4 + 2 + MAXPKT)];
        uint32_t seq = ++p->txSeq[channel]; size_t o = 0;
        memcpy(buf + o, MAGIC, 8); o += 8;
        memcpy(buf + o, &seq, 4); o += 4;
        uint16_t l16 = (uint16_t)len; memcpy(buf + o, &l16, 2); o += 2;
        int n = p->histN[channel]; if (n > g_redundancy) n = g_redundancy;
        uint16_t n16 = (uint16_t)n; memcpy(buf + o, &n16, 2); o += 2;
        memcpy(buf + o, data, len); o += len;
        for (int i = 0; i < n; i++) {           // du plus recent au plus ancien
            Pkt *h = &p->hist[channel][i];
            memcpy(buf + o, &h->seq, 4); o += 4; memcpy(buf + o, &h->len, 2); o += 2; memcpy(buf + o, h->data, h->len); o += h->len;
        }
        r = o_send(self, id, buf, (uint32_t)o, sendType, channel);
        // historique : decaler et inserer le courant en tete
        for (int i = HIST - 1; i > 0; i--) p->hist[channel][i] = p->hist[channel][i - 1];
        memcpy(p->hist[channel][0].data, data, len); p->hist[channel][0].len = (uint16_t)len; p->hist[channel][0].seq = seq;
        if (p->histN[channel] < HIST) p->histN[channel]++;
        p->bundlesTx++;
    } else {
        r = o_send(self, id, data, len, sendType, channel);
    }
    if (p) {
        p->txPk++; p->txBy += len; p->lastSeen = GetTickCount(); if (len > p->txMax) p->txMax = len;
        if (sendType >= 0 && sendType < 4) p->txType[sendType]++;
        if (channel >= 0 && channel < MAXCH) p->chan[channel]++;
        if (g_logPackets && g_packetLogged < g_packetLogMax) { g_packetLogged++; logf_("TX %llu ch%d type%d %u o%s", (unsigned long long)id, channel, sendType, len, bundle ? " [bundle]" : ""); }
    }
    LeaveCriticalSection(&g_cs);
    return r;
}

// ---- reception : lecture anticipee + deballage --------------------------------
// Lit un paquet Steam du canal `ch`, le deballe si c'est un bundle, et met en file
// ce qui doit etre rendu au jeu. Retourne 1 si quelque chose a ete mis en file.
static int pull_one(void *self, int ch)
{
    static uint8_t tmp[16384]; uint32_t len = 0; CSteamID id = 0;
    if (!o_read(self, tmp, sizeof tmp, &len, &id, ch)) return 0;
    Peer *p = peer(id);
    if (p) { p->rxPk++; p->rxBy += len; p->lastSeen = GetTickCount(); if (len > p->rxMax) p->rxMax = len; }
    if (len >= 16 && memcmp(tmp, MAGIC, 8) == 0 && p && ch < MAXCH) {
        p->bundlesRx++;
        size_t o = 8; uint32_t seq; uint16_t lcur, n;
        memcpy(&seq, tmp + o, 4); o += 4; memcpy(&lcur, tmp + o, 2); o += 2; memcpy(&n, tmp + o, 2); o += 2;
        if (o + lcur > len) { logf_("bundle corrompu (pair %llu)", (unsigned long long)id); return 0; }
        const uint8_t *cur = tmp + o; o += lcur;
        // precedents : les rendre d'abord (dans l'ordre) s'ils ont ete manques
        uint32_t pseq[HIST]; uint16_t plen[HIST]; const uint8_t *pdat[HIST]; int pn = 0;
        for (int i = 0; i < n && i < HIST; i++) {
            if (o + 6 > len) break;
            memcpy(&pseq[i], tmp + o, 4); o += 4; memcpy(&plen[i], tmp + o, 2); o += 2;
            if (o + plen[i] > len) break;
            pdat[i] = tmp + o; o += plen[i]; pn++;
        }
        int pushed = 0;
        for (int i = pn - 1; i >= 0; i--) {   // du plus ancien au plus recent
            if (!p->rxInit[ch] || (int32_t)(pseq[i] - p->rxLastSeq[ch]) > 0) {
                if (p->rxInit[ch]) { p->recovered++; logf_("paquet %u recupere via redondance (pair %llu, ch%d)", pseq[i], (unsigned long long)id, ch); }
                q_push(id, pdat[i], plen[i], pseq[i], ch); p->rxLastSeq[ch] = pseq[i]; p->rxInit[ch] = 1; pushed++;
            }
        }
        if (!p->rxInit[ch] || (int32_t)(seq - p->rxLastSeq[ch]) > 0) { q_push(id, cur, lcur, seq, ch); p->rxLastSeq[ch] = seq; p->rxInit[ch] = 1; pushed++; }
        else p->dupDropped++;
        if (g_logPackets && g_packetLogged < g_packetLogMax) { g_packetLogged++; logf_("RX %llu ch%d %u o [bundle seq %u, +%d anciens, %d rendus]", (unsigned long long)id, ch, len, seq, pn, pushed); }
        return pushed > 0;
    }
    if (g_logPackets && g_packetLogged < g_packetLogMax) { g_packetLogged++; logf_("RX %llu ch%d %u o", (unsigned long long)id, ch, len); }
    return q_push(id, tmp, len, 0, ch);
}

static int __thiscall hk_avail(void *self, uint32_t *outLen, int channel)
{
    EnterCriticalSection(&g_cs);
    if (!g_firstAvail) { g_firstAvail = 1; logf_("premier IsP2PPacketAvailable (self=%p ch%d)", self, channel); }
    if (channel != HELLO_CH) steam_tick(self);
    if (g_redundancy <= 0) {   // mode stats seules : simple passage, le hook ne sert qu'a vider le canal HELLO a chaque image
        LeaveCriticalSection(&g_cs);
        return o_avail(self, outLen, channel) & 0xFF;
    }
    QEntry *e = q_peek(channel);
    if (!e) {
        uint32_t sz = 0;
        for (int guard = 0; guard < 64 && o_avail(self, &sz, channel); guard++) { if (pull_one(self, channel)) break; }
        e = q_peek(channel);
    }
    int r = e != NULL; if (r && outLen) *outLen = e->p.len;
    LeaveCriticalSection(&g_cs);
    return r;
}

static int __thiscall hk_read(void *self, void *dest, uint32_t cap, uint32_t *outLen, CSteamID *outId, int channel)
{
    if (g_redundancy <= 0) {   // mode stats seules : identique a NetProbe (valide en jeu)
        int r = o_read(self, dest, cap, outLen, outId, channel) & 0xFF;
        if (r && outLen && outId) {
            EnterCriticalSection(&g_cs);
            if (channel != HELLO_CH) steam_tick(self);
            Peer *p = peer(*outId);
            if (p) { p->rxPk++; p->rxBy += *outLen; p->lastSeen = GetTickCount(); if (*outLen > p->rxMax) p->rxMax = *outLen; }
            LeaveCriticalSection(&g_cs);
        }
        return r;
    }
    EnterCriticalSection(&g_cs);
    QEntry *e = q_peek(channel);
    if (!e) {
        uint32_t sz = 0;
        for (int guard = 0; guard < 64 && o_avail(self, &sz, channel); guard++) { if (pull_one(self, channel)) break; }
        e = q_peek(channel);
    }
    int r = 0;
    if (e) {
        uint32_t n = e->p.len < cap ? e->p.len : cap;
        memcpy(dest, e->p.data, n); if (outLen) *outLen = e->p.len; if (outId) *outId = e->id;
        q_remove(e); r = 1;
    }
    LeaveCriticalSection(&g_cs);
    return r;
}

// ---- poignee de main + statistiques ----------------------------------------------
static const char *errName(uint8_t e)
{
    switch (e) { case 0: return "ok"; case 1: return "pas de droits/jeu"; case 2: return "pair hors ligne"; case 3: return "expire"; case 4: return "pas de connexion"; case 5: return "NAT"; default: return "?"; }
}

// ---- detecteur de cause du relais ------------------------------------------------
// Classe une adresse IPv4 (ordre hote) : 1 = privee (LAN), 2 = CGNAT 100.64.0.0/10,
// 3 = relais Valve (155.133.x / 162.254.x / 146.66.x / 185.25.18x / 205.196.6.x), 4 = publique.
static int ipClass(uint32_t ip)
{
    uint8_t a = ip >> 24, b = (ip >> 16) & 255;
    if (ip == 0) return 0;
    if (a == 10 || (a == 172 && b >= 16 && b <= 31) || (a == 192 && b == 168) || a == 127 || (a == 169 && b == 254)) return 1;
    if (a == 100 && b >= 64 && b <= 127) return 2;
    if (a == 155 && b == 133) return 3; if (a == 162 && b == 254) return 3; if (a == 146 && b == 66) return 3;
    if (a == 185 && (b == 25)) return 3; if (a == 205 && b == 196) return 3;
    return 4;
}
static const char *ipClassName(int c)
{
    switch (c) { case 1: return "LAN privee"; case 2: return "CGNAT operateur"; case 3: return "relais Valve"; case 4: return "publique"; default: return "aucune"; }
}
// Emet une fois par pair, des que la session est active (ou apres 15 s), la cause probable.
static void relay_verdict(Peer *p, const P2PSessionState_t *st)
{
    int c = ipClass(st->ip);
    if (c == 1) p->sawPrivate = 1; else if (c == 2) p->sawCgnat = 1; else if (c == 3) p->sawRelay = 1; else if (c == 4) p->sawPublic = 1;
    // 1 = direct, 2 = relais (cause autre), 3 = relais cause CGNAT. Le CGNAT apparait souvent
    // apres coup (Steam reessaie les candidats a la fin) -> on corrige le verdict dans ce cas.
    if (p->verdict == 3 || p->verdict == 1) return;
    if (p->verdict == 2 && !p->sawCgnat) return;
    if (!p->verdict && !st->active && (GetTickCount() - p->firstSeen) < 15000) return;
    const char *v; int kind;
    if (p->verdict == 2 && p->sawCgnat) { v = "MISE A JOUR -> RELAIS FORCE : adresse CGNAT (100.64-127.x) vue chez le pair : NAT d'operateur, Steam ne peut pas percer. A corriger chez lui (IP publique aupres du FAI)"; kind = 3; }
    else if (!st->relay)                  { v = "DIRECT : connexion pair a pair, rien a signaler"; kind = 1; }
    else if (p->sawCgnat)                 { v = "RELAIS FORCE : le pair est derriere un NAT d'operateur (CGNAT, IP 100.64-127.x) -> Steam ne peut pas percer, lag = detour par le relais Valve. A corriger chez lui (IP publique aupres du FAI)"; kind = 3; }
    else if (p->sawPrivate && !p->sawPublic) { v = "RELAIS FORCE : le pair n'annonce qu'une adresse LAN privee (double NAT / UPnP coupe chez lui)"; kind = 2; }
    else if (p->sawPublic)                { v = "RELAIS : le pair a une IP publique mais le percage NAT a echoue (pare-feu ou NAT strict, chez lui ou ici) - a retester"; kind = 2; }
    else                                  { v = "RELAIS : cause indeterminee (aucune adresse du pair vue)"; kind = 2; }
    p->verdict = kind;
    logf_("pair %llu : VERDICT -> %s [adresses vues : %s%s%s%s]", (unsigned long long)p->id, v,
          p->sawPrivate ? "LAN " : "", p->sawCgnat ? "CGNAT " : "", p->sawPublic ? "publique " : "", p->sawRelay ? "relais-Valve " : "");
}

// Qualite de connexion mesuree par le jeu pour ce pair : entree NameCard dont le nom = nom Steam du pair.
// Lecture memoire seule (pas d'appel Steam), tolerante : la fiche peut etre reecrite pendant la lecture.
static void namecard_peer_quality(Peer *p)
{
    if (!g_ncMgr || !p->name[0] || g_pingDisplay == 2) return;
    for (int i = 0; i < 16; i++) {
        uint8_t *e = g_ncMgr + 0xDC + i * 0x10C;
        int32_t key = *(int32_t *)e; if (key < 0 || key > 15) continue;
        size_t nl = strlen(p->name); if (strncmp((const char *)e + 0xE4, p->name, nl) != 0 || (e[0xE4 + nl] != 0 && e[0xE4 + nl] != ' ')) continue;   // nom exact ou nom + " 45ms"
        int q = *(int32_t *)(e + 0x108); if (q < 0 || q > 255) q = e[0x108];
        if (q != p->quality) { if (p->quality >= 0) logf_("pair %llu : qualite (jeu) %d -> %d", (unsigned long long)p->id, p->quality, q); p->quality = q; }
        if (q < p->qualityMin) p->qualityMin = q; if (q > p->qualityMax) p->qualityMax = q;
        p->ncLink = e[0x107];
        return;
    }
}
static const char *verdictName(int v) { return v == 1 ? "DIRECT" : v == 3 ? "RELAIS-CGNAT" : v == 2 ? "RELAIS-AUTRE" : "?"; }

static DWORD WINAPI stats_thread(LPVOID unused)
{
    char livePath[MAX_PATH]; snprintf(livePath, sizeof livePath, "%sDOA5LR-WiFi-Wired-Detector-live.txt", g_dir);
    for (;;) {
        for (int k = 0; k < 5; k++) { Sleep(200); namecard_fix(); EnterCriticalSection(&g_cs); namecard_ping_show(); LeaveCriticalSection(&g_cs); }
        LONG polls = InterlockedExchange(&g_pollCount, 0);
        EnterCriticalSection(&g_cs);
        FILE *live = fopen(livePath, "w");
        if (live) fprintf(live, "DOA5LR NetBoost — redondance=%d relais autorise=%d | version=0.8.8 lien=%s sondages/s=%ld\n", g_redundancy, g_allowRelay, linkName(g_linkType), (long)polls);
        for (int i = 0; i < MAXPEER; i++) {
            Peer *p = &g_peers[i]; if (!p->used) continue;
            // etat de session : cache rempli par steam_tick (thread du jeu). Jamais d'appel Steam ici.
            P2PSessionState_t st = p->st; int ok = p->stOk && (GetTickCount() - p->stTick) < 10000;
            uint64_t txPk = p->txPk - p->txPk1, txBy = p->txBy - p->txBy1, rxPk = p->rxPk - p->rxPk1, rxBy = p->rxBy - p->rxBy1;
            p->txPk1 = p->txPk; p->txBy1 = p->txBy; p->rxPk1 = p->rxPk; p->rxBy1 = p->rxBy;
            char ip[32]; snprintf(ip, sizeof ip, "%u.%u.%u.%u:%u", (st.ip >> 24) & 255, (st.ip >> 16) & 255, (st.ip >> 8) & 255, st.ip & 255, st.port);
            if (ok && (st.relay != p->lastRelay || st.active != p->lastActive || st.ip != p->lastIp || st.error != p->lastErr)) {
                logf_("pair %llu : %s, %s, distant %s, erreur=%s", (unsigned long long)p->id,
                      st.active ? "session ACTIVE" : (st.connecting ? "connexion..." : "inactive"), st.relay ? "via RELAIS Valve" : "DIRECT", ip, errName(st.error));
                p->lastRelay = st.relay; p->lastActive = st.active; p->lastIp = st.ip; p->lastErr = st.error;
            }
            if (ok) relay_verdict(p, &st);
            namecard_peer_quality(p);
            int idle = (GetTickCount() - p->lastSeen) > 5000;
            if (!idle) {
                char ping[64] = "";
                if (p->rttN) snprintf(ping, sizeof ping, " | ping %u ms (min %u moy %u max %u)", p->rttLast, p->rttMin, (unsigned)(p->rttSum / p->rttN), p->rttMax);
                logf_("pair %llu : TX %llu pk/s %llu o/s | RX %llu pk/s %llu o/s | attente %d o / %d pk | %s%s | recuperes %llu%s",
                      (unsigned long long)p->id, (unsigned long long)txPk, (unsigned long long)txBy, (unsigned long long)rxPk, (unsigned long long)rxBy,
                      st.bytesQueued, st.packetsQueued, st.relay ? "relais" : "direct", p->boosted ? " +plugin" : "", (unsigned long long)p->recovered, ping);
            }
            if (live) {
                // Format lu par DOA5LR-Telemetry : champs "| cle valeur" stables, ne pas renommer sans mettre a jour telemetry.c
                fprintf(live, "pair %llu %s | %s %s [%s%s] | %s | TX %llu pk/s %llu o/s (max %u) | RX %llu pk/s %llu o/s (max %u) | attente %d o/%d pk | bundles TX %llu RX %llu | recuperes %llu doublons %llu",
                        (unsigned long long)p->id, p->self ? "(soi)" : p->gone ? "(parti)" : idle ? "(inactif)" : "(actif)", st.relay ? "RELAIS" : "DIRECT", ip, ipClassName(ipClass(st.ip)), (st.relay && p->sawCgnat) ? ", pair derriere CGNAT" : (st.relay && p->sawPrivate && !p->sawPublic) ? ", pair en LAN seul" : "",
                        p->boosted ? (p->linkType == 2 ? "PLUGIN, WI-FI" : p->linkType == 1 ? "PLUGIN, CABLE" : "PLUGIN") : "sans plugin",
                        (unsigned long long)txPk, (unsigned long long)txBy, p->txMax, (unsigned long long)rxPk, (unsigned long long)rxBy, p->rxMax,
                        st.bytesQueued, st.packetsQueued, (unsigned long long)p->bundlesTx, (unsigned long long)p->bundlesRx, (unsigned long long)p->recovered, (unsigned long long)p->dupDropped);
                fprintf(live, " | verdict %s | qualite %d (min %d max %d) | ping %d/%d/%d ms dernier %d n=%u | plugin-pair %u | session %s",
                        verdictName(p->verdict), p->quality, p->qualityMax < 0 ? -1 : p->qualityMin, p->qualityMax,
                        p->rttN ? (int)p->rttMin : -1, p->rttN ? (int)(p->rttSum / p->rttN) : -1, p->rttN ? (int)p->rttMax : -1, p->rttN ? (int)p->rttLast : -1, p->rttN, p->peerVer,
                        !ok ? "?" : st.active ? "active" : st.connecting ? "connexion" : "inactive");
                fprintf(live, " | canaux:");
                for (int c = 0; c < MAXCH; c++) if (p->chan[c]) fprintf(live, " ch%d=%llu", c, (unsigned long long)p->chan[c]);
                fputc('\n', live);
            }
        }
        if (live) fclose(live);
        LeaveCriticalSection(&g_cs);
    }
    return 0;
}

#define SEEN_MAX 256
static char g_seen[SEEN_MAX][128]; static int g_seenN = 0;
static void note_kv(const char *what, const char *key, const char *value)
{
    char line[128]; snprintf(line, sizeof line, "%s %s=%s", what, key ? key : "(null)", value ? value : "(null)");
    EnterCriticalSection(&g_cs);
    int found = 0; for (int i = 0; i < g_seenN; i++) if (!strcmp(g_seen[i], line)) { found = 1; break; }
    if (!found && g_seenN < SEEN_MAX) { strcpy(g_seen[g_seenN++], line); logf_("LOBBY %s", line); }
    LeaveCriticalSection(&g_cs);
}
static uint8_t __thiscall hk_setLobbyData(void *self, CSteamID lobby, const char *key, const char *value)
{ note_kv("SetLobbyData", key, value); return o_setLobbyData(self, lobby, key, value) & 0xFF; }
static void __thiscall hk_setMemberData(void *self, CSteamID lobby, const char *key, const char *value)
{ note_kv("SetLobbyMemberData", key, value); o_setMemberData(self, lobby, key, value); }
static const char *__thiscall hk_getMemberData(void *self, CSteamID lobby, CSteamID user, const char *key)
{ const char *v = o_getMemberData(self, lobby, user, key); char k[96]; snprintf(k, sizeof k, "%s[%llu]", key ? key : "(null)", (unsigned long long)user); note_kv("GetLobbyMemberData", k, v); return v; }
static const char *__thiscall hk_getLobbyData(void *self, CSteamID lobby, const char *key)
{ const char *v = o_getLobbyData(self, lobby, key); note_kv("GetLobbyData", key, v); return v; }

static uint8_t want_link(void) { return g_linkOverride ? (uint8_t)g_linkOverride : (g_linkType == 2 ? 2 : 1); }
// Corrige l'octet type de connexion dans le paquet NameCard au moment ou le jeu le serialise :
// quel que soit le moment de l'envoi, ce qui part sur le reseau est juste.
static uint8_t __thiscall hk_ncSerialize(void *self, void *stream)
{
    uint8_t *pkt = (uint8_t *)self; uint8_t want = want_link();   // VERIFIE EN JEU : +0x117 (v0.8.1 affichait <n>, +0x113 en v0.8.2 non)
    if (pkt[0x117] != want) { logf_("NameCardPacket : type de connexion %d -> %d a l'envoi", pkt[0x117], want); pkt[0x117] = want; }
    return o_ncSerialize(self, stream) & 0xFF;
}

static void namecard_fix(void)
{
    if (!g_ncMgr || !g_persona[0]) return;
    uint8_t want = g_linkOverride ? (uint8_t)g_linkOverride : (g_linkType == 2 ? 2 : 1);
    if (want == 1) return;   // cable : valeur d'origine du jeu, rien a faire
    for (int i = 0; i < 16; i++) {
        uint8_t *e = g_ncMgr + 0xDC + i * 0x10C;
        int32_t key = *(int32_t *)e; if (key < 0 || key > 15) continue;
        if (strncmp((const char *)e + 0xE4, g_persona, 32) != 0) continue;
        if (e[0x107] != want) { e[0x107] = want; g_ncPatched++; logf_("fiche locale (entree %d, '%s') : type de connexion -> %d (%s)", i, g_persona, want, want == 2 ? "sans fil <n>" : "cable [n]"); }
    }
}

// 0.8.6 : ping en ms dans la fiche du pair (lecture memoire + ecriture de 35 octets, jamais d'appel Steam).
// Mode 1 : nom "<pseudo> 45ms" (champ +0xE4, 34 caracteres max, le NUL final a +0x106 est conserve, +0x107 intact).
// Mode 2 : RTT dans le champ qualite +0x108 (int32). Rafraichi au plus 1x/s par pair, seulement si la valeur change.
static void namecard_ping_show(void)
{
    if (!g_ncMgr || !g_pingDisplay) return;
    DWORD now = GetTickCount();
    for (int i = 0; i < MAXPEER; i++) {
        Peer *p = &g_peers[i];
        if (!p->used || p->gone || !p->rttN || !p->name[0]) continue;
        if (p->self && !g_pingDisplaySelf) continue;
        uint32_t ms = p->rttLast; if (ms > 999) ms = 999;
        if (p->pingShown && ms == p->pingShownMs) continue;
        if (p->pingShown && now - p->pingShownAt < 1000) continue;
        size_t nl = strlen(p->name);
        for (int k = 0; k < 16; k++) {
            uint8_t *e = g_ncMgr + 0xDC + k * 0x10C;
            int32_t key = *(int32_t *)e; if (key < 0 || key > 15) continue;
            if (strncmp((const char *)e + 0xE4, p->name, nl) != 0 || (e[0xE4 + nl] != 0 && e[0xE4 + nl] != ' ')) continue;
            if (g_pingDisplay == 2) { *(int32_t *)(e + 0x108) = (int32_t)ms; }
            else {
                char field[35]; char suf[8]; snprintf(suf, sizeof suf, " %ums", (unsigned)ms);
                size_t keep = nl; if (keep + strlen(suf) > 34) keep = 34 - strlen(suf);
                memset(field, 0, sizeof field); memcpy(field, p->name, keep); memcpy(field + keep, suf, strlen(suf));
                memcpy(e + 0xE4, field, sizeof field);   // 0xE4..0x106 : nom + NUL
            }
            if (!p->pingShown) logf_("fiche pair %llu ('%s', entree %d) : ping ecrit (%s, %u ms)%s", (unsigned long long)p->id, p->name, k, g_pingDisplay == 2 ? "champ qualite" : "suffixe du nom", (unsigned)ms, p->self ? " [soi, test]" : "");
            p->pingShown = 1; p->pingShownAt = now; p->pingShownMs = ms;
            break;
        }
    }
}

// GetFriendPersonaName hooke : le jeu l'appelle pour afficher la liste du salon. Pour un pair equipe (RTT connu,
// pas parti ; soi seulement si PingDisplaySelf), on renvoie "<nom> 45ms" (tampon statique par pair, thread du jeu).
static char g_dispName[MAXPEER][64];
// GetPersonaName (slot 0, nom du joueur LOCAL) : hooke seulement en mode test PingDisplaySelf=1, pour verifier seul
// dans un salon que la liste passe bien par ISteamFriends (le jeu lit son propre nom par cet appel, pas par slot 7).
typedef const char *(__thiscall *GetPersonaName_t)(void *self);
static GetPersonaName_t o_getPersonaName = NULL; static char g_selfDisp[64];
static const char *__thiscall hk_getPersonaName(void *self)
{
    const char *n = o_getPersonaName(self);
    if (!g_pingDisplay || !g_pingDisplaySelf || !n || !n[0]) return n;
    for (int i = 0; i < MAXPEER; i++) { Peer *p = &g_peers[i]; if (p->used && p->self && p->rttN && !p->gone) { snprintf(g_selfDisp, sizeof g_selfDisp, "%.40s %ums", n, (unsigned)(p->rttLast > 999 ? 999 : p->rttLast)); return g_selfDisp; } }
    return n;
}
static const char *__thiscall hk_personaName(void *self, CSteamID id)
{
    const char *n = o_personaName(self, id);
    if (!g_pingDisplay || !n || !n[0]) return n;
    Peer *p = peer_find(id);
    if (!p || p->gone || !p->rttN || (p->self && !g_pingDisplaySelf)) return n;
    uint32_t ms = p->rttLast; if (ms > 999) ms = 999;
    char *d = g_dispName[p - g_peers];
    snprintf(d, 64, "%.40s %ums", n, (unsigned)ms);
    return d;
}

static int patch_slot(void **vt, int slot, void *hook, void **orig)
{
    DWORD old;
    if (!VirtualProtect(&vt[slot], sizeof(void *), PAGE_EXECUTE_READWRITE, &old)) return 0;
    *orig = vt[slot]; vt[slot] = hook;
    VirtualProtect(&vt[slot], sizeof(void *), old, &old);
    return 1;
}

static DWORD WINAPI worker(LPVOID unused)
{
    char path[MAX_PATH];
    snprintf(path, sizeof path, "%sDOA5LR-WiFi-Wired-Detector.log", g_dir);
    g_log = fopen(path, "a");
    snprintf(path, sizeof path, "%sDOA5LR-WiFi-Wired-Detector.ini", g_dir);
    g_redundancy = GetPrivateProfileIntA("NetBoost", "Redundancy", 0, path);
    if (g_redundancy < 0) g_redundancy = 0; if (g_redundancy > HIST) g_redundancy = HIST;
    g_allowRelay = GetPrivateProfileIntA("NetBoost", "AllowRelay", 1, path);
    g_logPackets = GetPrivateProfileIntA("NetBoost", "LogPackets", 0, path);
    g_lobbyProbe = GetPrivateProfileIntA("NetBoost", "LobbyProbe", 0, path);
    g_linkOverride = GetPrivateProfileIntA("NetBoost", "LinkOverride", 0, path);
    if (g_linkOverride != 2) { if (g_linkOverride) logf_("LinkOverride=%d ignore (0.8.8 : seul 2 = forcer sans fil existe encore, jamais forcer cable)", g_linkOverride); g_linkOverride = 0; }
    g_pingDisplay = 0; g_pingDisplaySelf = 0;   // 0.8.7 : plus lus dans l'ini, affichage du ping retire
    g_packetLogMax = GetPrivateProfileIntA("NetBoost", "PacketLogMax", 3000, path);
    {   // type de connexion locale : carte active qui porte une passerelle par defaut
        ULONG sz = 0; GetAdaptersAddresses(AF_INET, GAA_FLAG_INCLUDE_GATEWAYS, NULL, NULL, &sz);
        IP_ADAPTER_ADDRESSES *aa = (IP_ADAPTER_ADDRESSES *)malloc(sz);
        if (aa && GetAdaptersAddresses(AF_INET, GAA_FLAG_INCLUDE_GATEWAYS, NULL, aa, &sz) == NO_ERROR) {
            for (IP_ADAPTER_ADDRESSES *a = aa; a; a = a->Next) {
                if (a->OperStatus != IfOperStatusUp || !a->FirstGatewayAddress) continue;
                if (a->IfType == IF_TYPE_IEEE80211) { g_linkType = 2; break; }
                if (a->IfType == IF_TYPE_ETHERNET_CSMACD) { g_linkType = 1; }
            }
        }
        free(aa);
    }
    logf_("connexion locale : %s", linkName(g_linkType));
    logf_("=== NetBoost v0.8.8 demarre (Redundancy=%d AllowRelay=%d LogPackets=%d PingDisplay=%d PingDisplaySelf=%d)", g_redundancy, g_allowRelay, g_logPackets, g_pingDisplay, g_pingDisplaySelf);
    for (int tries = 0; tries < 1200 && !g_iface; tries++) {
        HMODULE m = GetModuleHandleA("steam_api.dll");
        if (m) { SteamNetworking_t acc = (SteamNetworking_t)GetProcAddress(m, "SteamNetworking"); if (acc) g_iface = acc(); }
        if (!g_iface) Sleep(500);
    }
    if (!g_iface) { logf_("ISteamNetworking introuvable, abandon"); return 0; }
    void **vt = *(void ***)g_iface;
    logf_("ISteamNetworking = %p, vtable = %p", g_iface, vt);
    o_state = (GetP2PSessionState_t)vt[6];
    o_relay = (AllowP2PPacketRelay_t)vt[7];
    o_avail = (IsP2PPacketAvailable_t)vt[1];
    if (!patch_slot(vt, 0, (void *)hk_send, (void **)&o_send) || !patch_slot(vt, 2, (void *)hk_read, (void **)&o_read)) { logf_("patch vtable impossible"); return 0; }
    // IsP2PPacketAvailable toujours hooke (0.8.5) : en mode stats seules c'est un simple passage qui
    // sert a vider le canal HELLO a chaque image (pong immediat = ping precis)
    if (!patch_slot(vt, 1, (void *)hk_avail, (void **)&o_avail)) { logf_("patch IsP2PPacketAvailable impossible"); return 0; }
    logf_("hooks poses (SendP2PPacket, ReadP2PPacket, IsP2PPacketAvailable%s)", g_redundancy > 0 ? "" : " ; stats seules");
    {   // fiche joueur : verification de version + nom Steam local
        uint8_t *gameBase = (uint8_t *)GetModuleHandleA(NULL);
        // le .text est dechiffre par le stub Steam apres le chargement des DLL : on attend
        int okv = 0;
        for (int tries = 0; tries < 240 && !(okv = memcmp(gameBase + NC_CHECK_RVA, NC_CHECK, 16) == 0); tries++) Sleep(500);
        if (okv) {
            g_ncMgr = gameBase + NC_MGR_RVA;
            HMODULE m2 = GetModuleHandleA("steam_api.dll");
            SteamNetworking_t accF = m2 ? (SteamNetworking_t)GetProcAddress(m2, "SteamFriends") : NULL;
            void *fr = accF ? accF() : NULL;
            if (fr) { typedef const char *(__thiscall *GetPersonaName_t)(void *); const char *n = ((GetPersonaName_t)(*(void ***)fr)[0])(fr); if (n) { strncpy(g_persona, n, 63); g_persona[63] = 0; } g_friends = fr; }
            logf_("fiche joueur : gestionnaire %p, nom Steam '%s', LinkOverride=%d", g_ncMgr, g_persona, g_linkOverride);
            if (fr && g_pingDisplay) {   // 0.8.6b : le salon affiche les noms via GetFriendPersonaName -> hook (slot 7 de SteamFriends014)
                if (patch_slot(*(void ***)fr, 7, (void *)hk_personaName, (void **)&o_personaName)) logf_("hook ISteamFriends::GetFriendPersonaName pose (ping dans le nom)");
                else logf_("hook GetFriendPersonaName impossible");
                if (g_pingDisplaySelf && patch_slot(*(void ***)fr, 0, (void *)hk_getPersonaName, (void **)&o_getPersonaName)) logf_("hook ISteamFriends::GetPersonaName pose (TEST : ping dans SON propre nom)");
            }
            void **ncvt = (void **)(gameBase + NCP_VTABLE_RVA);
            if (ncvt[2] == (void *)(gameBase + NCP_SERIALIZE_RVA)) {
                if (patch_slot(ncvt, 2, (void *)hk_ncSerialize, (void **)&o_ncSerialize)) logf_("hook NameCardPacket::Serialize pose");
                else logf_("hook NameCardPacket::Serialize impossible");
            } else logf_("vtable NameCardPacket inattendue (%p), hook non pose", ncvt[2]);
        } else logf_("fiche joueur : version du jeu inattendue, correction du type de connexion desactivee");
    }
    if (g_lobbyProbe) {
        HMODULE m = GetModuleHandleA("steam_api.dll");
        SteamNetworking_t accMM = m ? (SteamNetworking_t)GetProcAddress(m, "SteamMatchmaking") : NULL;
        void *mm = accMM ? accMM() : NULL;
        if (mm) {
            void **mvt = *(void ***)mm;   // SteamMatchMaking009 : 19 GetLobbyData, 20 SetLobbyData, 24 GetLobbyMemberData, 25 SetLobbyMemberData
            int ok = patch_slot(mvt, 19, (void *)hk_getLobbyData, (void **)&o_getLobbyData) && patch_slot(mvt, 20, (void *)hk_setLobbyData, (void **)&o_setLobbyData)
                  && patch_slot(mvt, 24, (void *)hk_getMemberData, (void **)&o_getMemberData) && patch_slot(mvt, 25, (void *)hk_setMemberData, (void **)&o_setMemberData);
            logf_("sonde salon (ISteamMatchmaking %p) : %s", mm, ok ? "posee" : "ECHEC");
        } else logf_("ISteamMatchmaking introuvable, sonde salon inactive");
    }
    if (!g_allowRelay && o_relay) { o_relay(g_iface, 0); logf_("AllowP2PPacketRelay(false) demande"); }
    HANDLE t = CreateThread(NULL, 0, stats_thread, NULL, 0, NULL); if (t) CloseHandle(t);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        InitializeCriticalSection(&g_cs);
        GetModuleFileNameA(h, g_dir, sizeof g_dir);
        char *s = strrchr(g_dir, '\\'); if (s) s[1] = 0;
        HANDLE t = CreateThread(NULL, 0, worker, NULL, 0, NULL); if (t) CloseHandle(t);
    }
    return TRUE;
}
