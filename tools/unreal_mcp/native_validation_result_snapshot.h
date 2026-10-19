// SPDX-License-Identifier: MIT
// native_validation_result_snapshot.h
//
// Typed, data-only aggregate serializer for one UE 5.8.3 DataValidation
// ValidateAssetsWithSettings outcome: the requested object-path set, the int
// native return, and explicit member snapshots of FValidateAssetsSettings and
// FValidateAssetsResults. Output is the JSON object shape consumed by the
// existing Python acceptance contract
//   tools/unreal_mcp/validation_result_contract.py
//   evaluate_native_validation(requested_assets, native_return, results, settings)
// as {"requested_assets", "native_return", "results", "settings", "unknowns", ...}.
//
// Scope (deliberately narrow):
//   * Pure data. This header never invokes validation, loads the DataValidation
//     plugin, opens an endpoint or transport, or touches any module/build file.
//   * Default build is C++17 standard library only. The optional adapter that
//     copies from the real engine structs is compiled only when the including
//     translation unit defines DAEDALUS_WITH_UNREAL_DATAVALIDATION and already
//     includes EditorValidatorSubsystem.h; nothing here adds that dependency.
//   * Faithful, not judging. Counts, flags, the limit and the return are copied
//     verbatim (including impossible values) so the Python consumer, not this
//     serializer, decides acceptance. Nothing is defaulted to a passing value.
//   * Honest unknowns. Provenance the snapshot cannot prove (fresh OutResults,
//     the actual native invocation, runtime qualification, rich tokenized
//     message tokens, ValidatorStatistics, non-reflected settings) is reported
//     in "unknowns" instead of being inferred.
//
// Source provenance (read from the installed engine, not assumed):
//   UE 5.8.3, Engine/Plugins/Editor/DataValidation/Source/DataValidation/Public/
//   EditorValidatorSubsystem.h sha256 463558fd5bc145575def4caa75eb22d49a1c06da
//   b7e1e0b927dd9781fc058174 (lines 30-223: FValidateAssetsExternalObject,
//   FValidateAssetsDetails, FValidateAssetsResults, FValidateAssetsSettings).
//   That digest matches SOURCE_PROVENANCE["header_sha256"] in the consumer.
//
// Status: SOURCE ONLY. test_native_validation_result_snapshot.cpp is authored
// and unrun until a fresh serialized resource clear is granted.
#pragma once

