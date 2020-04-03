from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import textwrap
import os
import subprocess


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










	#img = Image.new('RGB', (5000,1000), (255,255,255))
	#W,H=img.size
	#draw = ImageDraw.Draw(img)
	#w, h = draw.textsize("1234756789123456789123456789")
	#font = ImageFont.truetype("futura light bt.ttf", 10)
	#draw.text((((W-w)/2),(H-h)/2),"1234756789123456789123456789",(0,0,0),font=font)
	#img.save('pop.png')



def normalize(l):
	for a in l:
		print(a)
		#while a!='\n'
		#tmp=tmp+a

tmp = ""
f=open("infos.txt", "r")
cmp=0
real = ""
anneePropre = ""
anneeSale = ""
duree = ""

titrePropre = ""
titreSale = ""

if f.mode == 'r': 
	fl =f.readlines()
	for x in fl:
		if (cmp==0) :
			for y in x:
				if y!='\n' :
					if y==' ' :
						titreSale = titreSale + '\\'
					if y!=':':
						titreSale = titreSale + y
					titrePropre = titrePropre + y

		if (cmp==1) :
			for y in x:
				if y!='\n' :
					if y=='(' or y==')':
						anneeSale = anneeSale + '\\'
					anneeSale = anneeSale + y
					anneePropre = anneePropre + y
		if (cmp==2) :
			for y in x:
				if y!='\n' :
					real = real + y
		if (cmp==3) :
			for y in x:
				if y!='\n' :
					duree = duree + y

		cmp = cmp+1

		


duree = duree+'\''
ecris(titrePropre, 'futura medium bt.ttf', "titre.png",200)
ecris(anneePropre, 'futura light bt.ttf', "année.png",200)
ecris(real, 'futura medium bt.ttf', "réalisateur.png",170)
ecris(duree, 'futura light bt.ttf', "durée.png",150)


