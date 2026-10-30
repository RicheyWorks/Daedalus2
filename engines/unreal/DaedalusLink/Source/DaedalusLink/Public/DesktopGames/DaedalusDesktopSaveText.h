// SPDX-License-Identifier: MIT
// Shared helpers for the text save format the Prismheart cabinets use:
//
//   <game> v1 key=value key=value ...
//
// SaveWriter builds that line; SaveFields reads it back without exceptions (preflight P8) and with
// range checks on every number, so a tampered save is refused instead of trusted. Lists are
// comma-separated and an empty list is written as "-".
#pragma once
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

/** Parses a whole-string signed integer. Empty text, trailing junk and overflow are all refused. */
inline bool ParseInteger(const std::string& Text, long long& Out) {
    if(Text.empty()) return false;
    char* End = nullptr;
    errno = 0;
    const long long Value = std::strtoll(Text.c_str(), &End, 10);
    if(End == Text.c_str() || *End != '\0' || errno == ERANGE) return false;
    Out = Value;
    return true;
}

/** Splits on one separator. "" gives no tokens; "a,,b" gives three. */
inline std::vector<std::string> SplitText(const std::string& Text, char Separator) {
    std::vector<std::string> Tokens;
    if(Text.empty()) return Tokens;
    std::string Current;
    for(char Ch : Text) {
        if(Ch == Separator) {
            Tokens.push_back(Current);
            Current.clear();
        } else {
            Current.push_back(Ch);
        }
    }
    Tokens.push_back(Current);
    return Tokens;
}

/** Joins integers with commas; an empty list becomes "-" so the save line never has an empty field. */
inline std::string JoinIntegers(const std::vector<int>& Values) {
    if(Values.empty()) return "-";
    std::string Out;
    for(size_t I = 0; I < Values.size(); ++I) {
        if(I) Out.push_back(',');
        Out += std::to_string(Values[I]);
    }
    return Out;
}

/** Builds "<game> v1 key=value ..." in the order fields are added. */
class SaveWriter {
    std::ostringstream Out;
public:
    explicit SaveWriter(const char* GameId) { Out << GameId << " v1"; }
    SaveWriter& Field(const char* Key, const std::string& Value) { Out << ' ' << Key << '=' << Value; return *this; }
    SaveWriter& Field(const char* Key, long long Value) { Out << ' ' << Key << '=' << Value; return *this; }
    SaveWriter& Field(const char* Key, unsigned long long Value) { Out << ' ' << Key << '=' << Value; return *this; }
    SaveWriter& Field(const char* Key, int Value) { return Field(Key, static_cast<long long>(Value)); }
    SaveWriter& Field(const char* Key, std::uint32_t Value) { return Field(Key, static_cast<unsigned long long>(Value)); }
    SaveWriter& Flag(const char* Key, bool Value) { return Field(Key, Value ? 1LL : 0LL); }
    SaveWriter& List(const char* Key, const std::vector<int>& Values) { return Field(Key, JoinIntegers(Values)); }
    std::string Text() const { return Out.str(); }
};

/** Reads "<game> v1 key=value ..." back. Every accessor returns false instead of throwing. */
class SaveFields {
    std::string Line;
    bool Valid = false;
public:
    SaveFields(const std::string& Text, const char* GameId) : Line(Text) {
        const std::string Header = std::string(GameId) + " v1 ";
        Valid = Line.rfind(Header, 0) == 0;
    }
    bool IsValid() const { return Valid; }

    /** The raw text after "key=" up to the next space; "" when the key is absent. */
    std::string Str(const char* Key) const {
        const std::string Needle = std::string(" ") + Key + "=";
        const size_t At = Line.find(Needle);
        if(At == std::string::npos) return "";
        const size_t Start = At + Needle.size();
        const size_t End = Line.find(' ', Start);
        return Line.substr(Start, End == std::string::npos ? std::string::npos : End - Start);
    }
    /** An integer within [Low, High]. */
    bool Int(const char* Key, long long Low, long long High, long long& Out) const {
        long long Value = 0;
        if(!ParseInteger(Str(Key), Value) || Value < Low || Value > High) return false;
        Out = Value;
        return true;
    }
    bool Int(const char* Key, int Low, int High, int& Out) const {
        long long Value = 0;
        if(!Int(Key, static_cast<long long>(Low), static_cast<long long>(High), Value)) return false;
        Out = static_cast<int>(Value);
        return true;
    }
    bool Seed(const char* Key, std::uint32_t& Out) const {
        long long Value = 0;
        if(!Int(Key, 0LL, 0xffffffffLL, Value)) return false;
        Out = static_cast<std::uint32_t>(Value);
        return true;
    }
    /** "0" or "1" only. */
    bool Flag(const char* Key, bool& Out) const {
        long long Value = 0;
        if(!Int(Key, 0LL, 1LL, Value)) return false;
        Out = Value != 0;
        return true;
    }
    /** A comma list of integers each within [Low, High]; "-" is the empty list. */
    bool IntList(const char* Key, int Low, int High, std::vector<int>& Out) const {
        Out.clear();
        const std::string Text = Str(Key);
        if(Text == "-") return true;
        if(Text.empty()) return false;
        for(const std::string& Token : SplitText(Text, ',')) {
            long long Value = 0;
            if(!ParseInteger(Token, Value) || Value < Low || Value > High) return false;
            Out.push_back(static_cast<int>(Value));
        }
        return true;
    }
};

/** Rising-edge latch for a held input: Rose() is true on the first step a button is down. */
struct EdgeLatch {
    bool Was = false;
    bool Rose(bool Now) {
        const bool Rising = Now && !Was;
        Was = Now;
        return Rising;
    }
    void Clear() { Was = false; }
};

/** Ordered keyboard events delivered to Game::SourceKeyDown. */
namespace SourceKey {
    constexpr int Up = 0, Down = 1, Left = 2, Right = 3, B = 4, A = 5, Enter = 6, Space = 7, R = 8;
    inline bool IsConfirm(int Key) { return Key == A || Key == Enter || Key == Space; }
    inline bool IsRestart(int Key) { return IsConfirm(Key) || Key == R; }
}
/** Controller events delivered to Game::SourceControllerButton. */
namespace PadButton {
    constexpr int A = 0, Start = 1;
}

}} // daedalus::desktop
