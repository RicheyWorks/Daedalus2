// SPDX-License-Identifier: MIT
// Pure policy tests: no Unreal, browser launch, service connection, filesystem or real photo data.
#include "DaedalusPhotoPdfCore.h"
#include <cstdio>
#include <limits>
#include <string>
#include <vector>

using namespace daedalus::photopdf;
static int Passed = 0;
static int Total = 0;
static void Check(const char* Name, bool OK)
{
	++Total;
	Passed += OK ? 1 : 0;
	std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name);
}

static std::string Link(const std::string& Port, const std::string& Token)
{
	return "http://127.0.0.1:" + Port + "/#token=" + Token;
}

int main()
{
	// Synthetic tokens only. Never print actual process capability values in tests or CI.
	const std::string Token = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopq";
	const std::string Valid = Link("49152", Token);
	Check("accept exact chooser link and 43-character token", IsValidChooserLink(Valid));
	Check("accept base64url alphabet", IsValidChooserLink(Link("49152", "abc_DEF-0123456789xyzABCDEFGHIJKLMNOPQRSTUVW")));
	Check("accept lower token length bound", IsValidChooserLink(Link("1024", std::string(32, 'a'))));
	Check("accept upper token length and port bound", IsValidChooserLink(Link("65535", std::string(128, 'z'))));
	Check("reject empty link", !IsValidChooserLink(""));
	Check("reject truncated authority", !IsValidChooserLink("http://127.0.0.1:"));
	Check("reject missing token", !IsValidChooserLink("http://127.0.0.1:49152/#token="));
	Check("reject short token", !IsValidChooserLink(Link("49152", std::string(31, 'a'))));
	Check("reject oversized token", !IsValidChooserLink(Link("49152", std::string(129, 'a'))));
	Check("reject very large input", !IsValidChooserLink(std::string(1000000, 'a')));
	Check("reject standard base64 padding", !IsValidChooserLink(Link("49152", Token + "=")));
	Check("reject base64 slash", !IsValidChooserLink(Link("49152", Token + "/")));
	Check("reject base64 plus", !IsValidChooserLink(Link("49152", Token + "+")));

	const std::vector<std::string> BadAuthorities = {
		"https://127.0.0.1:49152", "HTTP://127.0.0.1:49152", "http://localhost:49152",
		"http://[::1]:49152", "http://127.1:49152", "http://2130706433:49152",
		"http://0177.0.0.1:49152", "http://0x7f000001:49152", "http://127.0.0.2:49152",
		"http://0.0.0.0:49152", "http://192.168.1.1:49152", "http://example.com:49152",
		"http://127.0.0.1.evil.example:49152", "http://127.0.0.1:49152@evil.example",
		"http://user:password@127.0.0.1:49152", "http://evil.example@127.0.0.1:49152",
		"http://127.0.0.1.:49152", "http://127%2e0%2e0%2e1:49152",
		"http:\\\\127.0.0.1:49152", "file://127.0.0.1:49152", "javascript:49152",
	};
	bool AllAuthoritiesRefused = true;
	for (const std::string& Authority : BadAuthorities)
		AllAuthoritiesRefused = AllAuthoritiesRefused && !IsValidChooserLink(Authority + "/#token=" + Token);
	Check("reject remote hosts, aliases, userinfo and alternate schemes", AllAuthoritiesRefused);

	const std::vector<std::string> BadPorts = { "0", "1", "80", "1023", "65536", "99999", "100000", "99999999999999999999",
		"049152", "001024", "+49152", "-49152", "49152.0", "49152 ", "%34%39%31%35%32", "", "49152:80" };
	bool AllPortsRefused = true;
	for (const std::string& Port : BadPorts) AllPortsRefused = AllPortsRefused && !IsValidChooserLink(Link(Port, Token));
	Check("reject invalid, privileged, ambiguous and overflowing ports", AllPortsRefused);
	bool ExhaustivePorts = true;
	for (int Port = 0; Port <= 70000; ++Port)
		ExhaustivePorts = ExhaustivePorts && (IsValidChooserLink(Link(std::to_string(Port), Token)) == (Port >= 1024 && Port <= 65535));
	Check("classify every numeric port from zero through 70000", ExhaustivePorts);

	const std::vector<std::string> BadPaths = { "", "/", "/photos#token=", "//evil.example/#token=", "/../#token=",
		"/%2e%2e/#token=", "\\#token=", "/?token=", "/?q=1#token=", "/#TOKEN=", "/#token=token#token=" };
	bool AllPathsRefused = true;
	for (const std::string& Path : BadPaths)
		AllPathsRefused = AllPathsRefused && !IsValidChooserLink("http://127.0.0.1:49152" + Path + Token);
	Check("reject paths, queries, backslashes and extra fragments", AllPathsRefused);
	Check("reject URL with token in query", !IsValidChooserLink("http://127.0.0.1:49152/?token=" + Token));
	Check("reject additional fragment", !IsValidChooserLink(Valid + "#extra"));
	Check("reject additional query", !IsValidChooserLink(Valid + "?key=value"));
	Check("reject percent-encoded token", !IsValidChooserLink(Link("49152", Token + "%41")));
	Check("reject token parameters", !IsValidChooserLink(Valid + "&other=1"));
	Check("reject newline injection", !IsValidChooserLink(Valid + "\r\nhttp://example.com"));
	Check("reject leading whitespace", !IsValidChooserLink(" " + Valid));
	Check("reject trailing whitespace", !IsValidChooserLink(Valid + " "));
	Check("reject Unicode token", !IsValidChooserLink(Valid + "\xc3\xa9"));
	Check("reject embedded NUL with remaining valid text", !IsValidChooserLink(Link("49152", Token + std::string(1, '\0') + "a")));
	Check("reject trailing NUL", !IsValidChooserLink(Valid + std::string(1, '\0')));
	bool EveryByteChecked = true;
	for (int Byte = 0; Byte < 256; ++Byte)
	{
		const char C = static_cast<char>(Byte);
		const bool Safe = (Byte >= 'A' && Byte <= 'Z') || (Byte >= 'a' && Byte <= 'z') || (Byte >= '0' && Byte <= '9') || Byte == '_' || Byte == '-';
		EveryByteChecked = EveryByteChecked && IsValidChooserLink(Link("49152", std::string(32, C))) == Safe;
	}
	Check("reject every non-base64url byte including all control characters", EveryByteChecked);
	bool ExactPrefixOnly = true;
	constexpr std::size_t PrefixLength = 17;
	for (std::size_t At = 0; At < PrefixLength; ++At)
	{
		std::string Changed = Valid;
		Changed[At] = Changed[At] == 'X' ? 'Y' : 'X';
		ExactPrefixOnly = ExactPrefixOnly && !IsValidChooserLink(Changed);
	}
	Check("reject any changed literal scheme or host byte", ExactPrefixOnly);

	Check("allow nearby local player in game world", CanUseChooser(true, false, true, true, true));
	Check("refuse editor-world invocation", !CanUseChooser(false, false, true, true, true));
	Check("refuse dedicated server even if local flag supplied", !CanUseChooser(true, true, true, true, true));
	Check("refuse remote pawn or local AI", !CanUseChooser(true, false, false, true, true));
	Check("refuse another world", !CanUseChooser(true, false, true, false, true));
	Check("refuse direct use outside physical reach", !CanUseChooser(true, false, true, true, false));
	bool EveryContextChecked = true;
	for (int Mask = 0; Mask < 32; ++Mask)
		EveryContextChecked = EveryContextChecked && (CanUseChooser((Mask & 1) != 0, (Mask & 2) != 0,
			(Mask & 4) != 0, (Mask & 8) != 0, (Mask & 16) != 0) == (Mask == 29));
	Check("exactly one of all 32 context combinations permits opening", EveryContextChecked);

	LaunchGate Gate;
	Check("first launch attempt allowed at monotonic zero", Gate.TryBegin(0.0));
	Check("repeat at same instant refused", !Gate.TryBegin(0.0));
	Check("rapid repeat refused", !Gate.TryBegin(1.999));
	Check("next attempt allowed at cooldown boundary", Gate.TryBegin(2.0));
	Check("clock rollback refused", !Gate.TryBegin(1.0));
	Check("failed attempt still consumes cooldown", !Gate.TryBegin(3.0));
	Check("later deliberate interaction allowed", Gate.TryBegin(4.0));
	Check("NaN clock refused", !Gate.TryBegin(std::numeric_limits<double>::quiet_NaN()));
	Check("positive infinity clock refused", !Gate.TryBegin(std::numeric_limits<double>::infinity()));
	Check("negative infinity clock refused", !Gate.TryBegin(-std::numeric_limits<double>::infinity()));
	Check("negative clock refused", !Gate.TryBegin(-1.0));
	Check("invalid clocks did not alter the last attempt", Gate.TryBegin(6.0));
	LaunchGate Fresh;
	Check("fresh gate refuses invalid initial clock", !Fresh.TryBegin(std::numeric_limits<double>::infinity()));
	Check("refused initial clock does not poison fresh gate", Fresh.TryBegin(1000.0));

	std::printf("Photo PDF policy: %d/%d passed; no browser or app process was launched.\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
