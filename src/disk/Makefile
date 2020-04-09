CC = g++
CFLAGS = -g -Wall
SRCS = disk.cpp 
PROG = disk

OPENCV = `pkg-config opencv --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) -o $(PROG) $(SRCS) $(LIBS)
