#include "bridge.cpp"
#include <assert.h>
#include <stdio.h>
static int mockDeleted=0;
#include "mocks.generated.h"
struct HybridKeyboardTests {
 static HWND focus(){return (HWND)1;}
 static SwitchState::Keys noPad(HWND){return {};}
 static void run(){
  HybridKeyboard h;SwitchState::Keys k{};h.state.timestamp=1234;k[37]=128;h.state.update(k,false);
  DIDEVICEOBJECTDATA a={},b={};DWORD n=1;
  assert(h.deliver(sizeof(a),&a,&n,DIGDD_PEEK)==S_OK&&n==1&&h.state.pending.size()==1);
  n=1;assert(h.deliver(sizeof(b),&b,&n,DIGDD_PEEK)==S_OK&&memcmp(&a,&b,sizeof(a))==0);
  n=1;assert(h.deliver(sizeof(b),&b,&n,0)==S_OK&&h.state.pending.empty()&&b.dwOfs==37&&b.dwData==128&&b.dwTimeStamp==1234);
  k.fill(0);h.state.update(k,false);n=INFINITE;assert(h.deliver(sizeof(b),nullptr,&n,DIGDD_PEEK)==S_OK&&n==1&&h.state.pending.size()==1);
  n=INFINITE;assert(h.deliver(sizeof(b),nullptr,&n,0)==S_OK&&n==1&&h.state.pending.empty());
  k[50]=128;h.state.update(k,false);h.focusLost();for(auto& e:h.state.pending)assert(e.value==0);
  HybridKeyboard integrated;integrated.testForeground=focus;integrated.testPad=noPad;
  MockA* raw=new MockA;DIDEVICEOBJECTDATA result[8]={};n=8;
  assert(integrated.getData(raw,sizeof(result[0]),result,&n,0)==S_OK&&n==2);
  assert(result[0].dwOfs==17&&result[0].dwData==128&&result[1].dwOfs==17&&result[1].dwData==0);
  assert(result[0].dwTimeStamp==345&&result[0].dwSequence==456&&result[0].uAppData==567);
  assert(result[1].dwTimeStamp==346&&result[1].dwSequence==457&&result[1].uAppData==568);
  BYTE snapshot[256]={};assert(integrated.getState(raw,256,snapshot)==S_OK&&snapshot[17]==128);
  raw->Release();
 }
};
template<class Mock,class Wrapped> void exercise(REFIID iid){
 auto m=new Mock;auto w=new Wrapped(m);
 assert(w->SetDataFormat(&c_dfDIKeyboard)==S_OK);
 BYTE data[256]={};assert(w->GetDeviceState(256,data)==S_OK);assert(data[17]==128&&data[200]==0);
 m->fail=true;memset(data,7,256);assert(w->GetDeviceState(256,data)==DIERR_INPUTLOST);for(auto b:data)assert(b==7);
 m->fail=false;DIDEVICEOBJECTDATA e[2]={};DWORD n=2;assert(w->GetDeviceData(sizeof(e[0]),e,&n,DIGDD_PEEK)==S_OK);assert(n==2&&e[0].dwOfs==17&&e[1].dwOfs==17&&e[0].dwData==128&&e[1].dwData==0);
 n=0;assert(w->GetDeviceData(sizeof(e[0]),nullptr,&n,0)==S_OK&&n==2);
 DIDATAFORMAT invalid=c_dfDIKeyboard;invalid.dwNumObjs=1;assert(w->SetDataFormat(&invalid)==S_OK);memset(data,0,256);assert(w->GetDeviceState(256,data)==S_OK&&data[200]==128&&data[17]==0);
 void* p=nullptr;assert(w->QueryInterface(iid,&p)==S_OK&&p==w);assert(w->Release()==1);assert(w->QueryInterface(IID_IUnknown,&p)==S_OK&&p==w);assert(w->Release()==1);assert(w->Release()==0);
}
int main(){
 folder=L".\\";int t[]={17},s[]={200};assert(keymap.configure(t,s,1));
 exercise<MockA,KeyboardA>(IID_IDirectInputDevice8A);exercise<MockW,KeyboardW>(IID_IDirectInputDevice8W);assert(mockDeleted==2);
 HybridKeyboardTests::run();
 puts("PASS: ANSI/Unicode COM wrappers, state/events/peek, errors, nonstandard formats, COM identity/lifetime.");
}
