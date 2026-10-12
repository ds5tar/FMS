# render_check.js 가 받아 적은 것을 그림으로 굽는다
import json, sys, re
from PIL import Image, ImageDraw
d = json.load(open(sys.argv[1]))
im = Image.new("RGB", (d["w"], d["h"]), "#ffffff")
g = ImageDraw.Draw(im, "RGBA")

def 색(v, 기본=(0,0,0,255)):
    if not v: return 기본
    m = re.match(r"rgba?\(([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)(?:,\s*([-\d.]+))?\)", v)
    if m:
        r,gg,b = (int(float(m.group(i))) for i in (1,2,3))
        a = int(float(m.group(4))*255) if m.group(4) else 255
        return (r,gg,b,a)
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3: h = "".join(c*2 for c in h)
        return tuple(int(h[i:i+2],16) for i in (0,2,4)) + (255,)
    return 기본

for f in d["poly"]:
    pts = [tuple(p) for p in f["p"]]
    if f.get("채움만"):
        g.polygon(pts, fill=색(f.get("c")))
    else:
        c = 색(f.get("s"))
        g.line(pts, fill=c, width=max(1, int(round(f.get("lw", 1)))))
im.save(sys.argv[2])
print("저장", sys.argv[2], im.size)
