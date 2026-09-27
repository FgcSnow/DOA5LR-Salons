// Points de controle du Replay Takeover (moteur issu de la sonde DOA5LR-CheckpointProbe 0.55 ;
// recherche detaillee dans outputs/checkpoint-research/RESULTATS-SONDE-*.txt).
// Au moment de la reprise en main, l'etat du combat est copie ; L2 / R2 le remettent en
// place instantanement au lieu de relancer le replay puis de le rattraper en accelere.
// Ce qui est remis (valide frame par frame contre le replay d'origine en 0.26-0.55) :
//  - globaux du combat : RNG 1087AB0, joueurs FD0540 (+ secondaires FCF788, historiques
//    FCED68/FCEDD8), logique FCEE78, places d'entree, curseur du flux du replay et scalaires
//    du lecteur / gestionnaire ;
//  - animation : tableaux des deux owners de pose, descripteurs FCC760 et leurs matrices /
//    vecteurs, temps FCAB00, 258 canaux de decodage (curseurs gardes par empreinte),
//    indicateur d'avancement FCC214, position du corps FCBB00 ;
//  - physique secondaire (objets de la classe 0C64D0, 30Ch), fenetres statiques FCBAB0,
//    FCA000, FC7000, FCC000 (etat decisif, bisection 0.35) et cameras FB8000-FC0000 ;
//  - decor : fonctions load/save/apply du jeu pour les objets serialisables, puis regle
//    generale (objets du decor stables pendant les 10 frames suivant le point, meme type,
//    taille connue par l'accroche d'allocation, valeurs non pointeurs) et pages 1070000-107FFFF.
// Fin de round (choix de thebe, 25/09) : au K.O. (sante <= 0, mot +2C du bloc joueur, 300 au
// depart) ou au temps ecoule (chrono [10885DA] a 0), le point est efface et tout retour est
// desactive jusqu'a la prochaine reprise en main. Defaire la fin d'un round desynchronisait ou
// corrompait la memoire (sonde 0.36-0.54). Le point est aussi abandonne a la sortie de l'etat
// combat, au round suivant et si le replay repart en arriere.
// A fournir par l'appelant : base, Copy, Read, Log(const char*).
namespace cp {
struct Range { BYTE* address; DWORD size; const char* name; DWORD offset; };
struct Guard { BYTE* address; DWORD size; BYTE bytes[32]; };
struct Cursor { BYTE* target; void* allocation; };
static Range ranges[1024]; static unsigned count;
static Guard guards[1024]; static unsigned guardCount;
static Cursor cursors[258]; static unsigned cursorCount;
// 2.2 : objets physiques (classe 0x0C64D0) : plage et premiere des deux gardes (+4, +0x4C). Une
// reconstruction de la scene peut detruire ceux du decor : leur plage est alors sautee.
struct PhysicsRef { unsigned range,guard; };
static PhysicsRef physicsRefs[8]; static unsigned physicsCount;
static bool skip[1024];
static bool decorStale;                     // 2.2 : scene deja reconstruite pour ce point (voir RebuildScene)
static BYTE* animation[2];
static DWORD total,manager,threadId; static BYTE* reader;
static BYTE *saved,*scratch;
static constexpr DWORD limit=1024*1024;

static volatile LONG active;          // un point de controle existe
static DWORD savedFrame,lastFrame,frontierCount;
static volatile LONG requestSave,requestRestore;
static volatile LONG lastResult;      // 0 rien, 1 remis, 2 refuse (lu par le module)
static volatile LONG roundOver;       // K.O. / temps ecoule / fin du combat : plus de retour jusqu'a la prochaine reprise

static void Logf(const char* format,...) {
    char line[512];va_list a;va_start(a,format);vsprintf_s(line,format,a);va_end(a);Log(line);
}

// Physique secondaire : objets de la classe 0C64D0 notes par leur mise a jour.
struct Seen { DWORD object,stamp; };
static Seen seen[8];
static void NotePhysics(DWORD object) {
    unsigned oldest=0;
    for(unsigned i=0;i<8;++i){if(seen[i].object==object){seen[i].stamp=frontierCount;return;}if(seen[i].stamp<seen[oldest].stamp)oldest=i;}
    seen[oldest]={object,frontierCount};
}
static bool Writable(BYTE* p,DWORD n) {
    if(!p || !n || reinterpret_cast<uintptr_t>(p)+n<reinterpret_cast<uintptr_t>(p))return false;
    BYTE* end=p+n;
    while(p<end) {
        MEMORY_BASIC_INFORMATION m={};if(!VirtualQuery(p,&m,sizeof(m)))return false;
        DWORD protection=m.Protect&0xFF;
        if(m.State!=MEM_COMMIT || (m.Protect&PAGE_GUARD) ||
           (protection!=PAGE_READWRITE && protection!=PAGE_WRITECOPY))return false;
        BYTE* next=static_cast<BYTE*>(m.BaseAddress)+m.RegionSize;
        if(next<=p)return false;p=next<end?next:end;
    } return true;
}
static bool Readable(DWORD address,MEMORY_BASIC_INFORMATION& m) {
    if(!address || !VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof(m)))return false;
    DWORD p=m.Protect&0xFF;
    return m.State==MEM_COMMIT && !(m.Protect&PAGE_GUARD) &&
        (p==PAGE_READONLY || p==PAGE_READWRITE || p==PAGE_WRITECOPY);
}
static bool Add(BYTE* p,DWORD n,const char* name) {
    if(!n)return true;
    if(count==1024 || n>limit-total || !Writable(p,n))return false;
    for(unsigned i=0;i<count;++i)if(p<ranges[i].address+ranges[i].size && ranges[i].address<p+n)return false;
    ranges[count++]={p,n,name,total};total+=n;return true;
}
static bool GuardAt(BYTE* p,DWORD n) {
    if(guardCount==1024 || n>32)return false;
    Guard& g=guards[guardCount++];g.address=p;g.size=n;return Copy(g.bytes,p,n);
}
// Les selecteurs des descripteurs d'animation tournent entre trois emplacements.
static bool AnimationCheck() {
    for(BYTE* d:animation) {
        if(!d)return false;
        DWORD seenMask=0;
        for(unsigned i=0;i<4;++i) {
            DWORD p=Read(d+0x5C+i*4),which=3;
            for(unsigned j=0;j<3;++j)if(p==reinterpret_cast<DWORD>(d+8+j*0x1C))which=j;
            if(which==3)return false;
            if(i){if(seenMask&(1u<<which))return false;seenMask|=1u<<which;}
        }
    } return true;
}
static bool PrepareAnimation() {
    for(unsigned i=0;i<2;++i) {
        BYTE* idAddress=base+0xFD0540+i*0x6C8+0x28;BYTE id=0;
        if(!Copy(&id,idAddress,1)||id>1||!GuardAt(idAddress,1))return false;
        BYTE* d=base+0xFCC760+DWORD(id)*0x9C;animation[i]=d;
        if(i && d==animation[0])return false;
        BYTE n=0;if(!Copy(&n,d+0x94,1)||n!=21)return false;
        if(!GuardAt(d,8)||!GuardAt(d+0x88,0x14)||!Add(d,0x9C,"animation_descriptor"))return false;
        for(unsigned k=0;k<2;++k)
            if(!Add(reinterpret_cast<BYTE*>(Read(d+k*4)),DWORD(n)*64,"animation_matrices"))return false;
        for(DWORD off:{8u,0x24u,0x40u,0x6Cu}) {
            if(!GuardAt(d+off,12))return false;
            for(unsigned k=0;k<3;++k)
                if(!Add(reinterpret_cast<BYTE*>(Read(d+off+k*4)),DWORD(n)*16,"animation_vectors"))return false;
        }
    }
    return AnimationCheck() && Add(base+0xFCC220,32,"animation_previous_root") &&
        Add(base+0xFCACB0,32,"animation_movement") && Add(base+0xFC92E0,0xC00,"animation_world_cache");
}
// Canaux de decodage : enregistrement 2Ch remis en entier ; les donnees de mouvement
// pointees par chaque curseur sauvegarde doivent rester chargees (meme allocation, 16 octets).
static bool CheckChannels() {
    for(unsigned i=0;i<cursorCount;++i){
        if(!cursors[i].target)continue; // canal au repos
        MEMORY_BASIC_INFORMATION m={};
        if(!Readable(reinterpret_cast<DWORD>(cursors[i].target),m) || m.AllocationBase!=cursors[i].allocation)return false;
    }
    return true;
}
static bool PrepareChannels() {
    if(!GuardAt(base+0xFCC9D0,32))return false;
    for(unsigned p=0;p<2;++p){
        BYTE* table=base+0xFCC9D0+p*16;
        if(Read(table+12)!=21)return false;
        for(unsigned k=0;k<3;++k){
            BYTE* block=reinterpret_cast<BYTE*>(Read(table+k*4));
            unsigned objects=k?21:1;
            if(!Writable(block,k?21*0x88:0x84))return false;
            for(unsigned i=0;i<objects;++i)for(unsigned axis=0;axis<3;++axis){
                BYTE* c=block+i*0x88+axis*0x2C;
                if(cursorCount>=258)return false;
                DWORD address=Read(c+4);MEMORY_BASIC_INFORMATION m={};
                if(!address)cursors[cursorCount++]={nullptr,nullptr};
                else {
                    if(!Readable(address,m) || !GuardAt(reinterpret_cast<BYTE*>(address),16))return false;
                    cursors[cursorCount++]={reinterpret_cast<BYTE*>(address),m.AllocationBase};
                }
                if(!Add(c,0x2C,"channel"))return false;
            }
        }
    }
    return cursorCount==258 && CheckChannels();
}
static bool PhysicsGuard(unsigned g) {
    for(unsigned i=0;i<physicsCount;++i)if(g==physicsRefs[i].guard || g==physicsRefs[i].guard+1)return true;
    return false;
}
// tolerant : les gardes des objets physiques peuvent avoir change (retour avec reconstruction de la scene).
static const char* Check(bool tolerant=false) {
    if(GetCurrentThreadId()!=threadId)return "thread different";
    if(Read(base+0xFCE790)!=manager || Read(reinterpret_cast<void*>(manager+8))!=2 ||
       Read(reinterpret_cast<void*>(manager+0xC))!=reinterpret_cast<DWORD>(reader))return "lecteur de replay different";
    if(Read(base+0x1087A4C)!=4)return "pas en combat";
    for(unsigned i=0;i<guardCount;++i){
        if(tolerant && PhysicsGuard(i))continue;
        BYTE b[32];if(!Copy(b,guards[i].address,guards[i].size)||memcmp(b,guards[i].bytes,guards[i].size))return "garde modifiee";
    }
    for(unsigned i=0;i<count;++i)if(!skip[i] && !Writable(ranges[i].address,ranges[i].size))return "plage non inscriptible";
    if(!AnimationCheck())return "selecteurs d'animation incoherents";
    if(!CheckChannels())return "donnees de mouvement dechargees";
    return nullptr;
}
static bool ReadAll(BYTE* dest) {
    for(unsigned i=0;i<count;++i)if(!Copy(dest+ranges[i].offset,ranges[i].address,ranges[i].size))return false;
    return true;
}
static bool WriteAll(const BYTE* src) {
    __try {for(unsigned i=0;i<count;++i)if(!skip[i])memcpy(ranges[i].address,src+ranges[i].offset,ranges[i].size);return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
static bool SameAsSaved(const BYTE* now) {
    for(unsigned i=0;i<count;++i)if(!skip[i] && memcmp(now+ranges[i].offset,saved+ranges[i].offset,ranges[i].size))return false;
    return true;
}
static void Release() {
    if(saved)HeapFree(GetProcessHeap(),0,saved);
    saved=scratch=nullptr;
    count=guardCount=cursorCount=physicsCount=0;total=0;animation[0]=animation[1]=nullptr;InterlockedExchange(&active,0);
    memset(skip,0,sizeof(skip));decorStale=false;
}

// ---- decor par la serialisation du jeu (composant {proprietaire, descripteur load/save/apply},
// vus par 59EC00 / 59ED20 ; flux memoire vtable 9BA1F4, archive de bits, vidage 59EBC0) ----
struct Component { DWORD address,stamp; };
static Component components[64];
static void NoteComponent(DWORD address) {
    unsigned oldest=0;
    for(unsigned i=0;i<64;++i){if(components[i].address==address){components[i].stamp=frontierCount;return;}if(components[i].stamp<components[oldest].stamp)oldest=i;}
    components[oldest]={address,frontierCount};
}
struct MemoryStream { DWORD vtable; BYTE* buffer; DWORD size,position; };
struct Archive { MemoryStream* stream; BYTE owns,accumulator,mask,pad; };
typedef void(__cdecl* Serialize)(DWORD owner,Archive* archive);
typedef void(__cdecl* Apply)(DWORD owner);
typedef void(__fastcall* Flush)(Archive* archive,void* unused);
struct StageState { DWORD component,owner,descriptor,length; BYTE data[0x200]; };
static StageState stageStates[64]; static unsigned stageCount;
static BYTE stageScratch[0x1000];
static bool InText(DWORD v){return v>=reinterpret_cast<DWORD>(base)+0x1000 && v<reinterpret_cast<DWORD>(base)+0x966000;}
static bool InRdata(DWORD v){return v>=reinterpret_cast<DWORD>(base)+0x966000 && v<reinterpret_cast<DWORD>(base)+0xCB3000;}
static bool Describe(DWORD component,DWORD& owner,DWORD& descriptor) {
    owner=Read(reinterpret_cast<void*>(component));descriptor=Read(reinterpret_cast<void*>(component+4));
    return owner && InRdata(descriptor) && InText(Read(reinterpret_cast<void*>(descriptor))) &&
        InText(Read(reinterpret_cast<void*>(descriptor+4)));
}
static bool CallSave(DWORD owner,DWORD descriptor,MemoryStream* s) {
    __try {
        Archive a={s,1,0,1,0};
        reinterpret_cast<Serialize>(Read(reinterpret_cast<void*>(descriptor+4)))(owner,&a);
        reinterpret_cast<Flush>(base+0x59EBC0)(&a,nullptr);
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
static bool CallLoad(DWORD owner,DWORD descriptor,MemoryStream* s) {
    __try {
        Archive a={s,1,0,1,0};
        reinterpret_cast<Serialize>(Read(reinterpret_cast<void*>(descriptor)))(owner,&a);
        DWORD apply=Read(reinterpret_cast<void*>(descriptor+8));
        if(InText(apply))reinterpret_cast<Apply>(apply)(owner);
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
// 2.4 : tous les composants valides, quel que soit leur age. Sur HOME, l'etat de TOUS les objets cassables
// tient en 8 octets dans un seul composant (descripteur BF1548 : load 0x5EED90, save 0x5EEDB0, apply
// 0x5F2360 ; proprietaire de table BF1C94), que le jeu ne serialise pas a chaque image (vu 61 images avant
// un point le 26/09) : l'ancienne limite de 2 images l'ignorait. Il n'est pas recree par la reconstruction de
// la scene : le recharger apres la reconstruction recasse ce qui etait casse au point (sonde casse 0.2).
// 2.5 : bloc d'etat de la scene (proprietaire du composant, ex. HOME : demandes de casse +109E / +109F).
// Apres une reconstruction, le jeu remet ces bascules a 0 et CallLoad ne remet que +109E : la derniere
// demande (casse deja faite) etait retraitee. On garde le bloc brut au point et on remet ses mots de
// DRAPEAUX (chaque octet vaut 0 ou 1 : jamais une adresse ni un compteur) apres StageLoad.
struct StageRaw { DWORD owner,size; BYTE data[0x1400]; };
static StageRaw stageRaws[8]; static unsigned stageRawCount;
static bool FlagWord(DWORD v){return !(v&0xFEFEFEFEu);}
static DWORD RecordedSize(DWORD address);
static void StageRawSave(DWORD owner) {
    for(unsigned i=0;i<stageRawCount;++i)if(stageRaws[i].owner==owner)return;
    if(stageRawCount>=8)return;
    MEMORY_BASIC_INFORMATION mb={};if(!VirtualQuery(reinterpret_cast<void*>(owner),&mb,sizeof(mb)) || mb.State!=MEM_COMMIT)return;
    const DWORD end=reinterpret_cast<DWORD>(mb.BaseAddress)+static_cast<DWORD>(mb.RegionSize);
    DWORD size=RecordedSize(owner);if(!size || size>sizeof(stageRaws[0].data))size=sizeof(stageRaws[0].data);if(size>end-owner)size=end-owner;size&=~3u;
    StageRaw& r=stageRaws[stageRawCount];r.owner=owner;r.size=size;
    if(size && Copy(r.data,reinterpret_cast<void*>(owner),size))++stageRawCount;
}
static DWORD StageRawFlags() {
    DWORD n=0;
    for(unsigned i=0;i<stageRawCount;++i) {
        const StageRaw& r=stageRaws[i];bool alive=false;
        for(unsigned k=0;k<stageCount;++k)if(stageStates[k].owner==r.owner){DWORD o=0,d=0;alive=Describe(stageStates[k].component,o,d) && o==r.owner;break;}
        if(!alive)continue;
        for(DWORD k=0;k<r.size;k+=4) {
            DWORD old=0,now=0;memcpy(&old,r.data+k,4);
            if(!Copy(&now,reinterpret_cast<void*>(r.owner+k),4) || now==old || !FlagWord(old) || !FlagWord(now))continue;
            __try{*reinterpret_cast<DWORD*>(r.owner+k)=old;++n;}__except(EXCEPTION_EXECUTE_HANDLER){break;}
        }
    }
    return n;
}
static void StageSave() {
    stageCount=0;stageRawCount=0;
    for(const Component& c:components) {
        if(!c.address || stageCount>=64)continue;
        DWORD owner,descriptor;if(!Describe(c.address,owner,descriptor) || !InRdata(Read(reinterpret_cast<void*>(owner))))continue;
        MemoryStream s={reinterpret_cast<DWORD>(base)+0x9BA1F4,stageScratch,sizeof(stageScratch),0};
        memset(stageScratch,0,sizeof(stageScratch));
        if(!CallSave(owner,descriptor,&s) || s.position>sizeof(stageStates[0].data))continue;
        StageState& st=stageStates[stageCount++];
        st.component=c.address;st.owner=owner;st.descriptor=descriptor;st.length=s.position;memcpy(st.data,stageScratch,s.position);
        StageRawSave(owner);
    }
}
// 2.5 : composants de la scene dont l'etat serialise a change depuis le point (HOME : une table cassee ne cree ni
// ne detruit d'objet suivi, seul l'etat des cassables change ; sans reconstruction, la table revenait invisible).
static unsigned StageChanges() {
    unsigned n=0;
    for(unsigned i=0;i<stageCount;++i) {
        const StageState& st=stageStates[i];DWORD owner,descriptor;
        if(!Describe(st.component,owner,descriptor) || owner!=st.owner || descriptor!=st.descriptor)continue;
        MemoryStream s={reinterpret_cast<DWORD>(base)+0x9BA1F4,stageScratch,sizeof(stageScratch),0};
        memset(stageScratch,0,sizeof(stageScratch));
        if(!CallSave(owner,descriptor,&s))continue;
        if(s.position!=st.length || memcmp(stageScratch,st.data,st.length))++n;
    }
    return n;
}
static void StageLoad() {
    for(unsigned i=0;i<stageCount;++i) {
        StageState& st=stageStates[i];DWORD owner,descriptor;
        if(!Describe(st.component,owner,descriptor) || owner!=st.owner || descriptor!=st.descriptor)continue;
        memcpy(stageScratch,st.data,st.length);memset(stageScratch+st.length,0,16);
        MemoryStream s={reinterpret_cast<DWORD>(base)+0x9BA1F4,stageScratch,st.length+16,0};
        CallLoad(owner,descriptor,&s);
    }
}

// ---- decor par regle generale ----
// Tailles d'allocation notees par l'accroche sur la methode +5C de l'allocateur du jeu (7CBB80).
struct Allocation { DWORD address,size; };
static Allocation* allocations; static constexpr DWORD allocationSlots=1u<<19; static SRWLOCK allocationLock=SRWLOCK_INIT;
static void RecordAllocation(DWORD address,DWORD size) {
    if(!address || !allocations)return;
    AcquireSRWLockExclusive(&allocationLock);
    DWORD h=(address>>3)*2654435761u;
    for(DWORD i=0;i<64;++i){Allocation& a=allocations[(h+i)&(allocationSlots-1)];if(!a.address||a.address==address){a.address=address;a.size=size;break;}}
    ReleaseSRWLockExclusive(&allocationLock);
}
static DWORD RecordedSize(DWORD address) {
    if(!allocations)return 0;
    AcquireSRWLockShared(&allocationLock);DWORD size=0,h=(address>>3)*2654435761u;
    for(DWORD i=0;i<64;++i){const Allocation& a=allocations[(h+i)&(allocationSlots-1)];if(!a.address)break;if(a.address==address){size=a.size;break;}}
    ReleaseSRWLockShared(&allocationLock);return size;
}
struct Region { DWORD start,end; };
static Region regions[16384]; static unsigned regionCount;
struct Block { DWORD address,size,offset; WORD depth; bool bounded; };
static constexpr unsigned maxBlocks=8000,stableFrames=10;   // 2.1 : 3000 -> 8000 (HOME depassait 3000, releve par Snow)
static constexpr DWORD maxBlockBytes=8*1024*1024,pageStart=0x1070000,pageCount=16;
static Block blocks[maxBlocks]; static unsigned blockCount; static DWORD blockBytes;
static DWORD blockSet[32768];
static BYTE *blockSaved,*pageSaved; static DWORD *blockHashes,*pageHashes;
static unsigned hashedFrames;
static void ScanRegions() {
    regionCount=0;DWORD a=0x10000;
    while(regionCount<16384) {
        MEMORY_BASIC_INFORMATION m={};if(!VirtualQuery(reinterpret_cast<void*>(a),&m,sizeof(m)))break;
        DWORD s=reinterpret_cast<DWORD>(m.BaseAddress),e=s+static_cast<DWORD>(m.RegionSize);
        if(m.State==MEM_COMMIT && m.Type==MEM_PRIVATE && !(m.Protect&PAGE_GUARD) && (m.Protect&0xFF)==PAGE_READWRITE)regions[regionCount++]={s,e};
        if(e<=a)break;a=e;
    }
}
static bool HeapPointer(DWORD v,DWORD& regionEnd) {
    if(v&3)return false;
    unsigned lo=0,hi=regionCount;
    while(lo<hi){unsigned mid=(lo+hi)/2;if(regions[mid].end<=v)lo=mid+1;else hi=mid;}
    if(lo>=regionCount || v<regions[lo].start)return false;
    auto own=[&](const void* p,DWORD n){DWORD s=reinterpret_cast<DWORD>(p);return p && v>=s && v<s+n;};
    if(own(blockSaved,maxBlockBytes+pageCount*0x1000)||own(saved,total*2)||own(blockHashes,(maxBlocks+pageCount)*(stableFrames+1)*4))return false;
    regionEnd=regions[lo].end;return true;
}
static bool PointerLike(DWORD v) {
    DWORD e=0;
    return (v>=reinterpret_cast<DWORD>(base) && v<reinterpret_cast<DWORD>(base)+0x21F8000) || HeapPointer(v,e);
}
static void AddBlock(DWORD address,WORD depth) {
    DWORD regionEnd=0;
    if(blockCount>=maxBlocks || !HeapPointer(address,regionEnd))return;
    DWORD h=(address>>2)*2654435761u;bool inserted=false;
    for(unsigned i=0;i<32768;++i){DWORD& slot=blockSet[(h+i)&32767];if(slot==address)return;if(!slot){slot=address;inserted=true;break;}}
    if(!inserted)return;
    DWORD size=depth?0x800:0x2000;if(size>regionEnd-address)size=regionEnd-address;
    DWORD exact=RecordedSize(address);if(exact && exact<size)size=exact;size&=~3u;
    if(!size || blockBytes+size>maxBlockBytes)return;
    blocks[blockCount++]={address,size,blockBytes,depth,exact!=0};blockBytes+=size;
}
static DWORD FastHash(const void* p,DWORD n) {
    DWORD h=0x9E3779B9;
    __try{const DWORD* d=static_cast<const DWORD*>(p);for(DWORD i=0;i<n/4;++i){h^=d[i];h=(h<<5)|(h>>27);h*=0x01000193;}}
    __except(EXCEPTION_EXECUTE_HANDLER){return 0xDEADDEAD;}
    return h;
}
static void DecorBuild() {
    hashedFrames=0;
    if(!blockSaved)blockSaved=static_cast<BYTE*>(VirtualAlloc(nullptr,maxBlockBytes+pageCount*0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    if(!blockHashes)blockHashes=static_cast<DWORD*>(VirtualAlloc(nullptr,(maxBlocks+pageCount)*(stableFrames+1)*4,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    if(!blockSaved || !blockHashes){blockCount=0;return;}
    pageSaved=blockSaved+maxBlockBytes;pageHashes=blockHashes+maxBlocks*(stableFrames+1);
    memset(blockSet,0,sizeof(blockSet));blockCount=0;blockBytes=0;ScanRegions();
    AddBlock(Read(base+0x2072580),0);
    for(const Component& c:components)if(c.address)AddBlock(Read(reinterpret_cast<void*>(c.address)),0);
    for(unsigned i=0;i<blockCount;++i) {
        if(blocks[i].depth>=3)continue;
        for(DWORD o=0;o+4<=blocks[i].size;o+=4)AddBlock(Read(reinterpret_cast<void*>(blocks[i].address+o)),static_cast<WORD>(blocks[i].depth+1));
    }
    for(unsigned i=0;i<blockCount;++i)Copy(blockSaved+blocks[i].offset,reinterpret_cast<void*>(blocks[i].address),blocks[i].size);
    Copy(pageSaved,base+pageStart,pageCount*0x1000);
}
// Empreintes des objets et des pages pendant les 10 frames qui suivent le point.
static void DecorRecord(DWORD index) {
    if(!blockHashes || index>stableFrames || index!=hashedFrames)return;
    DWORD* row=blockHashes+index*maxBlocks;
    for(unsigned i=0;i<blockCount;++i)row[i]=FastHash(reinterpret_cast<void*>(blocks[i].address),blocks[i].size);
    DWORD* prow=pageHashes+index*pageCount;
    for(unsigned i=0;i<pageCount;++i)prow[i]=FastHash(base+pageStart+i*0x1000,0x1000);
    ++hashedFrames;
}
static void DecorRestore() {
    if(!blockHashes || hashedFrames<=stableFrames)return;
    DWORD written=0;
    for(unsigned i=0;i<blockCount;++i) {
        bool stable=true;for(DWORD k=1;k<=stableFrames;++k)if(blockHashes[k*maxBlocks+i]!=blockHashes[i]){stable=false;break;}
        const Block& b=blocks[i];
        if(!stable || !b.bounded)continue;
        DWORD typeNow=0,typeThen=0;memcpy(&typeThen,blockSaved+b.offset,4);
        if(!Copy(&typeNow,reinterpret_cast<void*>(b.address),4) || typeNow!=typeThen)continue;
        for(DWORD k=0;k+4<=b.size;k+=4) {
            DWORD old=0,now=0;memcpy(&old,blockSaved+b.offset+k,4);
            if(!Copy(&now,reinterpret_cast<void*>(b.address+k),4) || now==old || PointerLike(old) || PointerLike(now))continue;
            __try{*reinterpret_cast<DWORD*>(b.address+k)=old;written+=4;}__except(EXCEPTION_EXECUTE_HANDLER){}
        }
    }
    for(unsigned i=0;i<pageCount;++i) {
        bool stable=true;for(DWORD k=1;k<=stableFrames;++k)if(pageHashes[k*pageCount+i]!=pageHashes[i]){stable=false;break;}
        if(!stable)continue;
        for(DWORD k=0;k<0x1000;k+=4) {
            DWORD old=0,now=0;memcpy(&old,pageSaved+i*0x1000+k,4);Copy(&now,base+pageStart+i*0x1000+k,4);
            if(now==old || PointerLike(old) || PointerLike(now))continue;
            __try{*reinterpret_cast<DWORD*>(base+pageStart+i*0x1000+k)=old;written+=4;}__except(EXCEPTION_EXECUTE_HANDLER){}
        }
    }
    if(written)Logf("Point de controle : decor remis (%lu octets).",written);
}

// ---- 2.1 : securite « decor modifie » (idee et mesures de Snow, 26/09) ----
// Casser un objet du decor peut creer un composant serialisable ou detruire / remplacer des objets du
// graphe du decor. Le retour instantane reecrirait alors des objets liberes (plantages HOME 26/09 :
// game.exe+5F6D39 et +7668C1, mur et banc) : il est refuse, et le module revient au point par
// redemarrage + rattrapage (retour exact), qui recree le decor.
static DWORD compAtSave[64]; static unsigned compAtSaveCount;
// 2.4.1 : tous les composants connus au point, quel que soit leur age. Le jeu ne serialise certains composants
// que de temps en temps (HOME : l'etat des cassables, vu 61 images avant un point) : s'ils n'avaient pas ete
// vus juste avant le point, ils passaient pour « nouveaux » au retour -> reconstruction de la scene a chaque
// premier retour, meme sans casse (journaux du 26/09) ; sur d'autres scenes, elle remet a zero les elements
// animes (bugs d'objets signales).
static void ComponentSnapshot() {
    compAtSaveCount=0;
    for(const Component& c:components)if(c.address && compAtSaveCount<64)compAtSave[compAtSaveCount++]=c.address;
}
static unsigned NewComponents() {
    unsigned n=0;
    for(const Component& c:components) {
        if(!c.address || c.stamp+2<frontierCount)continue;
        bool old=false;for(unsigned i=0;i<compAtSaveCount;++i)if(compAtSave[i]==c.address){old=true;break;}
        if(!old)++n;
    }
    return n;
}
// Objets du graphe dont le 1er mot (table de methodes dans .rdata) a change depuis le point.
static unsigned DecorTypeChanges() {
    if(!blockSaved)return 0;unsigned n=0;
    for(unsigned i=0;i<blockCount;++i) {
        DWORD then=0,now=0;memcpy(&then,blockSaved+blocks[i].offset,4);
        if(!InRdata(then))continue;
        if(!Copy(&now,reinterpret_cast<void*>(blocks[i].address),4) || now!=then)++n;
    }
    return n;
}

// ---- 2.2 : reconstruction de la scene par le jeu (retour instantane avec le decor remis a neuf) ----
// Trouvee le 26/09 (sondes DOA5LR-ResetProbe 0.1-0.8) : Select+R2 en entrainement passe par 0x4003D0
// (remise en place du round, fil du combat), qui appelle 0x597AF0(n) = [0x2072580]->0x597940(n) :
// detruit puis recree les objets de la scene n (murs, bancs... intacts), puis 0x597B10. n = 0x5964C0()
// (scene courante). ~2,7 ms, essaye en entrainement et en replay (HOME). L'autre partie d'une scene en
// deux parties (n^1) n'est PAS reconstruite : l'appel sans les conditions du jeu vidait l'ecran.
// Les objets du decor sont recrees ailleurs : les copies du decor du point (blocs, composants) ne
// valent plus rien. decorStale : tous les retours suivants de ce point reconstruisent la scene et ne
// remettent que les plages hors decor (les objets physiques detruits sont sautes).
static bool rebuildAvailable;               // code du jeu verifie au demarrage (module)
static volatile LONG forceRebuild;          // demande du module (L3 / F7)
typedef DWORD(__cdecl* SceneFn)();
typedef void(__cdecl* RebuildFn)(DWORD);
typedef void(__cdecl* FinishFn)();
// 2.3 : HOME (et d'autres) ont des transitions sans retour (cour, sous-sol) : si la scene courante a
// change depuis le point, c'est la scene du point qui est redemandee (0x597940 bascule vers la scene n).
static DWORD sceneAtPoint=0xFF;
static DWORD CurrentScene(){return rebuildAvailable?reinterpret_cast<SceneFn>(base+0x5964C0)():0xFF;}
static bool RebuildScene(double& ms,DWORD n) {
    if(!rebuildAvailable)return false;
    if(n>1 || Read(base+0x2054540+n*0xA8+0x18)==0xFFFFFFFFu)return false;
    LARGE_INTEGER f,t0,t1;QueryPerformanceFrequency(&f);QueryPerformanceCounter(&t0);
    __try{reinterpret_cast<RebuildFn>(base+0x597AF0)(n);reinterpret_cast<FinishFn>(base+0x597B10)();}
    __except(EXCEPTION_EXECUTE_HANDLER){return false;}
    QueryPerformanceCounter(&t1);ms=double(t1.QuadPart-t0.QuadPart)*1000.0/double(f.QuadPart);
    return true;
}

// ---- preparation, abandon, retour ----
static bool AddWindow(DWORD start,DWORD end,const char* name) {
    BYTE* a=base+start;BYTE* e=base+end;
    while(a<e) {
        BYTE* next=e;BYTE* covered=nullptr;
        for(unsigned i=0;i<count;++i) {
            BYTE* rs=ranges[i].address;BYTE* re=rs+ranges[i].size;
            if(re<=a || rs>=e)continue;
            if(rs<=a){if(re>covered)covered=re;}else if(rs<next)next=rs;
        }
        if(covered){a=covered;continue;}
        if(!Add(a,static_cast<DWORD>(next-a),name))return false;
        a=next;
    }
    return true;
}
static BYTE savedClock;               // chrono du round [10885DA] au point de controle
// K.O. : sante (mot signe +2C du bloc joueur) a zero pour l'un des deux ; temps ecoule : chrono a 0.
static bool RoundDecided() {
    short h0=0,h1=0;BYTE clock=0;
    Copy(&h0,base+0xFD0540+0x2C,2);Copy(&h1,base+0xFD0540+0x6C8+0x2C,2);Copy(&clock,base+0x10885DA,1);
    return h0<=0 || h1<=0 || clock==0;
}
static const char* Prepare(BYTE* r,DWORD m) {
    Release();
    if(RoundDecided())return "round deja termine (K.O. ou temps ecoule)";
    reader=r;manager=m;threadId=GetCurrentThreadId();
    if(!GuardAt(reader,0x20) || !GuardAt(reinterpret_cast<BYTE*>(m),0x18))return "en-tete lecteur";
    BYTE* stream=reinterpret_cast<BYTE*>(Read(reader+4));
    BYTE* wrapper=reinterpret_cast<BYTE*>(Read(reader+8));
    if(!stream || !wrapper || Read(wrapper)!=reinterpret_cast<DWORD>(stream) ||
       Read(stream)!=reinterpret_cast<DWORD>(base+0x9BA1F4) || Read(stream+12)>Read(stream+8) ||
       !GuardAt(stream,12) || !GuardAt(wrapper,4))return "flux du replay";
    // Les tampons des manettes (appareils, agregat) ne sont pas remis : ils portent la vraie
    // manette du joueur, pas l'etat du replay.
    if(!Add(base+0x1087AB0,0x9C8,"rng") || !Add(base+0xFD0540,0xD90,"players") ||
       !Add(base+0xFCEE78,0x910,"logic") || !Add(base+0x10878F8,0xB0,"slots") ||
       !Add(base+0xFCE99C,8,"feed_globals") || !Add(reader+0x20,0x74,"reader_scalars") ||
       !Add(reinterpret_cast<BYTE*>(m)+0x18,0x18,"manager_scalars") ||
       !Add(stream+12,4,"stream_cursor"))return "plages globales";
    if(!Add(base+0xFCF788,0xD90,"player_secondary"))return "plages globales";
    if(!Add(base+0xFCED68,0x68,"player_history_previous") || !Add(base+0xFCEDD8,0x68,"player_history_current"))return "plages globales";
    BYTE* owner=reinterpret_cast<BYTE*>(Read(base+0x20720D4));
    if(!GuardAt(base+0x20720D4,4))return "liste des owners";
    for(unsigned i=0;i<2;++i) {
        if(!owner || !GuardAt(owner+8,0x10))return "liste des owners";
        for(DWORD off: {0x18u,0xC0u}) {
            if(!GuardAt(owner+off,8))return "liste des owners";
            DWORD begin=Read(owner+off),end=Read(owner+off+4);
            if(end<begin || end-begin>65536 || !Add(reinterpret_cast<BYTE*>(begin),end-begin,off==0x18?"pose":"array_c0"))return "tableaux de pose";
        }
        owner=reinterpret_cast<BYTE*>(Read(owner+0x10));
    }
    if(owner)return "plus de deux personnages";
    if(!PrepareAnimation())return "animation";
    for(unsigned player=0;player<2;++player)
        for(DWORD off:{0x10u,0x14u,0x1Cu,0x24u,0x34u})
            if(!Add(base+0xFCAB00+player*0x3C+off,4,"animation_time"))return "temps d'animation";
    if(!PrepareChannels())return "canaux d'animation";
    if(!Add(base+0xFCC214,4,"animation_advance_gate"))return "indicateur d'avancement";
    for(unsigned player=0;player<2;++player)
        if(!Add(base+0xFCBB00+player*0x180,12,"body_position"))return "position corps";
    for(const Seen& s:seen) {
        if(!s.object || s.stamp+2<frontierCount)continue;
        BYTE* p=reinterpret_cast<BYTE*>(s.object);
        const unsigned g=guardCount;
        if(!GuardAt(p+4,4) || !GuardAt(p+0x4C,8) || !Add(p,0x30C,"physics"))return "physique";
        if(physicsCount<8)physicsRefs[physicsCount++]={count-1,g};
    }
    if(!AddWindow(0xFCBAB0,0xFCBDB0,"w1_corps") || !AddWindow(0xFCA000,0xFCB700,"w2_mouvement") ||
       !AddWindow(0xFC7000,0xFCA000,"w3_blocs") || !AddWindow(0xFCC000,0xFD0540,"w4_globaux") ||
       !AddWindow(0xFB8000,0xFC0000,"w6_cameras"))return "fenetres statiques";
    saved=static_cast<BYTE*>(HeapAlloc(GetProcessHeap(),0,total*2));
    if(!saved){Release();return "memoire";}
    scratch=saved+total;
    const char* reason=Check();
    if(reason){Release();return reason;}
    if(!ReadAll(saved)){Release();return "lecture";}
    Copy(&savedClock,base+0x10885DA,1);
    return nullptr;
}
static void Drop(const char* reason) {
    if(!active)return;
    Logf("Point de controle abandonne : %s.",reason);
    Release();
}
static bool DoRestore(DWORD f) {
    const bool forced=InterlockedExchange(&forceRebuild,0)!=0;
    unsigned created=0,replaced=0,stateChanged=0;
    if(!decorStale){created=NewComponents();replaced=DecorTypeChanges();stateChanged=StageChanges();}
    const DWORD sceneNow=CurrentScene();
    const bool sceneChanged=sceneAtPoint<2 && sceneNow!=sceneAtPoint;
    const bool rebuild=forced || decorStale || created || replaced || stateChanged || sceneChanged;
    memset(skip,0,sizeof(skip));
    const char* reason=Check(rebuild);
    if(reason){Logf("Point de controle : retour refuse (%s).",reason);return false;}
    if(rebuild) {
        // Casser un objet cree ou detruit des objets du decor : les recopier ecrirait dans des objets
        // liberes (plantages HOME 26/09, releves par Snow). Le jeu recree la scene, puis on remet le reste.
        double ms=0;
        if(!RebuildScene(ms,sceneAtPoint<2?sceneAtPoint:sceneNow)) {
            Logf("Point de controle : decor modifie depuis le point (%u composant(s) nouveau(x), %u objet(s) detruit(s) ou remplace(s)) et reconstruction de la scene impossible : retour instantane refuse.",created,replaced);
            return false;
        }
        unsigned dropped=0;
        for(unsigned i=0;i<physicsCount;++i) {
            const PhysicsRef& ph=physicsRefs[i];bool same=true;
            for(unsigned g=ph.guard;g<ph.guard+2;++g){BYTE b[32];if(!Copy(b,guards[g].address,guards[g].size)||memcmp(b,guards[g].bytes,guards[g].size))same=false;}
            if(!same){skip[ph.range]=true;++dropped;}
        }
        Logf("Point de controle : scene %lu reconstruite par le jeu en %.2f ms (%s ; %u composant(s) nouveau(x), %u objet(s) detruit(s) ou remplace(s) ; scene courante avant %lu, apres %lu ; %u objet(s) physique(s) du decor saute(s)).",
            sceneAtPoint,ms,sceneChanged?"changement de zone depuis le point":forced?"demande":decorStale?"decor deja reconstruit pour ce point":(stateChanged && !created && !replaced)?"etat des cassables change depuis le point":"decor modifie depuis le point",
            created,replaced,sceneNow,CurrentScene(),dropped);
        decorStale=true;
    }
    if(!WriteAll(saved) || !ReadAll(scratch) || !SameAsSaved(scratch)) {
        Logf("Point de controle : ERREUR d'ecriture, abandonne.");Release();return false;
    }
    lastFrame=savedFrame;
    if(!rebuild)DecorRestore();
    StageLoad();                                   // 2.4 : aussi apres la reconstruction (etat des cassables du point)
    const DWORD flags=StageRawFlags();             // 2.5 : bascules de la scene (demandes deja traitees)
    Logf("Point de controle : retour instantane de l'image %lu a l'image %lu%s%s.",f,savedFrame,rebuild?" (decor remis a neuf)":"",flags?" ; drapeaux de la scene remis":"");
    return true;
}
// Appele une fois par image de la boucle du combat, sur le fil du jeu, apres le gestionnaire d'etat.
static void Frontier(BYTE* r) {
    ++frontierCount;
    DWORD m=Read(base+0xFCE790);
    bool fighting=r && m && Read(reinterpret_cast<void*>(m+8))==2 && Read(base+0x1087A4C)==4 &&
        Read(reinterpret_cast<void*>(m+0xC))==reinterpret_cast<DWORD>(r);
    if(!fighting) {
        if(active && Read(base+0x1087A4C)!=4){Drop("fin du combat, du round ou du replay");InterlockedExchange(&roundOver,1);}
        if(InterlockedExchange(&requestRestore,0))InterlockedExchange(&lastResult,2);
        InterlockedExchange(&requestSave,0);
        return;
    }
    DWORD f=Read(r+0x2C);
    if(Read(reinterpret_cast<void*>(m+0x1C))!=f)return;
    BYTE clock=0;Copy(&clock,base+0x10885DA,1);
    if(active && (r!=reader || m!=manager))Drop("autre lecteur de replay");
    else if(active && f<lastFrame)Drop("le replay est reparti en arriere");
    else if(active && clock>savedClock){Drop("nouveau round");InterlockedExchange(&roundOver,1);}
    else if(active && RoundDecided()){Drop("K.O. ou temps ecoule, retour desactive jusqu'a la prochaine reprise");InterlockedExchange(&roundOver,1);}
    lastFrame=f;
    if(InterlockedExchange(&requestSave,0)) {
        InterlockedExchange(&roundOver,0);
        const char* reason=Prepare(r,m);
        if(reason) {
            if(RoundDecided()){InterlockedExchange(&roundOver,1);Logf("Point de controle impossible a l'image %lu : %s ; retour desactive.",f,reason);}
            else Logf("Point de controle impossible a l'image %lu (%s) : retour par rattrapage accelere.",f,reason);
            return;
        }
        savedFrame=f;InterlockedExchange(&active,1);
        StageSave();DecorBuild();DecorRecord(0);ComponentSnapshot();sceneAtPoint=CurrentScene();
        Logf("Point de controle pose a l'image %lu (%u plages, %lu octets, %u objets de decor, scene %lu).",f,count,total,blockCount,sceneAtPoint);
        return;
    }
    if(InterlockedExchange(&requestRestore,0)) {
        InterlockedExchange(&lastResult,active && DoRestore(f)?1:2);
        return;
    }
    if(active && f>savedFrame)DecorRecord(f-savedFrame);
}
}
