#!/usr/bin/env python3
import os
import shlex
import shutil
import subprocess
import sys
from os.path import splitext, basename, dirname

import click
import ffpb
import magic
import tqdm
from PIL import Image


@click.group()
def main():
    pass


def list_all_video_files(directory):
    files = os.listdir(directory)
    print(sys.argv)
    for file in files:
        file_path = os.path.join(directory, file)

        print(file_path)
        if os.path.isdir(file_path):
            continue

        mime = magic.Magic(mime=True)
        real_file = os.readlink(file_path) if os.path.islink(file_path) else file_path

        try:
            filename = mime.from_file(real_file)
        except FileNotFoundError:
            continue
        if not filename.startswith('video/'):
            continue

        yield file_path


@main.command()
@click.argument('directory', default="PROCESSING_ZONE")
@click.option('-n', default=2000)
def disk(directory, n):
    for file_path in list_all_video_files(directory):
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
                                   cwd=os.path.join(file_without_ext), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        with tqdm.tqdm(total=n, desc="Generating and merging disk images...") as pbar:
            while process.poll() is None:
                line = process.stdout.readline()
                try:
                    p = int(line)
                    pbar.update(10)
                except ValueError:
                    pass

        shutil.move(save_png, file_underscores)


@main.command()
@click.argument('directory', default="PROCESSING_ZONE")
def page(directory):
    for file_path in list_all_video_files(directory):
        file_without_ext, _ = os.path.splitext(file_path)
        name = basename(file_without_ext)
        name = name.replace(' ', '_')
        name = name.replace('-', '_')
        file_png = os.path.join(dirname(file_without_ext), f'{name}.png')

        extcolors = ["extcolors", file_png, "-t", "12", "-l", "8"]
        print(shlex.join(extcolors))
        colors_txt = subprocess.check_output(extcolors)
        open(os.path.join(directory, "colors.txt"), 'wb').write(colors_txt)

        generate_infos = [sys.executable, os.path.join(os.getcwd(), 'generate_infos.py'), name]
        print(shlex.join(generate_infos))
        subprocess.check_output(generate_infos)
        shutil.move('titre.png', os.path.join(directory, 'titre.png'))
        shutil.move('année.png', os.path.join(directory, 'année.png'))
        shutil.move('réalisateur.png', os.path.join(directory, 'réalisateur.png'))
        shutil.move('durée.png', os.path.join(directory, 'durée.png'))

        run_page = [os.path.join(os.getcwd(), 'src', 'page', 'page'), name]
        print(shlex.join(run_page))
        subprocess.check_output(run_page, cwd=directory)
        os.remove(os.path.join(directory, 'titre.png'))
        os.remove(os.path.join(directory, 'année.png'))
        os.remove(os.path.join(directory, 'réalisateur.png'))
        os.remove(os.path.join(directory, 'durée.png'))
        os.remove(os.path.join(directory, 'colors.txt'))


if __name__ == '__main__':
    main()
