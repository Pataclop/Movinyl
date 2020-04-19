#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
#include <omp.h>
#define NTHREADS 4
using namespace cv;

//some movies have a black borderof a few pixels.
//To avoid it screwing the disk image, the croped circle will be in a center square of size Height-2*SAFE_DIST
//try to keep it over 15.
#define SAFE_DIST 40
#define WIDTH 2

cv::Mat ExtractCircle ();

cv::Mat ExtractCircle (Mat ims){
	int rows = ims.rows;
	int cols = ims.cols;

	float out_ring = rows/2-SAFE_DIST ;
	float in_ring =  (rows/2)-(SAFE_DIST+WIDTH);
	int diff = (cols-rows)/2;
	Mat imd = Mat(rows, rows, CV_8UC4, Scalar(0,0,0,0));//temporary image, containing only a circle, the rest is tranparent.
	double t_start = 0.0, t_taken;
	t_start = omp_get_wtime();
	#pragma omp parallel for num_threads(NTHREADS)
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
	t_taken = omp_get_wtime() - t_start;
	printf("Time taken for the main program: %f\n", t_taken);
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

//Here, we process all the images and save the disk image result.
void GenerateDisk(int FrameNumber){
	Mat tmp;
	//the output image will have a disk, made of FrameNumber circles, each 1 pixel wide.
	Mat out = Mat(FrameNumber*2, FrameNumber*2, CV_8UC4, Scalar(0,0,0,255));
	printf("START\n");
	for (int i=0; i<FrameNumber; i++){
		std::string name = "images/";
		name += std::to_string(i+1);
		name += ".jpg";
		Mat img = imread(name);
		//First we resize the picture to the wanted size.
		//This size is dependant of the frame position in the disk.
		//The more the image is late in the film, the smaller it will be.
		resize(img, tmp, Size((2*FrameNumber)-2*i, (2*FrameNumber)-2*i),INTER_NEAREST);
		//Then a circle is extracted from the image
		tmp=ExtractCircle(tmp);
		if(i%10==0)
			printf("%d\n",i);
		// And finaly the circle is inserted in the disk.
		out = Insert(tmp, out, i);
	}
	imwrite("save.png", out);

}

int main(int argc, char const *argv[])
{
	GenerateDisk(atoi(argv[1]));
	return 0;
}
