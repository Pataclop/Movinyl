// Movinyl - disk renderer
// ---------------------------------------------------------------------------
// Builds the "vinyl" image: each of the N movie frames becomes one concentric
// 1px ring. The outermost ring is frame 1 (start of the movie), the innermost
// is frame N (end). Every ring is colored by sampling its frame around a circle
// (the frame is squashed to a square, exactly like the historical resize).
//
// Design notes (rewrite):
//  * Determinism: ring membership of a pixel is decided with INTEGER arithmetic
//    only (no float in the geometry), so the output is bit-identical across
//    operating systems and independent of the number of threads.
//  * Each output pixel belongs to exactly ONE frame (the one whose radius equals
//    round(distance-to-center)). Frames therefore write disjoint pixels: we can
//    fill a single shared image in parallel with no data race and no merge step.
//  * Complexity: O(N^2) total (we touch each disk pixel once) instead of the old
//    O(N^3) (which up-scaled every frame to a ~4000x4000 square just to read a
//    1px ring out of it).
//  * Progress: prints one "PROGRESS" line per finished frame on stdout so the
//    Python front-end can drive a progress bar.
// ---------------------------------------------------------------------------

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <string>
#include <vector>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#ifdef _OPENMP
#include <omp.h>
#endif

using namespace cv;

// Some movies have a few black border pixels. To avoid them screwing the disk,
// the outermost ring is kept inside a centered square of size Height-2*SAFE_DIST.
#define SAFE_DIST 15

// Deterministic integer square root: largest r with r*r <= v (v >= 0).
static inline long isqrt_floor(long v) {
    if (v <= 0) return 0;
    long r = (long)std::sqrt((double)v);
    while (r > 0 && r * r > v) --r;
    while ((r + 1) * (r + 1) <= v) ++r;
    return r;
}

// Fill the single 1px ring of one frame directly into the final image.
// `i` is the 0-based frame index, `N` the frame count, `center` = N.
static void DrawRing(const Mat& src, Mat& dst, int i, int N) {
    const long R = (long)(N - i) - SAFE_DIST;     // target radius of this ring
    if (R <= 0) return;                            // innermost frames vanish at the hub

    const int rows0 = src.rows;
    const int cols0 = src.cols;
    if (rows0 <= 0 || cols0 <= 0) return;

    const long center   = N;                       // center of the (2N x 2N) image
    const long new_size = 2L * (N - i);            // virtual squared-frame size
    const long max_xy   = 2L * N - 1;              // last valid pixel index

    // A pixel at integer distance s2 = dx^2 + dy^2 belongs to this ring iff
    // round(sqrt(s2)) == R, which (s2 integer) is exactly:
    //     R*R - R + 1  <=  s2  <=  R*R + R
    const long s_lo = R * R - R + 1;
    const long s_hi = R * R + R;

    const long dyB = isqrt_floor(s_hi);            // rows that can contain the ring
    for (long dy = -dyB; dy <= dyB; ++dy) {
        const long Y = center + dy;
        if (Y < 0 || Y > max_xy) continue;

        const long hi = s_hi - dy * dy;            // >= 0 because |dy| <= dyB
        const long dx_max = isqrt_floor(hi);
        const long lo = s_lo - dy * dy;
        const long dx_min = (lo <= 0) ? 0 : (isqrt_floor(lo - 1) + 1); // ceil(sqrt(lo))

        const long y_imd = Y - i;
        const long src_y = (y_imd * (long)rows0) / new_size;
        if (src_y < 0 || src_y >= rows0) continue;
        const uchar* src_row = src.ptr<uchar>((int)src_y);

        for (long dx = dx_min; dx <= dx_max; ++dx) {
            // both arcs: X = center +/- dx (dx == 0 only once)
            for (int s = (dx == 0 ? 1 : 0); s < 2; ++s) {
                const long X = (s == 0) ? (center - dx) : (center + dx);
                if (X < 0 || X > max_xy) continue;

                const long x_imd = X - i;
                const long src_x = (x_imd * (long)cols0) / new_size;
                if (src_x < 0 || src_x >= cols0) continue;

                const uchar* sp = src_row + src_x * 3;      // BGR
                uchar* dp = dst.ptr<uchar>((int)Y) + X * 4; // BGRA
                dp[0] = sp[0];
                dp[1] = sp[1];
                dp[2] = sp[2];
                dp[3] = 255;
            }
        }
    }
}

static void GenerateDisk(int FrameNumber) {
    const int N = FrameNumber;
    Mat final = Mat(N * 2, N * 2, CV_8UC4, Scalar(0, 0, 0, 255));

    printf("START\n");
    fflush(stdout);

    #pragma omp parallel for schedule(dynamic, 4)
    for (int i = 0; i < N; ++i) {
        std::string name = "images/" + std::to_string(i + 1) + ".jpg";
        Mat img = imread(name, IMREAD_COLOR);   // always 3-channel BGR
        if (!img.empty()) {
            DrawRing(img, final, i, N);
        } else {
            // A missing/corrupt frame leaves a black ring; report it on stderr
            // (not on the stdout PROGRESS stream the front-end parses).
            fprintf(stderr, "MISSING %d\n", i + 1);
        }
        #pragma omp critical(progress)
        {
            printf("PROGRESS\n");
            fflush(stdout);
        }
    }

    // Fast PNG encode: level 1 is lossless (pixels are bit-identical to any other
    // level) but far quicker than OpenCV's default on a 4000x4000 image.
    const std::vector<int> png_params = {IMWRITE_PNG_COMPRESSION, 1};
    imwrite("save.png", final, png_params);
    printf("DONE\n");
    fflush(stdout);
}

int main(int argc, char const* argv[]) {
    setbuf(stdout, NULL);
    // We parallelize across frames with OpenMP; stop OpenCV from also spawning
    // its own worker pool inside each imread/imwrite so the two don't oversubscribe
    // the CPU. Purely a scheduling choice — the output is unaffected.
    cv::setNumThreads(0);
    if (argc < 2) {
        fprintf(stderr, "usage: %s <frame_count>\n", argv[0]);
        return 1;
    }
    int n = atoi(argv[1]);
    if (n <= 0) {
        fprintf(stderr, "error: frame_count must be a positive integer\n");
        return 1;
    }
    GenerateDisk(n);
    return 0;
}
