#define DIRECTINPUT_VERSION 0x0800
#include <windows.h>
#include <dinput.h>
#include <stdio.h>
#include <string>
static IDirectInput8W* di;
static void utf8(const wchar_t* s){char buf[2048];int n=WideCharToMultiByte(CP_UTF8,0,s,-1,buf,sizeof(buf),nullptr,nullptr);if(n>0)fwrite(buf,1,n-1,stdout);}
static BOOL CALLBACK found(const DIDEVICEINSTANCEW* info,void*){
 IDirectInputDevice8W* p=nullptr;DWORD vidpid=0;DIDEVCAPS caps={};caps.dwSize=sizeof(caps);
 if(SUCCEEDED(di->CreateDevice(info->guidInstance,&p,nullptr))){
  DIPROPDWORD prop={};prop.diph.dwSize=sizeof(prop);prop.diph.dwHeaderSize=sizeof(prop.diph);prop.diph.dwHow=DIPH_DEVICE;
  if(SUCCEEDED(p->GetProperty(DIPROP_VIDPID,&prop.diph)))vidpid=prop.dwData;
  p->GetCapabilities(&caps);p->Release();
 }
 utf8(info->tszProductName);printf("\tVID_%04X&PID_%04X\t%lu buttons / %lu axes / %lu POV hats\n",LOWORD(vidpid),HIWORD(vidpid),caps.dwButtons,caps.dwAxes,caps.dwPOVs);return DIENUM_CONTINUE;
}
int main(){wchar_t path[MAX_PATH];GetSystemDirectoryW(path,MAX_PATH);std::wstring dll=std::wstring(path)+L"\\dinput8.dll";
 HMODULE mod=LoadLibraryW(dll.c_str());if(!mod)return 1;
 auto create=(HRESULT(WINAPI*)(HINSTANCE,DWORD,REFIID,void**,LPUNKNOWN))GetProcAddress(mod,"DirectInput8Create");
 if(!create||FAILED(create(GetModuleHandleW(nullptr),DIRECTINPUT_VERSION,IID_IDirectInput8W,(void**)&di,nullptr)))return 2;
 HRESULT hr=di->EnumDevices(DI8DEVCLASS_GAMECTRL,found,nullptr,DIEDFL_ATTACHEDONLY);di->Release();FreeLibrary(mod);return FAILED(hr)?3:0;
}
