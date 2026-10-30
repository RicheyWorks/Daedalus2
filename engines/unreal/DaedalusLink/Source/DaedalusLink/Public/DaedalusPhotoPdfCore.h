// SPDX-License-Identifier: MIT
#pragma once

// Engine-free policy for the PhotosToPDFPC object. The capability is supplied at runtime by the
// user's local PhotosToPDFPC process. It is not a document path or a remote server address.
#include <cmath>
#include <cstddef>
#include <string_view>

namespace daedalus { namespace photopdf {

constexpr std::size_t MinTokenLength = 32;
constexpr std::size_t MaxTokenLength = 128;
constexpr double LaunchCooldownSeconds = 2.0;

/** Deliberately recognize one grammar, rather than normalize arbitrary browser URLs.
 * http://127.0.0.1:<canonical decimal port 1024..65535>/#token=<base64url token 32..128 chars>
 * Reject encoded characters, credentials, host aliases, paths, queries, whitespace and extra fragments.
 * The service generates 32 random bytes (43 unpadded base64url characters); syntax alone cannot verify
 * a service identity or a token's entropy. Pair only with a link obtained from that user's app.
 */
inline bool IsValidChooserLink(std::string_view Link)
{
	constexpr std::string_view Prefix = "http://127.0.0.1:";
	constexpr std::string_view Fragment = "/#token=";
	constexpr std::size_t MaxLinkLength = Prefix.size() + 5 + Fragment.size() + MaxTokenLength;
	if (Link.size() > MaxLinkLength || Link.substr(0, Prefix.size()) != Prefix) return false;
	std::size_t At = Prefix.size();
	if (At >= Link.size() || Link[At] < '1' || Link[At] > '9') return false;
	unsigned int Port = 0;
	std::size_t Digits = 0;
	while (At < Link.size() && Link[At] >= '0' && Link[At] <= '9')
	{
		if (++Digits > 5) return false;
		Port = Port * 10 + static_cast<unsigned int>(Link[At++] - '0');
	}
	if (Port < 1024 || Port > 65535 || Link.substr(At, Fragment.size()) != Fragment) return false;
	At += Fragment.size();
	const std::size_t TokenLength = Link.size() - At;
	if (TokenLength < MinTokenLength || TokenLength > MaxTokenLength) return false;
	for (; At < Link.size(); ++At)
	{
		const char C = Link[At];
		if (!((C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_' || C == '-'))
			return false;
	}
	return true;
}

/** The actor maps Unreal world/controller checks to this policy. A local AI is not a local player. */
inline bool CanUseChooser(bool GameWorld, bool DedicatedServer, bool LocalPlayer, bool SameWorld, bool InReach)
{
	return GameWorld && !DedicatedServer && LocalPlayer && SameWorld && InReach;
}

/** Record attempts, including failed browser launches, to avoid repeated interaction opening many tabs.
 * Use a monotonic process clock. Pairing/unpairing does not reset this gate.
 */
class LaunchGate
{
public:
	bool TryBegin(double Now)
	{
		if (!std::isfinite(Now) || Now < 0.0) return false;
		if (Attempted && (Now < LastAttempt || Now - LastAttempt < LaunchCooldownSeconds)) return false;
		Attempted = true;
		LastAttempt = Now;
		return true;
	}

private:
	bool Attempted = false;
	double LastAttempt = 0.0;
};

}} // namespace daedalus::photopdf
