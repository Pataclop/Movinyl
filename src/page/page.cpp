#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <iostream>
#include <string>
#include <ctime>

using namespace cv;

// Paste `src` onto `dst` with its top-left at (x, y), clipped to whatever
// actually fits inside `dst`. OpenCV's copyTo aborts the whole process on any
// out-of-bounds ROI or size mismatch, so a missing, oversized or unexpectedly
// shaped asset would crash the page. Here it just degrades gracefully.
static void safePaste(Mat& dst, const Mat& src, int x, int y) {
    if (src.empty() || dst.empty()) return;
    Rect roi = Rect(x, y, src.cols, src.rows) & Rect(0, 0, dst.cols, dst.rows);
    if (roi.width <= 0 || roi.height <= 0) return;      // nothing visible
    Rect srcRoi(roi.x - x, roi.y - y, roi.width, roi.height);  // handles x/y < 0
    src(srcRoi).copyTo(dst(roi));
}

// Function to add the color palette near the bottom of the page.
void addPalette(Mat& img) {
    Mat colorPalette = imread("palette.png");  // Load the predefined palette image
    if (colorPalette.empty()) return;
    // Position proportional to the page height (7/8 == the historical y=7000 on
    // an 8000px page) so it tracks any disk size instead of a hardcoded offset.
    const int y = (img.rows * 7) / 8;
    safePaste(img, colorPalette, 0, y);
}

// Function to assemble a movie's page layout with various elements like title, year, director, and duration.
void insertInFrame(const std::string& name) {
    Mat img;
    std::string filename = name + ".png";
    std::cout << "Now processing: " << filename << "\n";
    
    // Load the main image associated with the movie
    Mat originalImage = imread(filename);
    if (originalImage.empty()) {
        std::cerr << "Error: could not read disk image '" << filename << "'.\n";
        return;
    }
    originalImage.convertTo(img, CV_8UC3);

    // Define output image size
    int rows = img.rows;
    int cols = img.cols;
    int outputHeight = cols * 2;
    int outputWidth = rows + (rows / 4);
    Mat output = Mat(outputHeight, outputWidth, CV_8UC3, Scalar(0, 0, 0));

    // Center the main image on the output page
    safePaste(output, img, (outputWidth / 2) - cols / 2, (outputHeight / 2) - rows / 2);

    // Load pre-generated title, year, director, and duration images created with
    // Python. ASCII filenames are used on purpose for cross-platform reliability
    // (accented names break on some Windows code pages / filesystems).
    Mat title = imread("title.png");
    Mat year = imread("year.png");
    Mat director = imread("director.png");
    Mat duration = imread("duration.png");

    // Position these images on the output page (clipped/skipped if absent).
    safePaste(output, title, 0, outputHeight / 10);
    safePaste(output, year, 0, (outputHeight / 8) + 400);
    safePaste(output, director, 0, (outputHeight / 2) + (rows / 2) + (rows / 20));
    safePaste(output, duration, 0, (outputHeight / 2) + (rows / 2) + (rows / 20) + 400);

    // Insert the color palette at the specified position
    addPalette(output);

    // Save the assembled page to a new image file
    std::string outputFilename = name + "_page.png";
    imwrite(outputFilename, output);
}

int main(int argc, char const *argv[]) {
    if (argc < 2) {
        std::cerr << "Error: Please provide a filename as an argument.\n";
        return 1;
    }

    // Remove any quotes in the input filename
    std::string name = argv[1];
    name.erase(std::remove(name.begin(), name.end(), '\"'), name.end());

    // Generate the layout for the movie page
    insertInFrame(name);
    return 0;
}
