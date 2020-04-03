from PIL.Image import *
from math import *
from random import randint
from PIL import ImageFont
from PIL import ImageDraw 
import textwrap
import os
import subprocess


def ecris (nom, police, taille):

	para = textwrap.wrap(nom, width=50)

	MAX_W, MAX_H = 220, 120
	im = new('RGBA', (MAX_W, MAX_H), (0, 50, 0, 0))
	draw = ImageDraw.Draw(im)
	font = ImageFont.truetype(police, taille)

	current_h, pad = 50, 10
	for line in para:
	    w, h = draw.textsize(line, font=font)
	    draw.text(((MAX_W - w) / 2, current_h), line, font=font)
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
	count=0
	l=5
	h=8
	for planche in range (im_number//(l*h)+1):
		planche_name = "planche" + str(planche) + ".png"
		L=5000
		H=8000
		out= new('RGBA', (L,H), (0,0,0,255)) 
		positions=[0]*(2*l*h)
		cmp = 0
		for y in range (h) :
			for x in range (l):
				positions[cmp]=int(x*L/l)+50
				positions[cmp+1]=int(y*H/h)+50
				cmp=cmp+2
		for x in range (l*h) :
			if count<im_number:
				angle = 0
				name = str((x+1+(planche*l*h))) + ".png"
				raw = open(name)
				im = raw.convert("RGBA")          
				im_resize=im.resize((int((9*L)/(l*10)),int((9*L)/(l*10))), LANCZOS)
				out.paste(im_resize, (positions[2*x],positions[2*x+1]), im_resize)
				page_num=ecris(str(count+(im_number//(l*h)+1)), 'futura medium bt.ttf', 50)
				out.paste(page_num, (positions[2*x]-50,positions[2*x+1]-50), page_num)
				print (x)
				count=count+1
		out.save(planche_name)

faitou (118)


