# Movinyl

The goal of this project is to make a picture capturing the color spirit of a movie. 

![Result example](https://github.com/Pataclop/Movinyl/blob/master/example_img/3.jpg)


## How to create Disks and Pages

- Run setup : ```./0_Setup``` to build & install some of the required libraries
- Place your video files in PROCESSING_ZONE
- Run ```./1_IMAGE_GENERATOR``` and wait for the process to end. The more core, the better
- Run ```./2_VIDEO_REMOVER``` to delete all the video files (check they are deleted)
- Run ```./3_BATCH_LAUNCH``` and wait for the process to end. Not multithreaded yet, but one core per video file
- Run ```./4_RENAME_SAVE``` and you have all the disks.
- Remove the directories in ProcessingZone, leave only the disk images, and resize these images to 4000x4000, .png files.
- Consider adding them to the public [google photo album](https://photos.app.goo.gl/TtnD8yMPEKirk46R6)
- Replace the spaces and the parentheses in the names by underscores : ```./The Beach (2000)``` -> ```./The_Beach_2000```
- Update the file 5_MAKE_PAGE with the 5 main colors of your disk, with this format : 
```python3 generate_infos.py "IMDB_MovieName_Year"; ./page "YourDiskImageName" r g b r g b r g b r g b r g b``` You can use the provided GUI to find colors. Just run ```python3 run_interface.py```
- Move the disk images at the root of the project
- Run ```./5_MAKE_PAGE``` and it will create all the pages

## How to contribute

- If you know how to code, you're welcome to participate
- If you process movies, it would be amazing if you could add the disks to this [google photo album](https://photos.app.goo.gl/TtnD8yMPEKirk46R6) (please resize them to 4000x4000 in PNG so google doesn't compress them). 

Contact : project.movinyl@gmail.com

## TODO 
- Multithreading for disks
- Multithreading for pages
