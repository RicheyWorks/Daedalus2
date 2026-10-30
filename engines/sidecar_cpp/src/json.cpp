// SPDX-License-Identifier: MIT
#include "daedalus/sidecar/json.hpp"
#include <cctype>
#include <cstdlib>
#include <limits>
#include <fstream>
#include <sstream>

namespace daedalus::sidecar {

bool Json::has(const std::string& k) const { return find(k) != nullptr; }
const Json* Json::find(const std::string& k) const {
    if (!isObject()) return nullptr;
    for (auto& kv : obj) if (kv.first == k) return &kv.second;
    return nullptr;
}
const Json& Json::operator[](const std::string& k) const {
    const Json* j = find(k);
    if (!j) throw JsonError("missing key: " + k);
    return *j;
}
double Json::asNumber() const { if (!isNumber()) throw JsonError("not a number"); return num; }
const std::string& Json::asString() const { if (!isString()) throw JsonError("not a string"); return str; }
bool Json::asBool() const { if (type != Type::Bool) throw JsonError("not a bool"); return b; }

namespace {
struct Parser {
    const std::string& s; size_t i = 0;
    explicit Parser(const std::string& t) : s(t) {}
    [[noreturn]] void fail(const char* m) { throw JsonError(std::string(m) + " at offset " + std::to_string(i)); }
    void ws() { while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) ++i; }
    bool lit(const char* w) { size_t n = std::char_traits<char>::length(w); if (s.compare(i, n, w) == 0) { i += n; return true; } return false; }
    static void utf8(std::string& o, unsigned cp) {
        if (cp < 0x80) o += char(cp);
        else if (cp < 0x800) { o += char(0xC0 | (cp >> 6)); o += char(0x80 | (cp & 0x3F)); }
        else if (cp < 0x10000) { o += char(0xE0 | (cp >> 12)); o += char(0x80 | ((cp >> 6) & 0x3F)); o += char(0x80 | (cp & 0x3F)); }
        else { o += char(0xF0 | (cp >> 18)); o += char(0x80 | ((cp >> 12) & 0x3F)); o += char(0x80 | ((cp >> 6) & 0x3F)); o += char(0x80 | (cp & 0x3F)); }
    }
    unsigned hex4() {
        if (i + 4 > s.size()) fail("bad \\u escape");
        unsigned v = 0;
        for (int k = 0; k < 4; ++k) { char c = s[i++]; v <<= 4;
            if (c >= '0' && c <= '9') v |= unsigned(c - '0'); else if (c >= 'a' && c <= 'f') v |= unsigned(c - 'a' + 10);
            else if (c >= 'A' && c <= 'F') v |= unsigned(c - 'A' + 10); else fail("bad hex"); }
        return v;
    }
    std::string string() {
        if (s[i] != '"') fail("expected string");
        ++i; std::string o;
        while (true) {
            if (i >= s.size()) fail("unterminated string");
            char c = s[i++];
            if (c == '"') return o;
            if (c != '\\') { o += c; continue; }
            if (i >= s.size()) fail("bad escape");
            char e = s[i++];
            switch (e) {
                case '"': o += '"'; break; case '\\': o += '\\'; break; case '/': o += '/'; break;
                case 'b': o += '\b'; break; case 'f': o += '\f'; break; case 'n': o += '\n'; break;
                case 'r': o += '\r'; break; case 't': o += '\t'; break;
                case 'u': { unsigned cp = hex4();
                    if (cp >= 0xD800 && cp < 0xDC00 && lit("\\u")) { unsigned lo = hex4(); cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00); }
                    utf8(o, cp); break; }
                default: fail("bad escape");
            }
        }
    }
    Json value(int depth) {
        if (depth > 256) fail("too deep");
        ws(); if (i >= s.size()) fail("unexpected end");
        Json j; char c = s[i];
        if (c == '{') {
            j.type = Json::Type::Object; ++i; ws();
            if (s[i] == '}') { ++i; return j; }
            while (true) { ws(); std::string k = string(); ws(); if (s[i] != ':') fail("expected :"); ++i;
                j.obj.emplace_back(std::move(k), value(depth + 1)); ws();
                if (s[i] == ',') { ++i; continue; } if (s[i] == '}') { ++i; return j; } fail("expected , or }"); }
        }
        if (c == '[') {
            j.type = Json::Type::Array; ++i; ws();
            if (s[i] == ']') { ++i; return j; }
            while (true) { j.arr.push_back(value(depth + 1)); ws();
                if (s[i] == ',') { ++i; continue; } if (s[i] == ']') { ++i; return j; } fail("expected , or ]"); }
        }
        if (c == '"') { j.type = Json::Type::String; j.str = string(); return j; }
        if (lit("true")) { j.type = Json::Type::Bool; j.b = true; return j; }
        if (lit("false")) { j.type = Json::Type::Bool; return j; }
        if (lit("null")) return j;
        if (c == '-' || (c >= '0' && c <= '9')) {
            size_t st = i; ++i;
            while (i < s.size() && (std::isdigit((unsigned char)s[i]) || s[i] == '.' || s[i] == 'e' || s[i] == 'E' || s[i] == '+' || s[i] == '-')) ++i;
            std::string t = s.substr(st, i - st); char* end = nullptr;
            j.type = Json::Type::Number; j.num = std::strtod(t.c_str(), &end);
            if (!end || *end) fail("bad number");
            return j;
        }
        if (lit("NaN")) { j.type = Json::Type::Number; j.num = std::numeric_limits<double>::quiet_NaN(); return j; }
        fail("unexpected character");
    }
};
}  // namespace

Json parseJson(const std::string& text) {
    Parser p(text);
    if (text.size() >= 3 && (unsigned char)text[0] == 0xEF && (unsigned char)text[1] == 0xBB && (unsigned char)text[2] == 0xBF) p.i = 3;
    Json j = p.value(0); p.ws();
    if (p.i != text.size()) p.fail("trailing data");
    return j;
}

Json parseJsonFile(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw JsonError("cannot open " + path);
    std::ostringstream ss; ss << f.rdbuf();
    try { return parseJson(ss.str()); } catch (const JsonError& e) { throw JsonError(path + ": " + e.what()); }
}

}  // namespace daedalus::sidecar
