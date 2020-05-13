#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
using namespace cv;

//this does the same thing as the regular disk, but it outputs only one color per frame. Not as color acurate but should be MUCH faster.

#define WIDTH 2

cv::Mat ExtractCircle();

void GenerateDisk(int FrameNumber)
{
	Mat tmp;
	Mat out = Mat(FrameNumber * 2, FrameNumber * 2, CV_8UC4, Scalar(0, 0, 0, 255));
	printf("START\n");
	for (int i = 0; i < FrameNumber; i++)
	{
		std::string name = "images/";
		name += std::to_string(i + 1);
		name += ".jpg";
		Mat img = imread(name);

		resize(img, tmp, Size(1, 1), INTER_NEAREST);
		Vec3b colorS = ims1.at<Vec4b>(y, x);
		circle(out, Point(FrameNumber, FrameNumber), FrameNumber - i, Scalar(colorS.val[0], colorS.val[1], colorS.val[2]), CV_FILLED, 8, 0);
	}
	imwrite("save.png", out);
}

int main(int argc, char const *argv[])
{
	GenerateDisk(atoi(argv[1]));
	return 0;
}
