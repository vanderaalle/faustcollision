// Headless sclang batch, run once per build:
//   sclang translator/batch.scd <root> <buildDir> [no-render] [tolerant] <srcDir>...
// e.g. sclang translator/batch.scd $PWD build defs tests/cases
// For every <srcDir>/*.scd (each file evaluates to a SynthDef or an Array of SynthDefs):
//   <buildDir>/synthdefs/<name>.scsyndef   the binary the translator parses
//   <buildDir>/meta/<name>.json            specs, output count, render jobs
//   <buildDir>/nrt/<name>/<job>.wav        scsynth NRT render of each test signal
// Render settings per def: all controls at default, then each spec'd control at min and max.
// tolerant: a file that fails is recorded in <buildDir>/meta/<file>.sclang_error and skipped.
(
var argv = thisProcess.argv;
var root = argv[0] ?? { "usage: sclang batch.scd <root> <buildDir> [no-render] [tolerant] <srcDir>...".error; 1.exit };
var build = root +/+ argv[1];
var render = argv.includesEqual("no-render").not;
var tolerant = argv.includesEqual("tolerant");
var srcDirs = argv.drop(2).reject { |a| ["no-render", "tolerant"].includesEqual(a) };
var sampleRate = 48000;
var defDir = build +/+ "synthdefs/";
var metaDir = build +/+ "meta/";
var nrtRoot = build +/+ "nrt/";
var json, settingTag, process;

json = { |x|
	case
	{ x.isNil } { "null" }
	{ x.isKindOf(Boolean) } { x.asString }
	{ x.isKindOf(Symbol) or: { x.isKindOf(String) } } {
		"\"" ++ x.asString.replace("\\", "\\\\").replace("\"", "\\\"") ++ "\""
	}
	{ x.isKindOf(SimpleNumber) } {
		if(x.isNaN or: { x.abs == inf }) { Error("non-finite number in metadata").throw };
		if(x.isKindOf(Integer)) { x.asString } { x.asStringPrec(17) }
	}
	{ x.isKindOf(Dictionary) } {
		"{" ++ x.keys.asArray.sort.collect { |k| json.(k.asString) ++ ": " ++ json.(x[k]) }.join(", ") ++ "}"
	}
	{ x.isKindOf(SequenceableCollection) } { "[" ++ x.collect(json).join(", ") ++ "]" }
	{ Error("cannot encode % as JSON".format(x.class)).throw }
};

settingTag = { |setting|
	setting.keys.asArray.sort.collect { |k| k.asString ++ "=" ++ setting[k].asFloat.asStringPrec(6) }.join("_")
};

try {
	var files = srcDirs.collect { |d| (root +/+ d +/+ "*.scd").pathMatch }.flatten;
	var signals = (root +/+ "signals/*.wav").pathMatch.collect { |path|
		var sf = SoundFile.openRead(path) ?? { Error("cannot read " ++ path).throw };
		var info = (name: path.basename.splitext[0], path: path, dur: sf.duration, sr: sf.sampleRate, chans: sf.numChannels);
		sf.close;
		if(info.sr != sampleRate) { Error("% is not % Hz".format(path, sampleRate)).throw };
		if(info.chans != 1) { Error("% is not mono".format(path)).throw };
		info
	};
	if(signals.isEmpty) { Error("no signals in signals/; run signals/make_signals.py").throw };
	[defDir, metaDir, nrtRoot].do(File.mkdir(_));

	process = { |path, def|
		var md, specs, outs, numOutputs, settings, jobs, names, defaults, sigs, nrtDir;
		md = def.metadata ? ();
		specs = md[\specs] ? ();
		outs = def.children.select { |u| u.isKindOf(Out) };  // LocalOut is not an output
		if(outs.size != 1) { Error("%: expected exactly one Out, found %".format(def.name, outs.size)).throw };
		numOutputs = outs[0].inputs.size - 1;

		names = def.allControlNames.collect(_.name);
		defaults = ();
		def.allControlNames.do { |c| defaults[c.name] = c.defaultValue };
		specs.keys.do { |k|
			if(names.includes(k).not) { Error("%: spec for unknown control %".format(def.name, k)).throw }
		};

		settings = List[()];
		specs.keys.asArray.sort.do { |k| [specs[k].asSpec.minval, specs[k].asSpec.maxval].do { |v| settings.add(().put(k, v)) } };
		settings = settings.collect { |s| var full = (); specs.keys.do { |k| full[k] = s[k] ?? { specs[k].asSpec.default } }; full };
		settings = settings.asArray.reject { |s, i| settings.copyRange(0, i - 1).any { |t| t == s } };

		sigs = md[\signals] !? { |sel| signals.select { |s| sel.collect(_.asString).includesEqual(s.name) } } ? signals;
		nrtDir = nrtRoot +/+ def.name.asString;
		File.mkdir(nrtDir);
		def.writeDefFile(defDir);

		jobs = List[];
		sigs.do { |sig|
			settings.do { |setting|
				var tag = sig.name ++ (if(setting.isEmpty) { "" } { "__" ++ settingTag.(setting) });
				var osc = nrtDir +/+ tag ++ ".osc";
				var wav = nrtDir +/+ tag ++ ".wav";
				var args = setting.asKeyValuePairs;
				var score = Score([
					[0.0, ['/d_recv', def.asBytes]],
					[0.0, ['/s_new', def.name, 1000, 0, 0] ++ args],
					[sig.dur, ['/c_set', 0, 0]]
				]);
				var cmd, status;
				score.writeOSCFile(osc);
				cmd = "scsynth -N % % % % WAV float -i 1 -o % -m 65536 > /dev/null".format(
					osc.shellQuote, sig.path.shellQuote, wav.shellQuote, sampleRate, numOutputs);
				status = if(render) { cmd.systemCmd } { 0 };
				if(status != 0) { Error("scsynth NRT failed (%) for %".format(status, tag)).throw };
				File.delete(osc);
				if(render) { jobs.add((tag: tag, signal: sig.name, setting: setting, nrt: wav)) };
			}
		};

		File.use(metaDir +/+ def.name.asString ++ ".json", "w") { |f|
			f.write(json.((
				name: def.name,
				source: path,
				scsyndef: defDir +/+ def.name.asString ++ ".scsyndef",
				numOutputs: numOutputs,
				sampleRate: sampleRate,
				specs: specs.collect { |s| s = s.asSpec; (min: s.minval, max: s.maxval, warp: s.warp.asSpecifier, default: s.default) },
				jobs: jobs
			)));
		};
		"batch: % (% renders)".format(def.name, jobs.size).postln;
	};

	files.do { |path|
		var run = {
			var result = path.load;
			var defs = if(result.isKindOf(SynthDef)) { [result] } { result };
			if(defs.isKindOf(SequenceableCollection).not or: { defs.any { |d| d.isKindOf(SynthDef).not } }) {
				Error("% does not evaluate to a SynthDef or an Array of SynthDefs".format(path)).throw
			};
			defs.do { |def| process.(path, def) };
		};
		if(tolerant) {
			try { run.value } { |err|
				File.use(metaDir +/+ path.basename.splitext[0] ++ ".sclang_error", "w") { |f| f.write(err.errorString) };
				"batch: % FAILED: %".format(path.basename, err.errorString).postln;
			}
		} { run.value }
	};
	"batch: done".postln;
	0.exit;
} { |err|
	err.reportError;
	1.exit;
};
)
