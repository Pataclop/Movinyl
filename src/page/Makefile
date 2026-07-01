# Legacy convenience build (Linux). Prefer src/CMakeLists.txt via `movinyl setup`.
CC = g++
CFLAGS = -O3 -Wall
SRCS =  page.cpp
PROG = page

OPENCV = `pkg-config opencv4 --cflags --libs`
LIBS = $(OPENCV)

$(PROG):$(SRCS)
	$(CC) $(CFLAGS) -o $(PROG) $(SRCS) $(LIBS)
