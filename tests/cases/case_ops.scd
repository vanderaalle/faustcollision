// One regression case per operator: case_UnaryOp_<label>, case_BinaryOp_<label> (audio rate),
// plus <...>_kr twins through A2K/K2A: scsynth runs different code at each rate (nova-simd
// at ar, the C library at kr). a = 2 × input (unary) or 4 × input (binary),
// b = 4 × input² + 0.3, spanning small integers for the bitwise and integer operators.
(
var unary = [['neg', "neg"], ['not', "not"], ['bitNot', "bitNot"], ['abs', "abs"], ['asFloat', "asFloat"], ['asInteger', "asInteger"], ['ceil', "ceil"], ['floor', "floor"], ['frac', "frac"], ['sign', "sign"], ['squared', "squared"], ['cubed', "cubed"], ['sqrt', "sqrt"], ['exp', "exp"], ['reciprocal', "reciprocal"], ['midicps', "midicps"], ['cpsmidi', "cpsmidi"], ['midiratio', "midiratio"], ['ratiomidi', "ratiomidi"], ['dbamp', "dbamp"], ['ampdb', "ampdb"], ['octcps', "octcps"], ['cpsoct', "cpsoct"], ['log', "log"], ['log2', "log2"], ['log10', "log10"], ['sin', "sin"], ['cos', "cos"], ['tan', "tan"], ['asin', "asin"], ['acos', "acos"], ['atan', "atan"], ['sinh', "sinh"], ['cosh', "cosh"], ['tanh', "tanh"], ['rand', "rand"], ['rand2', "rand2"], ['linrand', "linrand"], ['bilinrand', "bilinrand"], ['sum3rand', "sum3rand"], ['distort', "distort"], ['softclip', "softclip"], ['coin', "coin"], ['silence', "silence"], ['thru', "thru"], ['rectWindow', "rectWindow"], ['hanWindow', "hanWindow"], ['welWindow', "welWindow"], ['triWindow', "triWindow"], ['ramp', "ramp"], ['scurve', "scurve"]];
var binary = [['+', "add"], ['-', "sub"], ['*', "mul"], ['div', "div"], ['/', "fdiv"], ['mod', "mod"], ['==', "eq"], ['!=', "ne"], ['<', "lt"], ['>', "gt"], ['<=', "le"], ['>=', "ge"], ['min', "min"], ['max', "max"], ['bitAnd', "bitAnd"], ['bitOr', "bitOr"], ['bitXor', "bitXor"], ['lcm', "lcm"], ['gcd', "gcd"], ['round', "round"], ['roundUp', "roundUp"], ['trunc', "trunc"], ['atan2', "atan2"], ['hypot', "hypot"], ['hypotApx', "hypotApx"], ['pow', "pow"], ['leftShift', "leftShift"], ['rightShift', "rightShift"], ['unsignedRightShift', "unsignedRightShift"], ['fill', "fill"], ['ring1', "ring1"], ['ring2', "ring2"], ['ring3', "ring3"], ['ring4', "ring4"], ['difsqr', "difsqr"], ['sumsqr', "sumsqr"], ['sqrsum', "sqrsum"], ['sqrdif', "sqrdif"], ['absdif', "absdif"], ['thresh', "thresh"], ['amclip', "amclip"], ['scaleneg', "scaleneg"], ['clip2', "clip2"], ['excess', "excess"], ['fold2', "fold2"], ['wrap2', "wrap2"], ['firstArg', "firstArg"], ['rrand', "rrand"], ['exprand', "exprand"]];
var random = ['rand', 'rand2', 'linrand', 'bilinrand', 'sum3rand', 'coin', 'rrand', 'exprand'];
[\ar, \kr].collect { |rate|
	var suffix = if(rate == \kr) { "_kr" } { "" };
	var src = { if(rate == \kr) { A2K.kr(SoundIn.ar(0)) } { SoundIn.ar(0) } };
	var out = { |sig| Out.ar(0, if(rate == \kr) { K2A.ar(sig) } { sig }) };
	// random operators scaled by an impulse give one random spike: compare on sustained signals only
	var md = { |op| if(random.includes(op)) { (signals: [\bass_di, \noise, \sweep]) } { () } };
	unary.collect { |p|
		SynthDef(("case_UnaryOp_" ++ p[1] ++ suffix).asSymbol, { out.(UnaryOpUGen(p[0], src.value * 2)) },
			metadata: md.(p[0]))
	} ++ binary.collect { |p|
		SynthDef(("case_BinaryOp_" ++ p[1] ++ suffix).asSymbol, { var in = src.value;
			out.(BinaryOpUGen(p[0], in * 4, in * in * 4 + 0.3)) }, metadata: md.(p[0]))
	}
}.flatten
)
