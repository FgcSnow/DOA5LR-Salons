// DOA5LR — reprise en main d un replay (« replay takeover »).
//
//   L2 / F5 pendant un replay     : prendre la main ; si les deux joueurs sont humains,
//                                   une fenetre (combat fige) propose P1 ou P2
//                                   (L2 valide, Start annule).
//   Select / F5 pendant la reprise: revenir instantanement a l instant de la reprise
//                                   (point de controle) et garder la main.
//   Start / F6 pendant la reprise : revenir a l instant de la reprise et rendre la main ;
//                                   le replay reprend normalement a partir de la.
//   Pendant la reprise, L2 va au combattant (il peut servir au combat) ; Start et Select
//   ne vont ni au combattant ni a l interface du replay (menu, masquage des barres).
//   En dehors de la reprise, Start et Select gardent leur role normal dans le replay.
//   L3 / F7 pendant la reprise   : retour instantane avec le decor remis a neuf : le jeu reconstruit
//                                   la scene (comme Select+R2 en entrainement), puis le point est remis.
//   Si un objet du decor a ete casse depuis le point, Select / Start font de meme automatiquement.
//   Si le point de controle est refuse en plein round (verification echouee), le replay est relance
//   sur place puis rattrape en accelere jusqu a l instant de la reprise ; au bip, la main est rendue
//   (Select, L3) ou laissee au replay (Start).
//   Apres un K.O. ou un temps ecoule, les retours sont desactives jusqu a la prochaine reprise.
//
// Version 2.0 : points de controle (Checkpoint.h), 25/09/2026.
// Version 2.2 : decor remis a neuf par le jeu (reconstruction de la scene), 26/09/2026.
// Version 2.3 : retour depuis une autre zone (cour, sous-sol) : la scene du point est redemandee.
// Version 2.4 : apres la reconstruction, les objets deja casses au point le redeviennent (etat du decor recharge).
// Version 2.1 : retour exact, securite « decor modifie », joueurs humains remis apres un
// redemarrage (trouves par Snow, 26/09), rattrapage par les pas de simulation natifs, 26/09/2026.
//
// Tout se fait en memoire ; aucun fichier du jeu n est modifie. Le fonctionnement,
// trouve pas a pas le 23/09/2026 (voir la sonde DOA5LR-ReplayProbe) :
//
//  * Entrees. 0x43B7F0 lit les manettes -> tampon APPAREILS [0x27F7928 + n*0x2C]
//    (+0 maintenu, +4 appuye, +8 relache) ; 0x3F52B0 les recopie dans le tampon PLACES
//    [0x18278F8 + p*0x2C] ; en replay, le lecteur 0x3396B0 ecrit les entrees enregistrees
//    dans ce meme tampon. Reprendre la main = au retour de 0x3396B0, remettre la vraie
//    manette dans la place du joueur choisi.
//  * Interface du replay (pause...). Elle lit le tampon appareils : pendant la reprise,
//    a la sortie de 0x43B7F0 on met l etat reel de cote puis on vide le tampon, et on le
//    restaure a l entree suivante (le jeu calcule ainsi appuis/relachements sur le vrai
//    etat precedent).
//  * Retour en arriere. Le « Play Again » d un replay redemarre le combat SUR PLACE :
//    [0x18285F8]=1 et octet [0x182851C]=1, consommes par 0x3F7CA0 a l image suivante.
//    On pose ces deux valeurs depuis la boucle du combat (entree de 0x337A10), puis on
//    attend que l image du lecteur ([lecteur+0x2C]) revienne a l image memorisee.
//  * Avance rapide. La logique tourne sur son propre fil et appelle le rappel range
//    dans [0x1719E7C] (0x3F4DB0) une fois par image ; la cadence vient de 0x823630, qui
//    attend l intervalle [0x16AD178] si [0x16AD170]==1. Pendant le rattrapage on force
//    actif=1 / intervalle=0, et on ne presente qu une image sur 8 (Present, D3D9).
//    Plusieurs mises a jour par image affichee font planter le jeu : ne pas y revenir.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincrypt.h>
#include <intrin.h>
#include <cstdio>
#include <cstring>
#include <cstdarg>
#include <cstdint>
#include <initializer_list>
#include <d3d9.h>
#pragma comment(lib,"advapi32.lib")
#pragma comment(lib,"user32.lib")
static_assert(sizeof(void*)==4,"Module x86 uniquement");

constexpr DWORD EXPECTED_TIMESTAMP=0x5a1faa36;
constexpr DWORD EXPECTED_IMAGE_SIZE=0x021f8000;
static const char* GAME_SHA="88d12d42ba49ac696de1acbb25da12615726e8b6259fc24dd6e7d4d939f89bbc";

// Adresses relatives a l image (adresse absolue du desassemblage - 0x7A0000).
constexpr DWORD RVA_MANAGER      =0xFCE790;   // [0x176E790] gestionnaire de replay ; +8 = mode (2/4 = lecture)
constexpr DWORD RVA_REPLAY_STATE =0xD2EBB8;   // [0x14CEBB8] 1 ou 3 = combat de replay
constexpr DWORD RVA_DEVICES      =0x2057928;  // [0x27F7928] 4 manettes + agregat, 0x2C chacune
constexpr DWORD RVA_SLOTS        =0x10878F8;  // [0x18278F8] 4 places, 0x2C chacune
constexpr DWORD RVA_FEED         =0x3396B0;   // lecteur de replay, ecrit le tampon places
constexpr DWORD RVA_POLLER       =0x43B7F0;   // lecture des manettes
constexpr DWORD RVA_FIGHT_FRAME  =0x337A10;   // appele par la boucle du combat juste apres le gestionnaire d etat
constexpr DWORD RVA_FIGHT_STATE  =0x1087A4C;  // [0x1827A4C] etat du combat (4 = combat)
constexpr DWORD RVA_REPLAY_AGAIN =0x10885F8;  // [0x18285F8] « rejouer »
constexpr DWORD RVA_RESTART_FLAG =0x108851C;  // [0x182851C] redemarrage sur place demande
constexpr DWORD RVA_UPDATE_PTR   =0xF79E7C;   // [0x1719E7C] rappel « mise a jour »
constexpr DWORD RVA_UPDATE_FN    =0x3F4DB0;
constexpr DWORD RVA_PACE_INTERVAL=0xF0D178;   // [0x16AD178] intervalle d image
constexpr DWORD RVA_PACE_ENABLED =0xF0D170;   // [0x16AD170] intervalle personnalise actif
constexpr DWORD RVA_PLAYERS      =0xFD0540;   // [0x1770540] joueurs, 0x6C8 octets ; +0 = 1 si humain
constexpr DWORD PAD_SIZE=0x2C, PAD_DWORDS=PAD_SIZE/4, DEVICES_BYTES=5*PAD_SIZE;

// ---- journal -------------------------------------------------------------------
static char g_root[MAX_PATH],g_logPath[MAX_PATH];
static SRWLOCK g_logLock=SRWLOCK_INIT;
static void Log(const char* t) {
    AcquireSRWLockExclusive(&g_logLock);
    FILE* f=nullptr; if(!fopen_s(&f,g_logPath,"a")&&f){fprintf(f,"%s\n",t);fclose(f);}
    ReleaseSRWLockExclusive(&g_logLock);
}

