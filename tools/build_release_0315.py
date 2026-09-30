from pathlib import Path
import json,subprocess,sys,shutil
from zipfile import ZipFile
from build_release_0311 import sha,sign,write_zip
from build_release_0314_ps4 import sums
from pack_docs import pack_guides,check_pack_guides
r=Path(__file__).resolve().parents[1];desktop=Path(r'C:\Users\Administrateur\Desktop');base=desktop/'DOA5LR-Salons-0.3.14-Installer137-Release';out=desktop/'DOA5LR-Salons-0.3.15-Release';out.mkdir(exist_ok=True)
manifest=(r/'version.txt').read_text();fields=dict(l.split('=',1) for l in manifest.splitlines() if '=' in l and not l.startswith('#'))
def read(p):
 with ZipFile(p) as z:
  assert z.testzip() is None;return {n:z.read(n) for n in z.namelist()}
fullpath=base/'DOA5LR-Salons-0.3.14-r2.zip';corepath=base/'DOA5LR-Salons-core-0.3.14-r2.zip';assert sha(fullpath.read_bytes())==fields['sha256'];assert sha(corepath.read_bytes())==fields['core'].split('|')[1]
full=read(fullpath);core=read(corepath);mapspath=desktop/'DOA5LR-Salons-0.3.14-PS4-Release/DOA5LR-Salons-maps-data-1.zip';assert sha(mapspath.read_bytes())==fields['data'].split('|')[2];maps=read(mapspath);assert core|maps==full
src=r/'src/Installer';subprocess.run(['cmd','/c',str(src/'build.cmd')],cwd=src,check=True);exe=sign({'DOA5LR-Salons-Installer.exe':(src/'DOA5LR-Salons-Installer.exe').read_bytes()})['DOA5LR-Salons-Installer.exe'];(out/'DOA5LR-Salons-Installer.exe').write_bytes(exe)
hotfix=desktop/'DOA5LR-RandomStages-2.2-HOTFIX';asi=(hotfix/'DOA5LR-RandomStages.asi').read_bytes();assert sha(asi)=='479e0aba1889f4d1d3764c54ccd5bb27390c6a65536eb8dcfc6774d352d9be75'
game=Path(r'D:\SteamLibrary\steamapps\common\Dead or Alive 5 Last Round');skins={n:(game/n).read_bytes() for n in ['DLC/990015/990015.bcm','DLC/990015/data/990015.bin','DLC/990015/data/990015.blp','DLC/990015/data/990015.lnk']};assert sha(skins['DLC/990015/990015.bcm'])=='56a70dea9fdb652b67c6ef4bc87092059477c7dfede923c70b16c332a6ad6289'
old=core.copy();core.update(pack_guides('0.3.15'));core.update({'scripts/DOA5LR-RandomStages.asi':asi,'DOA5LR-RandomStages.ini':(hotfix/'DOA5LR-RandomStages.ini').read_bytes(),'DOA5LR-Salons-Installer.exe':exe,'scripts/Installer-Source/Installer.cs':(src/'Installer.cs').read_bytes(),'DOA5LR-Salons-VERSION.txt':b'0.3.15\r\n'})
for listing,changes in [('DOA5LR-Diagnostic/maps-files.json',core),('DOA5LR-Diagnostic/ps4skins-files.json',skins)]:
 rows=json.loads(core[listing])
 for x in rows:
  n=x['path'].replace('\\','/')
  if n in changes:x['sha256']=sha(changes[n]);x['size']=len(changes[n])
 core[listing]=json.dumps(rows,indent=2).encode()
core['scripts/PS4-SKINS-EN.txt']=core['scripts/PS4-SKINS-EN.txt']+b'\n0.3.15: PS4 hairstyle choices/order corrected. Installer accepts absent appid/orgapi with default original DLL validation. Four targeted costume menu tests passed; all combinations are not combat-validated.\n'
if 'scripts/MAPS-DZ-CRIMSON-EN.txt' in core:core['scripts/MAPS-DZ-CRIMSON-EN.txt']=b'0.3.15 UPDATE: RandomStages 2.2 fixes online detection. Online=0 admits extra stages only when every lobby member reports map support. Online=1 bypasses this check. Mixed-lobby exclusion tested; two updated-player positive test still pending. Existing INI settings are preserved.\n\n'+core['scripts/MAPS-DZ-CRIMSON-EN.txt']
full=core|maps;full['SHA256SUMS.txt']=sums(full);core['SHA256SUMS.txt']=full['SHA256SUMS.txt'];assert core|maps==full
complete=full|skins;complete['SHA256SUMS.txt']=sums(complete)
for name,payload in [('DOA5LR-Salons-0.3.15.zip',full),('DOA5LR-Salons-core-0.3.15.zip',core),('DOA5LR-Salons-0.3.15-PS4.zip',complete),('DOA5LR-Salons-ps4skins-data-2.zip',skins)]:write_zip(out/name,payload)
shutil.copy2(mapspath,out/mapspath.name)
url='https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.15/'
def info(n):p=out/n;return url+n+'|'+sha(p.read_bytes())+'|'+str(p.stat().st_size)
updates={'version':'0.3.15','url':url+'DOA5LR-Salons-0.3.15.zip','sha256':sha((out/'DOA5LR-Salons-0.3.15.zip').read_bytes()),'size':str((out/'DOA5LR-Salons-0.3.15.zip').stat().st_size),'core':info('DOA5LR-Salons-core-0.3.15.zip'),'data':'maps|'+info(mapspath.name),'skins_data':info('DOA5LR-Salons-ps4skins-data-2.zip'),'installer':url+'DOA5LR-Salons-Installer.exe','installer_version':'1.3.8','installer_sha256':sha(exe),'notes':'0.3.15 emergency online Random fix, PS4 hairstyles and installer defaults fix'}
lines=[]
for l in manifest.splitlines():
 key=l.split('=',1)[0]
 if key in updates:l=key+'='+updates[key]
 if l.startswith('note=0.3.14: Danger Zone / Crimson are drawn by OFFLINE'):continue
 lines.append(l)
lines[1:1]=['note=0.3.15: RandomStages 2.2 fixes incorrect online detection in 0.3.14. With Online=0, extra stages are excluded unless every lobby member reports map support. Online=1 bypasses the check; existing settings are preserved.','note=0.3.15: mixed-lobby exclusion tested in game; positive Random selection between two updated players still needs confirmation.','note=0.3.15: PS4 hairstyle choices/order corrected; four targeted costume menu tests passed. Installer 1.3.8 accepts absent appid/orgapi while validating existing DLLs.']
text='\n'.join(lines)+'\n';(out/'version.txt').write_text(text);(r/'version.txt').write_text(text)
local=[]
for l in text.splitlines():
 if l.startswith(('installer=','installer_version=','installer_sha256=')):continue
 l=l.replace(url,str(out)+'\\');local.append(l)
(out/'version-TEST-LOCAL.txt').write_text('\n'.join(local)+'\n')
report={'changed_core_files':[n for n,b in core.items() if old.get(n)!=b],'assets':{p.name:{'sha256':sha(p.read_bytes()),'size':p.stat().st_size} for p in out.iterdir() if p.suffix in ['.exe','.zip']}}
(out/'build-report.json').write_text(json.dumps(report,indent=2));(out/'SHA256SUMS.txt').write_text(''.join(v['sha256']+' *'+n+'\n' for n,v in report['assets'].items()));print(json.dumps(report,indent=2))
