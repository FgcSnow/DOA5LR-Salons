# 0.3.15 r3 layout (full zip extracted) -> installer 1.3.11 --auto with the real 0.3.16 archives (local manifest). Fake game, never started.
import zipfile,subprocess,tempfile,os,json,hashlib
from pathlib import Path
R=Path(r'C:\Users\Administrateur\Desktop\DOA5LR-Salons-0.3.16-Release');OLD=Path(r'C:\Users\Administrateur\Desktop\DOA5LR-Salons-0.3.15-Installer1310-Release\DOA5LR-Salons-0.3.15-r3.zip')
root=Path(tempfile.mkdtemp(prefix='doa0316-'));g=root/'game';g.mkdir();c=root/'cache';c.mkdir()
(g/'game.exe').write_bytes(b'fake never execute')
zipfile.ZipFile(OLD).extractall(g)
(g/'DOA5LR-ExtraStages.ini').write_bytes(b'[Stages]\r\nFIREWORKS=0\r\n; mine\r\n');(g/'DOA5LR-DNZ-Menu.log').write_text('x')
# a player who had the PS4 skins (0.3.15): 0.3.16 no longer manages them, they must stay untouched
SKINS={'DLC/990015/990015.bcm':b'bcm','DLC/990015/data/990015.bin':b'bin','scripts/PS4-SKINS-EN.txt':b'guide','cream_api.ini':b'[dlc]\r\n990015=PS4 Skins\r\n'}
for n,b in SKINS.items():(g/n).parent.mkdir(parents=True,exist_ok=True);(g/n).write_bytes(b)
(g/'DOA5LR-Salons-Components.txt').write_text('ps4skins=1\nmaps=1\n')
env=dict(os.environ,TEMP=str(c),TMP=str(c))
p=subprocess.run([str(R/'DOA5LR-Salons-Installer.exe'),'--auto','--game',str(g),'--manifest',str(R/'version-TEST-LOCAL.txt')],env=env,timeout=600)
log=(g/'DOA5LR-Salons-Installer.log').read_text(errors='replace')
def ok(c,m):
    print(('OK   ' if c else 'FAIL ')+m)
    if not c:print(log[-4000:]);raise SystemExit(1)
ok(p.returncode==0,'installer --auto exit 0')
core=zipfile.ZipFile(R/'DOA5LR-Salons-core-0.3.16.zip');full=zipfile.ZipFile(R/'DOA5LR-Salons-0.3.16.zip')
MAPS=['Crimson','Crimson-Audio','Crimson-VFX','DangerZone','DNZ-Complete','DNZ-Name','DNZ-Preview','DNZ-SharedAudio','DNZ-Thumbnail','ExtraStages','RandomStages']
ok(not any((g/f'scripts/DOA5LR-{m}.asi').exists() for m in MAPS),'no stage module left in scripts folder')
for n in full.namelist():
    if n.endswith(('.asi','.dll','.exe','.textures')) and not n.startswith('DOA5LR-Diagnostic/Sonde') and n not in ('DOA5LR-Salons-Installer.exe','DOA5LR-Companion.exe','DOA5LR-InputBridge-Xidi.dll'):
        ok((g/n).exists() and (g/n).read_bytes()==full.read(n),'installed = archive: '+n)
ok((g/'scripts/DOA5LR-Stages/DOA5LR-ExtraStages.ini').read_bytes()==b'[Stages]\r\nFIREWORKS=0\r\n; mine\r\n','player ExtraStages.ini moved into scripts/DOA5LR-Stages and kept')
INIS=['Crimson-Audio','Crimson-VFX','DangerZone','DNZ-Complete','DNZ-SharedAudio','ExtraStages','RandomStages']
ok(not any((g/f'DOA5LR-{n}.ini').exists() for n in INIS) and all((g/f'scripts/DOA5LR-Stages/DOA5LR-{n}.ini').exists() for n in INIS),'7 stage .ini only in the stage folder')
left=sorted(f.name for f in g.iterdir() if f.is_file() and f.name.startswith('DOA5LR-'))
print('game folder DOA5LR-* files left:',left)
ok(not (g/'DOA5LR-DNZ-Menu.log').exists(),'orphan log removed')
ok('stage data up to date' in log or 'stage data to download: 1' not in log,'stage data: '+[l for l in log.splitlines() if 'stage data' in l][-1][:150])
ok((g/'DOA5LR-Salons-VERSION.txt').read_text().strip()=='0.3.16','VERSION 0.3.16')
for e in json.loads(core.read('DOA5LR-Diagnostic/salons-modules.json')):
    ok(hashlib.sha256((g/e['path']).read_bytes()).hexdigest()==e['sha256'],'diagnostic hash matches '+e['path'])
ok(all((g/n).read_bytes()==b for n,b in SKINS.items()),'installed PS4 skins and loader config left untouched')
ok(not any('skin' in n.lower() or '990015' in n for n in full.namelist()),'no PS4 skin file in the 0.3.16 archives')
ok('skins_data=' not in (R/'version.txt').read_text() and 'optional_v6=' not in (R/'version.txt').read_text(),'manifest has no skins component')
print('PASS',g)
