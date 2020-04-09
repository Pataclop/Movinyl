#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
#include <iostream>
#include <thread> 
using namespace cv;





cv::Mat ExtractCircle ();

cv::Mat ExtractCircle (Mat ims){
	int rows = ims.rows;
	int cols = ims.cols;
	int diff = (cols-rows)/2;
	Mat imd = Mat(rows, rows, CV_8UC4, Scalar(0,0,0,0));

	for (int x=0; x<cols; x++){
		for (int y=0; y<rows; y++){

			float dist = sqrt(pow((cols/2)-x,2)+pow((rows/2)-y,2));
			if (dist < rows/2 && dist > (rows/2)-2){
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

cv::Mat Insert(Mat ims1, Mat ims2, int margin){
	int rows = ims1.rows;
	for(int x=0; x<rows; x++){
		for(int y=0; y<rows; y++){
			Vec4b colorS = ims1.at<Vec4b>(y, x);
			Vec4b colorD;
			if(colorS.val[3]>200){
				colorD.val[0] = colorS.val[0];//blue
				colorD.val[1] = colorS.val[1];//green
				colorD.val[2] = colorS.val[2];//red
				colorD.val[3] = 255;//colorS.val[3];//alpha
				ims2.at<Vec4b>(y+margin,x+margin) = colorD;
			}
		}
	}
	return ims2;
}


void GenerateDisk(int FrameNumber, int num){
	Mat tmp;
	Mat out = Mat(FrameNumber*2, FrameNumber*2, CV_8UC4, Scalar(0,0,0,255));
	printf("START %d\n", num);
	float f_num = (float)num;
	int start = (int)(((f_num-1.0)/10.0)*(float)FrameNumber);
	printf("%d %d\n", start , (int)(((float)num/(float)10)*(float)FrameNumber)  );
	for (int i=start; i<(int)(((float)num/(float)10)*(float)FrameNumber)-1; i++){
		std::string name = "images/";
		name += std::to_string(i+1);
		name += ".jpg";
		Mat img = imread(name);
		resize(img, tmp, Size((2*FrameNumber)-2*i, (2*FrameNumber)-2*i),INTER_NEAREST);
		tmp=ExtractCircle(tmp);
		if(i%10==0)
			printf("image = %d       process = %d\n",i, num);
		out = Insert(tmp, out, i);
	}
	std::string nom = ".";
	nom += std::to_string(num);
	nom += ".png";
	imwrite(nom, out);

}

int main(int argc, char const *argv[]){

	int FrameNumber = atoi(argv[1]);
	
	//std::thread un(GenerateDisk, FrameNumber, 1);
	//std::thread deux(GenerateDisk, FrameNumber, 2);
	//std::thread trois(GenerateDisk, FrameNumber, 3);
	//std::thread quatre(GenerateDisk, FrameNumber, 4);
	//std::thread cinq(GenerateDisk, FrameNumber, 5);
	//std::thread six(GenerateDisk, FrameNumber, 6);
	//std::thread sept(GenerateDisk, FrameNumber, 7);
	//std::thread huit(GenerateDisk, FrameNumber, 8);
	std::thread neuf(GenerateDisk, FrameNumber, 9);
	std::thread dix(GenerateDisk, FrameNumber, 10);


	//un.join();
	//deux.join();
	//trois.join();
	//quatre.join();
	//cinq.join();
	//six.join();
	//sept.join();
	//huit.join();
	neuf.join();
	dix.join();
	

	//Mat n1 = imread(".1.png");
	//Mat n2 = imread(".2.png");
	//Mat n3 = imread(".3.png");
	//Mat n4 = imread(".4.png");
	//Mat n5 = imread(".5.png");
	//Mat n6 = imread(".6.png");
	//Mat n7 = imread(".7.png");
	//Mat n8 = imread(".8.png");
	Mat n9 = imread(".9.png");
	Mat n10 = imread(".10.png");

	Mat out = Mat(FrameNumber*2, FrameNumber*2, CV_8UC4, Scalar(0,0,0,255));


	//out = Insert(n1, out, 0);printf("1\n");imwrite("save1.png", out);
	//out = Insert(n2, out, 0);printf("2\n");imwrite("save2.png", out);
	//out = Insert(n3, out, 0);printf("3\n");imwrite("save3.png", out);
	//out = Insert(n4, out, 0);printf("4\n");imwrite("save4.png", out);
	//out = Insert(n5, out, 0);printf("5\n");imwrite("save5.png", out);
	//out = Insert(n6, out, 0);printf("6\n");imwrite("save6.png", out);
	//out = Insert(n7, out, 0);printf("7\n");imwrite("save7.png", out);
	//out = Insert(n8, out, 0);printf("8\n");imwrite("save8.png", out);
	out = Insert(n9, out, 0);printf("9\n");imwrite("save9.png", out);
	out = Insert(n10, out, 0);printf("10\n");
	
	printf("FINI\n");
	imwrite("save.png", out);



	return 0;
}
