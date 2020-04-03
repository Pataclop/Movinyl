# Movinyl

The goal of this project is to make a picture capturing the color spirit of a movie. 

![Result example](https://github.com/Pataclop/Movinyl/blob/master/example_img/3.jpg)


## The simple way 

- put all your movie files in **PROCESSING_ZONE**
- run ``` ./IMAGE_GENERATOR``` to extract the images
- then run  ```BATCH LAUNCH``` to create the disks

then if you want the page, refer to the **Making the page** section bellow.


## The complete process 

## Extracting the images

I use the ffmpeg library, since it accepts most movie formats. 
To extract the images, just run 
```
ffmpeg -i Film.mp4 -qscale:v 2 -r 1 images/%d.jpg
```

qscale:v is the picture quality of the jpg output files. As I understand it, the value is between 2 and 31, 2 being the best quality. There is no point in using png at this step, since it is much slower, files are way biger, and there is no visible difference.

-r is the sampling rate. The following number is the number of frames per second of video that you want to save. 1 will save one frame for each second of the film. to take one picture each 10 seconds, the value is 0.1. I find that using 0.4 produces enough images. For long movies (>3h) you may want to choose 0.3, and for short films (<80min) 0.6. My goal is to have more than 2000 images. The sampled images go to the images/ directory.

## Making the disk

As of right now, the program is not multythreaded, witch is a shame. It takes a long time to process a movie. But you can process multiple movies at once if you run the program multiple times (in separated directories...)

To run the program, you have to know how many images there are in the images/ foler.

```
./test number_of_images
```

After (looong) processing, this will return a square image of size 2x number_of_images, with a disk containing the colors of the movie (of each frame of the movie). The first image is at the exterior of the disk, the last is at the center. The center is often black because of the ending credits. You can get rid of it by entering the number of frame without the credits when launching the program. 

## Making the page
Go to the INFO folder.
For each movie, you will have to create a file named 
```
MOVIE_NAME_YEAR.txt
```
It must have exactly the same name as the square disc image. 

You have to fill these informations in the file : 

```
Name of the movie
(date of release) 
Realisator
Duration in minutes
```

Then go to SCRIPTS, and run 
```
./GENERATE MOVIE_NAME_YEAR r g b r g b r g b r g b r g b
```
r g b are the 5 main colors of the movie. You have to chose them yourself, because I have failed extracting them from the pictures/disc. 

Finaly, staying in SCRIPTS, you may launch 
```
./GENERATE MOVIE_NAME_YEAR
```
