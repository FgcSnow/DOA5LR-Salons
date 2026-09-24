#define DIRECTINPUT_VERSION 0x0800
#include "remap.h"
#include <assert.h>
#include <stdio.h>
int main(){
 KeyMap m;int t[]={0x11,0x1e,0x1f,0x20,0x24,0x25,0x26,0x32};
 int s[]={0xc8,0xcb,0xd0,0xcd,0x1e,0x11,0x2e,0x2f};
 assert(m.configure(t,s,8));bool seen[256]={};
 for(int i=0;i<256;i++){assert(!seen[m.output[i]]);seen[m.output[i]]=true;}
 for(int i=0;i<8;i++)assert(m.output[s[i]]==t[i]);
 BYTE data[256]={};data[s[0]]=data[s[4]]=0x80;m.state(data);
 assert(data[t[0]]==0x80&&data[t[4]]==0x80);int pressed=0;for(auto b:data)if(b)pressed++;assert(pressed==2);
 memset(data,0,256);m.state(data);for(auto b:data)assert(b==0);
 DIDEVICEOBJECTDATA events[2]={};events[0].dwOfs=events[1].dwOfs=s[4];events[0].dwData=0x80;events[0].dwTimeStamp=123;events[1].dwData=0;
 m.events(sizeof(events[0]),events,2);assert(events[0].dwOfs==(DWORD)t[4]&&events[1].dwOfs==(DWORD)t[4]&&events[0].dwData==0x80&&events[1].dwData==0&&events[0].dwTimeStamp==123);
 int duplicate[]={0x11,0x11};assert(!m.configure(t,duplicate,2));
 int invalid[]={256};assert(!m.configure(t,invalid,1));
 int swapT[]={30,31},swapS[]={31,30};assert(m.configure(swapT,swapS,2));assert(m.output[30]==31&&m.output[31]==30);
 puts("PASS: permutation, chords, releases, buffered events, duplicate/invalid rejection, swaps.");
}
