// DOA5LR 1.10C / AutoLink 3.30 v0.13b: v0.13 + offline paths require no online reader (online reader desync fix).
// Native timing tables and combat code are untouched. AutoLink's own FPS
// compensation factor is halved only while an eligible menu requests 60 fps.
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* -DNO_LOG : build release sans journal (le fichier .log n'est jamais cree) ; -debug : journal d'etat comme avant */
#ifdef NO_LOG
#define LOG_OPEN() ((FILE*)1)
#define fprintf(...) ((void)0)
#define fclose(f) ((void)0)
#define setvbuf(...) ((void)0)
#else
#define LOG_OPEN() _wfopen(logpath,L"w")
#endif

static BYTE *base, *albase;
static WCHAR ini[MAX_PATH], logpath[MAX_PATH];
static volatile LONG enabled, forced, filter_calls, menu_calls;
static BYTE *tracked;
static DWORD last_tick;
static BOOL scale_owned;
static float saved_fps_factor, written_fps_factor, written_scale;
static void (__cdecl *native_set)(int);
static void (__cdecl *native_refresh)(void);
static volatile LONG intro_enabled, match_intros_enabled, match_subframes_enabled, intro_active, intro_completed;
static BYTE *intro_blocked;
static BOOL intro_seen;
static int upstream_mode;
static volatile LONG win_enabled, story_enabled;
static int active_scene_kind;
static BOOL refreshing;
void *menu_original, *main_delete_original, *select_delete_original, *stage_delete_original;
void *movie_begin_original, *movie_update_original, *movie_end_original;

typedef struct {
    volatile LONG ready;
    DWORD tick, phase, mode, pending, gui;
    int event, active, completed;
    float factor, input, step, derived;
    DWORD animation[2], move[2];
    float frame[2], speed[2];
} IntroTrace;
static IntroTrace intro_trace[1024];
static volatile LONG trace_count;

static void trace_intro(int event) {
    LONG n=InterlockedIncrement(&trace_count)-1;
    if(n<0 || n>=1024)return;
    IntroTrace *t=&intro_trace[n];
    t->tick=GetTickCount();t->event=event;t->active=intro_active;t->completed=intro_completed;
    t->phase=*(DWORD*)(base+0xfce5cc);t->pending=*(DWORD*)(base+0x108b488);
    DWORD idx=*(DWORD*)(base+0x108b490)&3;
    t->mode=*(DWORD*)(base+0x108b448+idx*16);t->gui=*(DWORD*)(base+0xf8a7ac);
    t->factor=*(float*)(albase+0xbd634);t->input=*(float*)(base+0xdd8fbc);
    t->step=*(float*)(base+0xdd8fb8);t->derived=*(float*)(base+0xf9cec0);
    for(int p=0;p<2;p++) {
        BYTE *actor=base+0xfd0540+p*0x6c8;
        t->animation[p]=*(DWORD*)(actor+0x64);t->move[p]=*(DWORD*)(actor+0x6c);
        t->frame[p]=*(float*)(base+0xfcc0f0+p*4);t->speed[p]=*(float*)(base+0xfcc4b8+p*4);
    }
    InterlockedExchange(&t->ready,1);
}

// Only the game's own refresh routine computes the derived timing values.
// Calling it synchronously at intro boundaries is the hypothesis under test.
static void refresh_intro_timing(void) {
    if(refreshing)return;
    refreshing=TRUE;native_refresh();refreshing=FALSE;
}

static BOOL readmem(const void *p,void *out,SIZE_T n) {
    SIZE_T done=0;
    return ReadProcessMemory(GetCurrentProcess(),p,out,n,&done) && done==n;
}
static BOOL equal(const void *p,const void *expected,SIZE_T n) {
    BYTE b[128];return n<=sizeof(b)&&readmem(p,b,n)&&!memcmp(b,expected,n);
}
static DWORD u32(const BYTE *p) {DWORD v;memcpy(&v,p,4);return v;}

static void release_scale(void) {
    if(!scale_owned)return;
    float *fps=(float*)(albase+0xbd634), *scale=(float*)(base+0xdd8fbc);
    if(!memcmp(fps,&written_fps_factor,4))*fps=saved_fps_factor;
    if(!memcmp(scale,&written_scale,4))
        *scale=*fps * *(float*)(albase+0xbd638) * *(float*)(albase+0xbd268);
    scale_owned=FALSE;
}

static void apply_scale(void) {
    float *fps=(float*)(albase+0xbd634), *scale=(float*)(base+0xdd8fbc);
    saved_fps_factor=*fps;
    written_fps_factor=saved_fps_factor*0.5f;
    written_scale=written_fps_factor * *(float*)(albase+0xbd638) * *(float*)(albase+0xbd268);
    *fps=written_fps_factor;*scale=written_scale;scale_owned=TRUE;
}

// Context must be a live, visible instance of one of the three verified menus.
static BOOL eligible(BYTE *object) {
    BYTE header[0x6c];
    if(!object || !readmem(object,header,sizeof(header)))return FALSE;
    DWORD vt=u32(header), id=u32(header+4);
    if(!((vt==(DWORD)(base+0xc0f22c)&&id==9) ||
         (vt==(DWORD)(base+0xc0cea4)&&id==4) ||
         (vt==(DWORD)(base+0xc0d2cc)&&id==5)))return FALSE;
    return header[0x6a]==1 && header[0x6b]==1 &&
        *(DWORD*)(base+0xf8a7ac)==id && *(DWORD*)(base+0xfce5cc)==0;
}

static BOOL intro_eligible(void) {
    if(!intro_enabled)return FALSE;
    DWORD phase=*(DWORD*)(base+0xfce5cc);
    DWORD gui=*(DWORD*)(base+0xf8a7ac);
    if(phase<3 || phase>7 || (gui!=0xffffffff && !(match_intros_enabled && gui==0)))return FALSE;
    if(gui==0xffffffff && *(DWORD*)(base+0xf8f208)!=0)return FALSE; // v0.13b: GUI -1 path is offline only
    BYTE *object=*(BYTE**)(base+0xfce5e8),header[8];
    if(!object || object==intro_blocked || !readmem(object,header,8) ||
       u32(header)!=(DWORD)(base+0x9b932c) || header[4]!=1)return FALSE;
    // No action IDs, timelines or asset bytes are edited. The legacy GUI-1
    // path below remains restricted to the measured offline animations.
    BYTE *a=base+0xfd0540,*b=a+0x6c8;
    if(gui==0) {
        // Online05 showed 60 presentation frames consuming a 30 Hz spectator
        // stream too quickly. GUI0 is now restricted to that reader plus the
        // paired subframe hooks; ordinary online participants are not covered.
        if(!match_subframes_enabled || *(DWORD*)(base+0xf8f208)!=5 || base[0xf8f208+0xcd8]!=1)return FALSE;
        // The online04 recording showed GUI0, a shared intro script for the
        // speaking actor, and a normal standing animation for the other one.
        // GUI0/phase4 alone is NOT sufficient: actual combat cameras also use
        // that combination. Require both move IDs to be stand and a speaking
        // actor executing the exact common Movie override script. The other
        // actor can use animation0 OR its native standing script: online08
        // actor02 uses animation104, with action0, while the speaker uses3ED.
        if(*(DWORD*)(a+0x6c)!=0 || *(DWORD*)(b+0x6c)!=0)return FALSE;
        for(int p=0;p<2;p++) {
            BYTE *actor=base+0xfd0540+p*0x6c8;
            BYTE *other=base+0xfd0540+(1-p)*0x6c8;
            DWORD anim=*(DWORD*)(actor+0x64),pc=*(DWORD*)(base+0xfcc6d8+p*4);
            BOOL known=anim>0 && anim<0xffff;
            DWORD other_anim=*(DWORD*)(other+0x64);
            DWORD other_pc=*(DWORD*)(base+0xfcc6d8+(1-p)*4);
            WORD instruction;
            BOOL other_common=other_pc>=(DWORD)(base+0xd016fc) && other_pc<=(DWORD)(base+0xd01706);
            BOOL other_standing=other_anim==0 || (other_anim<0xffff && !other_common &&
                other_pc>=0x10000 && readmem((void*)other_pc,&instruction,sizeof(instruction)));
            if(known && other_standing &&
               pc>=(DWORD)(base+0xd016fc) && pc<=(DWORD)(base+0xd01706))return TRUE;
        }
        return FALSE;
    }
    // Preserve the measured v0.7.1 behavior for the original GUI-1 context.
    if(!((a[4]==4 && b[4]==13)||(a[4]==13 && b[4]==4)))return FALSE;
    for(int p=0;p<2;p++) {
        BYTE *actor=base+0xfd0540+p*0x6c8;
        DWORD anim=*(DWORD*)(actor+0x64),pc=*(DWORD*)(base+0xfcc6d8+p*4);
        BOOL known=(actor[4]==4 && (anim==0x3ec || anim==0x3ee))||(actor[4]==13 && anim==0x3f5);
        if(known && *(DWORD*)(actor+0x6c)==0 &&
           pc>=(DWORD)(base+0xd016fc) && pc<=(DWORD)(base+0xd01706))return TRUE;
    }
    return FALSE;
}

// Spectator playback does not expose the local result controller in online10.
// Use the recorded rate and active Movie, not the local Win object. This
// extension is limited to a non-standing action scene whose SOURCE requests30.
// Source60 combat cameras always bypass this path, including identical poses.
static BOOL win_source_eligible(void) {
    if(!win_enabled || !match_intros_enabled || !match_subframes_enabled ||
       upstream_mode!=1 || *(DWORD*)(albase+0xffff0)!=1 ||
       *(DWORD*)(base+0xf8a7ac)!=0 || *(DWORD*)(base+0xf8f208)!=5 ||
       base[0xf8f208+0xcd8]!=1)return FALSE;
    DWORD phase=*(DWORD*)(base+0xfce5cc);
    BYTE *object=*(BYTE**)(base+0xfce5e8),header[8];
    if(phase<3 || phase>7 || !object || object==intro_blocked ||
       !readmem(object,header,sizeof(header)) || u32(header)!=(DWORD)(base+0x9b932c) || header[4]!=1)return FALSE;
    // Both standing actions remain on the separately verified intro path.
    BYTE *a=base+0xfd0540,*b=a+0x6c8;
    DWORD ma=*(DWORD*)(a+0x6c),mb=*(DWORD*)(b+0x6c);
    DWORD aa=*(DWORD*)(a+0x64),ab=*(DWORD*)(b+0x64);
    return (ma || mb) && ma<0xffff && mb<0xffff && aa<0xffff && ab<0xffff && (aa || ab);
}
// Story-mode cutscenes (offline): an active RealTimeMovie outside any match GUI
// (0 online, -1 offline), outside the three handled menus and the post-match
// result screen (14, observed for minutes at source30 after a local win).
// The online reader (type5) is never touched by this path.
static BOOL story_eligible(void) {
    if(!story_enabled || upstream_mode!=1 || *(DWORD*)(albase+0xffff0)!=1)return FALSE;
    DWORD gui=*(DWORD*)(base+0xf8a7ac);
    if(gui==4 || gui==5 || gui==9 || gui==14)return FALSE;
    // v0.13b: any active online reader (type 1 seen in 2-player rooms, type 5 in 3-player rooms) means an
    // online match. Session 20/09 22:53 (2-player room): the online intros (scenes 270/478) ran under
    // GUI -1 with reader type 1, were taken for story cutscenes and played at 60 fps without the
    // 30 Hz stream pairing -> desync -> "network error" right after the intro. Offline only.
    if(*(DWORD*)(base+0xf8f208)!=0)return FALSE;
    if(gui==0) {
        // Session 20/09: the post-fight story cutscenes (scene 42 after Mila/Zack, scene 30) run under the
        // match GUI 0 with both actors Movie-driven (move 0x118) or idle (0) and story animation IDs above
        // 0xFFFF (0x19e2e). Real fights never show 0/0x118 on both actors while a RealTimeMovie is active.
        BYTE *a=base+0xfd0540,*b=a+0x6c8;
        DWORD ma=*(DWORD*)(a+0x6c),mb=*(DWORD*)(b+0x6c);
        if(!((ma==0 || ma==0x118) && (mb==0 || mb==0x118)))return FALSE;
    }
    if(gui==0xffffffff) {
        // Session 19/09: story cutscenes (scenes 29/41) and the intros of every
        // character (269/1147) run under the offline match GUI -1, exactly like
        // combat and win cameras. Story/intro actors are idle (move 0) or
        // Movie-driven (move 0x118); combat, damage and win cameras carry
        // action IDs (0x7d11/0x206a/0x83/0x2070 in the recordings) and stay native.
        BYTE *a=base+0xfd0540,*b=a+0x6c8;
        DWORD ma=*(DWORD*)(a+0x6c),mb=*(DWORD*)(b+0x6c);
        if(!((ma==0 || ma==0x118) && (mb==0 || mb==0x118)))return FALSE;
        if(*(DWORD*)(a+0x64)>=0xffff || *(DWORD*)(b+0x64)>=0xffff)return FALSE;
    }
    DWORD phase=*(DWORD*)(base+0xfce5cc);
    BYTE *object=*(BYTE**)(base+0xfce5e8),header[8];
    return phase>=3 && phase<=7 && object && object!=intro_blocked && readmem(object,header,sizeof(header)) &&
        u32(header)==(DWORD)(base+0x9b932c) && header[4]==1;
}
// Offline win poses (session 20/09 21:45): after a local fight the win pose RealTimeMovie
// (scenes 401/1112) runs under the match GUI 0 with NO online reader (type 0; online
// participants and spectators always carry type 5) and AutoLink requests the 30 fps
// mode for it (ALrequest=1). Combat and the KO slow-motion keep mode 0 / scale 0.15,
// so keying on the 30 fps request alone never touches them.
static BOOL win_offline_eligible(void) {
    if(!win_enabled || upstream_mode!=1 || *(DWORD*)(albase+0xffff0)!=1)return FALSE;
    if(*(DWORD*)(base+0xf8a7ac)!=0)return FALSE;      // match GUI 0 only
    if(*(DWORD*)(base+0xf8f208)!=0)return FALSE;      // offline: no online reader
    DWORD phase=*(DWORD*)(base+0xfce5cc);
    BYTE *object=*(BYTE**)(base+0xfce5e8),header[8];
    return phase>=3 && phase<=7 && object && object!=intro_blocked && readmem(object,header,sizeof(header)) &&
        u32(header)==(DWORD)(base+0x9b932c) && header[4]==1;
}
static int scene_kind(void) {
    if(intro_eligible())return 1;
    if(win_source_eligible())return 2;
    if(story_eligible())return 3;
    return win_offline_eligible()?4:0;
}
#include "reader_subframes.h"

static void release_intro(void) {
    if(!intro_active)return;
    trace_intro(3); // immediately before restoration
    release_scale();
    InterlockedExchange(&intro_active,0);active_scene_kind=0;
    if(InterlockedExchange(&forced,0) && upstream_mode>=0 && upstream_mode<=4 &&
       *(DWORD*)(base+0x108b488)==0)native_set(upstream_mode);
    refresh_intro_timing();
    trace_intro(4); // derived time restored before original end/actor cleanup
}

// AutoLink keeps its own original requested mode. We filter only the output
// to the native setter, so its next non-menu request restores native behavior.
static void __cdecl filtered_set(int mode) {
    InterlockedIncrement(&filter_calls);
    // Both AutoLink callsites write their current FPS factor and scale before
    // calling this pointer: they supersede our previous values, including a
    // legitimate 0.5 cinema/slow-motion value equal to our last menu value.
    BOOL was_intro=intro_active;
    scale_owned=FALSE;upstream_mode=mode;
    BOOL want_menu=enabled && mode==1 && (DWORD)(GetTickCount()-last_tick)<=100 && eligible(tracked);
    int kind=mode==1?scene_kind():0;
    BOOL want_intro=kind!=0;active_scene_kind=kind;
    BOOL want=want_menu || want_intro;
    if(want)apply_scale();
    if(want_intro)intro_seen=TRUE;
    InterlockedExchange(&intro_active,want_intro);
    InterlockedExchange(&forced,want);
    native_set(want?0:mode);
    if(was_intro || want_intro) {refresh_intro_timing();trace_intro(5);}
}

static void release_menu(void) {
    tracked=NULL;
    if(intro_active)return; // ownership already passed to the intro
    release_scale();
    if(InterlockedExchange(&forced,0)) {
        DWORD cached=*(DWORD*)(albase+0xffff0);
        // Leave later native requests intact. AutoLink's cached mode is never edited.
        if(cached<=4 && *(DWORD*)(base+0x108b488)==0)native_set((int)cached);
    }
}

void __cdecl menu_before(BYTE *object) {
    InterlockedIncrement(&menu_calls);
    if(eligible(object)) {
        tracked=object;last_tick=GetTickCount();
        DWORD requested=*(DWORD*)(albase+0xffff0);
        // This path has no preceding AutoLink calculation. Release our own
        // previous factor first, preventing cumulative 0.5 -> 0.25 -> ... drift.
        release_scale();
        if(requested<=4) {
            BOOL want=enabled && requested==1;
            if(want)apply_scale();
            InterlockedExchange(&forced,want);
            native_set(want?0:(int)requested);
        }
    } else if(tracked==object)release_menu();
}
void __cdecl menu_leaving(BYTE *object) {if(tracked==object)release_menu();}

void __cdecl movie_begin(BYTE *object) {
    if(intro_blocked==object)intro_blocked=NULL;
}
void __cdecl movie_before(BYTE *object) {
    if(object!=*(BYTE**)(base+0xfce5e8))return;
    int kind=scene_kind();
    if(upstream_mode==1 && kind) {
        active_scene_kind=kind;
        intro_seen=TRUE;
        release_scale();apply_scale();
        InterlockedExchange(&intro_active,1);InterlockedExchange(&forced,1);
        native_set(0);refresh_intro_timing();trace_intro(1);
    } else release_intro();
}
void __cdecl movie_leaving(BYTE *object) {
    if(object!=*(BYTE**)(base+0xfce5e8))return;
    BOOL tested=intro_seen;
    intro_seen=FALSE;
    intro_blocked=object;release_intro();
    if(tested)InterlockedIncrement(&intro_completed);
}

// Preserve the original thiscall ABI, arguments, return value, flags, x87/SSE
// and registers. Helpers run BEFORE native updates, so native transitions win.
#define BEFORE_HELPER(helper,target) \
    __asm__ volatile("pushfl\n pushal\n mov %esp,%ebp\n sub $544,%esp\n and $-16,%esp\n" \
        "fxsave 16(%esp)\n mov %ecx,(%esp)\n call _" helper "\n fxrstor 16(%esp)\n" \
        "mov %ebp,%esp\n popal\n popfl\n jmp *_" target "\n")
__attribute__((naked,thiscall)) void menu_hook(void *object) {BEFORE_HELPER("menu_before","menu_original");}
__attribute__((naked,thiscall)) int main_delete_hook(void *object,int flags) {BEFORE_HELPER("menu_leaving","main_delete_original");}
__attribute__((naked,thiscall)) int select_delete_hook(void *object,int flags) {BEFORE_HELPER("menu_leaving","select_delete_original");}
__attribute__((naked,thiscall)) int stage_delete_hook(void *object,int flags) {BEFORE_HELPER("menu_leaving","stage_delete_original");}
__attribute__((naked,thiscall)) int movie_begin_hook(void *object,int arg) {BEFORE_HELPER("movie_begin","movie_begin_original");}
__attribute__((naked,thiscall)) int movie_update_hook(void *object,float dt) {BEFORE_HELPER("movie_before","movie_update_original");}
__attribute__((naked,thiscall)) int movie_end_hook(void *object) {BEFORE_HELPER("movie_leaving","movie_end_original");}

typedef struct {void **slot;void *original;void *replacement;} Hook;
static BOOL exchange(Hook *h,BOOL install) {
    DWORD old,unused;
    if(!VirtualProtect(h->slot,sizeof(void*),PAGE_READWRITE,&old))return FALSE;
    void *expected=install?h->original:h->replacement;
    void *value=install?h->replacement:h->original;
    void *previous=InterlockedCompareExchangePointer(h->slot,value,expected);
    VirtualProtect(h->slot,sizeof(void*),old,&unused);
    return previous==expected;
}

static BOOL signatures(void) {
    DWORD table[15]={1,1,1,2,1,2,3,1,3,1,1,1,2,2,1};
    BYTE setter[20]={0x55,0x8b,0xec,0x8b,0x45,8,0xa3,0,0,0,0,0xc6,5,0,0,0,0,1,0x5d,0xc3};
    DWORD addr=(DWORD)(base+0x108b488);memcpy(setter+7,&addr,4);
    addr=(DWORD)(base+0x108b494);memcpy(setter+13,&addr,4);
    BYTE dispatch[17]={0x80,0x79,0x6a,0,0x74,0x0a,0x8b,1,0x8b,0x90,0x84,0,0,0,0xff,0xe2,0xc3};
    BYTE getter[7]={0xd9,5,0,0,0,0,0xc3};addr=(DWORD)(base+0xdd8fb8);memcpy(getter+2,&addr,4);
    void *expected=base+0x423330;
    void *expected_scale=base+0xdd8fbc;
    BYTE alcall[6]={0xff,0x15,0,0,0,0};addr=(DWORD)(albase+0xffff4);memcpy(alcall+2,&addr,4);
    return equal(base+0x9c1dac,table,sizeof(table)) && equal(base+0x423330,setter,sizeof(setter)) &&
        equal(base+0x690100,dispatch,sizeof(dispatch)) && equal(base+0x3f53f0,getter,7) &&
        equal(albase+0xffff4,&expected,4) && equal(albase+0xfffe8,&expected_scale,4) &&
        equal(albase+0x4cd8a,alcall,6) && equal(albase+0x4cdba,alcall,6);
}

static BOOL refresh_signature(void) {
    BYTE prefix[20]={0x55,0x8b,0xec,0x51,0xf3,0x0f,0x10,0x05,0,0,0,0,0xf3,0x0f,0x10,0x15,0,0,0,0};
    DWORD addr=(DWORD)(base+0xdd8fbc);memcpy(prefix+8,&addr,4);
    addr=(DWORD)(base+0xdd8fb8);memcpy(prefix+16,&addr,4);
    const BYTE tail[]={0x5b,0x8b,0xe5,0x5d,0xc3};
    return equal(base+0x3f5480,prefix,sizeof(prefix)) && equal(base+0x3f5570,tail,sizeof(tail));
}

static DWORD WINAPI worker(void *unused) {
    (void)unused;
    FILE *log=LOG_OPEN();if(!log)return 0;
    setvbuf(log,NULL,_IONBF,0);
    fprintf(log,"v0.13b; v0.13 + offline paths only without online reader (reader type 1 desync fix). PID=%lu\n",GetCurrentProcessId());
    BOOL ready=FALSE;
    for(int n=0;n<600;n++) {
        albase=(BYTE*)GetModuleHandleW(L"dinput8Hooked.dll");
        if(albase && signatures() && refresh_signature()) {ready=TRUE;break;}
        Sleep(100);
    }
    if(!ready){fprintf(log,"Incompatible/missing AutoLink or native signatures. No changes.\n");fclose(log);return 0;}
    native_set=(void(__cdecl*)(int))(base+0x423330);
    native_refresh=(void(__cdecl*)(void))(base+0x3f5480);
    movie_begin_original=base+0x321e70;movie_update_original=base+0x320250;movie_end_original=base+0x321030;
    reader_original=(void*)(base+0x528500);reader_advance_original=(void*)(base+0x524a20);
    ReaderCall reader_calls[]={
        {0x3f4aeb,(void*)reader_original,(void*)reader_hook},
        {0x40c463,(void*)reader_advance_original,(void*)reader_advance_hook}
    };
    const BYTE reader_prefix[]={0x53,0x56,0x8b,0xf1,0x32,0xdb,0x88,0x9e,0x08,0x0d,0,0};
    const BYTE advance_prefix[]={0x55,0x8b,0xec,0x81,0xec,0xb4,0,0,0,0x53,0x8b,0xd9};
    if(!reader_call_matches(&reader_calls[0]) || !reader_call_matches(&reader_calls[1]) ||
       !equal(base+0x528500,reader_prefix,sizeof(reader_prefix)) ||
       !equal(base+0x524a20,advance_prefix,sizeof(advance_prefix))) {
        fprintf(log,"Reader signatures differ. No changes.\n");fclose(log);return 0;
    }
    upstream_mode=*(DWORD*)(base+0x108b488);
    menu_original=base+0x690100;
    main_delete_original=base+0x6f0f50;select_delete_original=base+0x691d40;
    stage_delete_original=base+0x6944f0;
    Hook hooks[]={
        {(void**)(albase+0xffff4),(void*)native_set,(void*)filtered_set},
        {(void**)(base+0xc0f22c+12),menu_original,(void*)menu_hook},
        {(void**)(base+0xc0cea4+12),menu_original,(void*)menu_hook},
        {(void**)(base+0xc0d2cc+12),menu_original,(void*)menu_hook},
        {(void**)(base+0xc0f22c),main_delete_original,(void*)main_delete_hook},
        {(void**)(base+0xc0cea4),select_delete_original,(void*)select_delete_hook},
        {(void**)(base+0xc0d2cc),stage_delete_original,(void*)stage_delete_hook},
        {(void**)(base+0x9b932c+4),movie_begin_original,(void*)movie_begin_hook},
        {(void**)(base+0x9b932c+8),movie_update_original,(void*)movie_update_hook},
        {(void**)(base+0x9b932c+16),movie_end_original,(void*)movie_end_hook}
    };
    unsigned count=sizeof(hooks)/sizeof(hooks[0]);
    for(unsigned n=0;n<count;n++) {
        if(!equal(hooks[n].slot,&hooks[n].original,4)) {
            fprintf(log,"Conflicting pointer %u. No changes.\n",n);fclose(log);return 0;
        }
    }
    unsigned installed=0;
    for(;installed<count;installed++)if(!exchange(&hooks[installed],TRUE))break;
    if(installed!=count) {
        while(installed)exchange(&hooks[--installed],FALSE);
        fprintf(log,"Pointer installation failed; installed pointers rolled back.\n");fclose(log);return 0;
    }
    unsigned patched=0;
    for(;patched<2;patched++)if(!reader_call_exchange(&reader_calls[patched],TRUE))break;
    if(patched!=2) {
        while(patched)reader_call_exchange(&reader_calls[--patched],FALSE);
        while(installed)exchange(&hooks[--installed],FALSE);
        fprintf(log,"Reader installation failed; all own hooks rolled back.\n");fclose(log);return 0;
    }
    fprintf(log,"Ready: menus + legacy intros; source30 spectator action Movies and intro subframes; source60 bypass; no participant extension or local Win hooks.\n");
    unsigned trace_read=0;
    int previous_enabled=-1, previous_gui=-1, previous_forced=-1,previous_phase=-1;
    DWORD previous_mode=~0u,last_report=0,previous_scene=~0u;
    for(;;) {
        LONG on=GetPrivateProfileIntW(L"Menus",L"Enabled",0,ini)!=0;
        InterlockedExchange(&enabled,on);
        InterlockedExchange(&intro_enabled,GetPrivateProfileIntW(L"IntroTest",L"Enabled",0,ini)!=0);
        InterlockedExchange(&match_intros_enabled,GetPrivateProfileIntW(L"IntroTest",L"MatchContext",0,ini)!=0);
        InterlockedExchange(&match_subframes_enabled,GetPrivateProfileIntW(L"IntroTest",L"SpectatorSubframes",0,ini)!=0);
        InterlockedExchange(&win_enabled,GetPrivateProfileIntW(L"IntroTest",L"WinPoses",0,ini)!=0);
        InterlockedExchange(&story_enabled,GetPrivateProfileIntW(L"StoryTest",L"Enabled",0,ini)!=0);
        while(trace_read<1024 && intro_trace[trace_read].ready) {
            IntroTrace *t=&intro_trace[trace_read++];
            fprintf(log,"INTRO event=%d t=%lu phase=%ld gui=%ld active=%d completed=%d mode=%lu pending=%lu factor=%.3f input=%.3f step=%.3f derived=%.3f anim=%lx/%lx move=%lx/%lx frame=%.3f/%.3f speed=%.3f/%.3f\n",
                t->event,t->tick,(LONG)t->phase,(LONG)t->gui,t->active,t->completed,t->mode,t->pending,t->factor,t->input,t->step,t->derived,
                t->animation[0],t->animation[1],t->move[0],t->move[1],t->frame[0],t->frame[1],t->speed[0],t->speed[1]);
        }
        int gui=*(DWORD*)(base+0xf8a7ac),phase=*(DWORD*)(base+0xfce5cc);
        DWORD idx=*(DWORD*)(base+0x108b490)&3;
        DWORD mode=*(DWORD*)(base+0x108b448+idx*16);
        int active=forced;
        DWORD now=GetTickCount();
        // Diagnostic only: identify the story context (scene id, actors) for the gate above.
        BYTE *movie=*(BYTE**)(base+0xfce5e8),movie_header[0x20];
        DWORD scene=~0u;int movie_active=-1;
        if(phase>=3 && phase<=7 && movie && readmem(movie,movie_header,sizeof(movie_header)) &&
           u32(movie_header)==(DWORD)(base+0x9b932c)) {scene=u32(movie_header+0x1c);movie_active=movie_header[4];}
        if(on!=previous_enabled || gui!=previous_gui || active!=previous_forced ||
           phase!=previous_phase || mode!=previous_mode || scene!=previous_scene || now-last_report>=10000) {
            if(scene!=~0u)fprintf(log,"RTM gui=%d phase=%d movie=%p active=%d scene=%lu kind=%d readerType=%lu anim=%lx/%lx move=%lx/%lx\n",
                gui,phase,(void*)movie,movie_active,scene,active_scene_kind,*(DWORD*)(base+0xf8f208),
                *(DWORD*)(base+0xfd0540+0x64),*(DWORD*)(base+0xfd0540+0x6c8+0x64),
                *(DWORD*)(base+0xfd0540+0x6c),*(DWORD*)(base+0xfd0540+0x6c8+0x6c));
            fprintf(log,"t=%lu enabled=%ld gui=%d phase=%d override=%d nativeMode=%lu ALrequest=%lu menuCalls=%ld filterCalls=%ld FPSfactor=%.3f scale=%.3f\n",
                now,on,gui,phase,active,mode,*(DWORD*)(albase+0xffff0),menu_calls,filter_calls,
                *(float*)(albase+0xbd634),*(float*)(base+0xdd8fbc));
            fprintf(log,"READER subframes=%ld type=%lu reads=%ld reused=%ld advances=%ld held=%ld seq=%lu index=%lu data=%u\n",
                match_subframes_enabled,*(DWORD*)(base+0xf8f208),reader_reads,reader_reuses,reader_advances,reader_holds,
                *(DWORD*)(base+0xf8f208+0x10),*(DWORD*)(base+0xf8f208+0xcb0),base[0xf8f208+0xd08]);
            fprintf(log,"SOURCE_SCENE win_option=%ld story_option=%ld kind=%d\n",win_enabled,story_enabled,active_scene_kind);
            previous_enabled=on;previous_gui=gui;previous_forced=active;previous_phase=phase;previous_mode=mode;previous_scene=scene;last_report=now;
        }
        Sleep(250);
    }
}

#ifndef MENU_TEST
BOOL WINAPI DllMain(HINSTANCE inst,DWORD reason,LPVOID reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);base=(BYTE*)GetModuleHandleW(NULL);
        if(!GetModuleFileNameW(inst,ini,MAX_PATH))return TRUE;
        WCHAR *slash=wcsrchr(ini,L'\\');if(!slash || slash-ini>MAX_PATH-30)return TRUE;
        wcscpy(slash+1,L"DOA5LR-60fps-menus.ini");
        wcscpy(logpath,ini);wcscpy(wcsrchr(logpath,L'.'),L".log");
        HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);if(h)CloseHandle(h);
    }
    return TRUE;
}
#endif
