from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import textwrap
import os
import subprocess
import pymdb
import sys


def ecris (nom, police, saveName, taille):

	astr = '''Jurass'''
	para = textwrap.wrap(nom, width=50)

	MAX_W, MAX_H = 5000, 600
	im = Image.new('RGBA', (MAX_W, MAX_H), (0, 0, 0, 255))
	draw = ImageDraw.Draw(im)
	font = ImageFont.truetype(police, taille)

	current_h, pad = 50, 10
	for line in para:
	    w, h = draw.textsize(line, font=font)
	    draw.text(((MAX_W - w) / 2, current_h), line, font=font)
	    current_h += h + pad

	im.save(saveName)






raw=sys.argv[1]
raw=raw.replace("_", " ") 
raw=raw.replace("\"", "") 
word_list = raw.split()
year=word_list[-1]
length=len(raw)
film=raw[:length-4]

#film="A Bug's Life"
#year=str(1998)
print(film)
m = pymdb.Movie(film,year)
#print(m.info())
anneePropre="("+year+")"
duree = str(m.runtime()[0])
real = m.director()[0]

ecris(film, 'futura medium bt.ttf', "titre.png",200)
ecris(anneePropre, 'futura light bt.ttf', "année.png",200)
ecris(real, 'futura medium bt.ttf', "réalisateur.png",170)
ecris(duree, 'futura light bt.ttf', "durée.png",150)


print ("DONE")