#include <cstdint>
#include <cstdio>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace daedalus {
namespace validation_snapshot {

// Mirrors EDataValidationResult. Projected by native enum name, matching the
// consumer's convention (detail "Result" == "Valid").
enum class EResult { NotValidated, Invalid, Valid };

inline const char* ResultName(EResult r) {
    switch (r) {
        case EResult::Invalid: return "Invalid";
        case EResult::Valid: return "Valid";
        case EResult::NotValidated: default: return "NotValidated";
    }
}

// One tokenized message, projected to plain text only. Image/hyperlink tokens
// are not representable; their loss is reported via unknowns.
struct FMessageSnapshot {
    std::string Severity;  // native EMessageSeverity name, e.g. "Error", "Warning", "Info"
    std::string Text;      // FTokenizedMessage::ToText(), UTF-8
};

// Mirrors FValidateAssetsExternalObject.
struct FExternalObjectSnapshot {
    std::string PackageName;
    std::string AssetName;
};

// Mirrors FValidateAssetsDetails (members lack UPROPERTY in 5.8.3).
struct FDetailSnapshot {
    std::string PackageName;
    std::string AssetName;
    EResult Result = EResult::NotValidated;  // never defaulted to Valid
    std::vector<std::string> ValidationErrors;
    std::vector<std::string> ValidationWarnings;
    std::vector<FMessageSnapshot> ValidationMessages;
    std::vector<FExternalObjectSnapshot> ExternalObjects;
};

// Mirrors the FValidateAssetsResults members the consumer reads. int64_t holds
// any native int without truncation; values are copied, never clamped.
struct FResultsSnapshot {
    int64_t NumRequested = 0;
    int64_t NumExternalObjects = 0;
    int64_t NumChecked = 0;
    int64_t NumValid = 0;
    int64_t NumInvalid = 0;
    int64_t NumSkipped = 0;
    int64_t NumWarnings = 0;
    int64_t NumUnableToValidate = 0;
    bool bAssetLimitReached = false;
    // Keyed by object path exactly as the native TMap<FString, ...>; std::map
    // gives deterministic (sorted) output where TMap order carries no meaning.
    std::map<std::string, FDetailSnapshot> AssetsDetails;
    std::vector<FMessageSnapshot> ValidatorMessages;  // non-reflected member
    bool bValidatorStatisticsCaptured = false;        // not serialized; reported as unknown
};

// Mirrors the reflected FValidateAssetsSettings members.
struct FSettingsSnapshot {
    bool bSkipExcludedDirectories = true;
    bool bShowIfNoFailures = true;
    bool bCollectPerAssetDetails = false;
    std::string ValidationUsecase = "None";  // native EDataValidationUsecase name
    bool bLoadAssetsForValidation = true;
    bool bUnloadAssetsLoadedForValidation = false;
    bool bLoadExternalObjectsForValidation = true;
    bool bCaptureAssetLoadLogs = true;
    bool bCaptureLogsDuringValidation = true;
    bool bCaptureWarningsDuringValidationAsErrors = false;
    int64_t MaxAssetsToValidate = 2147483647;  // native default MAX_int32
    bool bValidateReferencersOfDeletedAssets = true;
    bool bSilent = false;  // non-reflected
};

// Caller-attested provenance. Every field defaults to the honest unknown.
struct FProvenance {
    std::string FreshOutResults = "unknown";      // "attested" only if the caller proves a fresh struct
    std::string NativeInvocation = "unknown";     // the actual ValidateAssetsWithSettings call is not proven here
    std::string CapturedAtUtc = "unknown";
};

struct FValidationSnapshot {
    std::vector<std::string> RequestedAssets;  // order preserved exactly
    int64_t NativeReturn = 0;                  // the int return, never reinterpreted as bool
    FResultsSnapshot Results;
    FSettingsSnapshot Settings;
    FProvenance Provenance;
};

namespace detail {

inline void AppendEscaped(std::string& out, const std::string& s) {
    out.push_back('"');
    for (unsigned char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", static_cast<unsigned>(c));
                    out += buf;
                } else {
                    out.push_back(static_cast<char>(c));  // UTF-8 passes through
                }
        }
    }
    out.push_back('"');
}

inline void AppendBool(std::string& out, bool b) { out += b ? "true" : "false"; }
inline void AppendInt(std::string& out, int64_t v) { out += std::to_string(v); }

inline void AppendKey(std::string& out, bool& first, const char* key) {
    if (!first) out += ", ";
    first = false;
    AppendEscaped(out, key);
    out += ": ";
}

inline void AppendStrings(std::string& out, const std::vector<std::string>& v) {
    out.push_back('[');
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) out += ", ";
        AppendEscaped(out, v[i]);
    }
    out.push_back(']');
}

inline void AppendMessages(std::string& out, const std::vector<FMessageSnapshot>& v) {
    out.push_back('[');
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) out += ", ";
        bool first = true;
        out.push_back('{');
        AppendKey(out, first, "Severity"); AppendEscaped(out, v[i].Severity);
        AppendKey(out, first, "Text"); AppendEscaped(out, v[i].Text);
        out.push_back('}');
    }
    out.push_back(']');
}

inline void AppendExternals(std::string& out, const std::vector<FExternalObjectSnapshot>& v) {
    out.push_back('[');
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) out += ", ";
        bool first = true;
        out.push_back('{');
        AppendKey(out, first, "PackageName"); AppendEscaped(out, v[i].PackageName);
        AppendKey(out, first, "AssetName"); AppendEscaped(out, v[i].AssetName);
        out.push_back('}');
    }
    out.push_back(']');
}

