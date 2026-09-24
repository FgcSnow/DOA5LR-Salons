#pragma once
#include "companion_client.h"
#include <algorithm>
class HybridKeyboard {
    friend struct HybridKeyboardTests;
    SRWLOCK lock=SRWLOCK_INIT;
    struct Guard {SRWLOCK* p;Guard(SRWLOCK* a):p(a){AcquireSRWLockExclusive(p);}~Guard(){ReleaseSRWLockExclusive(p);}};
    SwitchState state;
    CompanionClient reader;
    HWND (*testForeground)()=nullptr;
    SwitchState::Keys (*testPad)(HWND)=nullptr;
    HWND foreground(){if(testForeground)return testForeground();HWND h=GetForegroundWindow();DWORD pid=0;GetWindowThreadProcessId(h,&pid);return pid==GetCurrentProcessId()?h:nullptr;}
    void readPad(HWND hwnd){
        state.timestamp=GetTickCount();
        SwitchState::Keys observed=padTranslation==0?SwitchState::Keys{}:(testPad?testPad(hwnd):reader.read(hwnd));
        state.update(padTranslation==1?observed:SwitchState::Keys{},true);
    }
    void updateKeyboard(const SwitchState::Keys& keys){state.timestamp=GetTickCount();state.update(keys,false);}
    void focusLost(){state.pending.clear();state.timestamp=GetTickCount();state.clear();}
    HRESULT deliver(DWORD stride,LPDIDEVICEOBJECTDATA out,DWORD* count,DWORD flags){
        DWORD n=std::min<DWORD>(*count,(DWORD)state.pending.size());bool overflow=state.overflow;
        if(!out){if(!(flags&DIGDD_PEEK)){for(DWORD i=0;i<n;i++)state.pending.pop_front();state.overflow=false;}*count=n;return overflow?DI_BUFFEROVERFLOW:DI_OK;}
        for(DWORD i=0;i<n;i++){
            DIDEVICEOBJECTDATA data={};data.dwOfs=state.pending[i].key;data.dwData=state.pending[i].value;
            data.dwTimeStamp=state.pending[i].timestamp;data.dwSequence=state.pending[i].sequence;
            data.uAppData=state.pending[i].appData;
            memcpy((BYTE*)out+i*stride,&data,stride);
        }
        if(!(flags&DIGDD_PEEK)){for(DWORD i=0;i<n;i++)state.pending.pop_front();state.overflow=false;}
        *count=n;return overflow?DI_BUFFEROVERFLOW:DI_OK;
    }
public:
    template<class T> HRESULT getState(T* raw,DWORD size,void* out){
        if(size!=256||!out)return raw->GetDeviceState(size,out);
        Guard guard(&lock);BYTE data[256];HRESULT hr=raw->GetDeviceState(size,data);
        if(FAILED(hr)){focusLost();return hr;}
        HWND hwnd=foreground();if(!hwnd){focusLost();memset(out,0,256);return hr;}
        keymap.state(data);SwitchState::Keys k;memcpy(k.data(),data,256);updateKeyboard(k);readPad(hwnd);
        memcpy(out,state.output.data(),256);return hr;
    }
    template<class T> HRESULT getData(T* raw,DWORD stride,LPDIDEVICEOBJECTDATA out,DWORD* count,DWORD flags){
        if(!count||(stride!=sizeof(DIDEVICEOBJECTDATA)&&stride!=sizeof(DIDEVICEOBJECTDATA_DX3))||(flags&~DIGDD_PEEK))return raw->GetDeviceData(stride,out,count,flags);
        Guard guard(&lock);HWND hwnd=foreground();
        DIDEVICEOBJECTDATA events[64];DWORD got=64;
        HRESULT hr=raw->GetDeviceData(sizeof(events[0]),events,&got,0);
        if(FAILED(hr)){focusLost();return hr;}
        if(hr==DI_BUFFEROVERFLOW){
            BYTE actual[256];if(SUCCEEDED(raw->GetDeviceState(256,actual))){keymap.state(actual);SwitchState::Keys k;memcpy(k.data(),actual,256);updateKeyboard(k);}
            state.overflow=true;
        }else if(hwnd){
            for(DWORD i=0;i<got;i++)if(events[i].dwOfs<256){
                auto k=state.keyboard;
                BYTE translated=keymap.output[events[i].dwOfs];
                k[translated]=(BYTE)(events[i].dwData&128);
                size_t previous=state.pending.size();
                updateKeyboard(k);
                // An actual keyboard transition keeps the original DirectInput
                // event metadata; only its remapped scan code changes.
                if(state.pending.size()==previous+1){
                    auto& forwarded=state.pending.back();
                    forwarded.key=translated;
                    forwarded.value=events[i].dwData;
                    forwarded.timestamp=events[i].dwTimeStamp;
                    forwarded.sequence=events[i].dwSequence;
                    forwarded.appData=events[i].uAppData;
                }
            }
        }
        if(hwnd)readPad(hwnd);else focusLost();
        return deliver(stride,out,count,flags);
    }
};
