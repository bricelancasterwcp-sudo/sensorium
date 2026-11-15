# Build the C recorder runtime. `make -C c/rt` produces sensorium_c_rt.o.
CC ?= gcc
CFLAGS = -O2 -g -fno-omit-frame-pointer -fPIC -fno-instrument-functions \
	-Wall -Wextra -Wno-frame-address

.PHONY: all clean

all: sensorium_c_rt.o

sensorium_c_rt.o: sensorium_c_rt.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f sensorium_c_rt.o
