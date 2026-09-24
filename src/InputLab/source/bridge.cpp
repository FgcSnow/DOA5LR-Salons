#define DIRECTINPUT_VERSION 0x0800
#include <windows.h>
#include <dinput.h>
#include <new>
#include <string>
#include "remap.h"
static HMODULE selfModule;
static INIT_ONCE once=INIT_ONCE_STATIC_INIT;
static HMODULE backend;
static bool keyboardMode=false;
static bool hybridMode=false;
static int padTranslation=1;
static bool diagnostic=false;
static KeyMap keymap;
static std::wstring folder;
using CreateFn=HRESULT(WINAPI*)(HINSTANCE,DWORD,REFIID,LPVOID*,LPUNKNOWN);
static CreateFn realCreate;
#ifdef OUTER_DIAGNOSTIC
static const wchar_t* backendName=L"DOA5LR-AutoLink-original.dll";
#else
static const wchar_t* backendName=L"DOA5LR-InputBridge-Xidi.dll";
#endif
static void logline(const wchar_t* text) {
    if(!diagnostic)return;
    std::wstring path=folder+L"DOA5LR-InputBridge.log";
    HANDLE f=CreateFileW(path.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f==INVALID_HANDLE_VALUE)return;
    char buf[1024];int n=WideCharToMultiByte(CP_UTF8,0,text,-1,buf,sizeof(buf),NULL,NULL);DWORD written;
    if(n>0)WriteFile(f,buf,n-1,&written,NULL);
    WriteFile(f,"\r\n",2,&written,NULL);CloseHandle(f);
}
static BOOL CALLBACK init(PINIT_ONCE,void*,void**) {
    wchar_t path[32768];GetModuleFileNameW(selfModule,path,32768);
    folder=path;folder.resize(folder.find_last_of(L"\\/")+1);
    std::wstring ini=folder+L"DOA5LR-InputBridge.ini";
    diagnostic=GetPrivateProfileIntW(L"Input",L"Diagnostic",0,ini.c_str())!=0;
    wchar_t mode[64];GetPrivateProfileStringW(L"Input",L"Mode",L"Controller",mode,64,ini.c_str());
    hybridMode=(_wcsicmp(mode,L"Hybrid")==0);
    padTranslation=GetPrivateProfileIntW(L"Input",L"PadTranslation",1,ini.c_str());
    keyboardMode=hybridMode||(_wcsicmp(mode,L"Keyboard")==0);
    if(keyboardMode) {
        int targets[256],sources[256],count=0;
        for(int i=1;i<256;i++) {
            wchar_t k[12],v[32];wsprintfW(k,L"%d",i);
            GetPrivateProfileStringW(L"Keyboard",k,L"",v,32,ini.c_str());
            if(v[0]){wchar_t* end=nullptr;long src=wcstol(v,&end,10);targets[count]=i;sources[count++]=(end==v||*end)?-1:(int)src;}
        }
        if(!keymap.configure(targets,sources,count)){keymap.identity();logline(L"Invalid keyboard map: native keys retained.");}
        std::wstring dll=folder+backendName;
        backend=LoadLibraryExW(dll.c_str(),NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
        logline(hybridMode?L"Mode Hybrid: keyboard remapping and external controller reader.":L"Mode Keyboard: original Xidi frontend, controller enumeration filtered.");
    } else {
        std::wstring dll=folder+backendName;
        backend=LoadLibraryExW(dll.c_str(),NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
        logline(L"Mode Controller: original Xidi frontend, unchanged input path.");
    }
    logline(backendName);
    if(backend)realCreate=(CreateFn)GetProcAddress(backend,"DirectInput8Create");
    return TRUE;
}
static bool standardKeyboardFormat(LPCDIDATAFORMAT f) {
    if(!f||f->dwSize!=sizeof(DIDATAFORMAT)||f->dwObjSize!=sizeof(DIOBJECTDATAFORMAT)||f->dwDataSize!=256||f->dwNumObjs!=256||!f->rgodf)return false;
    bool seen[256]={};
    for(DWORD i=0;i<256;i++){
        auto& o=f->rgodf[i];DWORD instance=DIDFT_GETINSTANCE(o.dwType);
        if(o.dwOfs>=256||instance!=o.dwOfs||seen[o.dwOfs]||!(DIDFT_GETTYPE(o.dwType)&DIDFT_BUTTON))return false;
        seen[o.dwOfs]=true;
    }
    return true;
}
#include "hybrid_keyboard.h"
#include "wrappers.generated.h"
extern "C" HRESULT WINAPI DirectInput8Create(HINSTANCE h,DWORD ver,REFIID iid,LPVOID* out,LPUNKNOWN outer) {
    if(!out)return E_POINTER;*out=nullptr;
    InitOnceExecuteOnce(&once,init,NULL,NULL);
    if(!realCreate)return DIERR_GENERIC;
    HRESULT hr=realCreate(h,ver,iid,out,outer);
    if(FAILED(hr)||!keyboardMode||outer||!*out)return hr;
    if(iid==IID_IDirectInput8A){auto raw=(IDirectInput8A*)*out;auto w=new(std::nothrow)InputA(raw);if(!w){raw->Release();*out=nullptr;return E_OUTOFMEMORY;}*out=w;}
    else if(iid==IID_IDirectInput8W){auto raw=(IDirectInput8W*)*out;auto w=new(std::nothrow)InputW(raw);if(!w){raw->Release();*out=nullptr;return E_OUTOFMEMORY;}*out=w;}
    return hr;
}
extern "C" HRESULT WINAPI DllCanUnloadNow(){return S_FALSE;}
extern "C" HRESULT WINAPI DllGetClassObject(REFCLSID,REFIID,LPVOID* p){if(p)*p=nullptr;return CLASS_E_CLASSNOTAVAILABLE;}
extern "C" HRESULT WINAPI DllRegisterServer(){return E_NOTIMPL;}
extern "C" HRESULT WINAPI DllUnregisterServer(){return E_NOTIMPL;}
BOOL WINAPI DllMain(HINSTANCE h,DWORD why,LPVOID){if(why==DLL_PROCESS_ATTACH){selfModule=h;DisableThreadLibraryCalls(h);}return TRUE;}
