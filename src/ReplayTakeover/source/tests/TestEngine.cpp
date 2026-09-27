// Test sur memoire simulee du moteur de points de controle du Replay Takeover 2.0.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cstdarg>
#include <initializer_list>
#undef NDEBUG
#include <cassert>
static BYTE* base;
static void Log(const char* t){puts(t);}
static bool Copy(void* d,const void* s,size_t n){__try{memcpy(d,s,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){memset(d,0,n);return false;}}
static DWORD Read(const void* p){DWORD x=0;Copy(&x,p,4);return x;}
#include "../Checkpoint.h"
static void Put(BYTE* p,DWORD v){memcpy(p,&v,4);}
static BYTE *m,*r,*stream,*physics;
static void Frame(DWORD f,bool save=false,bool restore=false){
    Put(r+0x2C,f);Put(m+0x1C,f);cp::NotePhysics(reinterpret_cast<DWORD>(physics));
    if(save)cp::requestSave=1;if(restore)cp::requestRestore=1;cp::Frontier(r);
}
static void Setup() {
    base=static_cast<BYTE*>(VirtualAlloc(nullptr,0x2200000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));assert(base);
    m=base+0x1000;r=base+0x2000;stream=base+0x3000;BYTE* wrap=base+0x3100;physics=base+0x400000;
    Put(base+0xFCE790,reinterpret_cast<DWORD>(m));Put(m+8,2);Put(m+12,reinterpret_cast<DWORD>(r));Put(base+0x1087A4C,4);
    Put(r+4,reinterpret_cast<DWORD>(stream));Put(r+8,reinterpret_cast<DWORD>(wrap));Put(wrap,reinterpret_cast<DWORD>(stream));
    Put(stream,reinterpret_cast<DWORD>(base+0x9BA1F4));Put(stream+4,reinterpret_cast<DWORD>(base+0x4000));Put(stream+8,0x100);Put(stream+12,20);
    BYTE* o=base+0x5000;Put(base+0x20720D4,reinterpret_cast<DWORD>(o));Put(o+0x10,reinterpret_cast<DWORD>(o+0x200));
    for(unsigned i=0;i<2;++i){BYTE* obj=o+i*0x200;for(DWORD off:{0x18u,0xC0u}){BYTE* a=base+0x8000+i*0x1000+off*4;Put(obj+off,reinterpret_cast<DWORD>(a));Put(obj+off+4,reinterpret_cast<DWORD>(a+64));}}
    for(unsigned i=0;i<2;++i){
        base[0xFD0540+i*0x6C8+0x28]=static_cast<BYTE>(i);
        BYTE* d=base+0xFCC760+i*0x9C;d[0x94]=21;
        BYTE* pool=base+0x100000+i*0x10000;
        for(unsigned k=0;k<2;++k){Put(d+k*4,reinterpret_cast<DWORD>(pool));pool+=0x1000;}
        for(DWORD off:{8u,0x24u,0x40u,0x6Cu})for(unsigned k=0;k<3;++k){Put(d+off+k*4,reinterpret_cast<DWORD>(pool));pool+=0x400;}
        Put(d+0x5C,reinterpret_cast<DWORD>(d+8));for(unsigned k=0;k<3;++k)Put(d+0x60+k*4,reinterpret_cast<DWORD>(d+8+k*0x1C));
    }
    for(unsigned p=0;p<2;++p){
        BYTE* table=base+0xFCC9D0+p*16;Put(table+12,21);
        for(unsigned k=0;k<3;++k){
            BYTE* block=base+0x200000+p*0x10000+k*0x3000;Put(table+k*4,reinterpret_cast<DWORD>(block));
            for(unsigned i=0;i<(k?21u:1u);++i)for(unsigned a=0;a<3;++a){
                BYTE* c=block+i*0x88+a*0x2C;
                Put(c+4,reinterpret_cast<DWORD>(base+0x300000));Put(c+8,1);Put(c+0x24,34);Put(c+0x28,0x12345678);
            }
        }
    }
    Put(physics+4,0x11111111);Put(physics+0x4C,1);Put(physics+0x50,1);
    for(unsigned i=0;i<2;++i){short hp=300;memcpy(base+0xFD0540+i*0x6C8+0x2C,&hp,2);}base[0x10885DA]=0x30; // sante 300, chrono 48
}
int main() {
    Setup();
    Frame(100,true);assert(cp::active && cp::savedFrame==100);
    for(DWORD f=101;f<=112;++f){base[0xFD0540]=static_cast<BYTE>(f);Frame(f);}
    assert(cp::hashedFrames==11);
    base[0xFD0540]=9;base[0xFCD000]=5;Frame(113,false,true);
    assert(cp::lastResult==1 && Read(r+0x2C)==100 && base[0xFD0540]==0 && base[0xFCD000]==0);
    cp::lastResult=0;
    puts("PASS pose puis retour instantane");
    Frame(101);Frame(102,false,true);assert(cp::lastResult==1 && Read(r+0x2C)==100);cp::lastResult=0;
    puts("PASS second retour");
    base[0x10885DA]=0x3C;Frame(101);assert(!cp::active && cp::roundOver);base[0x10885DA]=0x30;
    Frame(102,false,true);assert(cp::lastResult==2);cp::lastResult=0;
    puts("PASS nouveau round : point abandonne, retour refuse");
    // K.O. : sante a zero -> point efface, retour desactive jusqu a la prochaine reprise.
    Frame(110,true);assert(cp::active && !cp::roundOver);
    short zero=0;memcpy(base+0xFD0540+0x6C8+0x2C,&zero,2);Frame(111);assert(!cp::active && cp::roundOver);
    Frame(112,true);assert(!cp::active && cp::roundOver); // reprise pendant le K.O. : refusee
    short full=300;memcpy(base+0xFD0540+0x6C8+0x2C,&full,2);
    base[0x10885DA]=0;Frame(113,true);assert(!cp::active && cp::roundOver);base[0x10885DA]=0x30; // temps ecoule
    puts("PASS K.O. et temps ecoule : point efface, retour desactive");
    Frame(120,true);assert(cp::active);Put(base+0x1087A4C,3);Frame(121);assert(!cp::active);Put(base+0x1087A4C,4);
    puts("PASS fin du combat : point abandonne");
    Frame(130,true);assert(cp::active);Frame(10);assert(!cp::active);
    puts("PASS replay reparti en arriere : point abandonne");
    // 2.1 : un composant du decor apparu depuis le point (objet casse) -> retour instantane refuse,
    // le point reste (le module revient alors par redemarrage + rattrapage).
    Frame(140,true);assert(cp::active);Frame(141);
    cp::NoteComponent(0x12345678);Frame(142,false,true);assert(cp::lastResult==2 && cp::active);cp::lastResult=0;
    memset(cp::components,0,sizeof(cp::components));
    Frame(143,true);Frame(144);Frame(145,false,true);assert(cp::lastResult==1);cp::lastResult=0;
    puts("PASS decor modifie : retour instantane refuse, retour normal ensuite");
    return 0;
}
