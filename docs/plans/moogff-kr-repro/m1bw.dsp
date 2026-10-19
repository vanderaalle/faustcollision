import("stdfaust.lib");
sc = library("sc.lib");
f1 = hslider("freq", 60, 2, 160, 0.01);
process(x) = (sc.latch(x, sc.a2k(sc.impulse_kr(300.0, 0.0)))) : \(k).(sc.moogff_kr(sc.a2k(f1), 0.5, k));
