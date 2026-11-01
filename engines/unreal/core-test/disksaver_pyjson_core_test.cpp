// SPDX-License-Identifier: MIT
// PyJson parity: DaedalusDiskSaverPyJsonCore.h replays disksaver_pyjson_parity.txt
// (json.dumps ensure_ascii=True, sort_keys=True, written by tools/streaming/disksaver_pyjson_parity.py).
#include "DaedalusDiskSaverPyJsonCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

using namespace DiskSaverParity;
namespace PJ = DaedalusDiskSaver::PyJson;

static int Nibble(char C) {
    if (C >= '0' && C <= '9') return C - '0';
    if (C >= 'a' && C <= 'f') return C - 'a' + 10;
    return -1;
}

static bool Unhex(const std::string& Hex, std::string& Out) {
    if (Hex == "-") { Out.clear(); return true; }
    if (Hex.size() % 2 != 0) return false;
    Out.clear();
    Out.reserve(Hex.size() / 2);
    for (std::size_t I = 0; I < Hex.size(); I += 2) {
        const int Hi = Nibble(Hex[I]), Lo = Nibble(Hex[I + 1]);
        if (Hi < 0 || Lo < 0) return false;
        Out.push_back(static_cast<char>((Hi << 4) | Lo));
    }
    return true;
}

static bool ToI64(const std::string& S, long long& Out) {
    std::size_t I = 0;
    const bool Neg = !S.empty() && S[0] == '-';
    if (Neg) I = 1;
    if (I >= S.size() || S.size() - I > 19) return false;
    unsigned long long V = 0;
    for (; I < S.size(); ++I) {
        if (S[I] < '0' || S[I] > '9') return false;
        V = V * 10 + static_cast<unsigned long long>(S[I] - '0');
    }
    if (!Neg && V > 9223372036854775807ULL) return false;
    Out = Neg ? -static_cast<long long>(V) : static_cast<long long>(V);
    return true;
}

static bool Flag(const std::string& S, bool& Out) {
    if (S == "0") { Out = false; return true; }
    if (S == "1") { Out = true; return true; }
    return false;
}

static void Expect(const std::string& What, const std::string& Got, const std::string& Want) {
    Check(Got == Want, What + " got '" + Got + "' want '" + Want + "'");
}

int main(int argc, char** argv) {
    int Cases = 0;
    const char* Path = argc > 1 ? argv[1] : "disksaver_pyjson_parity.txt";
    for (const auto& T : ReadLines(Path)) {
        const std::string& Op = T[0];
        if (Op == "STR" && T.size() == 3) {
            std::string In, Want;
            Check(Unhex(T[1], In) && Unhex(T[2], Want), "STR hex");
            Expect("STR", PJ::Str(In), Want);
            ++Cases;
        } else if (Op == "RAW" && T.size() == 3) {
            std::string In, Want;
            Check(Unhex(T[1], In) && Unhex(T[2], Want), "RAW hex");
            Expect("RAW", PJ::Str(In), Want);
            ++Cases;
        } else if (Op == "INT" && T.size() == 3) {
            long long N = 0;
            std::string Want;
            Check(ToI64(T[1], N) && Unhex(T[2], Want), "INT");
            Expect("INT", PJ::Int(N), Want);
            ++Cases;
        } else if (Op == "BOOL" && T.size() == 3) {
            bool B = false;
            std::string Want;
            Check(Flag(T[1], B) && Unhex(T[2], Want), "BOOL");
            Expect("BOOL", PJ::Bool(B), Want);
            ++Cases;
        } else if (Op == "NULL" && T.size() == 2) {
            std::string Want;
            Check(Unhex(T[1], Want), "NULL");
            Expect("NULL", PJ::Null(), Want);
            ++Cases;
        } else if ((Op == "OBJ" || Op == "LIST") && T.size() >= 4) {
            bool Compact = false;
            int Count = 0;
            Check(Flag(T[1], Compact) && ToInt(T[2], Count) && Count >= 0, Op + " header");
            const int Need = Op == "OBJ" ? 4 + Count * 2 : 4 + Count;
            Check(static_cast<int>(T.size()) == Need, Op + " width");
            std::string Want;
            Check(Unhex(T.back(), Want), Op + " out");
            if (Op == "OBJ") {
                PJ::Object Obj;
                for (int K = 0; K < Count; ++K) {
                    std::string Key, Value;
                    Check(Unhex(T[3 + K * 2], Key) && Unhex(T[4 + K * 2], Value), "OBJ field");
                    Obj.Add(Key, Value);
                }
                Expect("OBJ", Obj.Dump(Compact), Want);
            } else {
                std::vector<std::string> Values;
                for (int K = 0; K < Count; ++K) {
                    std::string Value;
                    Check(Unhex(T[3 + K], Value), "LIST value");
                    Values.push_back(Value);
                }
                Expect("LIST", PJ::List(Values, Compact), Want);
            }
            ++Cases;
        } else {
            Check(false, "bad line " + Op);
        }
    }
    return Finish("pyjson", Cases, Cases);
}
