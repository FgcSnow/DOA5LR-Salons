"""Build DOA5LR-Salons 0.3.16 from the published 0.3.15 r3 archives; no publication.

0.3.16 = 0.3.15 r3 + stage modules in scripts\\DOA5LR-Stages\\ (logs in DOA5LR-Logs\\), ExtraStages 2.0.9 with the
corrected stage-select texture (Lorelei Halloween, Scramble/Plant/Circus lower levels), LabDestroyed 1.0 (not announced), installer 1.3.11.
The corrected texture moves from the stage data archive to the core: players whose other stage files are intact
download only the core. maps-data-2 = maps-data-1 without that file.
  python tools/build_release_0316.py
"""
import json, re, shutil, subprocess
from pathlib import Path
from zipfile import ZipFile
from build_release_0311 import sign, write_zip, sha
from build_release_0314_ps4 import sums
from pack_docs import pack_guides, check_pack_guides

V = '0.3.16'
repo = Path(__file__).resolve().parents[1]
desk = Path(r'C:\Users\Administrateur\Desktop')
r3 = desk / 'DOA5LR-Salons-0.3.15-Installer1310-Release'
r315 = desk / 'DOA5LR-Salons-0.3.15-Release'
mods = Path(r'D:\DOA5LR-stage-analysis\clean-0316\out')
o1 = Path(r'D:\DOA5LR-stage-analysis\o1-builds')   # -O1 without -s (fewer antivirus false positives); see its LISEZ-MOI.md
out = desk / f'DOA5LR-Salons-{V}-Release'
assert not out.exists() or not any(out.iterdir()), 'remove or rename the previous output folder first'

MAPS = ['Crimson', 'Crimson-Audio', 'Crimson-VFX', 'DangerZone', 'DNZ-Complete', 'DNZ-Name', 'DNZ-Preview', 'DNZ-SharedAudio',
        'DNZ-Thumbnail', 'ExtraStages', 'RandomStages']
STAGES = 'scripts/DOA5LR-Stages/'
THUMBS = 'PS4Stages/MENU/STAGESELECT-THUMBS.textures'

def read(p):
    with ZipFile(p) as z:
        assert z.testzip() is None
        return {n: z.read(n) for n in z.namelist()}

# 1. inputs: the public 0.3.15 manifest, its archives, the module builds
manifest = (r3 / 'version.txt').read_text(encoding='utf-8-sig')
assert manifest.replace('\r\n', '\n') == (repo / 'version.txt').read_text(encoding='utf-8-sig').replace('\r\n', '\n'), 'repo version.txt is not the 0.3.15 r3 manifest'
fields = dict(l.split('=', 1) for l in manifest.splitlines() if '=' in l and not l.startswith('#'))
corepath = r3 / 'DOA5LR-Salons-core-0.3.15-r3.zip'; assert sha(corepath.read_bytes()) == fields['core'].split('|')[1]
mapspath = r315 / 'DOA5LR-Salons-maps-data-1.zip'; assert sha(mapspath.read_bytes()) == fields['data'].split('|')[2]
core = read(corepath); maps1 = read(mapspath)
assert core | maps1 == read(r3 / 'DOA5LR-Salons-0.3.15-r3.zip')
def pinned(d):
    out_ = {}
    for l in (d / 'SHA256SUMS.txt').read_text().splitlines():
        if not l.strip(): continue
        h, n = l.split(None, 1); n = n.lstrip('*'); b = (d / n).read_bytes(); assert sha(b) == h, n; out_[n] = b
    return out_
built = pinned(o1 / 'stages')
assert set(built) == {f'DOA5LR-{m}.asi' for m in MAPS if m != 'DangerZone'} | {'DOA5LR-DebugArchive.asi', 'DOA5LR-LabDestroyed.asi'}
assert sha(built['DOA5LR-ExtraStages.asi']) == 'ade22d4779d5b5d3bec55db849ebdcd6b37832148ad950950b98ff87b0360053'   # 2.0.9 -O1, v2.0 hosts
# Danger Zone: MSVC build (not concerned by the gcc flags)
dz = (mods / 'DOA5LR-DangerZone.asi').read_bytes(); assert sha(dz) == '4fd9b983e7db98dbad945883d331e5649293368f04109f5e2bd62eddc55e73a4'; built['DOA5LR-DangerZone.asi'] = dz
labb = built.pop('DOA5LR-LabDestroyed.asi')
coremods = pinned(o1 / 'core')
assert set(coremods) == {'DOA5LR-60fps-menus.asi', 'DOA5LR-Borderless.asi', 'DOA5LR-InviteFix.asi', 'DOA5LR-JoinFix.asi', 'DOA5LR-UpdateCheck.asi', 'DOA5LR-WiFi-Wired-Detector.asi'}
thumbs = (o1 / 'STAGESELECT-THUMBS.textures').read_bytes()   # v5: blank slots 25 (Crimson 1) and 27 (default, shown only for stage 7) changed; DNZ / Crimson 2 use native slots 55 / 56
assert sha(thumbs) == 'e76cdb0103f80e0e9885c58f35768800edf2af294ff00148ac285ece1cb41f76' and len(thumbs) == len(maps1[THUMBS])

