// P7 fixture: a TArray of a struct that holds std::string, and a TArray of std::string itself.
#include <string>
namespace core { struct Row
{
	std::string Name;
	int Value = 0;
}; }
struct FGood
{
	int Value = 0;
};
void F()
{
	TArray<core::Row> Bad;
	TArray<std::string> AlsoBad;
	TArray<FGood> Fine;
	TArray<TObjectPtr<UObject>> AlsoFine;
}
struct FWrap
{
	FString Id;
	core::Row R;   // holds std::string through Row
};
void G() { TArray<FWrap> Rows; }
