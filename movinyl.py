#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from os.path import splitext, basename, dirname

import click
import ffpb
import magic
import tqdm
from PIL import Image

from color_picker import get_points, kmeans


@click.group()
def main():
    pass


@main.command()
@click.argument('dir', default="PROCESSING_ZONE")
@click.option('--n', default=2000)
def disk(dir, n):
    files = os.listdir(dir)
    print(sys.argv)
    for file in files:
        file_path = os.path.join(dir, file)

        print(file_path)
        if os.path.isdir(file_path):
            continue

        mime = magic.Magic(mime=True)
        filename = mime.from_file(file_path)
        if not filename.startswith('video/'):
            continue

        video_length = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                                'default=noprint_wrappers=1:nokey=1', file_path])
        video_length = float(video_length)
        r = 2005 / video_length
        file_without_ext, _ = splitext(file_path)

        output2 = os.path.join(file_without_ext, 'images', '%d.jpg')

        ffmpeg_needed = False
        for i in range(1, n + 1):
            if not os.path.exists(output2 % i):
                ffmpeg_needed = True

        if ffmpeg_needed:
            os.makedirs(os.path.join(file_without_ext, 'images'), exist_ok=True)
            argv = [
                '-y', '-i', file_path, '-r', str(r), '-qscale:v', '1',
                '-f', 'image2', output2
            ]

            class ProgressBar(tqdm.tqdm):
                def __init__(self, **kwargs):
                    kwargs['desc'] = "Generating the snapshots..."
                    super().__init__(**kwargs)

            ffpb.main(argv, stream=sys.stdout, tqdm=ProgressBar)

        images_folder = os.path.join(file_without_ext, 'images')
        if not os.path.exists(images_folder):
            print(f'no "images" folder ({images_folder}), re-run.')
            return

        name = basename(file_without_ext)
        name = name.replace(' ', '_')
        name = name.replace('-', '_')

        file_underscores = os.path.join(dirname(file_path), f"{name}.png")

        if os.path.exists(file_underscores):
            print(f'OK {file_underscores}')
            return

        save_png = os.path.join(file_without_ext, 'save.png')
        process = subprocess.Popen([os.path.join(os.getcwd(), 'src', 'disk', 'disk'), str(n)],
                                   cwd=os.path.join(file_without_ext), stdout=subprocess.PIPE)

        previous = 0
        with tqdm.tqdm(total=n, desc="generating & merging disk images...") as pbar:
            while process.poll() is None:
                line = process.stdout.readline()
                try:
                    p = int(line)
                    pbar.update(p - previous)
                    previous = p
                except ValueError:
                    pass

        shutil.move(save_png, file_underscores)


@main.command()
@click.argument('dir', default="PROCESSING_ZONE")
def page(dir):
    files = os.listdir(dir)
    for file in files:
        file_path = os.path.join(dir, file)

        if os.path.isdir(file_path):
            continue

        mime = magic.Magic(mime=True)
        filename = mime.from_file(file_path)
        if not filename.startswith('video/'):
            continue

        file_without_ext, _ = os.path.splitext(file_path)
        name = basename(file_without_ext)
        name = name.replace(' ', '_')
        name = name.replace('-', '_')
        file_png = os.path.join(dirname(file_without_ext), f'{name}.png')

        def colorz(filename, n=3):
            img = Image.open(filename)
            img.thumbnail((200, 200))
            w, h = img.size

            points = get_points(img)
            clusters = kmeans(points, n, 1)
            return [str(int(x)) for c in clusters for x in c.center.coords]

        colors = colorz(file_png, 5)
        popen = [os.path.join(os.getcwd(), 'src', 'page', 'page'), name] + colors
        print(" ".join(popen))
        subprocess.check_output([sys.executable, 'generate_infos.py', name])
        shutil.move('titre.png', os.path.join(dir, 'titre.png'))
        shutil.move('année.png', os.path.join(dir, 'année.png'))
        shutil.move('réalisateur.png', os.path.join(dir, 'réalisateur.png'))
        shutil.move('durée.png', os.path.join(dir, 'durée.png'))
        subprocess.check_output(popen, cwd=dir)
        os.remove(os.path.join(dir, 'titre.png'))
        os.remove(os.path.join(dir, 'année.png'))
        os.remove(os.path.join(dir, 'réalisateur.png'))
        os.remove(os.path.join(dir, 'durée.png'))


if __name__ == '__main__':
    main()