# 2. installer 1.3.11 and module signatures
out.mkdir(exist_ok=True)
src = repo / 'src/Installer'
assert '"1.3.11"' in (src / 'Installer.cs').read_text(encoding='utf-8')
subprocess.run(['cmd', '/c', str(src / 'build.cmd')], cwd=src, check=True)
blobs = {'DOA5LR-Salons-Installer.exe': (src / 'DOA5LR-Salons-Installer.exe').read_bytes()}
blobs.update({STAGES + f'DOA5LR-{m}.asi': built[f'DOA5LR-{m}.asi'] for m in MAPS})
blobs['DOA5LR-DebugArchive.asi'] = built['DOA5LR-DebugArchive.asi']
blobs[STAGES + 'DOA5LR-LabDestroyed.asi'] = labb
blobs.update({'scripts/' + n: b for n, b in coremods.items()})
signed = sign(blobs)
exe = signed.pop('DOA5LR-Salons-Installer.exe'); (out / 'DOA5LR-Salons-Installer.exe').write_bytes(exe)

# 3. core
old = dict(core)
for m in MAPS: del core[f'scripts/DOA5LR-{m}.asi']
assert all('scripts/' + n in core for n in coremods)
core.update(signed)
core[THUMBS] = thumbs
core.update(pack_guides(V))
core.update({'DOA5LR-Salons-Installer.exe': exe, 'scripts/Installer-Source/Installer.cs': (src / 'Installer.cs').read_bytes(),
             'DOA5LR-Diagnostic/DOA5LR-Diagnostic.ps1': (repo / 'src/Diagnostic/DOA5LR-Diagnostic.ps1').read_bytes(),
             'DOA5LR-Salons-VERSION.txt': (V + '\r\n').encode()})
core['scripts/MAPS-DZ-CRIMSON-EN.txt'] = (b'0.3.16 UPDATE: the stage modules and their .ini files are in scripts\\DOA5LR-Stages\\, their logs in DOA5LR-Logs\\ (your settings are moved and kept). '
    b'Lorelei Halloween and the lower levels of Scramble, Plant and Circus show their own pictures again.\n\n') + core['scripts/MAPS-DZ-CRIMSON-EN.txt']
maps2 = {n: b for n, b in maps1.items() if n != THUMBS}
# 0.3.16: PS4 skins out of the pack (maintainer's decision): no skins archive, no optional_v6 line; installed copies are left alone
for n in ('scripts/PS4-SKINS-EN.txt', 'DOA5LR-Diagnostic/ps4skins-files.json'): del core[n]
assert not any('990015' in n or 'skin' in n.lower() for n in core)
INIS = [f'DOA5LR-{m}.ini' for m in ['Crimson-Audio', 'Crimson-VFX', 'DangerZone', 'DNZ-Complete', 'DNZ-SharedAudio', 'ExtraStages', 'RandomStages']]
for n in INIS: core[STAGES + n] = core.pop(n)   # the modules read scripts\DOA5LR-Stages\ first, then next to game.exe
# -O1 modules: their shipped build.cmd and the lobby-module hashes checked by DOA5LR-Diagnostic
for d, s in [('60fps-menus', '60fps'), ('Borderless', 'Borderless'), ('InviteFix', 'InviteFix'), ('JoinFix', 'JoinFix'), ('UpdateCheck', 'UpdateCheck'), ('WiFi-Wired-Detector', 'WiFi-Wired')]:
    k = f'scripts/{s}-Source/build.cmd'; assert k in core; core[k] = (repo / 'src' / d / 'build.cmd').read_bytes(); assert b' -O1 ' in core[k] and b'-O2 -s' not in core[k]
mrows = json.loads(core['DOA5LR-Diagnostic/salons-modules.json'])
for x in mrows:
    if x['path'] in core: x['sha256'] = sha(core[x['path']])
core['DOA5LR-Diagnostic/salons-modules.json'] = json.dumps(mrows, indent=2).encode()
(repo / 'src/Diagnostic/salons-modules.json').write_bytes(core['DOA5LR-Diagnostic/salons-modules.json'])

# 4. integrity list read by the installer (stage data = entries not in the core) and by DOA5LR-Diagnostic
rows = json.loads(core['DOA5LR-Diagnostic/maps-files.json'])
for x in rows:
    n = x['path'].replace('\\', '/')
    mm = re.fullmatch(r'scripts/(DOA5LR-[^/]+\.asi)', n)
    if mm and mm.group(1)[7:-4] in MAPS: n = STAGES + mm.group(1)
    if n in INIS: n = STAGES + n
    x['path'] = n
b_all = core | maps2
paths = [x['path'] for x in rows]
assert len(paths) == len(set(paths)) and all(p in b_all for p in paths), [p for p in paths if p not in b_all]
for x in rows: x['sha256'] = sha(b_all[x['path']]); x['size'] = len(b_all[x['path']])
assert {p for p in paths if p not in core} == set(maps2), 'stage data list != maps-data-2'
core['DOA5LR-Diagnostic/maps-files.json'] = json.dumps(rows, indent=2).encode()
for f in ('src/Diagnostic/maps-files.json', 'src/Maps/maps-files.json'): (repo / f).write_bytes(core['DOA5LR-Diagnostic/maps-files.json'])

