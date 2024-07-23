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

cv::Mat ExtractCircle (Mat ims) {
    int rows = ims.rows;
    int cols = ims.cols;

    float out_ring = rows / 2 - SAFE_DIST;
    float in_ring = (rows / 2) - (SAFE_DIST + WIDTH);
    int diff = (cols - rows) / 2;
    Mat imd = Mat(rows, rows, CV_8UC4, Scalar(0, 0, 0, 0)); // temporary image

    #pragma omp parallel for // Parallelize outer loop
    for (int y = 0; y < rows; ++y) {
        uchar* ims_ptr = ims.ptr<uchar>(y);
        uchar* imd_ptr = imd.ptr<uchar>(y);
        for (int x = 0; x < cols; ++x) {
            float dist = hypot((cols / 2) - x, (rows / 2) - y);
            if (dist < out_ring && dist > in_ring) {
                int x_diff = x - diff;
                if (x_diff >= 0 && x_diff < rows) {
                    imd_ptr[x_diff * 4 + 0] = ims_ptr[x * 3 + 0];
                    imd_ptr[x_diff * 4 + 1] = ims_ptr[x * 3 + 1];
                    imd_ptr[x_diff * 4 + 2] = ims_ptr[x * 3 + 2];
                    imd_ptr[x_diff * 4 + 3] = 255;
                }
            }
        }
    }
    return imd;
}

cv::Mat Insert(Mat ims1, Mat ims2, int margin) {
    int rows = ims1.rows;

    #pragma omp parallel for // Parallelize outer loop
    for (int y = 0; y < rows; ++y) {
        uchar* ims1_ptr = ims1.ptr<uchar>(y);
        uchar* ims2_ptr = ims2.ptr<uchar>(y + margin);
        for (int x = 0; x < rows; ++x) {
            if (ims1_ptr[x * 4 + 3] > 100) {
                ims2_ptr[(x + margin) * 4 + 0] = ims1_ptr[x * 4 + 0];
                ims2_ptr[(x + margin) * 4 + 1] = ims1_ptr[x * 4 + 1];
                ims2_ptr[(x + margin) * 4 + 2] = ims1_ptr[x * 4 + 2];
                ims2_ptr[(x + margin) * 4 + 3] = 255;
            }
        }
    }
    return ims2;
}

void GenerateDisk(int FrameNumber) {
    progressbar bar(2000);
    bar.set_todo_char(" ");
    bar.set_done_char("█");
    bar.set_opening_bracket_char("{");
    bar.set_closing_bracket_char("}");
    
    setenv("OMP_STACKSIZE", "10M", 1);
    printf("START\n");
    
    std::vector<Mat> vectorOfMatrices(THREAD_COUNT, Mat(FrameNumber * 2, FrameNumber * 2, CV_8UC4, Scalar(0, 0, 0, 255)));
    Mat final = Mat(FrameNumber * 2, FrameNumber * 2, CV_8UC4, Scalar(0, 0, 0, 255));

    #pragma omp parallel num_threads(THREAD_COUNT) shared(vectorOfMatrices)
    {
        Mat extracted;
        #pragma omp for schedule(static, 1)
        for (int i = 0; i < FrameNumber; ++i) {
            std::string name = "images/" + std::to_string(i + 1) + ".jpg";
            Mat img = imread(name);

            // First, resize the picture to the wanted size.
            int new_size = 2 * FrameNumber - 2 * i;
            resize(img, extracted, Size(new_size, new_size), INTER_NEAREST);

            // Extract circle from image
            extracted = ExtractCircle(extracted);

            // Print values for progress bar
            #pragma omp critical
            bar.update();

            // Store single disk back into the Matrix for each thread
            vectorOfMatrices[omp_get_thread_num()] = Insert(extracted, vectorOfMatrices[omp_get_thread_num()], i);
        }
    }

    // Merge all disks into the final image
    for (int i = 0; i < THREAD_COUNT; ++i) {
        max(final, vectorOfMatrices[i], final);
    }
    imwrite("save.png", final);
}

int main(int argc, char const *argv[]) {
    setbuf(stdout, NULL);
    GenerateDisk(atoi(argv[1]));
    printf("\n");
    return 0;
}
