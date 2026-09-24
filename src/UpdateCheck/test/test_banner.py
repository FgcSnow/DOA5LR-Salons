"""Exercise the shipped UpdateCheck DLL in fake games; never touches DOA5LR.

Uses the public HTTPS version manifest. A short test banner may appear. The
installer is a harmless stub that records --update in the temporary fixture.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

root=Path(__file__).resolve().parents[1]
url='https://raw.githubusercontent.com/FgcSnow/DOA5LR-Salons/main/version.txt'
body=urllib.request.urlopen(url,timeout=20).read().decode('utf-8-sig')
latest=next(line.split('=',1)[1].strip() for line in body.splitlines() if line.startswith('version='))
compilers=list(Path(os.environ['LOCALAPPDATA']).glob('Microsoft/WinGet/Packages/MartinStorsjo.LLVM-MinGW*/llvm-mingw-*/bin/i686-w64-mingw32-gcc.exe'))
compiler=Path(os.environ['LLVM_MINGW'])/'bin/i686-w64-mingw32-gcc.exe' if os.environ.get('LLVM_MINGW') else next(iter(compilers),None)
if not compiler: raise RuntimeError('LLVM-MinGW x86 compiler missing')
host=r'''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
static int seen;
static BOOL CALLBACK watch(HWND hwnd,LPARAM unused) {
  DWORD pid=0; GetWindowThreadProcessId(hwnd,&pid);
  WCHAR cls[128]; GetClassNameW(hwnd,cls,128);
  if(pid==GetCurrentProcessId()&&!wcscmp(cls,L"DOA5LR_UpdateCheck_Banner")&&IsWindowVisible(hwnd)){
    LONG styles=GetWindowLongW(hwnd,GWL_EXSTYLE);
    if((styles&WS_EX_NOACTIVATE)&&(styles&WS_EX_TRANSPARENT))seen=1;
  }
  return TRUE;
}
int main(int argc,char**argv){
  char path[MAX_PATH]; GetModuleFileNameA(NULL,path,MAX_PATH);
  char *end=strrchr(path,'\\'); if(!end)return 2; strcpy(end,"\\scripts\\DOA5LR-UpdateCheck.asi");
  if(!LoadLibraryA(path)){printf("Load failed: %lu\n",GetLastError());return 3;}
  for(int i=0;i<120;i++){EnumWindows(watch,0);Sleep(100);}
  int expected=argc>1?atoi(argv[1]):0;
  printf("banner=%d expected=%d\n",seen,expected);fflush(stdout);
  ExitProcess(seen==expected?0:4);
}
'''
stub=r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
int WINAPI WinMain(HINSTANCE a,HINSTANCE b,LPSTR cmd,int show){
  char path[MAX_PATH];GetModuleFileNameA(NULL,path,MAX_PATH);
  char *end=strrchr(path,'\\');if(!end)return 2;strcpy(end,"\\launched.txt");
  FILE *f=fopen(path,"w");if(!f)return 3;fputs(cmd,f);fclose(f);return 0;
}
'''
directory=Path(tempfile.mkdtemp(prefix='doa5lr-update-banner-'))
(directory/'host.c').write_text(host)
(directory/'stub.c').write_text(stub)
(directory/'stub.manifest').write_text('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>
<requestedExecutionLevel level="asInvoker" uiAccess="false" />
</requestedPrivileges></security></trustInfo></assembly>''')
(directory/'stub.rc').write_text('1 24 "stub.manifest"\n')
# Match the real installer's asInvoker manifest. Without this, Windows' legacy
# filename heuristic treats the fake *Installer.exe as requiring elevation;
# CreateProcess correctly refuses it with ERROR_ELEVATION_REQUIRED (740).
subprocess.run([str(compiler.with_name('i686-w64-mingw32-windres.exe')),'-O','coff','stub.rc','stub.res'],cwd=directory,check=True)
subprocess.run([str(compiler),'-O1','-static',str(directory/'host.c'),'-o',str(directory/'host.exe')],check=True)
subprocess.run([str(compiler),'-O1','-static','-mwindows',str(directory/'stub.c'),str(directory/'stub.res'),'-o',str(directory/'stub.exe')],check=True)
results=[]
for name,version,banner,expected_banner,expected_prompt in [('outdated','0.0.0',1,1,1),('current',latest,1,0,0),('banner-disabled','0.0.0',0,0,1)]:
    game=directory/name
    (game/'scripts').mkdir(parents=True)
    shutil.copy2(directory/'host.exe',game/'game.exe')
    shutil.copy2(directory/'stub.exe',game/'DOA5LR-Salons-Installer.exe')
    shutil.copy2(root/'DOA5LR-UpdateCheck.asi',game/'scripts/DOA5LR-UpdateCheck.asi')
    (game/'DOA5LR-Salons-VERSION.txt').write_text(version)
    (game/'scripts/DOA5LR-UpdateCheck.ini').write_text(f'[UpdateCheck]\nEnabled=1\nUpdatePrompt=1\nDelaySeconds=3\nBanner={banner}\nBannerSeconds=2\nVersionUrl={url}\n')
    start={str(p.relative_to(game)):p.read_bytes() for p in game.rglob('*') if p.is_file()}
    result=subprocess.run([str(game/'game.exe'),str(expected_banner)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,(name,result.stdout,result.stderr)
    for _ in range(150 if expected_prompt else 20):
        if (game/'launched.txt').exists():break
        time.sleep(.1)
    assert (game/'launched.txt').exists()==bool(expected_prompt),name
    if expected_prompt: assert (game/'launched.txt').read_text().strip()=='--update'
    after={str(p.relative_to(game)):p.read_bytes() for p in game.rglob('*') if p.is_file() and p.name!='launched.txt'}
    assert start==after,'Plugin unexpectedly wrote fixture files'
    results.append({'case':name,'passed':True,'banner':bool(expected_banner),'prompt_after_exit':bool(expected_prompt)})
    print('PASS',name,result.stdout.strip(),flush=True)
report={'remote_version':latest,'plugin_sha256':hashlib.sha256((root/'DOA5LR-UpdateCheck.asi').read_bytes()).hexdigest(),'cases':results,'scope':'Isolated fake game; actual DLL. Real-game fullscreen behavior not tested.'}
(directory/'result.json').write_text(json.dumps(report,indent=2))
print('Report:',directory/'result.json')
