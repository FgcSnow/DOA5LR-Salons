#define WIN32_LEAN_AND_MEAN
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <wincrypt.h>
#include <cstdio>
#include <cstring>
#include <cstdarg>
#include <cwchar>
#include <string>
static_assert(sizeof(void*)==4,"x86 observer for x86 DOA5LR");
static std::wstring Root,Session,GameDir;
static FILE* Output;static HANDLE Target=nullptr;static DWORD Base=0;static ULONGLONG Bytes=0;
static std::wstring Path(const std::wstring& a,const wchar_t* b){return a+L"\\"+b;}
static void Status(const wchar_t* text){FILE* f=_wfopen(Path(Root,L"ETAT.txt").c_str(),L"wb");if(f){fwprintf(f,L"%ls\r\n",text);fclose(f);}}
static void Log(const char* fmt,...){
 if(!Output||Bytes>20ull*1024*1024)return;
 SYSTEMTIME t;GetSystemTime(&t);char body[1600];va_list args;va_start(args,fmt);vsnprintf(body,sizeof(body),fmt,args);va_end(args);
 int n=fprintf(Output,"%04u-%02u-%02uT%02u:%02u:%02u.%03uZ tick=%llu %s\n",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,t.wMilliseconds,GetTickCount64(),body);
 if(n>0)Bytes+=n;fflush(Output);
}
static bool ReadAt(DWORD address,void* p,size_t n){SIZE_T got=0;return ReadProcessMemory(Target,(void*)address,p,n,&got)&&got==n;}
static bool ReadRva(DWORD offset,void* p,size_t n){return offset<0x21f8000&&n<=0x21f8000-offset&&ReadAt(Base+offset,p,n);}
struct Snapshot{
 DWORD selected,fight,mode,preferences[3],slots[4];
 BYTE candidates[74];
 DWORD activeStage,activeBank,networkReader;BYTE matching;
 DWORD bankState[2];BYTE requested[2],loaded[2];
};
static bool Take(Snapshot& s){
 memset(&s,0,sizeof(s));s.activeStage=s.activeBank=0xffffffff;
 DWORD reader=0,matching=0,manager=0,controller=0;
 bool ok=ReadRva(0xf83d64,&s.selected,4)&&ReadRva(0x1087a4c,&s.fight,4)&&ReadRva(0xf83d80,&s.mode,4)&&
 ReadRva(0xf74384+43*4,s.preferences,12)&&ReadRva(0x207fd0c,s.slots,16)&&ReadRva(0x207ecf8,s.candidates,74)&&
 ReadRva(0xf8f208,&reader,4)&&ReadRva(0xf8189c,&matching,4)&&ReadRva(0x2072580,&manager,4);
 s.networkReader=reader;s.matching=matching!=0;
 if(manager&&ReadAt(manager+12,&controller,4)&&controller){DWORD x[2],m2=0,c2=0;if(ReadAt(controller+4,x,8)&&ReadRva(0x2072580,&m2,4)&&m2==manager&&ReadAt(manager+12,&c2,4)&&c2==controller){s.activeBank=x[0];s.activeStage=x[1];}}
 for(unsigned i=0;i<2;i++){DWORD rva=0x2054540+i*0xa8;ok=ReadRva(rva+8,&s.bankState[i],4)&&ReadRva(rva+0x10,&s.requested[i],1)&&ReadRva(rva+0x18,&s.loaded[i],1)&&ok;}
 return ok;
}
static const char* Stage(DWORD n){switch(n){case 43:return "DangerZone";case 44:return "Crimson1";case 45:return "Crimson2";case 74:return "Random";case 255:case 0xffffffff:return "none";default:return "native/unknown";}}
static void Record(const Snapshot& s){
 char mask[350]={};size_t used=0;for(unsigned i=0;i<74;i++)if(s.candidates[i]){int n=snprintf(mask+used,sizeof(mask)-used,"%s%u",used?",":"",i);if(n>0)used+=(size_t)n;}
 Log("STATE active=%lu(%s) bank=%lu menu_stage_raw=%lu(%s) fight=%lu reader_type=%lu matching=%u mode_raw=%08lX prefs_DZ_C1_C2=%lu,%lu,%lu slots=%lu,%lu,%lu,%lu banks[state/req/loaded]=%lu/%u/%u;%lu/%u/%u candidates=[%s]",
 s.activeStage,Stage(s.activeStage),s.activeBank,s.selected,Stage(s.selected),s.fight,s.networkReader,s.matching,s.mode,s.preferences[0],s.preferences[1],s.preferences[2],s.slots[0],s.slots[1],s.slots[2],s.slots[3],s.bankState[0],s.requested[0],s.loaded[0],s.bankState[1],s.requested[1],s.loaded[1],mask);
}
static void TailFile(const std::wstring& from,const std::wstring& to){
 HANDLE in=CreateFileW(from.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);if(in==INVALID_HANDLE_VALUE)return;
 LARGE_INTEGER size;if(!GetFileSizeEx(in,&size)){CloseHandle(in);return;}const LONGLONG cap=2*1024*1024;
 HANDLE out=CreateFileW(to.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);if(out==INVALID_HANDLE_VALUE){CloseHandle(in);return;}
 DWORD wrote; if(size.QuadPart>cap){LARGE_INTEGER p;p.QuadPart=size.QuadPart-cap;SetFilePointerEx(in,p,nullptr,FILE_BEGIN);const char* msg="[tail: last 2 MiB only]\r\n";WriteFile(out,msg,(DWORD)strlen(msg),&wrote,nullptr);}
 char b[16384];DWORD got;LONGLONG remaining=size.QuadPart>cap?cap:size.QuadPart;while(remaining>0&&ReadFile(in,b,(DWORD)(remaining>(LONGLONG)sizeof(b)?sizeof(b):remaining),&got,nullptr)&&got){if(!WriteFile(out,b,got,&wrote,nullptr)||wrote!=got)break;remaining-=got;}
 CloseHandle(out);CloseHandle(in);
}
static void Collect(){
 std::wstring d=Path(Session,L"Logs-modules");CreateDirectoryW(d.c_str(),nullptr);
 const wchar_t* names[]={L"DOA5LR-RandomStages.log",L"DOA5LR-Crimson.log",L"DOA5LR-Crimson-VFX.log",L"DOA5LR-Crimson-Audio.log",L"DOA5LR-DangerZone.log",L"DOA5LR-DNZ-Complete.log",L"DOA5LR-DNZ-SharedAudio.log",L"DOA5LR-DNZ-Name.log",L"DOA5LR-DNZ-Preview.log"};
 for(auto n:names)TailFile(Path(GameDir,n),Path(d,n));
}
static void ShaFile(const wchar_t* path,char out[65]){
 strcpy(out,"unavailable");HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);if(f==INVALID_HANDLE_VALUE)return;
 HCRYPTPROV provider=0;HCRYPTHASH h=0;BYTE buffer[65536],digest[32];DWORD got=0,n=32;bool ok=false;
 if(CryptAcquireContextW(&provider,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&CryptCreateHash(provider,CALG_SHA_256,0,0,&h)){
  ok=true;for(;;){if(!ReadFile(f,buffer,sizeof(buffer),&got,nullptr)){ok=false;break;}if(!got)break;if(!CryptHashData(h,buffer,got,0)){ok=false;break;}}
  if(ok&&CryptGetHashParam(h,HP_HASHVAL,digest,&n,0)){for(unsigned i=0;i<32;i++)sprintf(out+2*i,"%02x",digest[i]);}
 }
 if(h)CryptDestroyHash(h);if(provider)CryptReleaseContext(provider,0);CloseHandle(f);
}
static bool Inspect(DWORD pid,bool modules){
 HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);if(snap==INVALID_HANDLE_VALUE)return false;
 MODULEENTRY32W m={};m.dwSize=sizeof(m);bool first=true;unsigned count=0;
 if(Module32FirstW(snap,&m)){do{
  if(first){Base=(DWORD)m.modBaseAddr;GameDir=m.szExePath;size_t pos=GameDir.find_last_of(L"\\/");if(pos!=std::wstring::npos)GameDir.resize(pos);first=false;}
  const wchar_t* ext=wcsrchr(m.szModule,L'.');if(modules&&ext&&!_wcsicmp(ext,L".asi")){
   char name[1024]={};if(!WideCharToMultiByte(CP_UTF8,0,m.szModule,-1,name,sizeof(name),nullptr,nullptr))strcpy(name,"unreadable_module_name");char hash[65];ShaFile(m.szExePath,hash);Log("MODULE %s size=%lu disk_sha256=%s",name,m.modBaseSize,hash);count++;
  }
 }while(Module32NextW(snap,&m));}CloseHandle(snap);
 if(first)return false;if(modules){Log("MODULE_INVENTORY asi_count=%u",count);return true;}
 IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS32 nt;
 return ReadAt(Base,&dos,sizeof(dos))&&dos.e_magic==IMAGE_DOS_SIGNATURE&&dos.e_lfanew>=64&&dos.e_lfanew<4096&&
 ReadAt(Base+dos.e_lfanew,&nt,sizeof(nt))&&nt.Signature==IMAGE_NT_SIGNATURE&&nt.FileHeader.Machine==IMAGE_FILE_MACHINE_I386&&nt.FileHeader.TimeDateStamp==0x5a1faa36&&nt.OptionalHeader.SizeOfImage==0x21f8000;
}
static DWORD Find(){
 HANDLE s=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);if(s==INVALID_HANDLE_VALUE)return 0;
 PROCESSENTRY32W p={};p.dwSize=sizeof(p);DWORD id=0;
 if(Process32FirstW(s,&p))do{if(!_wcsicmp(p.szExeFile,L"game.exe")){HANDLE h=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|SYNCHRONIZE,FALSE,p.th32ProcessID);if(h){Target=h;if(Inspect(p.th32ProcessID,false)){id=p.th32ProcessID;break;}CloseHandle(h);Target=nullptr;}}}while(Process32NextW(s,&p));CloseHandle(s);return id;
}
static int SelfTest(){
 Target=GetCurrentProcess();BYTE* memory=(BYTE*)VirtualAlloc(nullptr,0x21f8000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!memory)return 10;Base=(DWORD)memory;
 DWORD manager[4]={},controller[3]={0,1,45};manager[3]=(DWORD)controller;
 *(DWORD*)(memory+0x2072580)=(DWORD)manager;*(DWORD*)(memory+0xf83d64)=74;*(DWORD*)(memory+0x1087a4c)=4;*(DWORD*)(memory+0xf8f208)=123;
 *(DWORD*)(memory+0xf74384+44*4)=1;memory[0x207ecf8+45]=1;
 Snapshot a,b;if(!Take(a)||a.activeStage!=45||a.activeBank!=1||a.selected!=74||a.fight!=4||!a.networkReader||a.matching||a.preferences[1]!=1||a.candidates[45]!=1)return 11;
 if(!Take(b)||memcmp(&a,&b,sizeof(a)))return 12;
 controller[2]=43;if(!Take(b)||!memcmp(&a,&b,sizeof(a))||b.activeStage!=43)return 13;
 manager[3]=1;if(!Take(b)||b.activeStage!=0xffffffff)return 14;
 if(ReadRva(0x21f7fff,&b,2))return 15;
 DWORD marker=0x12345678;ReadAt((DWORD)&marker,&marker,4);if(marker!=0x12345678)return 16;
 puts("PASS: external read-only snapshot, active stage chain, Random/preferences, network flags, changed/unchanged, invalid pointers and bounds.");VirtualFree(memory,0,MEM_RELEASE);return 0;
}
int wmain(int argc,wchar_t** argv){
 if(argc>1&&!wcscmp(argv[1],L"--self-test"))return SelfTest();
 wchar_t path[32768];DWORD n=GetModuleFileNameW(nullptr,path,32768);if(!n||n>=32768)return 1;Root=path;Root.resize(Root.find_last_of(L"\\/"));
 HANDLE mutex=CreateMutexW(nullptr,TRUE,L"Local\\DOA5LR-OnlineTest-Observer-v1");if(!mutex||GetLastError()==ERROR_ALREADY_EXISTS){if(mutex)CloseHandle(mutex);return 0;}
 DeleteFileW(Path(Root,L"ARRETER.flag").c_str());CreateDirectoryW(Path(Root,L"Sessions").c_str(),nullptr);
 Status(L"Sonde active : en attente de DOA5LR. Lance le jeu normalement.");
 DWORD pid=0;ULONGLONG waitStart=GetTickCount64();
 while(!(pid=Find())){if(GetFileAttributesW(Path(Root,L"ARRETER.flag").c_str())!=INVALID_FILE_ATTRIBUTES||GetTickCount64()-waitStart>4ull*60*60*1000){Status(L"Sonde arretee (jeu non lance). Relancer Demarrer-sonde.cmd pour un nouveau test.");CloseHandle(mutex);return 0;}Sleep(500);}
 SYSTEMTIME t;GetLocalTime(&t);wchar_t folder[96];swprintf(folder,96,L"%04u%02u%02u-%02u%02u%02u-pid%lu",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,pid);
 Session=Path(Path(Root,L"Sessions"),folder);CreateDirectoryW(Session.c_str(),nullptr);
 Output=_wfopen(Path(Session,L"session.log").c_str(),L"wb");if(!Output){Status(L"Erreur : impossible de creer le journal.");CloseHandle(Target);CloseHandle(mutex);return 2;}
 Log("START observer=1.0 pid=%lu game=Steam1.10Cp1 sampling_ms=100 external_read_only=1 sampled_nonatomic=1",pid);
 Log("LEGEND stage43=DZ 44=Crimson1 45=Crimson2 74=Random; fight4=combat; reader_type0=offline 1=online 5=lobby/spectator, matching=object_present; not packet health.");
 Log("LIMITS sampled state can miss short events; no packets, chat, IP, Steam IDs, inputs or memory dumps recorded; exit code may not identify crash cause.");
 Status(L"Sonde active : enregistrement du test dans Sessions. Fermer le jeu termine la capture.");
 Inspect(pid,true);Snapshot last={};bool have=false;ULONGLONG heartbeat=0,collected=0,inventory=GetTickCount64();unsigned readFailures=0,inventoryRounds=0;
 for(;;){
  if(WaitForSingleObject(Target,0)==WAIT_OBJECT_0){DWORD code=0;if(GetExitCodeProcess(Target,&code))Log("PROCESS_EXIT code=0x%08lX",code);else Log("PROCESS_EXIT code=unavailable error=%lu",GetLastError());break;}
  if(GetFileAttributesW(Path(Root,L"ARRETER.flag").c_str())!=INVALID_FILE_ATTRIBUTES){Log("STOP requested_by_user=1 game_still_running=1");break;}
  Snapshot now;bool read=Take(now);ULONGLONG tick=GetTickCount64();
  if(read){if(!have||memcmp(&last,&now,sizeof(now))){Record(now);last=now;have=true;}readFailures=0;}
  else if(++readFailures==1||readFailures%100==0)Log("READ_INCOMPLETE error=%lu consecutive=%u",GetLastError(),readFailures);
  if(tick-heartbeat>=5000){PROCESS_MEMORY_COUNTERS pm={};pm.cb=sizeof(pm);if(GetProcessMemoryInfo(Target,&pm,sizeof(pm)))Log("HEARTBEAT active=%lu fight=%lu working_set_MiB=%llu private_commit_MiB=%llu",have?last.activeStage:0xffffffff,have?last.fight:0xffffffff,(unsigned long long)pm.WorkingSetSize/1048576,(unsigned long long)pm.PagefileUsage/1048576);else Log("HEARTBEAT memory_unavailable=1");heartbeat=tick;}
  if(tick-collected>=15000){Collect();collected=tick;}
  if(inventoryRounds<2&&tick-inventory>=15000){Inspect(pid,true);inventory=tick;inventoryRounds++;}
  if(Bytes>20ull*1024*1024){Status(L"Capture terminee : limite de 20 Mio atteinte.");break;}
  Sleep(100);
 }
 Collect();Log("END modules_log_tails_saved=1");fclose(Output);Output=nullptr;CloseHandle(Target);CloseHandle(mutex);
 Status(L"Capture terminee. Lancer Recuperer-les-logs.cmd pour creer le ZIP a transmettre.");return 0;
}
