#pragma once
#include "companion_protocol.h"
#include "switch_state.h"
#include <string>

// Reads a short-lived snapshot written by the independent controller process.
// No XInput or controller DirectInput call runs inside DOA5LR.
class CompanionClient {
    HANDLE mapping=nullptr;
    const companion::SharedState* shared=nullptr;
    bool started=false;
    DWORD lastChangeTick_=0;
    DWORD lastRetry=0;
    void connect() {
        if(shared)return;
        mapping=OpenFileMappingW(FILE_MAP_READ,FALSE,companion::kMapName);
        if(!mapping)return;
        shared=(const companion::SharedState*)MapViewOfFile(mapping,FILE_MAP_READ,0,0,sizeof(companion::SharedState));
        if(!shared){CloseHandle(mapping);mapping=nullptr;}
    }
    void start() {
        if(started)return;
        started=true;
        std::wstring program=folder+L"DOA5LR-Companion.exe";
        DWORD attributes=GetFileAttributesW(program.c_str());
        if(attributes==INVALID_FILE_ATTRIBUTES || (attributes&FILE_ATTRIBUTE_DIRECTORY)){
            logline(L"Companion executable missing; controller unavailable.");return;
        }
        // lpApplicationName fixes the exact executable; arguments are only our game folder.
        std::wstring command=L"\""+program+L"\" .";
        STARTUPINFOW startup={};startup.cb=sizeof(startup);PROCESS_INFORMATION process={};
        if(CreateProcessW(program.c_str(),&command[0],nullptr,nullptr,FALSE,CREATE_NO_WINDOW,
                          nullptr,folder.c_str(),&startup,&process)){
            CloseHandle(process.hThread);CloseHandle(process.hProcess);
            logline(L"Companion controller process started.");
        }else logline(L"Companion controller process failed to start.");
    }
public:
    DWORD lastChangeTick() const{return lastChangeTick_;}
    ~CompanionClient(){if(shared)UnmapViewOfFile(shared);if(mapping)CloseHandle(mapping);}
    SwitchState::Keys read(HWND){
        SwitchState::Keys result{};
        lastChangeTick_=0;
        start();
        if(!shared){DWORD now=GetTickCount();if(!lastRetry||now-lastRetry>=500){lastRetry=now;connect();}}
        if(!shared)return result;
        for(int tries=0;tries<3;tries++){
            LONG before=shared->sequence;
            if(before&1)continue;
            MemoryBarrier();
            companion::SharedState copy={};
            copy.magic=shared->magic;copy.version=shared->version;
            copy.tick=shared->tick;copy.changeTick=shared->changeTick;copy.writerPid=shared->writerPid;
            memcpy(copy.keys,shared->keys,sizeof(copy.keys));
            MemoryBarrier();
            LONG after=shared->sequence;
            if(before!=after || (after&1))continue;
            if(copy.magic!=companion::kMagic||copy.version!=companion::kVersion ||
               GetTickCount()-copy.tick>companion::kMaxAgeMs)return result;
            lastChangeTick_=copy.changeTick;
            memcpy(result.data(),copy.keys,result.size());return result;
        }
        return result;
    }
};
