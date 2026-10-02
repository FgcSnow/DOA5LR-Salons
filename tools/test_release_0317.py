# 0.3.16 published layout (full zip extracted, maps off and on) -> installer 1.3.11 --auto with the real 0.3.17 archives (local manifest).
# Fake game, never started. Checks: LabDestroyed module and log gone (every possible place), ExtraStages 2.0.8 + texture v4,
# no stage data download, every other installed binary = archive, diagnostic hashes match.
import zipfile,subprocess,tempfile,os,json,hashlib,sys
from pathlib import Path
R=Path(r'C:\Users\Administrateur\Desktop\DOA5LR-Salons-0.3.17-Release');OLD=Path(r'C:\Users\Administrateur\Desktop\DOA5LR-Salons-0.3.16-Release\DOA5LR-Salons-0.3.16.zip')
core=zipfile.ZipFile(R/'DOA5LR-Salons-core-0.3.17.zip');full=zipfile.ZipFile(R/'DOA5LR-Salons-0.3.17.zip')
LAB=['scripts/DOA5LR-Stages/DOA5LR-LabDestroyed.asi','scripts/DOA5LR-LabDestroyed.asi','DOA5LR-LabDestroyed.asi','DOA5LR-Logs/DOA5LR-LabDestroyed.log']
def run(maps):
    root=Path(tempfile.mkdtemp(prefix='doa0317-'));g=root/'game';g.mkdir();c=root/'cache';c.mkdir()
    (g/'game.exe').write_bytes(b'fake never execute')
    zipfile.ZipFile(OLD).extractall(g)
    for n in LAB[1:]:(g/n).parent.mkdir(parents=True,exist_ok=True);(g/n).write_bytes(b'x')
    (g/'DOA5LR-Logs/DOA5LR-Crimson.log').write_text('keep')
    (g/'DOA5LR-Salons-Components.txt').write_text(f'maps={maps}\n')
    env=dict(os.environ,TEMP=str(c),TMP=str(c))
    p=subprocess.run([str(R/'DOA5LR-Salons-Installer.exe'),'--auto','--game',str(g),'--manifest',str(R/'version-TEST-LOCAL.txt')],env=env,timeout=600)
    log=(g/'DOA5LR-Salons-Installer.log').read_text(errors='replace')
    def ok(cnd,m):
        print(('OK   ' if cnd else 'FAIL ')+f'[maps={maps}] '+m)
        if not cnd:print(log[-4000:]);sys.exit(1)
    ok(p.returncode==0,'installer --auto exit 0')
    for n in LAB: ok(not (g/n).exists(),'removed '+n)
    ok((g/'DOA5LR-Logs/DOA5LR-Crimson.log').exists(),'other logs kept')
    ok((g/'DOA5LR-Salons-VERSION.txt').read_text().strip()=='0.3.17','VERSION 0.3.17')
    ok('stage data to download: 1' not in log,'no stage data download')
    if maps:
        es=(g/'scripts/DOA5LR-Stages/DOA5LR-ExtraStages.asi').read_bytes();ok(b'2.0.8' in es and b'LabPicture' not in es,'ExtraStages 2.0.8')
        ok(hashlib.sha256((g/'PS4Stages/MENU/STAGESELECT-THUMBS.textures').read_bytes()).hexdigest().startswith('74e4e0c0'),'texture v4')
        for n in full.namelist():
            if n.endswith(('.asi','.dll','.exe','.textures')) and not n.startswith('DOA5LR-Diagnostic/Sonde') and n not in ('DOA5LR-Salons-Installer.exe','DOA5LR-Companion.exe','DOA5LR-InputBridge-Xidi.dll'):
                ok((g/n).exists() and (g/n).read_bytes()==full.read(n),'installed = archive: '+n)
        for e in json.loads(core.read('DOA5LR-Diagnostic/maps-files.json')):
            ok(hashlib.sha256((g/e['path']).read_bytes()).hexdigest()==e['sha256'],'maps-files hash '+e['path'])
    else:
        ok(not (g/'scripts/DOA5LR-Stages/DOA5LR-ExtraStages.asi').exists(),'maps left out')
    for e in json.loads(core.read('DOA5LR-Diagnostic/salons-modules.json')):
        ok(hashlib.sha256((g/e['path']).read_bytes()).hexdigest()==e['sha256'],'diagnostic hash matches '+e['path'])
    print([l for l in log.splitlines() if 'done:' in l][-1])
run(1);run(0);print('PASS')
