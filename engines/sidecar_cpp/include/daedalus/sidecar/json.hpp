// SPDX-License-Identifier: MIT
// Minimal, dependency-free JSON reader for Daedalus sidecars (C++17). Read-only: objects, arrays, strings, numbers, bools, null.
#pragma once
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace daedalus::sidecar {

struct Json {
    enum class Type { Null, Bool, Number, String, Array, Object };
    Type type = Type::Null;
    bool b = false;
    double num = 0.0;
    std::string str;
    std::vector<Json> arr;
    std::vector<std::pair<std::string, Json>> obj;  // keeps file order

    bool isNull() const { return type == Type::Null; }
    bool isNumber() const { return type == Type::Number; }
    bool isString() const { return type == Type::String; }
    bool isArray() const { return type == Type::Array; }
    bool isObject() const { return type == Type::Object; }
    bool has(const std::string& k) const;
    const Json& operator[](const std::string& k) const;  // throws if missing
    const Json* find(const std::string& k) const;          // nullptr if missing
    const Json& operator[](size_t i) const { return arr.at(i); }
    size_t size() const { return isArray() ? arr.size() : obj.size(); }
    double asNumber() const;
    const std::string& asString() const;
    bool asBool() const;
};

struct JsonError : std::runtime_error { using std::runtime_error::runtime_error; };

Json parseJson(const std::string& text);
Json parseJsonFile(const std::string& path);

}  // namespace daedalus::sidecar
