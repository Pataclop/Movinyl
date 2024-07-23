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
    """Creates a black image with white text and saves it.

    Arguments:
        text {string} -- Text to write in the image
        font {string} -- Font to use
        saveName {string} -- Name of the output image
        size {int} -- Size of the font
    """
    para = textwrap.wrap(text, width=50)

    MAX_W, MAX_H = 5000, 600
    im = Image.new('RGBA', (MAX_W, MAX_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(im)

    try:
        font = ImageFont.truetype(font, size)
    except IOError:
        print(f"Error: Font file '{font}' not found.")
        return

    current_h, pad = 50, 10
    for line in para:
        # Utiliser textbbox pour obtenir la taille du texte
        bbox = draw.textbbox((0, 0), line, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((MAX_W - w) / 2, current_h), line, font=font, fill="white")
        current_h += h + pad

    im.save(saveName)

def main():
    if len(sys.argv) < 2:
        print("Error: No input provided.")
        return

    raw = sys.argv[1]
    raw = raw.replace("_", " ").replace("\"", "")
    word_list = raw.split()
    if len(word_list) < 2:
        print("Error: Invalid input format.")
        return

    year = word_list[-1]
    length = len(raw)
    movie_name = raw[:length-4]

    real = " "
    duration = '0'
    search = tmdb.Search()
    response = search.movie(query=movie_name)
    
    if not search.results:
        print("Error: No results found for the given movie name.")
        return

    for s in search.results:
        if re.sub(r"[^\w]", " ", s['release_date']).split()[0] == year:
            id = s['id']
            m = tmdb.Movies(id)
            response = m.info()
            movie_name = m.original_title
            duration = str(m.runtime) + "'"
            response = m.credits()
            for credit in m.crew:
                if credit["job"] == "Director":
                    real = credit['name']
                    break
            break

    print(movie_name)
    cleanYear = "(" + year + ")"

    write_text_to_image(movie_name, 'futura medium bt.ttf', "titre.png", 200)
    write_text_to_image(cleanYear, 'futura light bt.ttf', "année.png", 200)
    write_text_to_image(real, 'futura medium bt.ttf', "réalisateur.png", 170)
    write_text_to_image(duration, 'futura light bt.ttf', "durée.png", 150)

    H = 8000
    W = 5000
    try:
        with open('colors.txt', 'r') as file1:
            lines = file1.readlines()
    except FileNotFoundError:
        print("Error: 'colors.txt' file not found.")
        return

    im = Image.new('RGB', (W, W//7), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    for i in range(14):
        if i % 2 == 0:
            draw.ellipse(((i*W//14)+W//28, 50, ((i+1)*W//14)+W//28, (W//14)+50), fill=(127, 127, 127))
            try:
                l = list(map(int, re.sub(r"[^\w]", " ", lines[(i+4)//2]).split()))
                t = (l[0], l[1], l[2])
                draw.ellipse(((i*W//14)+W//28+5, 55, ((i+1)*W//14)+W//28-5, (W//14)+45), fill=t)
            except (IndexError, ValueError):
                print(f"Error: Invalid color format in 'colors.txt' at line {(i+4)//2}.")
                return
    im.save('palette.png')
    print("DONE")

if __name__ == "__main__":
    main()
