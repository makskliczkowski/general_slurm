// Example C++ program that follows the sharding contract of general_slurm.
//
// usage: sim CONFIG [--out DIR] [--shard k/n] [--deadline EPOCH] [--allocation-start EPOCH]
// CONFIG has one line "runs = N". The program does block k of n equal blocks of the N runs and ignores the deadline, because each run
// here is instant. A real program starts a run only when it fits before the deadline, and exits 130 when runs are left.
// With --out DIR it appends one line per run to DIR/<config name>.txt. The project gets DIR from its own variable SIM_SCRATCH.
// -----------------------------------------------
// Author            : Maks Kliczkowski
// File              : sim.cpp
// -----------------------------------------------

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: sim CONFIG [--out DIR] [--shard k/n]\n";
        return 2;
    }

    int         block  = 0;
    int         blocks = 1;
    std::string out;
    for (int i = 2; i + 1 < argc; ++i) {
        if (std::string(argv[i]) == "--shard") {
            std::sscanf(argv[i + 1], "%d/%d", &block, &blocks);
        }
        if (std::string(argv[i]) == "--out") {
            out = argv[i + 1];
        }
    }

    int runs = 0;
    std::ifstream config(argv[1]);
    std::string   key;
    std::string   equals;
    int           value;
    while (config >> key >> equals >> value) {
        if (key == "runs") {
            runs = value;
        }
    }

    const int first = block * runs / blocks;
    const int last  = (block + 1) * runs / blocks;
    std::ofstream result;
    if (!out.empty()) {
        std::filesystem::create_directories(out);
        result.open(std::filesystem::path(out) / (std::filesystem::path(argv[1]).stem().string() + ".txt"), std::ios::app);
        std::cout << "gs: data=" << out << "\n";
    }
    for (int run = first; run < last; ++run) {
        result << "run " << run << "\n";
        std::cout << "run " << run << " of " << argv[1] << "\n";
        std::cout << "gs: progress=" << (run - first + 1) << "/" << (last - first) << std::endl;
    }
    return 0;
}

// -------------------------------------------
//! EOF
// -------------------------------------------
