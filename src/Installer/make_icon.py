# Genere installer.ico (carre rouge arrondi + "S" blanc, fleche de mise a jour) sans dependance : PNG dessine par
# System.Drawing via PowerShell, puis emballe en .ico (entrees PNG, valides depuis Vista).
import subprocess, struct, os, io
here = os.path.dirname(os.path.abspath(__file__))
sizes = [256, 64, 48, 32, 16]
ps = r'''
Add-Type -AssemblyName System.Drawing
foreach ($s in @(SIZES)) {
  $b = New-Object System.Drawing.Bitmap($s, $s)
  $g = [System.Drawing.Graphics]::FromImage($b)
  $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAliasGridFit'; $g.Clear([System.Drawing.Color]::Transparent)
  $r = [int]($s * 0.22); $p = New-Object System.Drawing.Drawing2D.GraphicsPath
  $p.AddArc(0, 0, $r, $r, 180, 90); $p.AddArc($s - $r - 1, 0, $r, $r, 270, 90); $p.AddArc($s - $r - 1, $s - $r - 1, $r, $r, 0, 90); $p.AddArc(0, $s - $r - 1, $r, $r, 90, 90); $p.CloseFigure()
  $g.FillPath((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(0xE2, 0x37, 0x44))), $p)
  $f = New-Object System.Drawing.Font('Segoe UI', [float]($s * 0.60), [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
  $sf = New-Object System.Drawing.StringFormat; $sf.Alignment = 'Center'; $sf.LineAlignment = 'Center'
  $g.DrawString('S', $f, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF(0, [float]($s * -0.02), $s, $s)), $sf)
  if ($s -ge 32) {  # petite fleche "update" en bas a droite
    $a = [int]($s * 0.30); $x0 = $s - $a - [int]($s * 0.06); $y0 = $s - $a - [int]($s * 0.06)
    $g.FillEllipse([System.Drawing.Brushes]::White, $x0, $y0, $a, $a)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(0xE2, 0x37, 0x44), [float]($a * 0.16)); $pen.StartCap = 'Round'; $pen.EndCap = 'Round'
    $cx = $x0 + $a / 2; $cy = $y0 + $a / 2; $h = $a * 0.26
    $g.DrawLine($pen, [float]$cx, [float]($cy - $h), [float]$cx, [float]($cy + $h))
    $g.DrawLine($pen, [float]($cx - $h * 0.8), [float]($cy - $h * 0.15), [float]$cx, [float]($cy - $h))
    $g.DrawLine($pen, [float]($cx + $h * 0.8), [float]($cy - $h * 0.15), [float]$cx, [float]($cy - $h))
  }
  $b.Save("OUT\icon-$s.png", [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $b.Dispose()
}
'''.replace("SIZES", ",".join(map(str, sizes))).replace("OUT", here)
subprocess.run(["pwsh", "-NoProfile", "-Command", ps], check=True)
pngs = [open(os.path.join(here, "icon-%d.png" % s), "rb").read() for s in sizes]
out = io.BytesIO(); out.write(struct.pack("<HHH", 0, 1, len(sizes)))
off = 6 + 16 * len(sizes)
for s, d in zip(sizes, pngs):
    out.write(struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(d), off)); off += len(d)
for d in pngs: out.write(d)
open(os.path.join(here, "installer.ico"), "wb").write(out.getvalue())
for s in sizes: os.remove(os.path.join(here, "icon-%d.png" % s))
print("installer.ico", len(out.getvalue()), "octets")
