#include "DaedalusOceanHostClient.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/Base64.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanClientTest,"Daedalus.Ocean.HostChunkDecoder",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDaedalusOceanClientTest::RunTest(const FString& Parameters)
{
    TArray<uint8> Bytes;Bytes.Init(1,4096);
    const FString Payload=FBase64::Encode(Bytes);
    auto Json=[&](const FString& Data,bool Present=true) {
        return FString::Printf(TEXT("{\"x\":-1,\"y\":-1,\"z\":0,\"revision\":2,\"present\":%s,\"palette\":[\"AIR\",\"WATER\"],\"data\":\"%s\"}"),Present?TEXT("true"):TEXT("false"),*Data);
    };
    FDaedalusOceanChunkView Out;
    auto Decode=[&](const FString& Text){return UDaedalusOceanHostClient::DecodeChunk(Text,-1,-1,0,Out);};
    TestTrue(TEXT("Valid water chunk"),Decode(Json(Payload)));
    TestEqual(TEXT("Exact voxel count"),Out.Blocks.Num(),4096);
    TestEqual(TEXT("Water ordinal"),Out.Blocks[0],static_cast<uint8>(1));
    TestFalse(TEXT("Coordinate mismatch"),UDaedalusOceanHostClient::DecodeChunk(Json(Payload),0,-1,0,Out));
    TestTrue(TEXT("Failure clears output"),Out.Blocks.IsEmpty() && Out.Palette.IsEmpty());
    TestTrue(TEXT("Empty chunk produces air"),Decode(Json(TEXT(""),false)));
    TestEqual(TEXT("Empty chunk is complete"),Out.Blocks.Num(),4096);
    TestEqual(TEXT("Empty voxel is air"),Out.Blocks[0],static_cast<uint8>(0));
    TestFalse(TEXT("Empty chunk cannot carry data"),Decode(Json(Payload,false)));
    TestFalse(TEXT("Short payload refuses"),Decode(Json(TEXT("AA=="))));
    Bytes[0]=2;TestFalse(TEXT("Unknown ordinal refuses"),Decode(Json(FBase64::Encode(Bytes))));
    TestFalse(TEXT("Duplicate palette refuses"),Decode(Json(Payload).Replace(TEXT("AIR\",\"WATER"),TEXT("AIR\",\"AIR"))));
    TestFalse(TEXT("Missing fields refuse"),Decode(TEXT("{}")));
    TestFalse(TEXT("Fractional coordinate refuses"),Decode(Json(Payload).Replace(TEXT("\"x\":-1"),TEXT("\"x\":-1.5"))));
    TestFalse(TEXT("Unsafe numeric revision refuses"),Decode(Json(Payload).Replace(TEXT("\"revision\":2"),TEXT("\"revision\":9007199254740992"))));
    auto* Client=NewObject<UDaedalusOceanHostClient>();
    TestFalse(TEXT("No session cannot request"),Client->RequestChunk(0,0,0));
    TestFalse(TEXT("Remote plaintext origin refuses"),Client->ConfigureSession(TEXT("http://example.com"),TEXT("a.b.c")));
    TestFalse(TEXT("Header injection refuses"),Client->ConfigureSession(TEXT("https://example.com"),TEXT("a\r\nb")));
    TestFalse(TEXT("Origin credentials refuse"),Client->ConfigureSession(TEXT("https://user@example.com"),TEXT("a.b.c")));
    TestTrue(TEXT("Loopback development origin accepted"),Client->ConfigureSession(TEXT("http://127.0.0.1:8088"),TEXT("a.b.c")));
    Client->ClearSession();TestFalse(TEXT("Clear removes session"),Client->RequestChunk(0,0,0));
    return true;
}
#endif