inline void AppendDetail(std::string& out, const FDetailSnapshot& d) {
    bool first = true;
    out.push_back('{');
    AppendKey(out, first, "PackageName"); AppendEscaped(out, d.PackageName);
    AppendKey(out, first, "AssetName"); AppendEscaped(out, d.AssetName);
    AppendKey(out, first, "Result"); AppendEscaped(out, ResultName(d.Result));
    AppendKey(out, first, "ValidationErrors"); AppendStrings(out, d.ValidationErrors);
    AppendKey(out, first, "ValidationWarnings"); AppendStrings(out, d.ValidationWarnings);
    AppendKey(out, first, "ValidationMessages"); AppendMessages(out, d.ValidationMessages);
    AppendKey(out, first, "ExternalObjects"); AppendExternals(out, d.ExternalObjects);
    out.push_back('}');
}

}  // namespace detail

// Results object: the 8 native counts, the limit flag, per-asset details and
// validator-wide messages, under the exact native member names.
inline std::string SerializeResults(const FResultsSnapshot& r) {
    using namespace detail;
    std::string out;
    bool first = true;
    out.push_back('{');
    AppendKey(out, first, "NumRequested"); AppendInt(out, r.NumRequested);
    AppendKey(out, first, "NumExternalObjects"); AppendInt(out, r.NumExternalObjects);
    AppendKey(out, first, "NumChecked"); AppendInt(out, r.NumChecked);
    AppendKey(out, first, "NumValid"); AppendInt(out, r.NumValid);
    AppendKey(out, first, "NumInvalid"); AppendInt(out, r.NumInvalid);
    AppendKey(out, first, "NumSkipped"); AppendInt(out, r.NumSkipped);
    AppendKey(out, first, "NumWarnings"); AppendInt(out, r.NumWarnings);
    AppendKey(out, first, "NumUnableToValidate"); AppendInt(out, r.NumUnableToValidate);
    AppendKey(out, first, "bAssetLimitReached"); AppendBool(out, r.bAssetLimitReached);
    AppendKey(out, first, "AssetsDetails");
    out.push_back('{');
    bool firstDetail = true;
    for (const auto& kv : r.AssetsDetails) {
        if (!firstDetail) out += ", ";
        firstDetail = false;
        AppendEscaped(out, kv.first);
        out += ": ";
        AppendDetail(out, kv.second);
    }
    out.push_back('}');
    AppendKey(out, first, "ValidatorMessages"); AppendMessages(out, r.ValidatorMessages);
    out.push_back('}');
    return out;
}

inline std::string SerializeSettings(const FSettingsSnapshot& s) {
    using namespace detail;
    std::string out;
    bool first = true;
    out.push_back('{');
    AppendKey(out, first, "bSkipExcludedDirectories"); AppendBool(out, s.bSkipExcludedDirectories);
    AppendKey(out, first, "bShowIfNoFailures"); AppendBool(out, s.bShowIfNoFailures);
    AppendKey(out, first, "bCollectPerAssetDetails"); AppendBool(out, s.bCollectPerAssetDetails);
    AppendKey(out, first, "ValidationUsecase"); AppendEscaped(out, s.ValidationUsecase);
    AppendKey(out, first, "bLoadAssetsForValidation"); AppendBool(out, s.bLoadAssetsForValidation);
    AppendKey(out, first, "bUnloadAssetsLoadedForValidation"); AppendBool(out, s.bUnloadAssetsLoadedForValidation);
    AppendKey(out, first, "bLoadExternalObjectsForValidation"); AppendBool(out, s.bLoadExternalObjectsForValidation);
    AppendKey(out, first, "bCaptureAssetLoadLogs"); AppendBool(out, s.bCaptureAssetLoadLogs);
    AppendKey(out, first, "bCaptureLogsDuringValidation"); AppendBool(out, s.bCaptureLogsDuringValidation);
    AppendKey(out, first, "bCaptureWarningsDuringValidationAsErrors"); AppendBool(out, s.bCaptureWarningsDuringValidationAsErrors);
    AppendKey(out, first, "MaxAssetsToValidate"); AppendInt(out, s.MaxAssetsToValidate);
    AppendKey(out, first, "bValidateReferencersOfDeletedAssets"); AppendBool(out, s.bValidateReferencersOfDeletedAssets);
    AppendKey(out, first, "bSilent"); AppendBool(out, s.bSilent);
    out.push_back('}');
    return out;
}

