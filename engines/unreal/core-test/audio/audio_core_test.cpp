// SPDX-License-Identifier: MIT
// Portable AUD1/Java PCM parity checks. Run from the repo root, or pass the fixture directory.
#include "DaedalusAudioCore.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <sstream>
#include <stdexcept>

using namespace daedalus::audio;
static int Passed = 0, Total = 0;

static void Check(const std::string& Name, bool Good)
{
	++Total;
	if (Good) ++Passed;
	else std::cerr << "FAIL " << Name << '\n';
}

static std::string Read(const std::string& File)
{
	std::ifstream Input(File, std::ios::binary);
	if (!Input) throw std::runtime_error("cannot read fixture " + File);
	return std::string(std::istreambuf_iterator<char>(Input), std::istreambuf_iterator<char>());
}

static std::string Replace(std::string Text, const std::string& Before, const std::string& After)
{
	const std::size_t At = Text.find(Before);
	if (At == std::string::npos) throw std::runtime_error("test replacement missing " + Before);
	Text.replace(At, Before.size(), After);
	return Text;
}

static Design Sentinel()
{
	Design D;
	D.MusicCue = "KEEP";
	D.Layers.push_back({"previous", 0.25, 6000, 0.1});
	D.Call.BaseHz = 777;
	return D;
}

static void Reject(const std::string& Name, const std::string& Wire)
{
	Design D = Sentinel();
	std::string Error;
	Check(Name, !DecodeAud1(Wire, D, Error) && !Error.empty() && D.MusicCue == "KEEP"
		&& D.Layers.size() == 1 && D.Layers[0].Id == "previous" && D.Call.BaseHz == 777);
}

static std::uint64_t Hash(const std::string& Bytes)
{
	std::uint64_t Result = UINT64_C(0xcbf29ce484222325);
	for (unsigned char Byte : Bytes) { Result ^= Byte; Result *= UINT64_C(0x100000001b3); }
	return Result;
}

static std::string PcmBytes(const std::vector<std::int16_t>& Samples)
{
	std::string Bytes;
	Bytes.reserve(Samples.size() * 2);
	for (std::int16_t Sample : Samples)
	{
		const auto Bits = static_cast<std::uint16_t>(Sample);
		Bytes.push_back(static_cast<char>(Bits & 255));
		Bytes.push_back(static_cast<char>(Bits >> 8));
	}
	return Bytes;
}

