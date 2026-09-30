"""Build installer-only revision r2 of validated 0.3.14 archives; no publication."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from zipfile import ZipFile
from build_release_0311 import sign, write_zip, sha
from pack_docs import pack_guides, check_pack_guides

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-dir',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[1]
    assert not args.out.exists(), 'Use a new output folder'
    for line in (args.base_dir/'SHA256SUMS.txt').read_text().splitlines():
        h,n=line.split(' *',1)
        assert sha((args.base_dir/n).read_bytes())==h,n
    args.out.mkdir()
    src=repo/'src/Installer'
    subprocess.run(['cmd','/c',str(src/'build.cmd')],cwd=src,check=True)
    installer=sign({'DOA5LR-Salons-Installer.exe':(src/'DOA5LR-Salons-Installer.exe').read_bytes()})['DOA5LR-Salons-Installer.exe']
    (args.out/'DOA5LR-Salons-Installer-1.3.7.exe').write_bytes(installer)
    source=(src/'Installer.cs').read_bytes()
    guides=pack_guides('0.3.14')
    changed={}
    mapping={}
    for name in ['DOA5LR-Salons-0.3.14.zip','DOA5LR-Salons-core-0.3.14.zip','DOA5LR-Salons-0.3.14-PS4.zip']:
        with ZipFile(args.base_dir/name) as z: original={n:z.read(n) for n in z.namelist()}
        payload=dict(original)
        assert 'DOA5LR-Salons-Installer.exe' in payload
        payload['DOA5LR-Salons-Installer.exe']=installer
        payload['scripts/Installer-Source/Installer.cs']=source
        payload.update(guides)
        check_pack_guides(payload,'0.3.14')
        changed[name]=[n for n in payload if payload[n]!=original.get(n)]
        assert all(n in ['DOA5LR-Salons-Installer.exe','scripts/Installer-Source/Installer.cs',*guides] for n in changed[name])
        target=name[:-4]+'-r2.zip'; write_zip(args.out/target,payload); mapping[name]=target
    manifest=(args.base_dir/'version.txt').read_text(encoding='utf-8-sig')
    old_full='DOA5LR-Salons-0.3.14.zip'; full=args.out/mapping[old_full]
    old_core='DOA5LR-Salons-core-0.3.14.zip'; core=args.out/mapping[old_core]
    lines=[]
    for line in manifest.splitlines():
        if line.startswith('url='): line=line.replace(old_full,full.name)
        elif line.startswith('sha256='): line='sha256='+sha(full.read_bytes())
        elif line.startswith('size='): line='size='+str(full.stat().st_size)
        elif line.startswith('core='): line=line.split('|')[0].replace(old_core,core.name)+'|'+sha(core.read_bytes())+'|'+str(core.stat().st_size)
        elif line.startswith('installer='): line=line.replace('DOA5LR-Salons-Installer.exe','DOA5LR-Salons-Installer-1.3.7.exe')
        elif line.startswith('installer_version='): line='installer_version=1.3.7'
        elif line.startswith('installer_sha256='): line='installer_sha256='+sha(installer)
        lines.append(line)
    lines.insert(1,'note=Installer 1.3.7: missing costume registration section is added with backup when the existing loader is compatible; loader detection errors now explain the missing requirement.')
    (args.out/'version.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assets=[p for p in args.out.iterdir() if p.suffix in ['.zip','.exe']]
    report={'installer_version':'1.3.7','changed':changed,'assets':{p.name:{'sha256':sha(p.read_bytes()),'size':p.stat().st_size} for p in assets}}
    (args.out/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (args.out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+' *'+p.name+'\n' for p in assets),encoding='ascii')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
