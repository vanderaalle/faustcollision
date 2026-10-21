// Census, step 1: dump every core UGen class with its rates and arguments.
//   sclang translator/census.scd <out.json>
// Classification and probe generation happen in translator/census.py.
(
var out = thisProcess.argv[0] ?? { "usage: sclang census.scd <out.json>".error; 1.exit };
var core = Platform.classLibraryDir;
var q = { |s| "\"" ++ s.asString.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ") ++ "\"" };
var rows = UGen.allSubclasses.reject(_.isMetaClass).select { |c| c.filenameSymbol.asString.beginsWith(core) };
rows = rows.sort { |a, b| a.name < b.name }.collect { |c|
	// \new: a scalar-rate class made only with *new (Rand, IRand, ...), when it defines *new itself
	var own = { |r| var m = c.class.findRespondingMethodFor(r);
		m.notNil and: { if(r == \new) { m.ownerClass == c.class } { m.ownerClass != UGen.class } } };
	var rated = [\ar, \kr, \ir, \dr].select(own);
	var rates = if(rated.notEmpty) { rated } { [\new].select(own) };
	var m = rates.notEmpty.if { c.class.findRespondingMethodFor(rates[0]) };
	var args = m !? { m.argNames.drop(1).collect { |a, i| "[%, %]".format(q.(a), q.(m.prototypeFrame[i + 1].asCompileString)) } } ? [];
	"{\"name\": %, \"file\": %, \"superclasses\": [%], \"rates\": [%], \"args\": [%]}".format(
		q.(c.name),
		q.(c.filenameSymbol.asString.drop(core.size + 1)),
		c.superclasses.collect(q).join(", "),
		rates.collect(q).join(", "),
		args.join(", "))
};
File.use(out, "w") { |f| f.write("[\n" ++ rows.join(",\n") ++ "\n]\n") };
"census: % core UGen classes".format(rows.size).postln;
0.exit;
)