static void ParserTests(const std::string& Good)
{
	Design D;
	std::string Error = "old error";
	Check("contract forest/canid fixture", DecodeAud1(Good, D, Error) && Error.empty() && D.MusicCue == "FIELD"
		&& D.Layers.size() == 4 && D.Layers[0].Id == "birds_day" && D.Layers[0].Gain == 0.421
		&& D.Layers[3].Id == "wind" && D.Call.BaseHz == 300 && D.Call.PulseMs == 223 && D.Call.Sweep == -0.4);
	Reject("empty body atomic refusal", "");
	Reject("unknown AUD version", Replace(Good, "AUD 1", "AUD 2"));
	Reject("wrong header", Replace(Good, "AUD 1", "OTHER 1"));
	Reject("leading empty line", "\n" + Good);
	Reject("duplicate header", Replace(Good, "jukebox FIELD", "AUD 1\njukebox FIELD"));
	Reject("missing jukebox", Replace(Good, "jukebox FIELD\n", ""));
	Reject("unknown music cue", Replace(Good, "jukebox FIELD", "jukebox CUSTOM"));
	Reject("duplicate jukebox", Replace(Good, "jukebox FIELD", "jukebox FIELD\njukebox TOWN"));
	Reject("missing end", Replace(Good, "end\n", ""));
	Reject("nonempty data after end", Good + "junk\n");
	Reject("unknown record", Replace(Good, "end\n", "herb mint\nend\n"));
	Reject("layer after PCS", Replace(Good, "end\n", "layer zebra 0.001 3000.000 0.000\nend\n"));
	Reject("duplicate PCS", Replace(Good, "end\n", "PCS 1 hz=300.000 sweep=-0.400 harm=1 bright=0.000 pulses=1 pulse_ms=223 gap_ms=0 vib_hz=3.000 vib_st=0.000 breath=0.000\nend\n"));
	Reject("early end", Replace(Good, "layer birds_day", "end\nlayer birds_day"));
	Reject("CRLF refused", Replace(Good, "AUD 1\n", "AUD 1\r\n"));
	Reject("tab refused", Replace(Good, "jukebox FIELD", "jukebox\tFIELD"));
	Reject("double spaces refused", Replace(Good, "jukebox FIELD", "jukebox  FIELD"));
	Reject("trailing space refused", Replace(Good, "jukebox FIELD", "jukebox FIELD "));
	Reject("internal empty line refused", Replace(Good, "jukebox FIELD\n", "jukebox FIELD\n\n"));
	Reject("embedded NUL refused", Good + std::string(1, '\0'));
	Reject("non-ASCII refused", Good + std::string(1, static_cast<char>(0xff)));
	Reject("comma locale refused", Replace(Good, "0.421", "0,421"));
	Reject("scientific notation refused", Replace(Good, "hz=300.000", "hz=3e2"));
	Reject("NaN refused", Replace(Good, "hz=300.000", "hz=NaN"));
	Reject("infinity refused", Replace(Good, "hz=300.000", "hz=inf"));
	Reject("hex number refused", Replace(Good, "hz=300.000", "hz=0x12c"));
	Reject("Java suffix refused", Replace(Good, "hz=300.000", "hz=300.000d"));
	Reject("too few decimals refused", Replace(Good, "hz=300.000", "hz=300.0"));
	Reject("too many decimals refused", Replace(Good, "hz=300.000", "hz=300.0000"));
	Reject("plus prefix refused", Replace(Good, "hz=300.000", "hz=+300.000"));
	Reject("fractional integer refused", Replace(Good, "harm=1", "harm=1.000"));
	Reject("leading integer zero refused", Replace(Good, "harm=1", "harm=01"));
	Reject("leading fixed zero refused", Replace(Good, "hz=300.000", "hz=0300.000"));
	Reject("wrong PCS key refused", Replace(Good, "hz=300.000", "freq=300.000"));
	Reject("same-length wrong PCS key refused", Replace(Good, "hz=300.000", "xx=300.000"));
	Reject("PCS reordered keys refused", Replace(Good, "hz=300.000 sweep=-0.400", "sweep=-0.400 hz=300.000"));
	Reject("missing PCS key refused", Replace(Good, " breath=0.000", ""));
	Reject("extra PCS key refused", Replace(Good, "breath=0.000", "breath=0.000 rate=22050"));
	Reject("unsupported PCS version", Replace(Good, "PCS 1", "PCS 2"));
	Reject("duplicate layer id", Replace(Good, "layer leaves", "layer birds_day"));
	Reject("unsorted layer ids", Replace(Good, "layer birds_day", "layer zebra"));
	Reject("invalid identifier", Replace(Good, "layer birds_day", "layer birds@day"));
	Reject("oversized identifier", Replace(Good, "layer birds_day", "layer " + std::string(MaxId + 1, 'a')));
	Reject("oversized line", Replace(Good, "jukebox FIELD", std::string(MaxLine + 1, 'a')));
	Reject("oversized integer", Replace(Good, "harm=1", "harm=" + std::string(100, '9')));
	Reject("oversized fixed integer part", Replace(Good, "hz=300.000", "hz=" + std::string(100, '9') + ".000"));

	struct Outside { const char* Before; const char* Low; const char* High; };
	const Outside Bounds[] = {
		{"hz=300.000", "hz=69.999", "hz=5200.001"}, {"sweep=-0.400", "sweep=-1.001", "sweep=1.001"},
		{"harm=1", "harm=0", "harm=9"}, {"bright=0.000", "bright=-0.001", "bright=1.001"},
		{"pulses=1", "pulses=0", "pulses=9"}, {"pulse_ms=223", "pulse_ms=0", "pulse_ms=1001"},
		{"gap_ms=0", "gap_ms=-1", "gap_ms=231"}, {"vib_hz=3.000", "vib_hz=2.999", "vib_hz=12.001"},
		{"vib_st=0.000", "vib_st=-0.001", "vib_st=0.801"}, {"breath=0.000", "breath=-0.001", "breath=0.801"}
	};
	for (const Outside& B : Bounds)
	{
		Reject(std::string("PCS lower bound ") + B.Before, Replace(Good, B.Before, B.Low));
		Reject(std::string("PCS upper bound ") + B.Before, Replace(Good, B.Before, B.High));
	}
	for (const char* Bad : {"-0.001", "1.001"})
	{
		Reject(std::string("layer gain ") + Bad, Replace(Good, "birds_day 0.421", std::string("birds_day ") + Bad));
		Reject(std::string("layer density ") + Bad, Replace(Good, "18000.000 1.000", std::string("18000.000 ") + Bad));
	}
	for (const char* Bad : {"2999.999", "18000.001"})
		Reject(std::string("lowpass ") + Bad, Replace(Good, "birds_day 0.421 18000.000", std::string("birds_day 0.421 ") + Bad));

	const std::string Pcs = Good.substr(Good.find("PCS 1"));
	std::string Layers = "AUD 1\njukebox FIELD\n";
	for (std::size_t I = 0; I < MaxLayers; ++I)
		Layers += "layer L" + std::to_string(10 + I) + " 0.001 3000.000 0.000\n";
	Check("16 layers accepted", DecodeAud1(Layers + Pcs, D, Error) && D.Layers.size() == MaxLayers);
	Reject("17 layers refused", Layers + "layer L99 0.001 3000.000 0.000\n" + Pcs);
	Check("64-character ASCII id accepted", DecodeAud1("AUD 1\njukebox FIELD\nlayer " + std::string(MaxId, 'a') + " 1.000 3000.000 1.000\n" + Pcs, D, Error));
	Check("no layer envelope accepted", DecodeAud1("AUD 1\njukebox FIELD\n" + Pcs, D, Error) && D.Layers.empty());
	Check("terminal empty lines accepted", DecodeAud1(Good + "\n\n", D, Error));
	Check("end without terminal LF accepted", DecodeAud1(Good.substr(0, Good.size() - 1), D, Error));
	Check("4096-byte input accepted", DecodeAud1(Good + std::string(MaxBody - Good.size(), '\n'), D, Error));
	Reject("4097-byte body refused", Good + std::string(MaxBody + 1 - Good.size(), '\n'));
	Check("rounded gain sum is not falsely capped at .900", DecodeAud1("AUD 1\njukebox FIELD\nlayer a 0.451 18000.000 1.000\nlayer b 0.450 18000.000 1.000\n" + Pcs, D, Error));
	for (const char* Cue : {"FIELD", "TOWN", "CASTLE", "CAVE", "BATTLE", "BOSS", "VICTORY", "DEFEAT", "INN"})
		Check(std::string("cue ") + Cue, DecodeAud1(Replace(Good, "jukebox FIELD", std::string("jukebox ") + Cue), D, Error));
}

