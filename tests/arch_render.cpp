// Faust architecture for the C++ renders of layer 2 (tests/faustrun.py render_cpp): the
// code a target compiles, run offline. Usage:
//   prog <in.f32> <out.f32> <frames> [label=value ...]
// in.f32: the inputs as float32, channel after channel (frames samples each);
// out.f32: the outputs, likewise. Processed in blocks of 64, as DawDreamer and scsynth.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>

#include "faust/dsp/dsp.h"
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"

<<includeIntrinsic>>

<<includeclass>>

int main(int argc, char** argv) {
    if (argc < 4) {
        std::fprintf(stderr, "usage: %s in.f32 out.f32 frames [label=value ...]\n", argv[0]);
        return 2;
    }
    const long n = std::atol(argv[3]);
    mydsp d;
    d.init(48000);
    MapUI ui;
    d.buildUserInterface(&ui);
    for (int a = 4; a < argc; a++) {
        std::string kv(argv[a]);
        size_t eq = kv.find('=');
        if (eq == std::string::npos) return 2;
        std::string label = kv.substr(0, eq);
        FAUSTFLOAT* zone = ui.getParamZone(label);
        if (!zone) {
            std::fprintf(stderr, "no control %s\n", label.c_str());
            return 3;
        }
        *zone = (FAUSTFLOAT)std::atof(kv.substr(eq + 1).c_str());
    }
    const int nin = d.getNumInputs(), nout = d.getNumOutputs();
    std::vector<float> in((size_t)nin * n), out((size_t)nout * n);
    if (nin > 0) {
        FILE* f = std::fopen(argv[1], "rb");
        if (!f || std::fread(in.data(), sizeof(float), in.size(), f) != in.size()) return 4;
        std::fclose(f);
    }
    std::vector<float*> ip(nin), op(nout);
    for (long i = 0; i < n; i += 64) {
        int m = (int)std::min<long>(64, n - i);
        for (int c = 0; c < nin; c++) ip[c] = in.data() + (size_t)c * n + i;
        for (int c = 0; c < nout; c++) op[c] = out.data() + (size_t)c * n + i;
        d.compute(m, ip.data(), op.data());
    }
    FILE* f = std::fopen(argv[2], "wb");
    if (!f || std::fwrite(out.data(), sizeof(float), out.size(), f) != out.size()) return 5;
    std::fclose(f);
    return 0;
}
