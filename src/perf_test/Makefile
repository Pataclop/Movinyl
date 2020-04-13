CC = g++
CFLAGS = -g -Wall
SRCS =  perf_test.cpp
PROG = perf_test

OPENCV = `pkg-config opencv --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) -o $(PROG) $(SRCS) $(LIBS)
