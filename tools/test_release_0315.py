from pathlib import Path
import json,hashlib,tempfile,subprocess,os,struct
from zipfile import ZipFile
r=Path(__file__).resolve().parents[1];out=Path(r'C:\Users\Administrateur\Desktop\DOA5LR-Salons-0.3.15-Release')
def sha(b):return hashlib.sha256(b).hexdigest()
report=json.loads((out/'build-report.json').read_text())
for n,v in report['assets'].items():assert sha((out/n).read_bytes())==v['sha256']
def read(n):
 with ZipFile(out/n) as z:assert z.testzip() is None;return {n:z.read(n) for n in z.namelist()}
core=read('DOA5LR-Salons-core-0.3.15.zip');maps=read('DOA5LR-Salons-maps-data-1.zip');full=read('DOA5LR-Salons-0.3.15.zip');skins=read('DOA5LR-Salons-ps4skins-data-2.zip');assert core|maps==full
for listing in ['maps-files.json','ps4skins-files.json']:
 for e in json.loads(core['DOA5LR-Diagnostic/'+listing]):
  b=(full|skins)[e['path'].replace('\\','/')];assert sha(b)==e['sha256'] and len(b)==e['size']
print('PASS release hashes, archive equality and both integrity manifests',flush=True)
def dll(proxy=False):
 b=bytearray(128);b[:2]=b'MZ';struct.pack_into('<I',b,60,64);b[64:68]=b'PE\0\0';struct.pack_into('<H',b,68,0x14c);return bytes(b)+b'SteamAPI_Init\0'+(b'cream_api.ini\0' if proxy else b'')
root=Path(tempfile.mkdtemp(prefix='doa5315-'));game=root/'game';game.mkdir();cache=root/'cache';cache.mkdir();(game/'game.exe').write_bytes(b'fake never execute');ini=b'[dlc]\r\n990015=PS4 Skins\r\n1234=Personal\r\n';(game/'cream_api.ini').write_bytes(ini);(game/'steam_api.dll').write_bytes(dll(True));(game/'steam_api_o.dll').write_bytes(dll())
# Exercise upgrade of the old hairstyle registration and preservation of explicit settings.
(game/'DLC/990015').mkdir(parents=True);(game/'DLC/990015/990015.bcm').write_bytes(Path(r'D:\DOA5LR-PS4-costume-analysis\backup-options-20260930-222707\990015.bcm').read_bytes());settings=b'[RandomStages]\r\nOnline=0\r\n; personal\r\n';(game/'DOA5LR-RandomStages.ini').write_bytes(settings)
env=dict(os.environ,TEMP=str(cache),TMP=str(cache));p=subprocess.run([str(out/'DOA5LR-Salons-Installer.exe'),'--auto','--game',str(game),'--manifest',str(out/'version-TEST-LOCAL.txt')],env=env,timeout=180)
assert p.returncode==0,(game/'DOA5LR-Salons-Installer.log').read_text(errors='replace')[-5000:]
for n,b in skins.items():assert (game/n).read_bytes()==b
assert (game/'scripts/DOA5LR-RandomStages.asi').read_bytes()==core['scripts/DOA5LR-RandomStages.asi'];assert (game/'cream_api.ini').read_bytes()==ini;assert (game/'DOA5LR-RandomStages.ini').read_bytes()==settings
assert list((game/'DOA5LR-Salons-Backups').rglob('990015.bcm'))
print('PASS real archives installed into isolated fake game; old hair file backed up and replaced; personal settings unchanged',flush=True)
(out/'validation.json').write_text(json.dumps({'passed':True,'fake_game':str(game),'checks':['hashes','integrity manifests','real archive upgrade','dlc-only config','backup','settings preservation']},indent=2))
