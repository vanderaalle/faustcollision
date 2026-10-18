// Headless sclang batch, run once per build:
//   sclang translator/batch.scd <root>
// For every defs/*.scd and tests/cases/*.scd (each file evaluates to a SynthDef):
//   build/synthdefs/<name>.scsyndef   the binary the translator parses
//   build/meta/<name>.json            specs, output count, render jobs
//   build/nrt/<name>/<job>.wav        scsynth NRT render of each test signal
// Render settings per def: all controls at default, then each spec'd control at min and max.
(
var root = thisProcess.argv[0] ?? { "usage: sclang batch.scd <root>".error; 1.exit };
var sampleRate = 48000;
var defDir = root +/+ "build/synthdefs/";
var metaDir = root +/+ "build/meta/";
var nrtRoot = root +/+ "build/nrt/";
var json, settingTag;

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
	var files = (root +/+ "defs/*.scd").pathMatch ++ (root +/+ "tests/cases/*.scd").pathMatch;
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

	files.do { |path|
		var def = path.load;
		var md, specs, outs, numOutputs, settings, jobs, names, defaults, sigs, nrtDir;
		if(def.isKindOf(SynthDef).not) { Error("% does not evaluate to a SynthDef".format(path)).throw };
		md = def.metadata ? ();
		specs = md[\specs] ? ();
		outs = def.children.select { |u| u.isKindOf(AbstractOut) };
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
				status = cmd.systemCmd;
				if(status != 0) { Error("scsynth NRT failed (%) for %".format(status, tag)).throw };
				File.delete(osc);
				jobs.add((tag: tag, signal: sig.name, setting: setting, nrt: wav));
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
	"batch: done".postln;
	0.exit;
} { |err|
	err.reportError;
	1.exit;
};
)
