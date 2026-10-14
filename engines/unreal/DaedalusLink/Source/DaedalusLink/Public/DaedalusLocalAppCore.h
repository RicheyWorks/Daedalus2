// SPDX-License-Identifier: MIT
#pragma once

#include "DaedalusPhotoPdfCore.h"
#include <string>
#include <string_view>

namespace daedalus { namespace localapp {

enum class Kind { ImageOptimizer, Synapse };
constexpr std::size_t TokenLength = 43;
constexpr std::size_t MaxLinkLength = 95;

/** Commit a preset change only after forgetting its old capability. Returning to the previous
 * preset does not resurrect a pairing. A same-value write preserves pairing. The callback only
 * clears pairing; the separate shared launch gate survives all changes.
 */
template <typename ClearPairingFunction>
inline bool ChangeApplication(Kind& Selected, Kind Next, ClearPairingFunction ClearPairing)
{
	if (Selected == Next) return false;
	ClearPairing();
	Selected = Next;
	return true;
}

inline std::string_view CompanionPath(Kind App)
{
	switch (App)
	{
	case Kind::ImageOptimizer: return "/realm/image-optimizer/";
	case Kind::Synapse: return "/realm/synapse/";
	default: return {};
	}
}

inline const char* AppName(Kind App)
{
	switch (App)
	{
	case Kind::ImageOptimizer: return "Image Optimizer";
	case Kind::Synapse: return "Synapse";
	default: return "Local app";
	}
}

/** Recognize the expected app's one exact typed path, then reuse the existing photo policy for
 * the origin, canonical port and token alphabet. Removing this known literal path is the only
 * transformation; arbitrary/encoded paths are never normalized into an approved URL.
 * New companions require exactly 43 unpadded base64url characters. The legacy photo grammar
 * remains unchanged. Syntax does not establish listener identity or actual token entropy.
 */
inline bool IsValidCompanionLink(std::string_view Link, Kind ExpectedApp)
{
	const std::string_view Path = CompanionPath(ExpectedApp);
	constexpr std::string_view Fragment = "#token=";
	if (Path.empty() || Link.size() > MaxLinkLength) return false;
	// Start beyond http://. The legacy validator checks the complete unchanged authority below.
	const std::size_t PathAt = Link.find('/', 7);
	if (PathAt == std::string_view::npos || Link.substr(PathAt, Path.size()) != Path) return false;
	const std::size_t FragmentAt = PathAt + Path.size();
	if (Link.substr(FragmentAt, Fragment.size()) != Fragment || Link.size() - FragmentAt - Fragment.size() != TokenLength)
		return false;
	std::string PhotoShape(Link.substr(0, PathAt));
	PhotoShape += '/';
	PhotoShape += Link.substr(FragmentAt);
	return photopdf::IsValidChooserLink(PhotoShape);
}

}} // namespace daedalus::localapp
