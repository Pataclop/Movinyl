from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import textwrap
import os
import subprocess
import pymdb
import sys


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
movie = raw[:length-4]


print(movie)
m = pymdb.Movie(movie, year)
cleanYear = "("+year+")"
duration = str(m.runtime()[0])+"'"
real = m.director()[0]

write_text_to_image(movie, 'futura medium bt.ttf', "titre.png", 200)
write_text_to_image(cleanYear, 'futura light bt.ttf', "année.png", 200)
write_text_to_image(real, 'futura medium bt.ttf', "réalisateur.png", 170)
write_text_to_image(duration, 'futura light bt.ttf', "durée.png", 150)


print("DONE")
