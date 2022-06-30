from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import PIL
import textwrap
import extcolors
import os
import subprocess
import sys
import tmdbsimple as tmdb
import re
tmdb.API_KEY = '38b045cf5307eaa109b937ba5047d015'
tmdb.REQUESTS_TIMEOUT = 5  # seconds, for both connect and read

def write_text_to_image(text, font, saveName, size):
    """[creates a black image with white text and writes it in the main folder]

    Arguments:
            text {[string]} -- [text to write in the image]
            font {[string]} -- [font to use]
            saveName {[string]} -- [name of the outut image]
            size {[int]} -- [size of the font]
    """

    astr = '''Jurass'''
    para = textwrap.wrap(text, width=50)

    MAX_W, MAX_H = 5000, 600
    im = Image.new('RGBA', (MAX_W, MAX_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(font, size)

    current_h, pad = 50, 10
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, current_h), line, font=font)
        current_h += h + pad

    im.save(saveName)

raw = sys.argv[1]
raw = raw.replace("_", " ")
raw = raw.replace("\"", "")
word_list = raw.split()
year = word_list[-1]
length = len(raw)
movie_name = raw[:length-4]

real = " "
duration = '0'
search = tmdb.Search()
response = search.movie(query=movie_name)
for s in search.results:
    if (re.sub("[^\w]", " ",  s['release_date']).split()[0] == year) :
        id = s['id']
        m = tmdb.Movies(id)
        response = m.info()
        movie_name = m.original_title
        duration = str(m.runtime) +"'"
        response = m.credits()
        for credit in m.crew :
            if credit["job"] == "Director" :
                real = credit['name']
                break
        break




print(movie_name)
cleanYear = "("+year+")"

write_text_to_image(movie_name, 'futura medium bt.ttf', "titre.png", 200)
write_text_to_image(cleanYear, 'futura light bt.ttf', "année.png", 200)
write_text_to_image(real, 'futura medium bt.ttf', "réalisateur.png", 170)
write_text_to_image(duration, 'futura light bt.ttf', "durée.png", 150)
H = 8000
W = 5000
file1 = open('colors.txt', 'r')
Lines = file1.readlines()

im = Image.new('RGB', (W, W//7), (0, 0, 0))
draw = ImageDraw.Draw(im)
for i in range (14) :
    if (i%2==0) :
        draw.ellipse(((i*W//14)+W//28, 50, ((i+1)*W//14)+W//28, (W//14)+50), fill=(127, 127, 127))
        l = ((re.sub("[^\w]", " ",  Lines[(i+4)//2]).split()))
        t=(int(l[0]), int(l[1]), int(l[2]))
        draw.ellipse(((i*W//14)+W//28+5, 55, ((i+1)*W//14)+W//28-5, (W//14)+45), fill=t)
im.save('palette.png')
print("DONE")
