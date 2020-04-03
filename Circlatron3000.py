from PIL.Image import *
from math import sqrt
import os
cmd= 'ffmpeg -i FILM.mkv -qscale:v 2 -r 1 images/%d.jpg'
#os.system(cmd)


def extract_circle (im):
    (l,h)=im.size
    out= new('RGBA', (l,h), (0,0,0,0))

    X=l//2
    Y=h//2
    
    for x in range (l) :
        for y in range (h) :
            distance = sqrt(pow(X-x,2)+pow(Y-y,2))
            if distance<((h-2)/2) and distance>(h/2)-3 :
                r,g,b=Image.getpixel(im,(x,y))
                Image.putpixel(out, (x,y), (r,g,b))
    return (out)

def generate_disk() :
    im=open("1.png")
    (L,H)=im.size
    out= new('RGBA', (2*L,2*H), (0,0,0,255))

    for i in range (60):
        name=str(i+48)+".png"
        im=open(name)
        (l,h)=im.size
        size=2*H-(i*2)
        normalize = im.resize((int(size*l/h), size))
        circle=extract_circle(normalize)
        out.paste(circle, (int(i*l/h),i), circle)
        print(i)
    out.save("fini.png")
generate_disk()
