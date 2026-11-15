# Default target builds and runs hello. $(CC) and $(CFLAGS) are how
# `sensorium c run` hands the wrapper to a build that does not name it.
CC ?= gcc
CFLAGS ?=

.PHONY: all
all: hello
	./hello

hello: main.c
	$(CC) $(CFLAGS) -o hello main.c
