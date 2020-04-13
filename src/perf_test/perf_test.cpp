#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
using namespace cv;
#include <chrono> 
using namespace std::chrono; 


#define SAFE_DIST 40



void openImage(int iter){
	for (int i=0; i<iter; i++){
		Mat img = imread("test.jpg");
	}
}

void circle(int iter, float width){
	Mat ims = imread("test.jpg");
	for (int i=0; i<iter; i++){
		int rows = ims.rows;
		int cols = ims.cols;
		float out_ring = rows/2-SAFE_DIST ;
		float in_ring =  (rows/2)-(SAFE_DIST+width);
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
	}
}
void resize(Mat ims, int iter, float factor){
	for(int i=0; i<iter; i++){
		Mat tmp;
		int rows = ims.rows;
		resize(ims, tmp, Size((int)(rows*factor), (int)(rows*factor)),INTER_NEAREST);
	}
}

void blend(Mat ims1, Mat ims2, int iter){
	int margin=100;
	for(int i=0; i<iter; i++){
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
	}
}


int main(int argc, char const *argv[])
{

	int numberIter = 100;

	Mat ims2 = Mat(2000, 2000, CV_8UC4, Scalar(0,0,0,0));
	Mat ims1 = imread("testCircle.png");

	printf("open = ");
	auto start = high_resolution_clock::now(); 
	openImage(numberIter);
	auto stop = high_resolution_clock::now(); 
	auto duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());




	printf("circle 1 = ");
	 start = high_resolution_clock::now(); 
	circle(numberIter, 1);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

	printf("circle 2 = ");
	 start = high_resolution_clock::now(); 
	circle(numberIter, 2);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());



	printf("resize 4 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 4);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

printf("resize 3 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 3);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());



	printf("resize 2.5 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 2.5);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

	printf("resize 2 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 2);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());


	printf("resize 1.5 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 1.5);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

	printf("resize 0.75 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 0.75);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

	printf("resize 0.5 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 0.5);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

		printf("resize 0.25 = ");
	 start = high_resolution_clock::now(); 
	resize(ims1,numberIter, 0.25);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());



	printf("blend = ");
	 start = high_resolution_clock::now(); 
	openImage(numberIter);
	 stop = high_resolution_clock::now(); 
	 duration = duration_cast<milliseconds>(stop - start); 
	printf("%d\n",(int)duration.count());

	return 0;
}