// Honest unknowns: what this snapshot cannot prove. Always emitted.
inline std::vector<std::string> Unknowns(const FValidationSnapshot& snap) {
    std::vector<std::string> u;
    if (snap.Provenance.FreshOutResults != "attested") u.push_back("fresh_out_results_unproven");
    if (snap.Provenance.NativeInvocation != "attested") u.push_back("native_invocation_unproven");
    u.push_back("native_runtime_unqualified");
    u.push_back("official_mcp_callable_unverified");
    u.push_back("tokenized_message_tokens_projected_to_text_only");
    if (!snap.Results.bValidatorStatisticsCaptured) u.push_back("validator_statistics_not_captured");
    u.push_back("settings_message_log_fields_not_captured");  // ShowMessageLogSeverity/MessageLogName/MessageLogPageTitle
    return u;
}

// Full envelope. results/settings/requested_assets/native_return map 1:1 onto
// evaluate_native_validation's four arguments.
inline std::string Serialize(const FValidationSnapshot& snap) {
    using namespace detail;
    std::string out;
    bool first = true;
    out.push_back('{');
    AppendKey(out, first, "snapshot_kind"); AppendEscaped(out, "explicit_native_members_not_mcp_schema");
    AppendKey(out, first, "requested_assets"); AppendStrings(out, snap.RequestedAssets);
    AppendKey(out, first, "native_return"); AppendInt(out, snap.NativeReturn);
    AppendKey(out, first, "results"); out += SerializeResults(snap.Results);
    AppendKey(out, first, "settings"); out += SerializeSettings(snap.Settings);
    AppendKey(out, first, "provenance");
    {
        bool f = true;
        out.push_back('{');
        AppendKey(out, f, "fresh_out_results"); AppendEscaped(out, snap.Provenance.FreshOutResults);
        AppendKey(out, f, "native_invocation"); AppendEscaped(out, snap.Provenance.NativeInvocation);
        AppendKey(out, f, "captured_at_utc"); AppendEscaped(out, snap.Provenance.CapturedAtUtc);
        out.push_back('}');
    }
    AppendKey(out, first, "native_runtime_qualified"); AppendBool(out, false);
    AppendKey(out, first, "unknowns"); AppendStrings(out, Unknowns(snap));
    out.push_back('}');
    return out;
}

