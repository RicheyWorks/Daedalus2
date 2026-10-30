// SPDX-License-Identifier: MIT
// Portable typed-capability checks only: no browser, native launcher, files, notes or app process.
#include "DaedalusLocalAppCore.h"
#include <cstdio>
#include <limits>
#include <string>
#include <vector>

using namespace daedalus::localapp;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK)
{
	++Total; Passed += OK ? 1 : 0;
	std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name);
}
static std::string Link(Kind App, const std::string& Port, const std::string& Token)
{
	return "http://127.0.0.1:" + Port + std::string(CompanionPath(App)) + "#token=" + Token;
}

int main()
{
	const std::string Token = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopq"; // synthetic, 43 characters
	const std::string Image = Link(Kind::ImageOptimizer, "49152", Token);
	const std::string Study = Link(Kind::Synapse, "49152", Token);
	Check("image optimizer accepts its typed capability", IsValidCompanionLink(Image, Kind::ImageOptimizer));
	Check("synapse accepts its typed capability", IsValidCompanionLink(Study, Kind::Synapse));
	Check("image optimizer rejects synapse capability", !IsValidCompanionLink(Study, Kind::ImageOptimizer));
	Check("synapse rejects image optimizer capability", !IsValidCompanionLink(Image, Kind::Synapse));
	Check("changed object app rejects a previously accepted capability", IsValidCompanionLink(Image, Kind::ImageOptimizer)
		&& !IsValidCompanionLink(Image, Kind::Synapse));
	Check("unknown app enum fails closed", !IsValidCompanionLink(Image, static_cast<Kind>(255)));
	Check("negative app enum fails closed", !IsValidCompanionLink(Study, static_cast<Kind>(-1)));
	Check("no path for unsupported application", CompanionPath(static_cast<Kind>(255)).empty());
	Check("correct display names are independent of capability", std::string(AppName(Kind::ImageOptimizer)) == "Image Optimizer"
		&& std::string(AppName(Kind::Synapse)) == "Synapse");
	Check("typed utility rejects legacy photo link", !IsValidCompanionLink("http://127.0.0.1:49152/#token=" + Token, Kind::Synapse));
	Check("legacy photo policy rejects typed utility link", !daedalus::photopdf::IsValidChooserLink(Image)
		&& !daedalus::photopdf::IsValidChooserLink(Study));
	Check("legacy minimum token contract remains accepted", daedalus::photopdf::IsValidChooserLink(
		"http://127.0.0.1:49152/#token=" + std::string(32, 'a')));
	Check("legacy maximum token contract remains accepted", daedalus::photopdf::IsValidChooserLink(
		"http://127.0.0.1:49152/#token=" + std::string(128, 'a')));
	Check("typed links require exactly 43 chars", !IsValidCompanionLink(Link(Kind::Synapse, "49152", std::string(42, 'a')), Kind::Synapse)
		&& !IsValidCompanionLink(Link(Kind::Synapse, "49152", std::string(44, 'a')), Kind::Synapse));
	Check("typed links reject legacy token length bounds", !IsValidCompanionLink(Link(Kind::ImageOptimizer, "49152", std::string(32, 'a')), Kind::ImageOptimizer)
		&& !IsValidCompanionLink(Link(Kind::ImageOptimizer, "49152", std::string(128, 'a')), Kind::ImageOptimizer));
	Check("token accepts URL-safe alphabet", IsValidCompanionLink(Link(Kind::Synapse, "49152", std::string(40, '_') + "-Az"), Kind::Synapse));
	Check("minimum canonical port accepted for both apps", IsValidCompanionLink(Link(Kind::Synapse, "1024", Token), Kind::Synapse)
		&& IsValidCompanionLink(Link(Kind::ImageOptimizer, "1024", Token), Kind::ImageOptimizer));
	Check("maximum canonical port accepted for both apps", IsValidCompanionLink(Link(Kind::Synapse, "65535", Token), Kind::Synapse)
		&& IsValidCompanionLink(Link(Kind::ImageOptimizer, "65535", Token), Kind::ImageOptimizer));
	Check("maximum image link fits bounded policy", Link(Kind::ImageOptimizer, "65535", Token).size() == MaxLinkLength);
	Check("empty input refused", !IsValidCompanionLink("", Kind::Synapse));
	Check("oversized input refused", !IsValidCompanionLink(std::string(1000000, 'a'), Kind::ImageOptimizer));
	Check("truncated authority refused", !IsValidCompanionLink("http://127.0.0.1:", Kind::Synapse));
	Check("truncated path refused", !IsValidCompanionLink("http://127.0.0.1:49152/realm/synapse", Kind::Synapse));
	Check("missing token fragment refused", !IsValidCompanionLink("http://127.0.0.1:49152/realm/synapse/", Kind::Synapse));
	Check("missing token refused", !IsValidCompanionLink("http://127.0.0.1:49152/realm/synapse/#token=", Kind::Synapse));

	const std::vector<std::string> BadAuthorities = {
		"https://127.0.0.1:49152", "HTTP://127.0.0.1:49152", "http://localhost:49152", "http://[::1]:49152",
		"http://127.1:49152", "http://2130706433:49152", "http://0177.0.0.1:49152", "http://0x7f000001:49152",
		"http://127.0.0.2:49152", "http://127.0.0.1.:49152", "http://127%2e0%2e0%2e1:49152",
		"http://0.0.0.0:49152", "http://example.com:49152", "http://127.0.0.1.evil.example:49152",
		"http://127.0.0.1:49152@evil.example", "http://user:password@127.0.0.1:49152",
		"file://127.0.0.1:49152", "http:\\\\127.0.0.1:49152",
	};
	bool AuthoritiesRefused = true;
	for (const auto& Authority : BadAuthorities)
		for (Kind App : {Kind::ImageOptimizer, Kind::Synapse})
			AuthoritiesRefused = AuthoritiesRefused && !IsValidCompanionLink(Authority + std::string(CompanionPath(App)) + "#token=" + Token, App);
	Check("both typed apps reject host aliases, remote hosts, userinfo and schemes", AuthoritiesRefused);
	const std::vector<std::string> BadPorts = { "", "0", "80", "1023", "65536", "99999", "100000", "99999999999999999999",
		"049152", "001024", "+49152", "-49152", "49152.0", "49152 ", "49152:80", "%34%39%31%35%32" };
	bool PortsRefused = true;
	for (const auto& Port : BadPorts) for (Kind App : {Kind::ImageOptimizer, Kind::Synapse})
		PortsRefused = PortsRefused && !IsValidCompanionLink(Link(App, Port, Token), App);
	Check("both typed apps reject privileged, ambiguous and overflowing ports", PortsRefused);
	bool AllNumericPorts = true;
	for (int Port = 0; Port <= 70000; ++Port) for (Kind App : {Kind::ImageOptimizer, Kind::Synapse})
		AllNumericPorts = AllNumericPorts && (IsValidCompanionLink(Link(App, std::to_string(Port), Token), App) == (Port >= 1024 && Port <= 65535));
	Check("both typed apps classify every numeric port 0 through 70000", AllNumericPorts);
	const std::vector<std::string> BadPaths = {
		"/realm/Synapse/", "/realm/synapse", "/realm/synapse//", "//realm/synapse/", "/realm/./synapse/",
		"/realm/../synapse/", "/realm/%73ynapse/", "/realm/synapse/%2e%2e/", "/realm/synapse/extra/",
		"/realm/synapse/?q=1", "/realm/synapse/\\", "/realm/empty/", "/realm/synapse/#token=extra",
	};
	bool PathsRefused = true;
	for (const auto& Path : BadPaths)
		PathsRefused = PathsRefused && !IsValidCompanionLink("http://127.0.0.1:49152" + Path + "#token=" + Token, Kind::Synapse);
	Check("reject encoded, ambiguous, wrong-case and extra paths", PathsRefused);
	Check("reject query-token form", !IsValidCompanionLink("http://127.0.0.1:49152/realm/synapse/?token=" + Token, Kind::Synapse));
	Check("reject extra fragment", !IsValidCompanionLink(Study + "#other", Kind::Synapse));
	Check("reject extra query", !IsValidCompanionLink(Study + "?other=1", Kind::Synapse));
	Check("reject extra token parameter", !IsValidCompanionLink(Study + "&other=1", Kind::Synapse));
	Check("reject leading whitespace", !IsValidCompanionLink(" " + Study, Kind::Synapse));
	Check("reject trailing whitespace", !IsValidCompanionLink(Study + " ", Kind::Synapse));
	Check("reject newline injection", !IsValidCompanionLink(Study + "\r\nhttp://example.com", Kind::Synapse));
	Check("reject embedded authority NUL", !IsValidCompanionLink("http://127.0.0.1:" + std::string(1, '\0') + "49152/realm/synapse/#token=" + Token, Kind::Synapse));
	Check("reject embedded token NUL preserving string length", !IsValidCompanionLink(Link(Kind::Synapse, "49152", std::string(42, 'a') + std::string(1, '\0')), Kind::Synapse));
	Check("reject UTF-8 token", !IsValidCompanionLink(Link(Kind::Synapse, "49152", std::string(41, 'a') + "\xc3\xa9"), Kind::Synapse));
	bool BytesClassified = true;
	for (int Byte = 0; Byte < 256; ++Byte)
	{
		const bool Safe = (Byte >= 'A' && Byte <= 'Z') || (Byte >= 'a' && Byte <= 'z') || (Byte >= '0' && Byte <= '9') || Byte == '_' || Byte == '-';
		for (Kind App : {Kind::ImageOptimizer, Kind::Synapse})
			BytesClassified = BytesClassified && (IsValidCompanionLink(Link(App, "49152", std::string(43, static_cast<char>(Byte))), App) == Safe);
	}
	Check("both typed apps classify all 256 token byte values", BytesClassified);
	bool EveryContext = true;
	for (int Mask = 0; Mask < 32; ++Mask)
		EveryContext = EveryContext && (daedalus::photopdf::CanUseChooser((Mask & 1) != 0, (Mask & 2) != 0,
			(Mask & 4) != 0, (Mask & 8) != 0, (Mask & 16) != 0) == (Mask == 29));
	Check("shared context permits only nearby local player in game world", EveryContext);
	daedalus::photopdf::LaunchGate Gate;
	Check("shared rate gate permits first deliberate attempt", Gate.TryBegin(100.0));
	Check("valid repeated pairing does not bypass existing gate", IsValidCompanionLink(Study, Kind::Synapse) && !Gate.TryBegin(100.5));
	Check("wrong-app refusal does not authorize immediate repeated launch", !IsValidCompanionLink(Study, Kind::ImageOptimizer) && !Gate.TryBegin(101.0));
	Check("later deliberate retry permitted at shared boundary", Gate.TryBegin(102.0));
	Check("failed attempt still consumes shared rate limit", !Gate.TryBegin(103.9));
	Check("clock rollback still refused", !Gate.TryBegin(101.0));
	Check("nonfinite clock still refused", !Gate.TryBegin(std::numeric_limits<double>::infinity()));
	Check("valid attempt after invalid clocks permitted", Gate.TryBegin(104.0));

	// Exercise the same transition callback used by SetApplication, including the review regression:
	// image -> synapse -> image, with no intervening Use, must not resurrect the earlier capability.
	Kind Selected = Kind::ImageOptimizer;
	std::string Pairing = Image;
	int ClearCalls = 0;
	auto Forget = [&Pairing, &ClearCalls]() { Pairing.clear(); ++ClearCalls; };
	daedalus::photopdf::LaunchGate SelectionGate;
	Check("paired selection can consume a deliberate launch attempt", SelectionGate.TryBegin(200.0));
	Check("same-value preset write changes nothing", !ChangeApplication(Selected, Kind::ImageOptimizer, Forget)
		&& Pairing == Image && ClearCalls == 0);
	Check("actual preset change invokes forgetting once", ChangeApplication(Selected, Kind::Synapse, Forget)
		&& Selected == Kind::Synapse && Pairing.empty() && ClearCalls == 1);
	Check("changed preset cannot immediately relaunch", !SelectionGate.TryBegin(200.5));
	Check("returning to original app clears again", ChangeApplication(Selected, Kind::ImageOptimizer, Forget)
		&& Selected == Kind::ImageOptimizer && ClearCalls == 2);
	Check("away-and-back without use cannot resurrect earlier capability", Pairing.empty());
	Check("away-and-back cannot reset launch cooldown", !SelectionGate.TryBegin(201.0));
	Pairing = Image;
	Check("explicit fresh pairing can validate original app again", IsValidCompanionLink(Pairing, Selected));
	Check("fresh pairing still respects same cooldown", !SelectionGate.TryBegin(201.9));
	Check("later fresh-paired attempt allowed at original boundary", SelectionGate.TryBegin(202.0));
	Check("unsupported native preset clears pairing and fails closed", ChangeApplication(Selected, static_cast<Kind>(255), Forget)
		&& Pairing.empty() && !IsValidCompanionLink(Image, Selected) && ClearCalls == 3);
	Check("return from unsupported preset needs fresh pairing", ChangeApplication(Selected, Kind::ImageOptimizer, Forget)
		&& Pairing.empty() && ClearCalls == 4);
	std::printf("Local app policy: %d/%d passed; no browser or app process was launched.\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
