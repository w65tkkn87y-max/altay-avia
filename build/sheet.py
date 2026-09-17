import sys
from PIL import Image
m=sys.argv[1]; out=sys.argv[2]
names=['side','front34','front','rear34','top','left']
ims=[Image.open(f'site/img/3d/_{m}-{n}.png').convert('RGB') for n in names]
w=700; h=400
S=Image.new('RGB',(w*2,h*3),(255,255,255))
for i,im in enumerate(ims):
    im=im.resize((w,h)); S.paste(im,((i%2)*w,(i//2)*h))
S.save(out,quality=85)
