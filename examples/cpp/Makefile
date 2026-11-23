# Builds build/sim; run "make" in this folder, on a login node or a compute node, with the modules of GS_MODULES loaded.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : Makefile
# -----------------------------------------------

build/sim: src/sim.cpp
	mkdir -p build
	$(CXX) -O2 -std=c++17 -o $@ $<

# -------------------------------------------
#! EOF
# -------------------------------------------
