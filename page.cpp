#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <stdio.h>
#include <stdlib.h>
#include <string>
using namespace cv;
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>


/*
			IT IS IMPORTANT TO KEEP A SAVING OF THE CIRCLE PICTURE SO YOU CAN CHANGE THE PAGE LAYOUT 
								WITHOUT HAVING TO REPROCESS A MOVIE*/


// in this file, a lot of code is unused, results of failed attempts to extract 
// main colors from the disc image. 
#define COLORNUMBER 8

int proche(int r, int g, int b, int ** colors){

	int indice = -1;
	float min = 999999999;

	r=(int)r/(int)COLORNUMBER;
	r=r*COLORNUMBER;
	b=(int)b/(int)COLORNUMBER;
	b=b*COLORNUMBER;
	g=(int)g/(int)COLORNUMBER;
	g=g*COLORNUMBER;
	for(int i=0; i<(COLORNUMBER+1)*(COLORNUMBER+1)*(COLORNUMBER+1); i++){
		float distance = (r-colors[i][1])*(r-colors[i][1])+(g-colors[i][2])*(g-colors[i][2])+(b-colors[i][3])*(b-colors[i][3]);// sqrt(pow(r-colors[i+1],2) + pow(g-colors[i+2],2) + pow(b-colors[i+3],2));
		if (distance<min){
			min = distance;
			indice=i;
			
		}

	}
	return indice;
}



int max4(int**tab, int n){
	int max=-1; 
	int indice=-1;
	for (int i=0; i<n; i++){
		if(tab[i][0]>max){
			max=tab[i][0];
			indice=i;
		}
	}
	if(tab[indice][0]>0)
		return indice;
	else
		return -1;
}


void maincolors(Mat ims){
	int numberOfColors=(COLORNUMBER+1)*(COLORNUMBER+1)*(COLORNUMBER+1);
	int rows = ims.rows;
	int cols = ims.cols;

	int ** colors=(int**)malloc(numberOfColors*sizeof(int*));
	for(int i=0; i<numberOfColors; i++){
		colors[i]=(int*)calloc(4, sizeof(int));
	}




	//COLORIZE
	printf("colorize\n");
	int intervalle = 255/COLORNUMBER;//validé
	int cmp = 0;
	for(int r=0; r<COLORNUMBER+1; r++){
		for (int g = 0; g<COLORNUMBER+1; g++){
			for(int b=0; b<COLORNUMBER+1; b++){
				int R = r*intervalle;
				int G = g*intervalle;
				int B = b*intervalle;
				R = R/COLORNUMBER;
				G = G/COLORNUMBER;
				B = B/COLORNUMBER;


				R = r*intervalle;
				G = g*intervalle;
				B = b*intervalle;

				colors[cmp][0]=0;
				colors[cmp][1]=R;
				colors[cmp][2]=G;
				colors[cmp][3]=B;
				cmp++;
			}
		}
	}
	//for(int i=0; i<pow(COLORNUMBER,3);i++) printf("%d %d\n",i,colors[i][0] );

	for(int i=0; i<numberOfColors; i++){
		//printf("%d %d %d %d %d\n",i, colors[i][0],colors[i][1],colors[i][2],colors[i][3] );
	}
	printf("colorCount\n");
	for (int x=0; x<cols; x++){
		for(int y=0; y<rows; y++){
			float dist = sqrt(pow((cols/2)-x,2)+pow((rows/2)-y,2));
			//printf("%d %d %f \n",cols, rows, dist);
			if (dist<(rows/2)-5){
				Vec3b colorS = ims.at<Vec3b>(y, x);
				int b=colorS.val[0];//blue
				int g=colorS.val[1];//green
				int r=colorS.val[2];//red
				//printf("capture R%d G%d B%d %d %d %d\n", r,g,b,colorS.val[2],colorS.val[1],colorS.val[0]);

				int indice = proche(r,g,b,colors);
				//printf("indice %d r=%d g=%d b=%d\n",indice,r,g,b );//couleur vue
				colors[indice][0]++;
			}
		}
	}

	printf("maincolors\n");
	for(int i=0; i<10; i++){
		int indice = max4(colors, numberOfColors);
		if (indice !=-1){
			printf("%d %d %d %d %d \n",indice, colors[indice][0],colors[indice][1],colors[indice][2],colors[indice][3] );
			colors[indice][0]=0;
		}

	}


}
//takes 5 colors and creates 5 colored discs, each fitted inside a round grey border.
void palette (int **colors,  int ColorNumber, Mat img){

	int height = img.rows;
	int width = img.cols;

	int size = ((width))/ColorNumber;
	Mat colorPalette = Mat( size,ColorNumber*size, CV_8UC3, Scalar(0,0,0));
	Vec3b colorD;
	for(int i=0; i<ColorNumber; i++){
		for (int x=0; x<size; x++){
			for (int y=0; y<size; y++){
				int distance = sqrt(pow((size/2)-x,2)+pow((size/2)-y,2));
				//if i am not in a colored disc nor in the border, the background is black
				if ((distance<=size/2) && (distance>=(size/2)-(size/3))){
					colorD.val[0] = 0;//blue
					colorD.val[1] = 0;//green
					colorD.val[2] = 0;//red

					colorPalette.at<Vec3b>(y,x+size*i) = colorD;
				}
				//if i am between the background and the color, the border is grey (I wanted a neutral color, so 127 gray does the job)
				if  ((distance<=(size/2)-(size/3)) && (distance>=(size/2)-(size/2.9))){
					colorD.val[0] = 127;//blue
					colorD.val[1] = 127;//green
					colorD.val[2] = 127;//red

					colorPalette.at<Vec3b>(y,x+size*i) = colorD;
				}
				//and else, i am in the color disc, and i draw the corresponding color.
				else {
					if (distance<(size/2)-(size/2.9)) {
						colorD.val[0] = colors[i][2];//blue
						colorD.val[1] = colors[i][1];//green
						colorD.val[2] = colors[i][0];//red
						colorPalette.at<Vec3b>(y,x+(size*i)) = colorD;
					}
				}
			}
		}
	}
	Mat tmp;
	colorPalette.convertTo(tmp, CV_8UC3);
	imwrite("palette.png", colorPalette);
	int x=(width/2)-((size*ColorNumber)/2);
	int y=height-size;

	tmp.copyTo(img(cv::Rect(x,y,size*ColorNumber, size)));

}


