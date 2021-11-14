#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
#include <omp.h>
#include <iostream>
#include "progressbar.hpp"

using namespace cv;

//some movies have a black border of a few pixels.
//To avoid it screwing the disk image, the croped circle will be in a center square of size Height-2*SAFE_DIST
//try to keep it over 15.
#define SAFE_DIST 15
#define WIDTH 1.001 //this is the thickness of the circles.

int THREAD_COUNT = omp_get_max_threads();

cv::Mat ExtractCircle ();

cv::Mat ExtractCircle (Mat ims){
	int rows = ims.rows;
	int cols = ims.cols;

	float out_ring = rows/2-SAFE_DIST ;
	float in_ring =  (rows/2)-(SAFE_DIST+WIDTH);
	int diff = (cols-rows)/2;
	Mat imd = Mat(rows, rows, CV_8UC4, Scalar(0,0,0,0));//temporary image, containing only a circle, the rest is tranparent.
	for (int x = 0; x<cols; x++){
		for (int y = 0; y<rows; y++){
			//here we crop a circle, 2 pixels thick, centered in the image.
			//2 pixels intead of 1 to avoid aliassing issues.
			float dist = sqrt(pow((cols/2)-x,2)+pow((rows/2)-y,2));
			if (dist < out_ring && dist > in_ring){
				Vec3b colorS = ims.at<Vec3b>(y, x);
				Vec4b colorD;
				colorD.val[0] = colorS.val[0];//blue
				colorD.val[1] = colorS.val[1];//green
				colorD.val[2] = colorS.val[2];//red
				colorD.val[3] = 255;//alpha

				imd.at<Vec4b>(y,x-diff) = colorD;
			}
		}
	}
	return imd;
}

//This one pastes the circle in the final image, slowly creating a disk with all the circles.
cv::Mat Insert(Mat ims1, Mat ims2, int margin){
	int rows = ims1.rows;
	for(int x=0; x<rows; x++){
		for(int y=0; y<rows; y++){
			Vec4b colorS = ims1.at<Vec4b>(y, x);
			Vec4b colorD;
			if(colorS.val[3]>100){
				colorD.val[0] = colorS.val[0];//blue
				colorD.val[1] = colorS.val[1];//green
				colorD.val[2] = colorS.val[2];//red
				colorD.val[3] = 255;//alpha
				ims2.at<Vec4b>(y+margin,x+margin) = colorD;
			}
		}
	}
	return ims2;
}

// Read all frames, extract circles, and merge them into single disk
void GenerateDisk(int FrameNumber) {
	progressbar bar(2000);
    bar.set_todo_char(" ");
    bar.set_done_char("█");
    bar.set_opening_bracket_char("{");
    bar.set_closing_bracket_char("}");
	// Increase stack size per thread, overwrite existing env variable
	setenv("OMP_STACKSIZE","10M",1);
	printf("START\n");
	std::vector<Mat> vectorOfMatrices;
	Mat final = Mat(FrameNumber*2, FrameNumber*2, CV_8UC4, Scalar(0,0,0,255));
	// Fill vectorOfMatrices with known sizes of Matrices
	for (int i=0; i<THREAD_COUNT; i++) {
		vectorOfMatrices.push_back(Mat(FrameNumber*2, FrameNumber*2, CV_8UC4, Scalar(0,0,0,255)));
	}
	// Generate THREAD_COUNT of threads to extract circles in parallel
	#pragma omp parallel num_threads(THREAD_COUNT) shared(vectorOfMatrices)
	{	
		Mat extracted;
		// Each thread will have a disk, made of FrameNumber circles, each 1 pixel wide
		// Use static scheduling of 1 to distribute work load equally since task gets easier each loop
		#pragma omp for schedule(static, 1)
		for (int i=0; i<FrameNumber; i++) {
			std::string name = "images/";
			name += std::to_string(i+1);
			name += ".jpg";
			Mat img = imread(name);
			// First, resize the picture to the wanted size.
			// This size is dependent on the frame position in the disk.
			// The later the image is in the movie file, the smaller it will be.
			resize(img, extracted, Size((2*FrameNumber)-2*i, (2*FrameNumber)-2*i),INTER_NEAREST);
			// Extract circle from image
			extracted=ExtractCircle(extracted);
			// Print values for progress bar
			#pragma omp critical
				bar.update();
			

			// Store single disk back into the Matrix for each thread
			vectorOfMatrices[omp_get_thread_num()] = Insert(extracted, vectorOfMatrices[omp_get_thread_num()], i);
		}
	}
	// Merge all disks into 
	for (int i=0; i<THREAD_COUNT; i++) {
		max(final, vectorOfMatrices[i], final);
	}
	imwrite("save.png", final);
}

int main(int argc, char const *argv[])
{
    setbuf(stdout, NULL);
	GenerateDisk(atoi(argv[1]));
	return 0;
}
