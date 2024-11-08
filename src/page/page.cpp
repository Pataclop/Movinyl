#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <iostream>
#include <string>
#include <ctime>

using namespace cv;

// Function to add a palette of 5 colored discs inside a grey-bordered circle.
void addPalette(Mat img) {
    Mat temp;
    Mat colorPalette = imread("palette.png");  // Load the predefined palette image
    colorPalette.convertTo(temp, CV_8UC3);     // Convert it to a compatible format
    Mat insetImage(img, Rect(0, 7000, temp.cols, temp.rows));  // Define the position for the palette
    temp.copyTo(insetImage);                   // Insert the palette into the main image
}

// Function to assemble a movie's page layout with various elements like title, year, director, and duration.
void insertInFrame(const std::string& name) {
    Mat img;
    std::string filename = name + ".png";
    std::cout << "Now processing: " << filename << "\n";
    
    // Load the main image associated with the movie
    Mat originalImage = imread(filename);
    originalImage.convertTo(img, CV_8UC3);

    // Define output image size
    int rows = img.rows;
    int cols = img.cols;
    int outputHeight = cols * 2;
    int outputWidth = rows + (rows / 4);
    Mat output = Mat(outputHeight, outputWidth, CV_8UC3, Scalar(0, 0, 0));

    // Center the main image on the output page
    img.copyTo(output(cv::Rect((outputWidth / 2) - cols / 2, (outputHeight / 2) - rows / 2, cols, rows)));

    // Load pre-generated title, year, director, and duration images created with Python
    Mat title = imread("titre.png");
    Mat year = imread("année.png");
    Mat director = imread("réalisateur.png");
    Mat duration = imread("durée.png");

    // Position these images on the output page
    title.copyTo(output(cv::Rect(0, outputHeight / 10, outputWidth, 600)));
    year.copyTo(output(cv::Rect(0, (outputHeight / 8) + 400, outputWidth, 600)));
    director.copyTo(output(cv::Rect(0, (outputHeight / 2) + (rows / 2) + (rows / 20), outputWidth, 600)));
    duration.copyTo(output(cv::Rect(0, (outputHeight / 2) + (rows / 2) + (rows / 20) + 400, outputWidth, 600)));

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
