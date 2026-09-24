#pragma once
#include <array>
#include <deque>
#include <stdint.h>
// Native keyboard scan codes, after keyboard remapping / pad translation.
struct SwitchState {
    using Keys=std::array<unsigned char,256>;
    struct Event { uint32_t key,value,sequence,timestamp; uintptr_t appData=0; };
    Keys keyboard{},pad{},output{};
    std::deque<Event> pending;
    bool padActive=false,overflow=false;
    uint32_t nextSequence=0,timestamp=0;
    void publish(){
        Keys next{};
        // Both physical sources feed a single logical keyboard. A release from
        // one source must not release a command still held by the other.
        for(unsigned i=0;i<256;i++)next[i]=(keyboard[i]||pad[i])?128:0;
        // Release changed commands before pressing new commands.
        for(int down=0;down<2;down++)for(unsigned i=0;i<256;i++)
            if(next[i]!=output[i] && ((next[i]!=0)==(down!=0))){
                if(pending.size()==1024){pending.pop_front();overflow=true;}
                pending.push_back({i,next[i],nextSequence++,timestamp});
            }
        output=next;
    }
    void update(const Keys& next,bool fromPad){
        auto& previous=fromPad?pad:keyboard;bool pressed=false;
        for(unsigned i=0;i<256;i++)if(next[i]&&!previous[i])pressed=true;
        previous=next;
        if(pressed)padActive=fromPad;
        publish();
    }
    void clear(){keyboard.fill(0);pad.fill(0);publish();}
};
