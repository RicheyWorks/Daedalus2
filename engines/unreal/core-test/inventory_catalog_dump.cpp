#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusInventoryCore.h"
#include <fstream>
#include <iostream>
#include <iterator>
static std::string Hex(const std::string& value)
{
    const char* digits="0123456789abcdef";
    std::string result;
    for (unsigned char c:value) { result+=digits[c>>4]; result+=digits[c&15]; }
    return result;
}
int main(int argc,char** argv)
{
    if (argc!=2) return 2;
    std::ifstream input(argv[1],std::ios::binary);
    if (!input) return 2;
    const std::string text((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
    daedalus::inv::Catalog catalog;
    std::string error;
    if (!catalog.Parse(text,error)) return 3;
    std::cout << "realm\t" << Hex(catalog.Realm) << "\ntheme\t" << Hex(catalog.Theme) << '\n';
    for (const auto& tab:catalog.Tabs) std::cout << "tab\t" << Hex(tab) << '\n';
    for (const auto& slot:catalog.Slots) std::cout << "slot\t" << Hex(slot) << '\n';
    for (const auto& item:catalog.Items)
    {
        std::cout << "item\t" << Hex(item.Id) << '\t' << Hex(item.Tab) << '\t' << Hex(item.Slot)
                  << '\t' << Hex(item.Name) << '\t' << Hex(item.Detail);
        for (const auto& action:item.Actions) std::cout << '\t' << Hex(action);
        std::cout << '\n';
    }
}
