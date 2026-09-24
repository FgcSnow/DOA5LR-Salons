#pragma once
#include <windows.h>
#include <dinput.h>
#include <string.h>
// A bijection preserves press/release events, chords, and unmapped keys.
// Config: native scan code -> physical scan code. Duplicate sources rejected.
struct KeyMap {
    BYTE output[256];
    KeyMap() { identity(); }
    void identity() { for(int i=0;i<256;i++) output[i]=(BYTE)i; }
    bool configure(const int* target, const int* source, int n) {
        identity(); bool seenT[256]={},seenS[256]={};
        for(int i=0;i<n;i++) {
            if(target[i]<=0||target[i]>255||source[i]<=0||source[i]>255||seenT[target[i]]||seenS[source[i]]) return false;
            seenT[target[i]]=seenS[source[i]]=true;
        }
        for(int i=0;i<n;i++) {
            int other=0;while(output[other]!=target[i])++other;
            BYTE old=output[source[i]];output[source[i]]=output[other];output[other]=old;
        }
        return true;
    }
    void state(BYTE* data) const {
        BYTE copy[256];memcpy(copy,data,256);
        for(int i=0;i<256;i++)data[output[i]]=copy[i];
    }
    void events(DWORD stride, void* data, DWORD count) const {
        if(!data||stride<sizeof(DIDEVICEOBJECTDATA_DX3))return;
        for(DWORD i=0;i<count;i++) {
            auto event=(DIDEVICEOBJECTDATA*)((BYTE*)data+i*stride);
            if(event->dwOfs<256)event->dwOfs=output[event->dwOfs];
        }
    }
};
