"""DOA5LR-Salons 0.3.17 = the published 0.3.16 back to its state before the Lab (Destroyed) work (desyncs reported online):
DOA5LR-LabDestroyed.asi removed, ExtraStages 2.0.9 + texture v5 (slot 27 = Lab (Destroyed) picture) back to the signed
ExtraStages 2.0.8 + texture v4 of the earlier 0.3.16 build (Desktop/DOA5LR-Salons-0.3.16-Release-v208-ANCIEN).

Nothing is rebuilt or re-signed: the core keeps the 0.3.16 bytes except the removed module, the version file, the guides
and SHA256SUMS.txt. Installer 1.3.11 (same bytes, no installer prompt) and maps-data-2 (same bytes, re-uploaded under
v0.3.17) are reused. (2.0.8 checks the v4 texture hash: the two go together).
  python tools/build_release_0317.py
"""
import json, shutil
from pathlib import Path
from zipfile import ZipFile
from build_release_0311 import write_zip, sha
from build_release_0314_ps4 import sums
from pack_docs import pack_guides, check_pack_guides

V, PREV = '0.3.17', '0.3.16'
repo = Path(__file__).resolve().parents[1]
desk = Path(r'C:\Users\Administrateur\Desktop')
prev = desk / f'DOA5LR-Salons-{PREV}-Release'
out = desk / f'DOA5LR-Salons-{V}-Release'
assert not out.exists() or not any(out.iterdir()), 'remove or rename the previous output folder first'
out.mkdir(exist_ok=True)
LAB = 'scripts/DOA5LR-Stages/DOA5LR-LabDestroyed.asi'

def read(p):
    with ZipFile(p) as z:
        assert z.testzip() is None
        return {n: z.read(n) for n in z.namelist()}

# 1. the published 0.3.16 (manifest = the public one)
manifest = (prev / 'version.txt').read_text(encoding='utf-8-sig')
assert manifest.replace('\r\n', '\n') == (repo / 'version.txt').read_text(encoding='utf-8-sig').replace('\r\n', '\n')
fields = dict(l.split('=', 1) for l in manifest.splitlines() if '=' in l and not l.startswith('#'))
assert fields['version'] == PREV
names_prev = {'full': f'DOA5LR-Salons-{PREV}.zip', 'core': f'DOA5LR-Salons-core-{PREV}.zip', 'maps': 'DOA5LR-Salons-maps-data-2.zip'}
assert sha((prev / names_prev['full']).read_bytes()) == fields['sha256']
assert sha((prev / names_prev['core']).read_bytes()) == fields['core'].split('|')[1]
assert sha((prev / names_prev['maps']).read_bytes()) == fields['data'].split('|')[2]
exe = (prev / 'DOA5LR-Salons-Installer.exe').read_bytes(); assert sha(exe) == fields['installer_sha256']
core = read(prev / names_prev['core']); maps2 = read(prev / names_prev['maps'])
assert core | maps2 == read(prev / names_prev['full'])

# 2. core: module out, version, guides, sums
old = dict(core)
del core[LAB]
ES, THUMBS = 'scripts/DOA5LR-Stages/DOA5LR-ExtraStages.asi', 'PS4Stages/MENU/STAGESELECT-THUMBS.textures'
pre = read(desk / 'DOA5LR-Salons-0.3.16-Release-v208-ANCIEN' / 'DOA5LR-Salons-core-0.3.16.zip')
assert sha(pre[ES]) == '46d5bca0' + sha(pre[ES])[8:] and b'2.0.8' in pre[ES] and b'LabPicture' not in pre[ES]
assert sha(pre[THUMBS]) == '74e4e0c08057ca6f4671cbd8c1d3f9fdddfb067dcf85fc9c89573f963a4c2fb5' and sha(pre[THUMBS]).encode() in pre[ES]
assert len(pre[THUMBS]) == len(core[THUMBS])
core[ES], core[THUMBS] = pre[ES], pre[THUMBS]
for f in ('DOA5LR-Diagnostic/maps-files.json', 'DOA5LR-Diagnostic/salons-modules.json'):
    rows = json.loads(core[f])
    for x in rows:
        n = x['path'].replace(chr(92), '/')
        if n in (ES, THUMBS):
            x['sha256'] = sha(core[n])
            if 'size' in x: x['size'] = len(core[n])
    core[f] = json.dumps(rows, indent=2).encode()
