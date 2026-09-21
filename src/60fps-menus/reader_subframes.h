// Only the confirmed spectator reader (type5) can consume an intro packet
// over two presentation frames. Writer/participant and combat paths delegate.
static void (__attribute__((thiscall)) *reader_advance_original)(BYTE *);
static BYTE (__attribute__((thiscall)) *reader_original)(BYTE *);
static volatile LONG reader_reads,reader_reuses,reader_advances,reader_holds;
static BOOL reader_pending,reader_held;
static BYTE *reader_saved_object,*reader_saved_movie;
static DWORD reader_saved_seq,reader_saved_index,reader_saved_scene;
static DWORD reader_saved_anim[2],reader_saved_tick;
static int reader_saved_kind;

static void reader_reset(void) {
    reader_pending=reader_held=FALSE;reader_saved_object=NULL;
}
static BOOL reader_context(BYTE *object) {
    if(!match_subframes_enabled || !match_intros_enabled || object!=base+0xf8f208 ||
       *(DWORD*)object!=5 || object[0xcd8]!=1 || object[0xd08]!=1 ||
       *(DWORD*)(albase+0xffff0)!=1 || upstream_mode!=1)return FALSE;
    int kind=scene_kind();
    if(kind!=1 && kind!=2)return FALSE; // story (kind3) never pairs with the online reader
    DWORD seq=*(DWORD*)(object+0x10),index=*(DWORD*)(object+0xcb0);
    return index<24 && *(DWORD*)(object+0xcb4+(seq&3)*8)==2;
}
static void reader_remember(BYTE *object) {
    reader_saved_object=object;reader_saved_movie=*(BYTE**)(base+0xfce5e8);
    reader_saved_scene=*(DWORD*)(reader_saved_movie+0x1c);
    reader_saved_seq=*(DWORD*)(object+0x10);reader_saved_index=*(DWORD*)(object+0xcb0);
    for(int p=0;p<2;p++)reader_saved_anim[p]=*(DWORD*)(base+0xfd0540+p*0x6c8+0x64);
    reader_saved_kind=scene_kind();
    reader_saved_tick=GetTickCount();reader_pending=TRUE;
}
static BOOL reader_same(BYTE *object) {
    if(object!=reader_saved_object || (DWORD)(GetTickCount()-reader_saved_tick)>100 ||
       !reader_context(object))return FALSE;
    BYTE *movie=*(BYTE**)(base+0xfce5e8);
    return scene_kind()==reader_saved_kind && movie==reader_saved_movie && *(DWORD*)(movie+0x1c)==reader_saved_scene &&
        *(DWORD*)(object+0x10)==reader_saved_seq && *(DWORD*)(object+0xcb0)==reader_saved_index &&
        // During a result scene the loser's own timeline can change animation
        // between half-steps. That is not a new source packet or a new Movie.
        (reader_saved_kind==2 || (*(DWORD*)(base+0xfd0540+0x64)==reader_saved_anim[0] &&
         *(DWORD*)(base+0xfd0540+0x6c8+0x64)==reader_saved_anim[1]));
}
static void __attribute__((thiscall)) reader_advance_hook(BYTE *object) {
    // Never hold two consecutive cursor advances, even if the reader was not
    // called in between. A stale half-frame must not stall the native reader.
    if(reader_pending && !reader_held && reader_same(object)) {
        reader_pending=FALSE;reader_held=TRUE;
        InterlockedIncrement(&reader_holds);return;
    }
    reader_reset();InterlockedIncrement(&reader_advances);
    reader_advance_original(object);
}
static BYTE __attribute__((thiscall)) reader_hook(BYTE *object) {
    if(reader_held) {
        if(reader_same(object)) {
            reader_held=FALSE;reader_pending=FALSE;
            InterlockedIncrement(&reader_reuses);
            return 1; // Existing decoded data remains valid for one half-step.
        }
        // Setting/context changed after the advance hook: perform the held
        // native advance before reading, avoiding delivery of old events again.
        if(object==reader_saved_object) {
            InterlockedIncrement(&reader_advances);reader_advance_original(object);
        }
        reader_reset();
    }
    InterlockedIncrement(&reader_reads);
    BYTE result=reader_original(object);
    reader_pending=FALSE;
    if(result && reader_context(object))reader_remember(object);
    return result;
}

typedef struct {DWORD rva;void *original,*replacement;} ReaderCall;
static BOOL reader_call_matches(const ReaderCall *c) {
    BYTE bytes[5];
    return readmem(base+c->rva,bytes,5) && bytes[0]==0xe8 &&
        (DWORD)(base+c->rva+5)+(DWORD)u32(bytes+1)==(DWORD)c->original;
}
static BOOL reader_call_exchange(const ReaderCall *c,BOOL install) {
    // Both displacement operands are aligned, permitting atomic replacement.
    DWORD *operand=(DWORD*)(base+c->rva+1),old,unused;
    if(((uintptr_t)operand&3) || base[c->rva]!=0xe8)return FALSE;
    DWORD native=(DWORD)c->original-(DWORD)(base+c->rva+5);
    DWORD replacement=(DWORD)c->replacement-(DWORD)(base+c->rva+5);
    DWORD expected=install?native:replacement,value=install?replacement:native;
    if(!VirtualProtect(operand,4,PAGE_EXECUTE_READWRITE,&old))return FALSE;
    DWORD previous=(DWORD)InterlockedCompareExchange((LONG*)operand,(LONG)value,(LONG)expected);
    FlushInstructionCache(GetCurrentProcess(),base+c->rva,5);
    VirtualProtect(operand,4,old,&unused);
    return previous==expected;
}