static void TransportTests()
{
	BoundedBody Body;
	Check("zero-length response chunk", Body.Append(nullptr, 0) && Body.Body().empty() && !Body.Failed());
	const auto Capacity = Body.Body().capacity();
	Check("oversized chunk refused before allocation", !Body.Append("x", std::numeric_limits<std::size_t>::max())
		&& Body.Failed() && Body.Body().empty() && Body.Body().capacity() == Capacity);
	Check("response overflow latches", !Body.Append("ok", 2) && Body.Body().empty());
	Body.Reset();
	const std::string Part(2048, 'a');
	Check("exact response limit accepted", Body.Append(Part.data(), Part.size()) && Body.Append(Part.data(), Part.size()) && Body.Body().size() == MaxBody);
	const auto FullCapacity = Body.Body().capacity();
	Check("cumulative overflow preserves bounded body", !Body.Append("x", 1) && Body.Failed() && Body.Body().size() == MaxBody && Body.Body().capacity() == FullCapacity);
	Body.Reset();
	Check("null nonempty chunk refused", !Body.Append(nullptr, 1) && Body.Failed() && Body.Body().empty());
	Body.Reset();
	Check("reset makes body reusable", Body.Append("AUD", 3) && Body.Body() == "AUD" && !Body.Failed());

	RequestFence Fence;
	std::uint64_t First = 0, Second = 0, Unchanged = 42;
	Check("first request starts", Fence.Begin(First) && First == 1 && Fence.Busy() && Fence.IsCurrent(First));
	Check("one request in flight", !Fence.Begin(Unchanged) && Unchanged == 42 && Fence.Current() == First);
	Check("wrong completion preserves current request", !Fence.Complete(First + 1) && Fence.Busy() && Fence.IsCurrent(First));
	Check("matching completion accepted once", Fence.Complete(First) && !Fence.Busy() && !Fence.Complete(First));
	Check("next generation is monotonic", Fence.Begin(Second) && Second > First);
	Check("stale completion cannot clear new request", !Fence.Complete(First) && Fence.IsCurrent(Second));
	Fence.Invalidate();
	Check("invalidate rejects outstanding request", !Fence.IsCurrent(Second) && !Fence.Complete(Second) && !Fence.Busy() && Fence.Current() > Second);
	Check("request after invalidate has fresh generation", Fence.Begin(First) && First > Second && Fence.IsCurrent(First));
	RequestFence Last(std::numeric_limits<std::uint64_t>::max() - 1);
	Check("last uint64 generation accepted", Last.Begin(First) && First == std::numeric_limits<std::uint64_t>::max() && Last.Complete(First));
	Check("counter cannot wrap or reuse", !Last.Begin(Unchanged) && Unchanged == 42 && !Last.IsCurrent(First));
	Last.Invalidate();
	Check("invalidate after exhaustion stays safe", !Last.Begin(Unchanged) && Last.Current() == std::numeric_limits<std::uint64_t>::max());
}