assert not any('labdestroyed' in n.lower() for n in core | maps2)
core['DOA5LR-Salons-VERSION.txt'] = (V + '\r\n').encode()
core.update(pack_guides(V))
for f in ('DOA5LR-Diagnostic/maps-files.json', 'DOA5LR-Diagnostic/salons-modules.json'):
    assert b'LabDestroyed' not in core[f]
full = core | maps2; full['SHA256SUMS.txt'] = sums(full); core['SHA256SUMS.txt'] = full['SHA256SUMS.txt']
check_pack_guides(core, V)
changed = sorted(n for n, b in core.items() if old.get(n) != b)
assert set(changed) <= {ES, THUMBS, 'DOA5LR-Diagnostic/maps-files.json', 'DOA5LR-Diagnostic/salons-modules.json', 'DOA5LR-Salons-VERSION.txt', 'SHA256SUMS.txt', 'READ-ME-FIRST-EN.txt', 'START-HERE.md', 'InputLab/START-HERE-EN.md'}, changed
names = {'full': f'DOA5LR-Salons-{V}.zip', 'core': f'DOA5LR-Salons-core-{V}.zip', 'maps': 'DOA5LR-Salons-maps-data-2.zip'}
write_zip(out / names['full'], full); write_zip(out / names['core'], core)
shutil.copyfile(prev / names_prev['maps'], out / names['maps'])
(out / 'DOA5LR-Salons-Installer.exe').write_bytes(exe)

# 3. manifest
url = f'https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v{V}/'
def info(n): p = out / n; return url + n + '|' + sha(p.read_bytes()) + '|' + str(p.stat().st_size)
updates = {'version': V, 'url': url + names['full'], 'sha256': sha((out / names['full']).read_bytes()), 'size': str((out / names['full']).stat().st_size),
           'core': info(names['core']), 'data': 'maps|' + info(names['maps']), 'installer': url + 'DOA5LR-Salons-Installer.exe',
           'notes': '0.3.17 back to 0.3.16 without the Lab (destroyed) variant (online desyncs)'}
lines = []
for l in manifest.splitlines():
    key = l.split('=', 1)[0]
    if key in updates: l = key + '=' + updates[key]
    lines.append(l)
assert fields['installer_version'] == '1.3.11'
# every place a copy could be (the installer only de-duplicates the 11 map modules, and no component owns this one)
dels = ['delete=scripts\\DOA5LR-Stages\\DOA5LR-LabDestroyed.asi', 'delete=scripts\\DOA5LR-LabDestroyed.asi', 'delete=DOA5LR-LabDestroyed.asi',
        'delete=DOA5LR-Logs\\DOA5LR-LabDestroyed.log', 'delete=DOA5LR-LabDestroyed.log']
at = max(i for i, l in enumerate(lines) if l.startswith('delete=')) + 1; lines[at:at] = dels
lines[1:1] = ['note=0.3.17: the second variant of the Lab tile (Lab, destroyed) added in 0.3.16 is removed (desyncs reported online): the update deletes its module and its log, the Lab tile is the original one again. Everyone should update: a 0.3.16 player can still pick it.',
              'note=0.3.17: ExtraStages and the stage-select pictures are back to the 0.3.16 build made before that work. Every other file is byte-identical to 0.3.16 (same Installer 1.3.11, no stage data download).']
text = '\n'.join(lines) + '\n'
assert all(d in text for d in dels) and sum(l.startswith('version=') for l in text.splitlines()) == 1
(out / 'version.txt').write_text(text, encoding='utf-8'); (repo / 'version.txt').write_text(text, encoding='utf-8')
local = [l.replace(url, str(out) + '\\') for l in text.splitlines() if not l.startswith(('installer=', 'installer_version=', 'installer_sha256='))]
(out / 'version-TEST-LOCAL.txt').write_text('\n'.join(local) + '\n', encoding='utf-8')
report = {'version': V, 'changed_core_files': changed, 'removed_core_files': sorted(n for n in old if n not in core),
          'assets': {p.name: {'sha256': sha(p.read_bytes()), 'size': p.stat().st_size} for p in sorted(out.iterdir()) if p.suffix in ('.exe', '.zip')}}
(out / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(out / 'SHA256SUMS.txt').write_text(''.join(v['sha256'] + ' *' + n + '\n' for n, v in report['assets'].items()), encoding='ascii')
print(json.dumps(report, indent=2))
