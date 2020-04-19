CC = g++
CFLAGS = -g -Wall
SRCS = disk.cpp
PROG = disk
OMP = -fopenmp

OPENCV = `pkg-config opencv --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) $(OMP) -o $(PROG) $(SRCS) $(LIBS)