// ---- reglages (DOA5LR-ReplayTakeover.ini) --------------------------------------
static bool  g_skipPresent=true;              // SkipPresent : une image sur 8 pendant le rattrapage
// Codes mesures en jeu le 23/09 (JournalBoutons=1, manette PlayStation) : L2 0x4000,
// R2 0x8000, Carre 0x40, validation des menus 0x10. La table moteur->bits 0x135D350
// ne suit PAS l ordre PS3 libpad : ne pas deduire les codes, les mesurer.
// 25/09 : Select 0x200, Start 0x100, L3 0x400, R3 0x10 (= validation des menus : non retenu).
static DWORD g_btnTake=0x4000;                // BoutonPrise  : L2, prendre la main (hors reprise seulement)
static DWORD g_btnRewind=0x200;         // BoutonRetour : Select, revenir au point (pendant la reprise)
static DWORD g_btnRelease=0x100;         // BoutonRendre : Start, revenir au point et rendre la main
static bool  g_maskTake=false;                // L2 de la prise encore tenu : ne pas le donner au combattant
static DWORD g_btnExact=0x400;                // BoutonRetourExact : L3, retour avec le decor remis a neuf (pendant la reprise)
static DWORD g_catchTicks=10;                 // PasRattrapage : pas de simulation par image affichee pendant le rattrapage
static bool  g_logButtons=false;              // JournalBoutons : noter chaque appui (pour choisir d autres boutons)
static bool  g_showChoice=true;               // ChoixJoueur : fenetre P1/P2 a chaque nouvelle reprise

// ---- etat ----------------------------------------------------------------------
static BYTE* g_base=nullptr;
static BYTE* volatile g_player=nullptr;       // objet lecteur (this de 0x3396B0) ; [+0x2C] = image du replay
static volatile LONG g_takeSlot=-1;           // -1 = replay normal, 0 = joueur 1 pilote par la manette
static volatile LONG g_takeFrame=-1;          // image du replay au moment de la reprise
static volatile LONG g_takeChosen=0;          // joueur repris (0 = P1, 1 = P2), rendu apres chaque retour
static volatile LONG g_rewindPending=0;       // 1 = redemarrer sur place a la prochaine image de combat
static volatile LONG g_rewindTarget=-1;       // image a rejoindre ; -1 = aucun retour en cours
static volatile LONG g_restartAsked=0;        // drapeau pose, pas encore consomme par le jeu
static bool  g_seenReset=false;               // image du lecteur vue repasser sous la cible
static DWORD g_rewindStart=0,g_restartTick=0;
static volatile LONG g_ffUpdates=0;           // mises a jour pendant le rattrapage
static DWORD g_live[DEVICES_BYTES/4];         // etat reel des manettes (le tampon du jeu peut etre vide)
static bool  g_blanked=false;
static volatile LONG g_lastDevice=-1;         // derniere manette ou quelque chose a bouge
static SRWLOCK g_actLock=SRWLOCK_INIT;
static volatile LONG g_selecting=0;           // fenetre de choix du joueur ouverte
static volatile LONG g_selCursor=0;           // joueur en surbrillance (0 = P1, 1 = P2)
static volatile LONG g_freezeReq=0;           // 1 = figer le combat, 2 = le relancer (fait dans la boucle du combat)
static bool  g_frozenByUs=false;
static bool  g_selArmed=false;                // la fenetre n accepte rien avant un relachement complet
static volatile LONG g_releaseAtArrival=0;    // rattrapage demande par R2 : ne pas rendre la main a l arrivee
static volatile LONG g_restoreRelease=0;      // retour instantane demande par R2 (main deja rendue)
static bool  g_roundSeenDecided=false;        // pendant la reprise : K.O. ou temps ecoule deja vu