static void MusicPolicyTests()
{
	CueRoutePolicy Policy;
	std::string ToSend = "UNCHANGED";
	Check("invalid cue cannot start route", !Policy.Offer("ARBITRARY", ToSend) && !Policy.Busy() && ToSend == "UNCHANGED");
	Check("initial cue starts once", Policy.Offer("FIELD", ToSend) && ToSend == "FIELD" && Policy.Busy() && Policy.InFlightCue() == "FIELD");
	ToSend = "UNCHANGED";
	Check("in-flight identical refresh is suppressed", !Policy.Offer("FIELD", ToSend) && Policy.PendingCue().empty() && ToSend == "UNCHANGED");
	Check("different refresh waits behind flight", !Policy.Offer("BATTLE", ToSend) && Policy.InFlightCue() == "FIELD" && Policy.PendingCue() == "BATTLE");
	Check("A-B-A clears stale pending B", !Policy.Offer("FIELD", ToSend) && Policy.PendingCue().empty());
	Check("A-B-A emits only A", !Policy.Complete(true, ToSend) && !Policy.Busy() && ToSend == "UNCHANGED");
	Check("successful unchanged cue never restarts", !Policy.Offer("FIELD", ToSend) && !Policy.Busy());
	Check("new cue after success starts", Policy.Offer("TOWN", ToSend) && ToSend == "TOWN");
	ToSend = "UNCHANGED";
	Check("first pending value stores no second flight", !Policy.Offer("BATTLE", ToSend) && Policy.PendingCue() == "BATTLE");
	Check("only latest pending value retained", !Policy.Offer("BOSS", ToSend) && Policy.PendingCue() == "BOSS");
	Check("invalid pending cue preserves latest", !Policy.Offer("ARBITRARY", ToSend) && Policy.PendingCue() == "BOSS");
	Check("completion starts latest pending value", Policy.Complete(true, ToSend) && ToSend == "BOSS" && Policy.InFlightCue() == "BOSS" && Policy.PendingCue().empty());
	ToSend = "UNCHANGED";
	Check("failure never auto-retries same cue", !Policy.Complete(false, ToSend) && !Policy.Busy() && ToSend == "UNCHANGED");
	Check("explicit refresh may retry failed cue", Policy.Offer("BOSS", ToSend) && ToSend == "BOSS");
	ToSend = "UNCHANGED";
	Check("pending different cue survives flight failure", !Policy.Offer("DEFEAT", ToSend) && Policy.Complete(false, ToSend) && ToSend == "DEFEAT" && Policy.InFlightCue() == "DEFEAT");
	Check("same cue refresh clears pending even before failure", !Policy.Offer("VICTORY", ToSend) && !Policy.Offer("DEFEAT", ToSend) && Policy.PendingCue().empty());
	ToSend = "UNCHANGED";
	Check("failure after A-B-A still has no automatic retry", !Policy.Complete(false, ToSend) && !Policy.Busy() && ToSend == "UNCHANGED");
	Check("idle completion ignored", !Policy.Complete(true, ToSend) && ToSend == "UNCHANGED");
	Check("route can restart explicitly after failure", Policy.Offer("DEFEAT", ToSend));
	Policy.Offer("INN", ToSend);
	Policy.Reset();
	Check("reset invalidates flight and pending", !Policy.Busy() && Policy.PendingCue().empty() && Policy.InFlightCue().empty());
	Check("reset permits current cue explicitly", Policy.Offer("DEFEAT", ToSend) && ToSend == "DEFEAT");
}

