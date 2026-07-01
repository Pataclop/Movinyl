# Legacy convenience build (Linux). The cross-platform path is src/CMakeLists.txt
# (used by `movinyl setup`). -O3 matters a lot here: the old flags had no
# optimization at all.
CC = g++
CFLAGS = -O3 -Wall -fopenmp
SRCS = disk.cpp 
PROG = disk

OPENCV = `pkg-config opencv4 --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) -o $(PROG) $(SRCS) $(LIBS)