full = core | maps2; full['SHA256SUMS.txt'] = sums(full); core['SHA256SUMS.txt'] = full['SHA256SUMS.txt']
assert core | maps2 == full
check_pack_guides(core, V)
names = {'full': f'DOA5LR-Salons-{V}.zip', 'core': f'DOA5LR-Salons-core-{V}.zip', 'maps': 'DOA5LR-Salons-maps-data-2.zip'}
for k, payload in [('full', full), ('core', core), ('maps', maps2)]: write_zip(out / names[k], payload)

# 5. manifest
url = f'https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v{V}/'
def info(n): p = out / n; return url + n + '|' + sha(p.read_bytes()) + '|' + str(p.stat().st_size)
updates = {'version': V, 'url': url + names['full'], 'sha256': sha((out / names['full']).read_bytes()), 'size': str((out / names['full']).stat().st_size),
           'core': info(names['core']), 'data': 'maps|' + info(names['maps']), 'installer': url + 'DOA5LR-Salons-Installer.exe', 'installer_version': '1.3.11', 'installer_sha256': sha(exe),
           'notes': '0.3.16 correct stage thumbnails, stage modules in their own folder, logs in DOA5LR-Logs'}
cs = (src / 'Installer.cs').read_text(encoding='utf-8')
mline = re.search(r'public static readonly Component Maps = new Component \{ Id = "maps", Label = "([^"]*)", Globs = new\[\] \{(.*?)\} \};', cs)
v7 = 'optional_v7=maps|' + mline.group(1) + '|' + ';'.join(re.findall(r'@"([^"]*)"', mline.group(2)))
assert v7.split('|')[2].startswith('scripts\\DOA5LR-Stages\\DOA5LR-Crimson.asi')
lines = []
for l in manifest.splitlines():
    key = l.split('=', 1)[0]
    if key in updates: l = key + '=' + updates[key]
    if key in ('skins_data', 'optional_v6') or (key == 'note' and any(w in l for w in ('PS4 skins', 'hairstyle', 'costume registration', 'DLC configuration'))): continue
    if key == 'optional_v5': lines.append(v7)   # first line with a given id wins; 1.3.5-1.3.10 ignore optional_v7
    lines.append(l)
moves = [f'move={n}|scripts\\DOA5LR-Stages\\{n}' for n in INIS]
at = max(i for i, l in enumerate(lines) if l.startswith('move=')) + 1; lines[at:at] = moves
dels = [f'delete=scripts\\DOA5LR-{m}.asi' for m in MAPS] + ['delete=DOA5LR-DNZ-Menu.log', 'delete=DOA5LR-DangerZone-crash.txt']
at = max(i for i, l in enumerate(lines) if l.startswith('delete=')) + 1; lines[at:at] = dels
lines[1:1] = ['note=0.3.16: some stage tiles showed the picture of another stage (Lorelei Halloween, and the lower levels of Scramble, Plant and Circus; the right stage still loaded): each tile has its own picture again, and The Crimson 1 now has its own PS4 picture.',
              'note=0.3.16: tidier game folder: the stage modules and their .ini files are in scripts\\DOA5LR-Stages\\, their logs in DOA5LR-Logs\\. Your settings are moved with them and kept; the update removes the old copies.',
              'note=0.3.16: the pack modules are now built with other compiler options (-O1, thanks WAZAAAAA) and signed: fewer antivirus false positives ("Wacatac" and similar). Same source code, same behaviour.',
              'note=0.3.16: the PS4 skins are no longer part of the pack. If you installed them, the update leaves them in place (it no longer installs, checks or removes them).',
              'note=0.3.16: accept Installer 1.3.11 when it is offered (it knows the new folder). Small update when your stage data is intact.']
text = '\n'.join(lines) + '\n'
assert 'skins_data=' not in text and 'optional_v6=' not in text and 'ps4skins' not in text and 'hairstyle' not in text
assert text.count('optional_v7=') == 1 and all(d in text for d in dels + moves)
(out / 'version.txt').write_text(text, encoding='utf-8'); (repo / 'version.txt').write_text(text, encoding='utf-8')
local = [l.replace(url, str(out) + '\\') for l in text.splitlines() if not l.startswith(('installer=', 'installer_version=', 'installer_sha256='))]
(out / 'version-TEST-LOCAL.txt').write_text('\n'.join(local) + '\n', encoding='utf-8')
report = {'version': V, 'changed_core_files': sorted(n for n, b in core.items() if old.get(n) != b), 'removed_core_files': sorted(n for n in old if n not in core),
          'assets': {p.name: {'sha256': sha(p.read_bytes()), 'size': p.stat().st_size} for p in sorted(out.iterdir()) if p.suffix in ('.exe', '.zip')}}
(out / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(out / 'SHA256SUMS.txt').write_text(''.join(v['sha256'] + ' *' + n + '\n' for n, v in report['assets'].items()), encoding='ascii')
print(json.dumps(report, indent=2))
