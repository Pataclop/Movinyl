CC = g++
CFLAGS = -g -Wall
SRCS = disk_mono.cpp 
PROG = disk

OPENCV = `pkg-config opencv4 --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) -o $(PROG) $(SRCS) $(LIBS)