static void RenderBoundsTests()
{
	std::string Error;
	std::vector<std::int16_t> Pcm{1234};
	CallSpec Maximum{70, -1, 8, 1, 8, 1000, 230, 12, 0.8, 0.8};
	Check("maximum contractual render stays in budget", RenderCall(Maximum, 0, Pcm, Error) && Pcm.size() == MaxSamples);
	CallSpec Minimum{70, -1, 1, 0, 1, 1, 0, 3, 0, 0};
	Check("minimum render has 22 samples", RenderCall(Minimum, 0, Pcm, Error) && Pcm.size() == 22);
	const auto Small = Pcm;
	for (double Invalid : {0.0, 5201.0, std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity()})
	{
		CallSpec Bad = Minimum; Bad.BaseHz = Invalid;
		Check("invalid direct-render frequency refused atomically", !RenderCall(Bad, 0, Pcm, Error) && !Error.empty() && Pcm == Small);
	}
	for (int Invalid : {-1, 0, 1001, std::numeric_limits<int>::max()})
	{
		CallSpec Bad = Minimum; Bad.PulseMs = Invalid;
		Check("invalid direct-render duration refused before allocation", !RenderCall(Bad, 0, Pcm, Error) && Pcm == Small);
	}
	CallSpec Bad = Maximum; Bad.Pulses = std::numeric_limits<int>::max();
	Check("invalid pulse count cannot overflow allocation math", !RenderCall(Bad, 0, Pcm, Error) && Pcm == Small);
	Bad = Maximum; Bad.GapMs = std::numeric_limits<int>::max();
	Check("invalid gap cannot overflow allocation math", !RenderCall(Bad, 0, Pcm, Error) && Pcm == Small);
	std::uint64_t Seed = 123;
	for (const std::string& Hex : {std::string(), std::string("0"), std::string("zz"), std::string("0x00"), std::string(" 00"), std::string(130, 'a')})
		Check("invalid genome leaves seed unchanged", !GenomeSeed(Hex, Seed, Error) && Seed == 123);
	std::uint64_t Upper = 0, Lower = 1;
	Check("genome hex case preserves decoded-byte seed", GenomeSeed("FFAB", Upper, Error) && GenomeSeed("ffab", Lower, Error) && Upper == Lower);
	Check("maximum genome length accepted", GenomeSeed(std::string(128, 'f'), Seed, Error));
}

