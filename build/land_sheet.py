import sys
from PIL import Image, ImageDraw
def sky(w,h):
    im=Image.new('RGB',(w,h)); d=ImageDraw.Draw(im)
    for y in range(h):
        t=y/h
        if t<0.55: c=tuple(int(a+(b-a)*(t/0.55)) for a,b in zip((217,235,255),(237,245,255)))
        else: c=tuple(int(a+(b-a)*((t-0.55)/0.45)) for a,b in zip((237,245,255),(255,255,255)))
        d.line([(0,y),(w,y)],fill=c)
    return im
ims=[]
for n in 'abcd':
    im=Image.open(f'site/img/3d/_land_{n}.png').convert('RGBA'); bg=sky(*im.size); bg.paste(im,(0,0),im); ims.append(bg.resize((700,380)))
S=Image.new('RGB',(1400,760)); [S.paste(im,((i%2)*700,(i//2)*380)) for i,im in enumerate(ims)]; S.save(sys.argv[1],quality=85)