#if defined(DAEDALUS_WITH_UNREAL_DATAVALIDATION)
// Optional engine adapter. Compiled only by a separately admitted native
// producer that already includes EditorValidatorSubsystem.h; it copies members
// and performs no validation, loading or invocation of its own.
namespace unreal_adapter {

// Length-aware: a legal FString/FText may carry embedded NULs ("A\0B").
// TCHAR_TO_UTF8 into std::string(const char*) would stop at the first NUL and
// silently drop diagnostic text, so convert with the explicit source length and
// build the std::string from (data, length). Embedded NULs then reach
// AppendEscaped and are emitted as \u0000, never truncated.
inline std::string ToUtf8(const FString& s) {
    const FTCHARToUTF8 converted(*s, s.Len());
    return std::string(converted.Get(), static_cast<size_t>(converted.Length()));
}

inline EResult ToResult(EDataValidationResult r) {
    switch (r) {
        case EDataValidationResult::Valid: return EResult::Valid;
        case EDataValidationResult::Invalid: return EResult::Invalid;
        default: return EResult::NotValidated;
    }
}

inline const char* SeverityName(EMessageSeverity::Type s) {
    switch (s) {
        case EMessageSeverity::Error: return "Error";
        case EMessageSeverity::PerformanceWarning: return "PerformanceWarning";
        case EMessageSeverity::Warning: return "Warning";
        case EMessageSeverity::Info: return "Info";
        default: return "Unknown";
    }
}

inline std::vector<FMessageSnapshot> ToMessages(const TArray<TSharedRef<FTokenizedMessage>>& In) {
    std::vector<FMessageSnapshot> out;
    for (const TSharedRef<FTokenizedMessage>& M : In) {
        out.push_back({SeverityName(M->GetSeverity()), ToUtf8(M->ToText().ToString())});
    }
    return out;
}

inline std::vector<std::string> ToTexts(const TArray<FText>& In) {
    std::vector<std::string> out;
    for (const FText& T : In) out.push_back(ToUtf8(T.ToString()));
    return out;
}

inline FResultsSnapshot FromNative(const FValidateAssetsResults& R) {
    FResultsSnapshot S;
    S.NumRequested = R.NumRequested;
    S.NumExternalObjects = R.NumExternalObjects;
    S.NumChecked = R.NumChecked;
    S.NumValid = R.NumValid;
    S.NumInvalid = R.NumInvalid;
    S.NumSkipped = R.NumSkipped;
    S.NumWarnings = R.NumWarnings;
    S.NumUnableToValidate = R.NumUnableToValidate;
    S.bAssetLimitReached = R.bAssetLimitReached;
    for (const TPair<FString, FValidateAssetsDetails>& Pair : R.AssetsDetails) {
        const FValidateAssetsDetails& D = Pair.Value;
        FDetailSnapshot DS;
        DS.PackageName = ToUtf8(D.PackageName.ToString());
        DS.AssetName = ToUtf8(D.AssetName.ToString());
        DS.Result = ToResult(D.Result);
        DS.ValidationErrors = ToTexts(D.ValidationErrors);
        DS.ValidationWarnings = ToTexts(D.ValidationWarnings);
        DS.ValidationMessages = ToMessages(D.ValidationMessages);
        for (const FValidateAssetsExternalObject& E : D.ExternalObjects) {
            DS.ExternalObjects.push_back({ToUtf8(E.PackageName.ToString()), ToUtf8(E.AssetName.ToString())});
        }
        S.AssetsDetails[ToUtf8(Pair.Key)] = std::move(DS);
    }
    S.ValidatorMessages = ToMessages(R.ValidatorMessages);
    S.bValidatorStatisticsCaptured = false;
    return S;
}

inline FSettingsSnapshot FromNative(const FValidateAssetsSettings& In) {
    FSettingsSnapshot S;
    S.bSkipExcludedDirectories = In.bSkipExcludedDirectories;
    S.bShowIfNoFailures = In.bShowIfNoFailures;
    S.bCollectPerAssetDetails = In.bCollectPerAssetDetails;
    S.ValidationUsecase = ToUtf8(UEnum::GetValueAsString(In.ValidationUsecase));
    S.bLoadAssetsForValidation = In.bLoadAssetsForValidation;
    S.bUnloadAssetsLoadedForValidation = In.bUnloadAssetsLoadedForValidation;
    S.bLoadExternalObjectsForValidation = In.bLoadExternalObjectsForValidation;
    S.bCaptureAssetLoadLogs = In.bCaptureAssetLoadLogs;
    S.bCaptureLogsDuringValidation = In.bCaptureLogsDuringValidation;
    S.bCaptureWarningsDuringValidationAsErrors = In.bCaptureWarningsDuringValidationAsErrors;
    S.MaxAssetsToValidate = In.MaxAssetsToValidate;
    S.bValidateReferencersOfDeletedAssets = In.bValidateReferencersOfDeletedAssets;
    S.bSilent = In.bSilent;
    return S;
}

}  // namespace unreal_adapter
#endif  // DAEDALUS_WITH_UNREAL_DATAVALIDATION

}  // namespace validation_snapshot
}  // namespace daedalus
