import PIL.Image
from random import randint
from PIL import ImageFont
from PIL import ImageDraw 
import textwrap
import os
import subprocess
import sys


def ecris (nom, police, taille, largeur):

	para = textwrap.wrap(nom, width=largeur)

	MAX_W, MAX_H = largeur, largeur//10
	im = PIL.Image.new('RGBA', (MAX_W, MAX_H), (0, 0, 0, 0))
	draw = ImageDraw.Draw(im)

	font = ImageFont.truetype(police, taille)

	current_h, pad = 50, 10
	for line in para:
	    w, h = draw.textsize(line, font=font)
	    draw.text(((MAX_W - w) / 2, current_h), line, fill=(255,255,255,255), font=font)
	    current_h += h + pad

	return im

def partition(arr,low,high): 
	i = ( low-1 )
	pivot = arr[high]      

	for j in range(low , high): 

		if   arr[j] <= pivot: 

			i = i+1 
			arr[i],arr[j] = arr[j],arr[i] 

			arr[i+1],arr[high] = arr[high],arr[i+1] 
			return ( i+1 ) 

def quickSort(arr,low,high): 
	if low < high: 
		pi = partition(arr,low,high) 
		quickSort(arr, low, pi-1) 
		quickSort(arr, pi+1, high) 



def border(im, border_size):
	border_size=border_size+1
	(l,h)=im.size
	big= new('RGBA', (l+(2*border_size), (h+(2*border_size))), (0,0,0,255))
	big.paste(im, (border_size, border_size))
	return big

def rotate (im, angle):
	return  im.rotate(angle, expand=True)

def faitou (im_number):
	f = open(sys.argv[2], "r")
	lines = f.readlines()
	f.close()
	count=0
	l=5
	h=2
	for planche in range (im_number//(l*h)+1):
		planche_name = "planche" + str(planche) + ".png"
		L=10000
		H=4000
		out= PIL.Image.new('RGBA', (L,H), (0,0,0,255)) 
		positions=[0]*(2*l*h)
		cmp = 0
		resized_disk_size=int((8.5*L)/(l*10))
		for y in range (h) :
			for x in range (l):
				positions[cmp]=int(x*L/l) + int((1.5*L)/(l*10))//2
				positions[cmp+1]=int(y*H/h) + int((1.5*L)/(l*10))//2
				cmp=cmp+2
		for x in range (l*h) :
			if count<im_number:
				name = str((x+1+(planche*l*h))) + ".png"		#name of the current disk being processed
				raw = PIL.Image.open(name)
				im = raw.convert("RGBA")          
				im_resize=im.resize((resized_disk_size,resized_disk_size), PIL.Image.LANCZOS) #we have l*h slots, we want the disk to be 90% of the size of the slot.
				out.paste(im_resize, (positions[2*x],positions[2*x+1]), im_resize) #paste the disc at the right place
				page_num=ecris(lines[count], 'futura medium bt.ttf', 50, int(L/l)) 

				out.paste(page_num, (positions[2*x]-int((1.5*L)/(l*10))//2,positions[2*x+1]+int((8.4*L)/(l*10))), page_num)
				print (x)
				count=count+1
		out.save(planche_name)

faitou (sys.argv[1])