// ---- points de controle ----------------------------------------------------------------
static BYTE* base=nullptr;                    // = g_base, nom attendu par Checkpoint.h
static bool Copy(void* dst,const void* src,size_t n) {
    __try { memcpy(dst,src,n); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { memset(dst,0,n); return false; }
}
static DWORD Read(const void* p) { DWORD v=0; Copy(&v,p,4); return v; }
#include "Checkpoint.h"

static DWORD ReplayMode() {
    void* obj=*reinterpret_cast<void**>(g_base+RVA_MANAGER);
    return obj?*reinterpret_cast<DWORD*>(static_cast<BYTE*>(obj)+8):0;
}
static bool ReplayPlaying() { const DWORD m=ReplayMode(); return m==2u||m==4u; }
static DWORD PlayerFrame() { BYTE* o=g_player; return o?*reinterpret_cast<DWORD*>(o+0x2C):0xFFFFFFFFu; }
static bool CatchingUp() { return g_rewindTarget>=0&&!g_rewindPending; }
static DWORD& At(DWORD rva) { return *reinterpret_cast<DWORD*>(g_base+rva); }

// ---- actions (clavier ou manette) ----------------------------------------------
// Un joueur pilote par l ordinateur dans le replay n est pas propose : son IA est
// recalculee a chaque lecture et le jeu ignore la manette pour lui (non teste).
static bool IsHuman(LONG who) { return At(RVA_PLAYERS+who*0x6C8)==1; }
static void TakeNow(const char* from,LONG who) {           // sous g_actLock
    g_takeChosen=who;
    g_takeFrame=static_cast<LONG>(PlayerFrame());
    InterlockedExchange(&g_takeSlot,who);
    InterlockedExchange(&cp::requestSave,1);                // point de controle pose a cette image
    g_roundSeenDecided=false;
    char l[128];sprintf_s(l,"%s : reprise en main du joueur %ld a l image %ld.",from,who+1,g_takeFrame); Log(l);
}
static void CloseSelector() {                               // sous g_actLock
    InterlockedExchange(&g_selecting,0);
    InterlockedExchange(&g_freezeReq,2);
}
static void SelectToggle() {
    AcquireSRWLockExclusive(&g_actLock);
    if(g_selecting) {const LONG other=1-g_selCursor; if(IsHuman(other)) InterlockedExchange(&g_selCursor,other);}
    ReleaseSRWLockExclusive(&g_actLock);
}
static void ActionPrimary(const char* from,bool exact=false) {
    AcquireSRWLockExclusive(&g_actLock);
    char l[160];
    if(g_selecting) {                                       // valider le choix
        CloseSelector();
        TakeNow(from,g_selCursor);
    } else if(g_rewindTarget>=0) {
        // retour en cours : appui ignore sans bruit
    } else if(g_takeSlot<0) {
        if(!ReplayPlaying()||!g_player) {sprintf_s(l,"%s ignore : aucun replay en lecture.",from); Log(l);}
        else if(g_showChoice&&IsHuman(1)) {                 // deux joueurs possibles : on demande
            InterlockedExchange(&g_selCursor,IsHuman(g_takeChosen)?g_takeChosen:0);
            g_selArmed=false;
            InterlockedExchange(&g_selecting,1);
            InterlockedExchange(&g_freezeReq,1);
            sprintf_s(l,"%s : choix du joueur (combat fige).",from); Log(l);
        } else TakeNow(from,IsHuman(g_takeChosen)?g_takeChosen:0);
    } else if(cp::roundOver) {
        sprintf_s(l,"%s ignore : round termine (K.O. ou temps ecoule), retour desactive jusqu a la prochaine reprise.",from); Log(l);
    } else if(cp::active&&(!exact||cp::rebuildAvailable)) {
        InterlockedExchange(&g_restoreRelease,0);
        if(exact) InterlockedExchange(&cp::forceRebuild,1);  // decor remis a neuf par le jeu
        InterlockedExchange(&cp::requestRestore,1);         // la main reste au joueur
        sprintf_s(l,"%s : retour au point de controle (image %ld)%s.",from,g_takeFrame,exact?", decor remis a neuf":""); Log(l);
    } else {
        InterlockedExchange(&g_takeSlot,-1);
        InterlockedExchange(&g_releaseAtArrival,0);
        InterlockedExchange(&g_rewindTarget,g_takeFrame);
        InterlockedExchange(&g_rewindPending,1);
        sprintf_s(l,"%s : retour %sa l image %ld par redemarrage et rattrapage accelere.",from,exact?"EXACT ":"",g_takeFrame); Log(l);
    }
    ReleaseSRWLockExclusive(&g_actLock);
}
static void ActionRelease(const char* from) {
    AcquireSRWLockExclusive(&g_actLock);
    char l[128];
    if(g_selecting) {CloseSelector(); sprintf_s(l,"%s : choix annule.",from);}
    else if(g_rewindTarget>=0) l[0]=0;                     // retour en cours : appui ignore
    else if(g_takeSlot>=0) {
        InterlockedExchange(&g_takeSlot,-1);
        if(cp::active) {
            InterlockedExchange(&g_restoreRelease,1);
            InterlockedExchange(&cp::requestRestore,1);
            sprintf_s(l,"%s : retour au point de controle (image %ld), le replay reprend normalement.",from,g_takeFrame);
        } else if(cp::roundOver) {
            sprintf_s(l,"%s : main rendue (round termine, pas de retour).",from);
        } else {
            InterlockedExchange(&g_releaseAtArrival,1);
            InterlockedExchange(&g_rewindTarget,g_takeFrame);
            InterlockedExchange(&g_rewindPending,1);
            sprintf_s(l,"%s : retour a l image %ld par rattrapage accelere, puis le replay reprend.",from,g_takeFrame);
        }
    }
    else sprintf_s(l,"%s ignore : aucune reprise en main en cours.",from);
    if(l[0]) Log(l);
    ReleaseSRWLockExclusive(&g_actLock);
}

// ---- lecteur de replay : injection de la manette et detection de l arrivee -------
static void __cdecl OnFed() {
    if(!g_base) return;
    const LONG target=g_rewindTarget;
    if(target>=0&&!g_rewindPending&&!g_restartAsked) {
        const LONG f=static_cast<LONG>(PlayerFrame());
        if(f<target) g_seenReset=true;
        else if(g_seenReset) {
            char l[160];
            sprintf_s(l,"Revenu a l image %ld en %lu ms (%ld mises a jour).",f,GetTickCount()-g_rewindStart,g_ffUpdates);
            Log(l);
            InterlockedExchange(&g_ffUpdates,0);
            InterlockedExchange(&g_rewindTarget,-1);
            if(InterlockedExchange(&g_releaseAtArrival,0)) Log("Le replay reprend normalement.");
            else {
                InterlockedExchange(&g_takeSlot,g_takeChosen);
                InterlockedExchange(&cp::requestSave,1);    // nouveau point de controle a l arrivee
            }
            MessageBeep(MB_OK);
        }
    }
    const LONG slot=g_takeSlot;
    if(slot<0||!ReplayPlaying()) return;
    LONG d=g_lastDevice;
    if(d<0||d>3) {d=g_base[0x10877C0]; if(d>3) d=0;}        // appareil attitre de la place 0 ([0x18277C0])
    DWORD pad[PAD_DWORDS];
    memcpy(pad,g_live+d*PAD_DWORDS,PAD_SIZE);
    DWORD mine=g_btnRewind|g_btnRelease|g_btnExact;          // nos boutons ne vont pas au combattant
    if(g_maskTake) mine|=g_btnTake;                          // L2 de la prise, jusqu a son relachement
    pad[0]&=~mine; pad[1]&=~mine; pad[2]&=~mine;
    BYTE* slots=g_base+RVA_SLOTS;
    memcpy(slots+slot*PAD_SIZE,pad,PAD_SIZE);
    memcpy(slots+(slot^2)*PAD_SIZE,pad,PAD_SIZE);           // partenaire de tag
}
static BYTE* g_resumeFeed=nullptr;
static __declspec(naked) void OriginalFeed() { __asm { push ebp
                                                       mov  ebp,esp
                                                       sub  esp,0x2C
                                                       jmp  [g_resumeFeed] } }
static __declspec(naked) void FeedThunk() {    // thiscall sans argument, simple ret
    __asm {
        mov  g_player,ecx
        call OriginalFeed
        pushad
        pushfd
        call OnFed
        popfd
        popad
        ret
    }
}

// ---- lecture des manettes : masquage de l interface et boutons du module ---------
// JournalBoutons=1 : note les boutons maintenus (+0) et les 6 axes (flottants en +0xC,
// dont probablement les gachettes L2/R2) quand ils changent nettement.
static DWORD g_lastHeld[4]={0}, g_lastAxes[4]={0};
static void LogButtons(LONG d,const DWORD* p) {
    DWORD axes=0;                              // 2 bits par axe : 01 = > +0,5 ; 10 = < -0,5
    const float* f=reinterpret_cast<const float*>(p+3);
    for(int i=0;i<6;++i) {if(f[i]>0.5f) axes|=1u<<(2*i); else if(f[i]<-0.5f) axes|=2u<<(2*i);}
    if(p[0]==g_lastHeld[d]&&axes==g_lastAxes[d]) return;
    g_lastHeld[d]=p[0]; g_lastAxes[d]=axes;
    char l[200];
    sprintf_s(l,"manette %ld : maintenu %08lX  axes %+.2f %+.2f %+.2f %+.2f %+.2f %+.2f  (+24 %08lX +28 %08lX)",
        d,p[0],f[0],f[1],f[2],f[3],f[4],f[5],p[9],p[10]);
    Log(l);
}
static LONG g_stickSide[4]={0};
// Le mot +4 du tampon (« appuye ») inclut la REPETITION AUTOMATIQUE des menus : un bouton
// tenu s y « reappuie » regulierement (essai du 23/09 : la fenetre de choix se validait
// toute seule, R2 compte 5 fois). On calcule donc nos appuis a partir du mot +0 (maintenu).
static DWORD g_prevHeld[4]={0};
static void __cdecl OnPollEnter() {
    if(g_blanked&&g_base) {memcpy(g_base+RVA_DEVICES,g_live,DEVICES_BYTES); g_blanked=false;}
}
static void __cdecl OnPollExit() {
    if(!g_base) return;
    BYTE* dev=g_base+RVA_DEVICES;
    memcpy(g_live,dev,DEVICES_BYTES);
    DWORD pressed=0,held=0;
    for(LONG d=0;d<4;++d) {
        const DWORD* p=g_live+d*PAD_DWORDS;
        if(p[0]||p[1]||p[2]||p[3]||p[4]) g_lastDevice=d;
        pressed|=p[0]&~g_prevHeld[d];
        held|=p[0];
        g_prevHeld[d]=p[0];
        if(g_logButtons) LogButtons(d,p);
    }
    if(g_selecting&&!g_selArmed) {                          // attendre que tout soit relache
        if(!held) g_selArmed=true;
        pressed=0;
    }
    if(g_selecting) {
        if(!ReplayPlaying()) {AcquireSRWLockExclusive(&g_actLock); CloseSelector(); ReleaseSRWLockExclusive(&g_actLock);}
        // n importe quel autre bouton ou direction fait changer de joueur (il n y en a que deux)
        if(pressed&~(g_btnTake|g_btnRelease)) SelectToggle();
        for(LONG d=0;d<4;++d) {                             // stick gauche, axe horizontal
            const float x=reinterpret_cast<const float*>(g_live+d*PAD_DWORDS+3)[0];
            const LONG side=x>0.5f?1:x<-0.5f?-1:0;
            if(side&&side!=g_stickSide[d]&&g_selArmed) SelectToggle();
            g_stickSide[d]=side;
        }
    }
    if(g_maskTake&&!(held&g_btnTake)) g_maskTake=false;
    bool consumed=false;                                     // appui a nous : l interface du replay ne le voit pas
    if(g_takeSlot>=0||g_rewindTarget>=0) {                   // reprise (ou retour) en cours : L2 va au combat
        if(g_btnRewind&&(pressed&g_btnRewind)) {ActionPrimary("Select"); consumed=true;}
        if(g_btnRelease&&(pressed&g_btnRelease)) {ActionRelease("Start"); consumed=true;}
        if(g_btnExact&&(pressed&g_btnExact)&&g_takeSlot>=0) {ActionPrimary("L3",true); consumed=true;}
    } else {
        if(g_btnTake&&(pressed&g_btnTake)) {ActionPrimary("L2"); g_maskTake=true; consumed=g_selecting||g_takeSlot>=0;}
        else if(g_selecting&&g_btnRelease&&(pressed&g_btnRelease)) {ActionRelease("Start"); consumed=true;}
    }
    if((g_takeSlot>=0||g_selecting||consumed)&&ReplayPlaying()) {memset(dev,0,DEVICES_BYTES); g_blanked=true;}
}
static BYTE* g_resumePoll=nullptr;
static __declspec(naked) void OriginalPoll() { __asm { push ebp
                                                       mov  ebp,esp
                                                       sub  esp,0x6C
                                                       jmp  [g_resumePoll] } }
static __declspec(naked) void PollThunk() {
    __asm {
        pushad
        pushfd
        call OnPollEnter
        popfd
        popad
        call OriginalPoll
        pushad
        pushfd
        call OnPollExit
        popfd
        popad
        ret
    }
}

// ---- boucle du combat : redemarrage sur place --------------------------------------
// 0x313010 / 0x313030 : les fonctions de pause du jeu (menu pause, lecteur de replay...) :
// figent le combat ([0x18279B1]=1) sans toucher a l affichage.
constexpr DWORD RVA_FREEZE=0x313010, RVA_UNFREEZE=0x313030, RVA_FROZEN=0x10879B1;
// Le redemarrage sur place (0x3F6B60) reecrit l indicateur « humain » des joueurs ([0xFD0540],
// [0xFD0C08]) depuis [0x1088604] : apres un retour par rattrapage, J2 passait « CPU » (plus de
// fenetre P1/P2). Trouve par Snow (26/09) : notes au debut de la lecture, remis apres chaque redemarrage.
static DWORD g_humanFlags[2]; static bool g_humanValid=false;
static void __cdecl OnFightFrame() {
    if(!g_base) return;
    if(!ReplayPlaying()) g_humanValid=false;
    else if(!g_humanValid&&g_rewindTarget<0&&!g_restartAsked) {
        g_humanFlags[0]=At(RVA_PLAYERS); g_humanFlags[1]=At(RVA_PLAYERS+0x6C8); g_humanValid=true;
    }
    if(g_freezeReq) {
        typedef void (__cdecl *VoidFn)();
        const LONG req=InterlockedExchange(&g_freezeReq,0);
        if(req==1&&!g_base[RVA_FROZEN]) {reinterpret_cast<VoidFn>(g_base+RVA_FREEZE)(); g_frozenByUs=true;}
        else if(req==2&&g_frozenByUs) {reinterpret_cast<VoidFn>(g_base+RVA_UNFREEZE)(); g_frozenByUs=false;}
    }
    // Fin de round pendant la reprise : au debut du round suivant (combat, les deux sante > 0,
    // chrono qui tourne), la main revient automatiquement aux entrees du replay.
    if(g_takeSlot>=0&&g_rewindTarget<0) {
        const bool decided=cp::RoundDecided();
        if(decided) g_roundSeenDecided=true;
        else if(g_roundSeenDecided&&At(RVA_FIGHT_STATE)==4) {
            g_roundSeenDecided=false;
            InterlockedExchange(&g_takeSlot,-1);
            Log("Nouveau round : la main revient aux entrees du replay.");
        }
    }
    if(InterlockedExchange(&cp::lastResult,0)==2&&g_rewindTarget<0) {
        if(cp::roundOver) Log("Retour refuse : round termine (K.O. ou temps ecoule).");
        else {
            // point de controle refuse en plein round : retour par rattrapage accelere
            InterlockedExchange(&g_takeSlot,-1);
            InterlockedExchange(&g_releaseAtArrival,g_restoreRelease);
            InterlockedExchange(&g_rewindTarget,g_takeFrame);
            InterlockedExchange(&g_rewindPending,1);
            Log("Retour par rattrapage accelere.");
        }
    }
    if(g_rewindPending) {
        InterlockedExchange(&g_rewindPending,0);
        const DWORD st=At(RVA_FIGHT_STATE), rs=At(RVA_REPLAY_STATE);
        if(st!=4||(rs!=1&&rs!=3)) {
            char l[128];sprintf_s(l,"Retour abandonne : pas en combat de replay (etat %lu, replay %lu).",st,rs);Log(l);
            InterlockedExchange(&g_rewindTarget,-1);
            return;
        }
        At(RVA_REPLAY_AGAIN)=1;
        g_base[RVA_RESTART_FLAG]=1;
        InterlockedExchange(&g_restartAsked,1);
        g_seenReset=false;
        g_rewindStart=g_restartTick=GetTickCount();
    } else if(g_restartAsked) {
        if(!g_base[RVA_RESTART_FLAG]) {                                            // consomme par le jeu
            InterlockedExchange(&g_restartAsked,0);
            if(g_humanValid&&(At(RVA_PLAYERS)!=g_humanFlags[0]||At(RVA_PLAYERS+0x6C8)!=g_humanFlags[1])) {
                At(RVA_PLAYERS)=g_humanFlags[0]; At(RVA_PLAYERS+0x6C8)=g_humanFlags[1];
                Log("Redemarrage : joueurs humains remis.");
            }
        }
        else if(GetTickCount()-g_restartTick>5000) {
            Log("Retour abandonne : redemarrage non pris en compte par le jeu.");
            g_base[RVA_RESTART_FLAG]=0; At(RVA_REPLAY_AGAIN)=0;
            InterlockedExchange(&g_restartAsked,0);
            InterlockedExchange(&g_rewindTarget,-1);
        }
    }
}
static BYTE* g_resumeFightFrame=nullptr;
static __declspec(naked) void FightFrameThunk() {
    __asm {
        pushad
        pushfd
        call OnFightFrame
        popfd
        popad
        push ebp                 // 5 premiers octets d origine : 55 8B EC 6A FF
        mov  ebp,esp
        push -1
        jmp  [g_resumeFightFrame]
    }
}

// ---- avance rapide ---------------------------------------------------------------
typedef void (__cdecl *UpdateFn)();
static UpdateFn g_origUpdate=nullptr;
static bool  g_paceLifted=false;
static DWORD g_paceSaved=0,g_paceEnabledSaved=0;
static void PaceControl(bool fast) {
    DWORD& interval=At(RVA_PACE_INTERVAL);
    DWORD& enabled=At(RVA_PACE_ENABLED);
    if(fast) {
        if(!g_paceLifted) {g_paceSaved=interval; g_paceEnabledSaved=enabled; g_paceLifted=true;}
        interval=0; enabled=1;                   // chaque image : le jeu ou un autre mod peut les remettre
    } else if(g_paceLifted) {
        interval=g_paceSaved; enabled=g_paceEnabledSaved; g_paceLifted=false;
    }
}
// Pas de simulation par image affichee : 0x3F4A80 fait N pas (ordonnanceur de fibres 0x423690, dont
// le combat) puis un seul rendu ; N = 0x423420() (rattrapage natif du jeu quand il rame). 0x423420 est
// remplace par TickCount : meme calcul + g_extraTicks, fixe au debut de chaque mise a jour. Pendant le
// rattrapage : PasRattrapage pas par image, reduits a l approche pour s arreter pile sur l image visee.
// (Rappeler toute la mise a jour plusieurs fois plantait, v10 : le rendu garde des elements d une
// mise a jour a l autre. Les pas natifs, eux, ne produisent qu un rendu.)
static volatile LONG g_extraTicks=0; static volatile LONG g_stepInUpdate=0;   // 2.5 : pas de la mise a jour en cours
static DWORD __cdecl TickCount() {
    const DWORD i=(Read(g_base+0x108B490)-2)&3; BYTE* rec=g_base+0x108B448+i*16;
    return Read(g_base+0x9C1DB0+Read(rec)*12)+Read(rec+8)+static_cast<DWORD>(g_extraTicks);
}
static __declspec(naked) void TickCountThunk() {     // l original ne touche que eax / ecx
    __asm {
        push edx
        call TickCount
        pop  edx
        ret
    }
}
static void PlanTicks() {
    LONG extra=0;
    const LONG target=g_rewindTarget;
    if(target>=0&&!g_rewindPending&&!g_restartAsked&&g_seenReset&&g_catchTicks>1&&!g_base[RVA_FROZEN]) {
        const LONG remaining=target-static_cast<LONG>(PlayerFrame());
        extra=static_cast<LONG>(g_catchTicks)-1;
        if(remaining-1<extra) extra=remaining-1;
        if(extra<0) extra=0;
    }
    InterlockedExchange(&g_extraTicks,extra);
}
static void __cdecl UpdateWrapper() {
    PlanTicks();
    InterlockedExchange(&g_stepInUpdate,0);
    g_origUpdate();
    const bool fast=CatchingUp();
    if(fast) InterlockedIncrement(&g_ffUpdates);
    PaceControl(fast);
}
static void InstallUpdateWrapper() {          // le rappel n existe qu une fois le moteur demarre
    if(g_origUpdate) return;
    DWORD* slot=reinterpret_cast<DWORD*>(g_base+RVA_UPDATE_PTR);
    const DWORD expected=reinterpret_cast<DWORD>(g_base+RVA_UPDATE_FN);
    if(*slot!=expected) return;
    g_origUpdate=reinterpret_cast<UpdateFn>(expected);
    InterlockedExchange(reinterpret_cast<volatile LONG*>(slot),static_cast<LONG>(reinterpret_cast<DWORD>(&UpdateWrapper)));
    Log("Avance rapide prete.");
}

// ---- fenetre de choix, dessinee a chaque presentation --------------------------------
// Pas de police disponible : texte en blocs 5x7, dessine avec des Clear rectangulaires
// sur le tampon arriere juste avant Present (etat D3D sauvegarde puis restaure).
struct Glyph { char c; BYTE rows[7]; };
static const Glyph FONT[]={
    {'A',{14,17,17,31,17,17,17}},{'C',{14,17,16,16,16,17,14}},{'D',{30,17,17,17,17,17,30}},
    {'E',{31,16,16,30,16,16,31}},{'G',{14,17,16,23,17,17,15}},{'H',{17,17,17,31,17,17,17}},
    {'I',{14,4,4,4,4,4,14}},     {'J',{7,2,2,2,2,18,12}},     {'L',{16,16,16,16,16,16,31}},
    {'N',{17,25,21,19,17,17,17}},{'O',{14,17,17,17,17,17,14}},{'P',{30,17,17,30,16,16,16}},
    {'R',{30,17,17,30,20,18,17}},{'S',{15,16,16,14,1,1,30}},  {'T',{31,4,4,4,4,4,4}},{'U',{17,17,17,17,17,17,14}},{'V',{17,17,17,17,17,10,4}},
    {'X',{17,17,10,4,10,17,17}}, {'1',{4,12,4,4,4,4,14}},     {'2',{14,17,1,2,4,8,31}},
    {'<',{2,4,8,16,8,4,2}},      {'>',{8,4,2,1,2,4,8}},
};
struct RectList { D3DRECT r[1024]; DWORD n=0; void Add(LONG x,LONG y,LONG w,LONG h){if(n<1024){r[n]={x,y,x+w,y+h};++n;}} };
static void TextRects(RectList& out,LONG x,LONG y,LONG s,const char* t) {
    for(;*t;++t,x+=6*s) {
        const Glyph* g=nullptr; for(const auto& f:FONT) if(f.c==*t) {g=&f;break;}
        if(!g) continue;
        for(int row=0;row<7;++row) for(int col=0;col<5;) {        // segments horizontaux continus
            if(!(g->rows[row]&(16>>col))) {++col;continue;}
            int end=col; while(end<5&&(g->rows[row]&(16>>end))) ++end;
            out.Add(x+col*s,y+row*s,(end-col)*s,s); col=end;
        }
    }
}
static LONG TextWidth(const char* t,LONG s) { return static_cast<LONG>(strlen(t))*6*s-s; }
static void Fill(IDirect3DDevice9* d,const RectList& l,D3DCOLOR c) { if(l.n) d->Clear(l.n,l.r,D3DCLEAR_TARGET,c,1.0f,0); }
static RectList g_rl[7];                      // listes de rectangles (trop grosses pour la pile)
static volatile LONG g_drawLogged=0,g_drawFailLogged=0,g_selectorDraws=0;
static void DrawSelector(IDirect3DDevice9* d) {
    IDirect3DSurface9 *bb=nullptr,*old=nullptr;
    if(FAILED(d->GetBackBuffer(0,0,D3DBACKBUFFER_TYPE_MONO,&bb))||!bb) {
        if(!InterlockedExchange(&g_drawFailLogged,1)) Log("Fenetre de choix : tampon arriere inaccessible, rien n est dessine.");
        return;
    }
    D3DSURFACE_DESC desc; bb->GetDesc(&desc);
    if(!InterlockedExchange(&g_drawLogged,1)) {
        char l[128];sprintf_s(l,"Fenetre de choix dessinee (tampon %ux%u).",desc.Width,desc.Height);Log(l);
    }
    InterlockedIncrement(&g_selectorDraws);
    D3DVIEWPORT9 vp; d->GetViewport(&vp);
    DWORD scissor=0,colorWrite=0;
    d->GetRenderState(D3DRS_SCISSORTESTENABLE,&scissor); d->GetRenderState(D3DRS_COLORWRITEENABLE,&colorWrite);
    d->GetRenderTarget(0,&old);
    d->SetRenderTarget(0,bb);
    d->SetRenderState(D3DRS_SCISSORTESTENABLE,FALSE); d->SetRenderState(D3DRS_COLORWRITEENABLE,0xF);

    for(auto& l:g_rl) l.n=0;
    RectList &frame=g_rl[0],&panel=g_rl[1],&boxOn=g_rl[2],&boxOff=g_rl[3],&textOn=g_rl[4],&textDark=g_rl[5],&textGrey=g_rl[6];
    const LONG s=desc.Height>=400?static_cast<LONG>(desc.Height/200):2;   // taille d un bloc
    const LONG w=112*s,h=62*s,x0=(static_cast<LONG>(desc.Width)-w)/2,y0=(static_cast<LONG>(desc.Height)-h)/2;
    frame.Add(x0-s,y0-s,w+2*s,h+2*s); panel.Add(x0,y0,w,h);
    const char* title="CHOIX DU JOUEUR";
    TextRects(textOn,x0+(w-TextWidth(title,s))/2,y0+6*s,s,title);
    const LONG sel=g_selCursor;
    for(LONG who=0;who<2;++who) {
        const LONG bx=x0+(who?64:16)*s,by=y0+20*s,bw=32*s,bh=17*s;
        const bool on=who==sel, human=IsHuman(who);
        if(on) boxOn.Add(bx,by,bw,bh);
        else {boxOff.Add(bx,by,bw,s); boxOff.Add(bx,by+bh-s,bw,s); boxOff.Add(bx,by,s,bh); boxOff.Add(bx+bw-s,by,s,bh);}
        const char* label=who?"P2":"P1";
        RectList& tl=on?textDark:(human?textOn:textGrey);
        TextRects(tl,bx+(bw-TextWidth(label,2*s))/2,by+(human?2:1)*s+s,2*s,label);
        if(!human) TextRects(textGrey,bx+(bw-TextWidth("CPU",s))/2,by+bh-8*s,s,"CPU");
    }
    const LONG hs=s>=4?s/2:1;
    const char* help="<> CHANGER  L2 VALIDER  START ANNULER";
    TextRects(textGrey,x0+(w-TextWidth(help,hs))/2,y0+h-11*s,hs,help);
    Fill(d,frame,D3DCOLOR_XRGB(210,210,210)); Fill(d,panel,D3DCOLOR_XRGB(18,20,26));
    Fill(d,boxOff,D3DCOLOR_XRGB(120,120,120)); Fill(d,boxOn,D3DCOLOR_XRGB(232,184,58));
    Fill(d,textOn,D3DCOLOR_XRGB(255,255,255)); Fill(d,textDark,D3DCOLOR_XRGB(18,20,26)); Fill(d,textGrey,D3DCOLOR_XRGB(150,150,150));

    d->SetRenderState(D3DRS_SCISSORTESTENABLE,scissor); d->SetRenderState(D3DRS_COLORWRITEENABLE,colorWrite);
    if(old) {d->SetRenderTarget(0,old); old->Release();}
    d->SetViewport(&vp);
    bb->Release();
}

typedef HRESULT (__stdcall *PresentFn)(void*,const RECT*,const RECT*,HWND,const void*);
// Une table de methodes accrochee = son Present d origine. Normalement une seule (celle du
// peripherique factice est aussi celle du jeu) ; avec un outil qui s intercale (ReShade,
// DXVK, correctif...) le peripherique du jeu peut avoir sa propre table : elle est accrochee
// a part (essai d un ami le 26/09 : fenetre ouverte mais jamais dessinee).
struct PresentPatch { void** vt; PresentFn orig; };
static PresentPatch g_pp[4];
static volatile LONG g_ppCount=0;
static volatile LONG g_presents=0;
static PresentFn OrigPresent(void* dev) {
    void** vt=*static_cast<void***>(dev);
    const LONG n=g_ppCount;
    for(LONG i=0;i<n;++i) if(g_pp[i].vt==vt) return g_pp[i].orig;
    return g_pp[0].orig;
}
static HRESULT __stdcall PresentHook(void* dev,const RECT* a,const RECT* b,HWND w,const void* r) {
    const LONG n=InterlockedIncrement(&g_presents);
    if(g_skipPresent&&CatchingUp()&&(n&7)) return S_OK;
    if(g_selecting) DrawSelector(static_cast<IDirect3DDevice9*>(dev));
    return OrigPresent(dev)(dev,a,b,w,r);
}
static bool PatchPresent(void** vt) {                 // fil unique : le fil de demarrage puis Keys
    if(vt[17]==reinterpret_cast<void*>(&PresentHook)) return true;
    if(g_ppCount>=4) return false;
    DWORD old=0,ig=0;
    if(!VirtualProtect(&vt[17],4,PAGE_READWRITE,&old)) return false;
    g_pp[g_ppCount]={vt,reinterpret_cast<PresentFn>(vt[17])};
    InterlockedIncrement(&g_ppCount);                 // l entree est complete avant l echange
    InterlockedExchange(reinterpret_cast<volatile LONG*>(&vt[17]),static_cast<LONG>(reinterpret_cast<DWORD>(&PresentHook)));
    VirtualProtect(&vt[17],4,old,&ig);
    return true;
}
// Peripherique du jeu : objet graphique [0x2820938] (RVA 0x2080938), peripherique en +0xC4 ;
// 0x76CF40 y appelle Present (entree 17) et teste D3DERR_DEVICELOST.
constexpr DWORD RVA_GRAPHICS=0x2080938;
static void CheckGameDevice() {
    const DWORD gfx=Read(g_base+RVA_GRAPHICS); if(!gfx) return;
    const DWORD dev=Read(reinterpret_cast<void*>(gfx+0xC4)); if(!dev) return;
    void** vt=reinterpret_cast<void**>(Read(reinterpret_cast<void*>(dev)));
    if(!vt||Read(&vt[17])==reinterpret_cast<DWORD>(&PresentHook)) return;
    const bool ok=PatchPresent(vt);
    char l[160];sprintf_s(l,"Affichage : le peripherique du jeu a sa propre table (outil graphique intercale ?) : %s.",ok?"accroche":"ECHEC");Log(l);
}
// Adresse de IDirect3DDevice9::Present (entree 17) lue sur un peripherique invisible ;
// en general la table est commune a tous les peripheriques D3D9, donc aussi a celui du jeu.
static bool HookPresent() {
    HMODULE d3d=GetModuleHandleA("d3d9.dll"); if(!d3d) return false;
    typedef IDirect3D9* (WINAPI *CreateFn)(UINT);
    CreateFn create=reinterpret_cast<CreateFn>(GetProcAddress(d3d,"Direct3DCreate9"));
    if(!create) return false;
    HWND w=CreateWindowExA(0,"STATIC","rt",WS_POPUP,0,0,8,8,nullptr,nullptr,nullptr,nullptr);
    IDirect3D9* d=create(D3D_SDK_VERSION);
    bool ok=false;
    if(d&&w) {
        D3DPRESENT_PARAMETERS pp={}; pp.Windowed=TRUE; pp.SwapEffect=D3DSWAPEFFECT_DISCARD; pp.hDeviceWindow=w;
        IDirect3DDevice9* dev=nullptr;
        if(SUCCEEDED(d->CreateDevice(D3DADAPTER_DEFAULT,D3DDEVTYPE_HAL,w,D3DCREATE_SOFTWARE_VERTEXPROCESSING|D3DCREATE_MULTITHREADED,&pp,&dev))&&dev) {
            ok=PatchPresent(*reinterpret_cast<void***>(dev));
            dev->Release();
        }
    }
    if(d) d->Release();
    if(w) DestroyWindow(w);
    return ok;
}

// ---- points de controle : accroches ----------------------------------------------------
// Fin d image de la boucle du combat : l appel de 0x337A10 en 0x3F6857 est redirige ; le
// point de controle est pose / remis juste apres (meme endroit que dans la sonde).
static BYTE* g_fightFrameFn=nullptr;
// 2.5 : la mise a jour de la scene qui traite les casses (0x597AA0, vt+18 de la scene courante) n'est appelee
// qu'une fois par image affichee, apres la boucle des pas (0x3F4C35). Pendant le rattrapage (plusieurs pas par
// image affichee), elle ne suivait que le dernier : casses traitees en retard, trajectoires differentes du
// replay (trouve avec le labo de rollback 0.17). On l'appelle apres chaque pas qui n'est pas le dernier.
typedef void(__cdecl* SceneFrameFn)(float);
static bool g_sceneFrameOk=false;
static void __cdecl FrameEnd() {
    cp::Frontier(g_player);
    const LONG step=InterlockedIncrement(&g_stepInUpdate);
    if(g_sceneFrameOk && g_extraTicks>0 && step<1+g_extraTicks)
        __try{reinterpret_cast<SceneFrameFn>(g_base+0x597AA0)(1.0f);}__except(EXCEPTION_EXECUTE_HANDLER){}
}
static __declspec(naked) void FightEndThunk() {
    __asm {
        call [g_fightFrameFn]
        pushfd
        pushad
        mov ebx,esp
        sub esp,528
        and esp,0FFFFFFF0h
        fxsave [esp]
        mov esi,esp
        cld
        call FrameEnd
        fxrstor [esi]
        mov esp,ebx
        popad
        popfd
        ret
    }
}
// Physique secondaire : mise a jour 0x0C64D0 (thiscall), ecx = objet.
static BYTE* g_resumePhysics=nullptr;
static void __cdecl PhysicsSeen(DWORD object) {cp::NotePhysics(object);}
static __declspec(naked) void PhysicsThunk() {
    __asm {
        pushfd
        pushad
        push ecx
        call PhysicsSeen
        add esp,4
        popad
        popfd
        push ebp
        mov ebp,esp
        push esi
        mov esi,ecx
        jmp [g_resumePhysics]
    }
}
// Composants serialisables du decor : 0x59EC00 (chargement) et 0x59ED20 (sauvegarde).
static BYTE *g_resumeComponentLoad=nullptr,*g_resumeComponentSave=nullptr;
static void __cdecl ComponentSeen(DWORD component) {cp::NoteComponent(component);}
static __declspec(naked) void ComponentLoadThunk() {
    __asm {
        pushfd
        pushad
        push ecx
        call ComponentSeen
        add esp,4
        popad
        popfd
        push ebp
        mov ebp,esp
        push -1
        jmp [g_resumeComponentLoad]
    }
}
static __declspec(naked) void ComponentSaveThunk() {
    __asm {
        pushfd
        pushad
        push ecx
        call ComponentSeen
        add esp,4
        popad
        popfd
        push ebp
        mov ebp,esp
        push -1
        jmp [g_resumeComponentSave]
    }
}
// Allocateur du jeu, methode +5C (0x7CBB80 : add ecx,4 / jmp [[ecx]+14]), partagee par
// plusieurs classes aux arguments differents : seule l adresse de retour est echangee
// contre un relais (pile par fil) qui note (resultat, 1er argument) puis rend la main.
static __declspec(thread) DWORD g_allocReturns[16],g_allocSizes[16]; static __declspec(thread) int g_allocDepth;
static DWORD __cdecl AllocationEnter(DWORD ret,DWORD arg) {
    if(g_allocDepth>=16) return 0;
    g_allocReturns[g_allocDepth]=ret; g_allocSizes[g_allocDepth]=arg; ++g_allocDepth; return 1;
}
static DWORD __cdecl AllocationLeave(DWORD result) {
    --g_allocDepth;
    if(g_allocSizes[g_allocDepth]&&g_allocSizes[g_allocDepth]<0x4000000) cp::RecordAllocation(result,g_allocSizes[g_allocDepth]);
    return g_allocReturns[g_allocDepth];
}
static __declspec(naked) void AllocationAfter() {
    __asm {
        push edx
        push eax
        push eax
        call AllocationLeave
        add esp,4
        mov ecx,eax
        pop eax
        pop edx
        jmp ecx
    }
}
static __declspec(naked) void AllocationThunk() {
    __asm {
        push ecx
        push edx
        push eax
        push dword ptr [esp+0x10]
        push dword ptr [esp+0x10]
        call AllocationEnter
        add esp,8
        test eax,eax
        jz keep
        mov dword ptr [esp+0xC],offset AllocationAfter
    keep:
        pop eax
        pop edx
        pop ecx
        add ecx,4
        mov eax,[ecx]
        jmp dword ptr [eax+0x14]
    }
}

// ---- pose des detours --------------------------------------------------------------
static bool Detour(BYTE* target,const BYTE* expected,SIZE_T len,void* thunk,BYTE** resume) {
    if(memcmp(target,expected,len)) return false;
    *resume=target+len;
    BYTE patch[8]={0xE9};
    *reinterpret_cast<DWORD*>(patch+1)=reinterpret_cast<DWORD>(thunk)-(reinterpret_cast<DWORD>(target)+5);
    for(SIZE_T i=5;i<len;++i) patch[i]=0x90;
    DWORD old=0,ig=0;
    if(!VirtualProtect(target,len,PAGE_EXECUTE_READWRITE,&old)) return false;
    memcpy(target,patch,len);
    VirtualProtect(target,len,old,&ig);
    FlushInstructionCache(GetCurrentProcess(),target,len);
    return true;
}

static DWORD WINAPI Keys(void*) {
    bool f5=false,f6=false,fl=false,fr=false,fe=false,fx=false;
    DWORD openedAt=0; LONG drawsAtOpen=0; bool silentLogged=false;
    for(;;) {
        Sleep(40);
        InstallUpdateWrapper();
        CheckGameDevice();
        { static bool f7=false; const bool n7=(GetAsyncKeyState(VK_F7)&0x8000)!=0;
          if(n7&&!f7&&g_takeSlot>=0) ActionPrimary("F7",true); f7=n7; }
        if(g_selecting) {
            if(!openedAt) {openedAt=GetTickCount(); drawsAtOpen=g_selectorDraws;}
            else if(!silentLogged&&GetTickCount()-openedAt>1500&&g_selectorDraws==drawsAtOpen) {
                silentLogged=true;
                char l[160];sprintf_s(l,"Fenetre de choix ouverte mais jamais dessinee (%ld presentations interceptees au total).",g_presents);Log(l);
            }
        } else openedAt=0;
        const bool n5=(GetAsyncKeyState(VK_F5)&0x8000)!=0;
        if(n5&&!f5) ActionPrimary("F5");
        f5=n5;
        const bool nl=(GetAsyncKeyState(VK_LEFT)&0x8000)!=0, nr=(GetAsyncKeyState(VK_RIGHT)&0x8000)!=0;
        const bool ne=(GetAsyncKeyState(VK_RETURN)&0x8000)!=0, nx=(GetAsyncKeyState(VK_ESCAPE)&0x8000)!=0;
        if(g_selecting) {
            if((nl&&!fl)||(nr&&!fr)) SelectToggle();
            if(ne&&!fe) ActionPrimary("Entree");
            if(nx&&!fx) ActionRelease("Echap");
        }
        fl=nl; fr=nr; fe=ne; fx=nx;
        const bool n6=(GetAsyncKeyState(VK_F6)&0x8000)!=0;
        if(n6&&!f6) ActionRelease("F6");
        f6=n6;
    }
}

static bool HashMatches(const char* path,const char* expected) {
    HANDLE f=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;
    HCRYPTPROV p=0;HCRYPTHASH h=0;bool ok=false;DWORD read=0;BYTE buf[65536],dig[32];DWORD n=32;
    if(!CryptAcquireContextA(&p,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT))goto done;
    if(!CryptCreateHash(p,CALG_SHA_256,0,0,&h))goto done;
    for(;;){if(!ReadFile(f,buf,sizeof(buf),&read,nullptr))goto done;if(!read)break;if(!CryptHashData(h,buf,read,0))goto done;}
    if(CryptGetHashParam(h,HP_HASHVAL,dig,&n,0)){char hex[65];for(unsigned i=0;i<32;++i)sprintf_s(hex+i*2,3,"%02x",dig[i]);ok=strcmp(hex,expected)==0;}
done:
    if(h)CryptDestroyHash(h);if(p)CryptReleaseContext(p,0);CloseHandle(f);return ok;
}

static DWORD ReadHex(const char* ini,const char* key,DWORD def) {
    char v[32]; GetPrivateProfileStringA("ReplayTakeover",key,"",v,sizeof(v),ini);
    return v[0]?strtoul(v,nullptr,0):def;
}

static DWORD WINAPI Worker(void*) {
    char gamePath[MAX_PATH]; if(!GetModuleFileNameA(nullptr,gamePath,MAX_PATH)) return 0;
    strcpy_s(g_root,gamePath); char* s=strrchr(g_root,'\\'); if(!s) return 0; s[1]=0;
    sprintf_s(g_logPath,"%sDOA5LR-ReplayTakeover.log",g_root);
    { FILE* f=nullptr; if(!fopen_s(&f,g_logPath,"w")&&f) fclose(f); }   // journal neuf a chaque lancement
    Log("=== DOA5LR Replay Takeover 2.5 : tout se fait en memoire, aucun fichier du jeu n est modifie. ===");

    char ini[MAX_PATH]; sprintf_s(ini,"%sDOA5LR-ReplayTakeover.ini",g_root);
    if(!GetPrivateProfileIntA("ReplayTakeover","Enabled",1,ini)) {Log("Desactive par configuration."); return 0;}
    g_skipPresent=GetPrivateProfileIntA("ReplayTakeover","SkipPresent",1,ini)!=0;
    g_btnTake=ReadHex(ini,"BoutonPrise",0x4000);
    g_btnRewind=ReadHex(ini,"BoutonRetour",0x200);
    g_btnRelease=ReadHex(ini,"BoutonRendre",0x100);
    g_btnExact=ReadHex(ini,"BoutonRetourExact",0x400);
    {UINT t=GetPrivateProfileIntA("ReplayTakeover","PasRattrapage",10,ini); g_catchTicks=t<1?1:t>16?16:t;}
    g_logButtons=GetPrivateProfileIntA("ReplayTakeover","JournalBoutons",0,ini)!=0;
    g_showChoice=GetPrivateProfileIntA("ReplayTakeover","ChoixJoueur",1,ini)!=0;
    if(!HashMatches(gamePath,GAME_SHA)) {Log("REFUS : empreinte de game.exe differente."); return 0;}

    HMODULE pinned=nullptr;
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCSTR>(&Worker),&pinned);
    Sleep(3000);
    BYTE* image=reinterpret_cast<BYTE*>(GetModuleHandleA(nullptr));
    auto dos=reinterpret_cast<IMAGE_DOS_HEADER*>(image);
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS32*>(image+dos->e_lfanew);
    if(nt->FileHeader.TimeDateStamp!=EXPECTED_TIMESTAMP||nt->OptionalHeader.SizeOfImage!=EXPECTED_IMAGE_SIZE) {Log("REFUS : image PE differente."); return 0;}
    g_base=image;

    static const BYTE feed[6]={0x55,0x8B,0xEC,0x83,0xEC,0x2C};
    static const BYTE poll[6]={0x55,0x8B,0xEC,0x83,0xEC,0x6C};
    static const BYTE fight[5]={0x55,0x8B,0xEC,0x6A,0xFF};
    const bool okFeed =Detour(image+RVA_FEED,feed,6,&FeedThunk,&g_resumeFeed);
    const bool okPoll =Detour(image+RVA_POLLER,poll,6,&PollThunk,&g_resumePoll);
    const bool okFight=Detour(image+RVA_FIGHT_FRAME,fight,5,&FightFrameThunk,&g_resumeFightFrame);
    const bool okPres =HookPresent();
    // points de controle
    base=g_base;                                           // global lu par Checkpoint.h
    static const BYTE physicsBytes[6]={0x55,0x8B,0xEC,0x56,0x8B,0xF1};
    static const BYTE componentBytes[5]={0x55,0x8B,0xEC,0x6A,0xFF};
    static const BYTE allocationBytes[14]={0x55,0x8B,0xEC,0x83,0xC1,0x04,0x8B,0x01,0x8B,0x40,0x14,0x5D,0xFF,0xE0};
    static const BYTE callBytes[5]={0xE8,0xB4,0x11,0xF4,0xFF};
    bool okCheckpoint=okFight&&!memcmp(image+0x3F6857,callBytes,5)&&!memcmp(image+0xC64D0,physicsBytes,6)&&
        !memcmp(image+0x59EC00,componentBytes,5)&&image[0x59EC05]==0x68&&!memcmp(image+0x59ED20,componentBytes,5)&&image[0x59ED25]==0x68&&
        !memcmp(image+0x7CBB80,allocationBytes,14);
    if(okCheckpoint) {
        cp::allocations=static_cast<cp::Allocation*>(VirtualAlloc(nullptr,cp::allocationSlots*sizeof(cp::Allocation),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        BYTE* unused=nullptr;
        okCheckpoint=cp::allocations&&
            Detour(image+0x7CBB80,allocationBytes,6,&AllocationThunk,&unused)&&
            Detour(image+0xC64D0,physicsBytes,6,&PhysicsThunk,&g_resumePhysics)&&
            Detour(image+0x59EC00,componentBytes,5,&ComponentLoadThunk,&g_resumeComponentLoad)&&
            Detour(image+0x59ED20,componentBytes,5,&ComponentSaveThunk,&g_resumeComponentSave);
        if(okCheckpoint) {                                    // l appel en 0x3F6857 vise desormais FightEndThunk
            g_fightFrameFn=image+RVA_FIGHT_FRAME;
            DWORD old=0,ig=0;BYTE* call=image+0x3F6857;
            if(VirtualProtect(call,5,PAGE_EXECUTE_READWRITE,&old)) {
                *reinterpret_cast<DWORD*>(call+1)=reinterpret_cast<DWORD>(&FightEndThunk)-reinterpret_cast<DWORD>(call)-5;
                VirtualProtect(call,5,old,&ig);FlushInstructionCache(GetCurrentProcess(),call,5);
            } else okCheckpoint=false;
        }
    }
    // pas de simulation par image (rattrapage) : 0x423420 (8B 0D [108B490] ...) remplace entierement
    BYTE tickBytes[6]={0x8B,0x0D}; *reinterpret_cast<DWORD*>(tickBytes+2)=reinterpret_cast<DWORD>(image+0x108B490);
    BYTE* unusedTick=nullptr;
    const bool okTicks=Detour(image+0x423420,tickBytes,6,&TickCountThunk,&unusedTick);
    {   // 2.5 : 0x3F4C35 = call 0x597AA0 (mise a jour de la scene par image affichee) : code verifie
        BYTE* call=image+0x3F4C35;
        g_sceneFrameOk=call[0]==0xE8 && reinterpret_cast<DWORD>(call)+5+*reinterpret_cast<DWORD*>(call+1)==reinterpret_cast<DWORD>(image+0x597AA0) &&
            image[0x597AA0]==0x55 && image[0x597AA1]==0x8B && image[0x597AA2]==0xEC && image[0x597AA3]==0xF3;
        Log(g_sceneFrameOk?"Scene : mise a jour de la scene entre les pas du rattrapage.":"Scene : mise a jour de la scene entre les pas indisponible (code different).");
    }
    // reconstruction de la scene (2.2) : 0x5964C0, 0x597AF0, 0x597B10, 0x597940 verifies octet par octet
    {
        const DWORD mgr=reinterpret_cast<DWORD>(image+0x2072580);
        BYTE a[9]={0xA1,0,0,0,0,0x8B,0x40,0x0C,0}; memcpy(a+1,&mgr,4);
        BYTE b[13]={0x55,0x8B,0xEC,0x8B,0x45,0x08,0x8B,0x0D,0,0,0,0,0x50}; memcpy(b+8,&mgr,4);
        BYTE c[7]={0x8B,0x0D,0,0,0,0,0xE9}; memcpy(c+2,&mgr,4);
        static const BYTE e[12]={0x55,0x8B,0xEC,0x8B,0x45,0x08,0x83,0xEC,0x10,0x56,0x8B,0xF1};
        cp::rebuildAvailable=okCheckpoint&&!memcmp(image+0x5964C0,a,8)&&!memcmp(image+0x597AF0,b,13)&&
            !memcmp(image+0x597B10,c,7)&&!memcmp(image+0x597940,e,12);
    }
    char l[260];
    sprintf_s(l,"Points d accroche : lecteur %s, manettes %s, boucle du combat %s, affichage %s, points de controle %s.",
        okFeed?"oui":"REFUS",okPoll?"oui":"REFUS",okFight?"oui":"REFUS",okPres?"oui":"non (rattrapage sans saut d images)",
        okCheckpoint?"oui":"non (retour par rattrapage accelere seulement)");
    Log(l);
    Log(cp::rebuildAvailable?"Decor : remis a neuf par le jeu au retour si un objet a ete casse (reconstruction de la scene).":"Decor : REFUS de la reconstruction de la scene (retour par rattrapage si un objet a ete casse).");
    if(okTicks) sprintf_s(l,"Rattrapage : %lu pas de simulation par image affichee.",g_catchTicks);
    else sprintf_s(l,"Rattrapage : REFUS des pas natifs (rattrapage plus lent).");
    Log(l);
    if(!okFeed||!okPoll) {Log("Module inactif : le jeu n a pas la forme attendue."); return 0;}
    sprintf_s(l,"Touches : F5 / bouton %08lX = prendre la main ; pendant la reprise F5 / bouton %08lX = revenir au point, F6 / bouton %08lX = revenir au point et rendre la main, F7 / bouton %08lX = retour avec le decor remis a neuf.",
        g_btnTake,g_btnRewind,g_btnRelease,g_btnExact);
    Log(l);
    HANDLE t=CreateThread(nullptr,0,Keys,nullptr,0,nullptr); if(t) CloseHandle(t);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID) {
    if(reason==DLL_PROCESS_ATTACH) {DisableThreadLibraryCalls(h); HANDLE t=CreateThread(nullptr,0,Worker,nullptr,0,nullptr); if(t) CloseHandle(t);}
    return TRUE;
}
