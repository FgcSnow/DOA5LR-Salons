#include "switch_state.h"
#include <assert.h>
#include <stdio.h>
int main(){
 SwitchState s;SwitchState::Keys k{},p{};
 k[17]=128;s.update(k,false);assert(s.output[17]);
 p[50]=128;s.update(p,true);assert(s.output[50]&&s.output[17]);
 k[17]=0;s.update(k,false);assert(!s.output[17]&&s.output[50]);
 k[31]=128;s.update(k,false);assert(s.output[31]&&s.output[50]);
 p.fill(0);s.update(p,true);assert(s.output[31]&&!s.output[50]);
 // Same command on both devices: one down, no spurious up on one release.
 s.clear();s.pending.clear();k.fill(0);p.fill(0);
 k[37]=128;s.update(k,false);assert(s.pending.size()==1);s.pending.clear();
 p[37]=128;s.update(p,true);assert(s.pending.empty());
 k.fill(0);s.update(k,false);assert(s.pending.empty()&&s.output[37]);
 p.fill(0);s.update(p,true);assert(s.pending.size()==1&&s.pending[0].value==0&&!s.output[37]);
 // Repeated controller-to-keyboard round trips cannot lock either device.
 s.clear();k.fill(0);p.fill(0);
 for(int n=0;n<100;n++){
  p[50]=128;s.update(p,true);assert(s.output[50]);p[50]=0;s.update(p,true);
  k[17]=128;s.update(k,false);assert(s.output[17]);k[17]=0;s.update(k,false);
 }
 s.clear();for(auto b:s.output)assert(!b);
 puts("PASS: simultaneous devices, keyboard after pad, shared-command ownership, releases, 100 round trips, focus reset.");
}