//Here starts the page assembly. 
//Here we just assemble multiple images. There is the disc, the name of the movie, year, realisator, and durration.
//since opencv doesn't support third party fonts (as far as I know), all these pictures were created in python.
void insert_in_frame(std::string name, int aa1, int aa2, int aa3,int aa4,int aa5,int aa6,int aa7,int aa8,int aa9,int aa10,int aa11,int aa12,int aa13,int aa14,int aa15, std::string outputName){
	Mat img;
	Mat ims = imread(name);
	
	ims.convertTo(img, CV_8UC3);

	int rows = img.rows;
	int cols = img.cols;
	int H=cols*2;
	int W=rows+(rows/4);
	Mat out = Mat( H,W, CV_8UC3, Scalar(0,0,0));
	img.convertTo(img, CV_8UC3);

	img.copyTo(out(cv::Rect((W/2)-cols/2,(H/2)-rows/2,cols, rows)));

	//I think this was from when I tried to extract colors automaticaly. not sure, so not removing rn
	Mat tmp;
	resize(img, tmp, Size(1000,1000),INTER_NEAREST);
	tmp.convertTo(tmp, CV_8UC4);
	//

	int numberOfColors = 5;
	int ** colors=(int**)malloc(numberOfColors*sizeof(int*));
	for(int i=0; i<numberOfColors; i++){
		colors[i]=(int*)calloc(4, sizeof(int));
	}
	colors[0][0]=aa1,
	colors[0][1]=aa2,
	colors[0][2]=aa3,
	colors[1][0]=aa4,
	colors[1][1]=aa5,
	colors[1][2]=aa6,
	colors[2][0]=aa7,
	colors[2][1]=aa8,
	colors[2][2]=aa9,
	colors[3][0]=aa10,
	colors[3][1]=aa11,
	colors[3][2]=aa12,
	colors[4][0]=aa13,
	colors[4][1]=aa14,
	colors[4][2]=aa15,
	//here we generate the picture containing the 5 colored circles.
	palette(colors, 5, out);
	//these images were generated by a python script.
	Mat titre = imread("titre.png");
	Mat annee = imread("année.png");
	Mat real = imread("réalisateur.png");
	Mat duree = imread("durée.png");



	//the size of the pictures is determined in the pithon file, thought for a 8000x5000 image.
	//the positioning is ajustable, I find it nice this way.
	titre.copyTo(out(cv::Rect(0,H/10, W,600)));
	annee.copyTo(out(cv::Rect(0,(H/8)+400,W, 600)));
	real.copyTo(out(cv::Rect(0, (H/2)+(rows/2)+(rows/20),W, 600)));
	duree.copyTo(out(cv::Rect(0, (H/2)+(rows/2)+(rows/20)+400,W, 600)));

	imwrite(outputName, out);

}

int main(int argc, char const *argv[])
{
	insert_in_frame(argv[1],
		atoi(argv[2]),
		atoi(argv[3]),
		atoi(argv[4]),
		atoi(argv[5]),
		atoi(argv[6]),
		atoi(argv[7]),
		atoi(argv[8]),
		atoi(argv[9]),
		atoi(argv[10]),
		atoi(argv[11]),
		atoi(argv[12]),
		atoi(argv[13]),
		atoi(argv[14]),
		atoi(argv[15]),
		atoi(argv[16]),
		argv[17]
		);
	return 0;
}