static void JavaParity(const std::string& Directory, const std::string& Name)
{
	std::istringstream Metadata(Read(Directory + "/" + Name + ".txt"));
	std::string Line, Genome, Pcs;
	std::uint64_t Seed = 0, Checksum = 0;
	std::size_t Count = 0;
	int Rate = 0;
	std::vector<std::uint64_t> Random;
	std::vector<std::pair<std::size_t, int>> Selected;
	std::getline(Metadata, Line);
	if (Line != "JAVA_PCM 1") throw std::runtime_error("bad Java fixture metadata");
	while (std::getline(Metadata, Line))
	{
		std::istringstream Fields(Line);
		std::string Key; Fields >> Key;
		if (Key == "genome") Fields >> Genome;
		else if (Key == "seed") Fields >> std::hex >> Seed;
		else if (Key == "rng") { std::uint64_t Value; while (Fields >> std::hex >> Value) Random.push_back(Value); }
		else if (Key == "PCS") Pcs = Line;
		else if (Key == "sample_rate") Fields >> Rate;
		else if (Key == "samples") Fields >> Count;
		else if (Key == "checksum") Fields >> std::hex >> Checksum;
		else if (Key == "selected")
		{
			std::string Pair;
			while (Fields >> Pair)
			{
				const std::size_t Colon = Pair.find(':');
				Selected.emplace_back(static_cast<std::size_t>(std::stoull(Pair.substr(0, Colon))), std::stoi(Pair.substr(Colon + 1)));
			}
		}
	}
	const std::string Prefix = "Java " + Name + ": ";
	std::uint64_t NativeSeed = 0;
	std::string Error;
	Check(Prefix + "decoded genome FNV64 parity", GenomeSeed(Genome, NativeSeed, Error) && NativeSeed == Seed);
	SplitMix64 Generator(Seed), DoubleGenerator(Seed);
	bool IntegerParity = Random.size() == 8, DoubleParity = Random.size() == 8;
	for (const std::uint64_t Expected : Random)
	{
		IntegerParity = IntegerParity && Generator.NextLong() == Expected;
		const double Value = DoubleGenerator.NextDouble();
		DoubleParity = DoubleParity && Value == static_cast<double>(Expected >> 11) * 0x1.0p-53 && Value >= 0 && Value < 1;
	}
	Check(Prefix + "SplitMix64 unsigned integer parity", IntegerParity);
	Check(Prefix + "SplitMix64 double parity", DoubleParity);
	Design D;
	if (!DecodeAud1("AUD 1\njukebox FIELD\n" + Pcs + "\nend\n", D, Error)) throw std::runtime_error("invalid Java PCS fixture: " + Error);
	std::vector<std::int16_t> Actual;
	if (!RenderCall(D.Call, Seed, Actual, Error)) throw std::runtime_error("Java fixture render failed: " + Error);
	const std::string Expected = Read(Directory + "/" + Name + ".pcm");
	Check(Prefix + "Java PCM fixture checksum", Hash(Expected) == Checksum);
	Check(Prefix + "canonical fixed sample rate and sample count", Rate == SampleRate && Actual.size() == Count && Expected.size() == Count * 2 && Count <= MaxSamples);
	if (Expected.size() != Actual.size() * 2) return;
	int MaximumDifference = 0, Peak = 0;
	std::size_t Differences = 0;
	for (std::size_t I = 0; I < Actual.size(); ++I)
	{
		const std::uint16_t Bits = static_cast<std::uint16_t>(static_cast<unsigned char>(Expected[I * 2]))
			| static_cast<std::uint16_t>(static_cast<unsigned char>(Expected[I * 2 + 1]) << 8);
		const int JavaSample = Bits < 32768 ? Bits : static_cast<int>(Bits) - 65536;
		const int Difference = std::abs(static_cast<int>(Actual[I]) - JavaSample);
		MaximumDifference = std::max(MaximumDifference, Difference);
		Differences += Difference != 0;
		Peak = std::max(Peak, std::abs(static_cast<int>(Actual[I])));
	}
	// std::sin/pow and Java Math may differ at a quantization boundary. Compare every sample, allowing one LSB.
	Check(Prefix + "every PCM sample agrees within one LSB", MaximumDifference <= 1);
	Check(Prefix + "nonzero PCM within canonical .8 peak headroom", Peak > 1000 && Peak <= 26214);
	bool SelectedParity = Selected.size() == 7;
	for (const auto& Pair : Selected)
		SelectedParity = SelectedParity && Pair.first < Actual.size() && std::abs(static_cast<int>(Actual[Pair.first]) - Pair.second) <= 1;
	Check(Prefix + "selected Java samples agree", SelectedParity);
	const std::size_t PulseN = static_cast<std::size_t>(D.Call.PulseMs) * SampleRate / 1000;
	const std::size_t GapN = static_cast<std::size_t>(D.Call.GapMs) * SampleRate / 1000;
	bool SilentGaps = true;
	for (int Pulse = 0; Pulse < D.Call.Pulses - 1; ++Pulse)
	{
		const std::size_t Start = static_cast<std::size_t>(Pulse) * (PulseN + GapN) + PulseN;
		for (std::size_t I = Start; I < Start + GapN; ++I) SilentGaps = SilentGaps && Actual[I] == 0;
	}
	Check(Prefix + "all inter-pulse gap samples silent", SilentGaps);
	std::vector<std::int16_t> Again;
	Check(Prefix + "same seed produces identical PCM bytes/checksum", RenderCall(D.Call, Seed, Again, Error) && PcmBytes(Again) == PcmBytes(Actual) && Hash(PcmBytes(Again)) == Hash(PcmBytes(Actual)));
	std::cout << Prefix << "max difference " << MaximumDifference << ", " << Differences << " differing samples; native checksum "
		<< std::hex << Hash(PcmBytes(Actual)) << std::dec << '\n';
}

int main(int Argc, char** Argv)
{
	try
	{
		const std::string Directory = Argc > 1 ? Argv[1] : "engines/unreal/core-test/audio/fixtures";
		ParserTests(Read(Directory + "/forest-canid.aud"));
		TransportTests();
		MusicPolicyTests();
		RenderBoundsTests();
		for (const char* Name : {"canid-zero", "goat-varied", "songbird-max", "bovine-max"}) JavaParity(Directory, Name);
	}
	catch (const std::exception& Error)
	{
		std::cerr << "ERROR " << Error.what() << '\n';
		return 2;
	}
	std::cout << Passed << '/' << Total << " audio core checks passed\n";
	return Passed == Total ? 0 : 1;
}
