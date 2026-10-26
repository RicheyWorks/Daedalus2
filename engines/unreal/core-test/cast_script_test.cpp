// SPDX-License-Identifier: MIT
// DCS 1: the cast script. Parses the shipped realm casts and plays a few conversations through their branches.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public cast_script_test.cpp -o cast_test
//   ./cast_test ../DaedalusLink/Content/Casts

#include "DaedalusCastScriptCore.h"

#include <fstream>
#include <iostream>
#include <sstream>

using namespace daedalus::cast;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

static std::string ReadAll(const std::string& Path) { std::ifstream In(Path); std::stringstream S; S << In.rdbuf(); return S.str(); }

int main(int argc, char** argv)
{
    const std::string Dir = argc > 1 ? argv[1] : "../DaedalusLink/Content/Casts";
    Cast G;
    std::string Err;
    Check("the Gallery City cast parses", G.Parse(ReadAll(Dir + "/gallery-city.dcs"), Err), Err);
    Check("twelve characters with a start step each", G.Scripts.size() == 12 && G.Realm == "GALLERY-CITY");
    Check("a script is found by name, any case", G.Find("curator vell") && G.Find("CURATOR VELL")->Pitch == 3);

    // ---- refusals
    {
        Cast B;
        Check("no magic", !B.Parse("hello\n", Err) && Err.rfind("line 1", 0) == 0, Err);
        Check("a choice to nowhere", !B.Parse("DCS 1\ncast X\nwho A\nstep start\nask Hi? | Yes=nope\n", Err) && Err.find("goes nowhere") != std::string::npos, Err);
        Check("a script without start", !B.Parse("DCS 1\ncast X\nwho A\nstep begin\nsay hi\n", Err) && Err.find("no 'start'") != std::string::npos, Err);
        Check("an empty step", !B.Parse("DCS 1\ncast X\nwho A\nstep start\nstep two\n", Err) && Err.find("empty") != std::string::npos, Err);
        Check("a line before who", !B.Parse("DCS 1\ncast X\nstep start\n", Err) && Err.find("before any 'who'") != std::string::npos, Err);
        Check("five choices", !B.Parse("DCS 1\ncast X\nwho A\nstep start\nask Q? | a=start | b=start | c=start | d=start | e=start\n", Err) && Err.find("four") != std::string::npos, Err);
        Check("a bad pitch", !B.Parse("DCS 1\ncast X\nwho A\nvoice 12\nstep start\nsay hi\n", Err) && Err.find("0..11") != std::string::npos, Err);
    }

    // ---- numeric arguments ignore repeated ASCII spaces; pipe-separated choices keep empty fields
    {
        const std::string Head = "DCS 1\ncast ARGUMENTS\nwho Guide\n";
        const std::string Repeated = Head + "voice 7  1.05\nstep start\ngive TOKEN  2\nsay Ready.\nend\n";
        Cast Numeric;
        std::string E;
        const bool Loaded = Numeric.Parse(Repeated, E);
        Check("repeated-space numeric arguments parse", Loaded, E);
        const Script* S = Loaded ? Numeric.Find("Guide") : nullptr;
        Check("repeated spaces do not discard the requested voice rate", S && S->Pitch == 7 && S->Rate == 1.05);
        Conversation C;
        C.Bind(S);
        const Beat First = C.Talk();
        Check("repeated spaces preserve the requested gift amount", First.Text == "Ready."
            && First.Gifts.size() == 1 && First.Gifts[0].first == "TOKEN" && First.Gifts[0].second == 2);
        C.Talk();
        const Beat Again = C.Talk();
        Check("the parsed gift still emits only once across repeated talks", C.Has("gave_TOKEN")
            && Again.Text == "Ready." && Again.Gifts.empty());

        const std::string Defaults = Head + "voice 7\nstep start\ngive TOKEN\nsay Ready.\nend\n";
        Cast Defaulted;
        const bool DefaultLoaded = Defaulted.Parse(Defaults, E);
        const Script* D = DefaultLoaded ? Defaulted.Find("Guide") : nullptr;
        Conversation DefaultTalk;
        DefaultTalk.Bind(D);
        const Beat DefaultBeat = DefaultTalk.Talk();
        Check("omitted voice rate and gift amount retain defaults of one", D && D->Pitch == 7 && D->Rate == 1.0
            && DefaultBeat.Gifts.size() == 1 && DefaultBeat.Gifts[0].first == "TOKEN" && DefaultBeat.Gifts[0].second == 1, E);

        for (const char* Rate : {"2.1", "0.49"})
        {
            Cast Bad;
            const bool Refused = !Bad.Parse(Head + "voice 7  " + Rate + "\nstep start\nsay hi\nend\n", E);
            Check(std::string("repeated-space out-of-range voice rate refuses: ") + Rate,
                Refused && E.rfind("line 4:", 0) == 0 && E.find("rate is 0.5..2") != std::string::npos, E);
        }
        for (const char* Amount : {"1000", "0"})
        {
            Cast Bad;
            const bool Refused = !Bad.Parse(Head + "step start\ngive TOKEN  " + Amount + "\nend\n", E);
            Check(std::string("repeated-space out-of-range gift amount refuses: ") + Amount,
                Refused && E.rfind("line 5:", 0) == 0 && E.find("1..999") != std::string::npos, E);
        }

        Cast BadChoice;
        Check("an empty pipe-separated choice still refuses", !BadChoice.Parse(Head
            + "step start\nask Choose? | First=start || Last=start\nend\n", E)
            && E.rfind("line 5:", 0) == 0 && E.find("choice") != std::string::npos, E);

        Cast Retained;
        const bool Seeded = Retained.Parse(Defaults, E);
        const bool Rejected = !Retained.Parse("DCS 1\ncast REPLACED\nwho Other\nstep start\ngive TOKEN  1000\nend\n", E);
        const Script* Kept = Retained.Find("Guide");
        Check("a refused repeated-space amount preserves the previous cast", Seeded && Rejected
            && Retained.Realm == "ARGUMENTS" && Retained.Scripts.size() == 1 && Kept && Kept->Pitch == 7 && Kept->Rate == 1.0);
    }

    // ---- numeric tokens must parse completely; malformed/non-finite rates never reach dialogue rendering
    {
        const std::string Head = "DCS 1\ncast NUMBERS\nwho Guide\n";
        std::string E;
        for (const char* Pitch : {"frogs", "7cats"})
        {
            Cast Bad;
            const bool Refused = !Bad.Parse(Head + "voice " + Pitch + "\nstep start\nsay hi\nend\n", E);
            Check(std::string("a pitch must be a complete integer token: ") + Pitch,
                Refused && E.rfind("line 4:", 0) == 0 && E.find("pitch is 0..11") != std::string::npos, E);
        }
        for (const char* Rate : {"nan", "NaN(payload)", "1.05x"})
        {
            Cast Bad;
            const bool Refused = !Bad.Parse(Head + "voice 7 " + Rate + "\nstep start\nsay hi\nend\n", E);
            Check(std::string("a voice rate must be a complete finite number: ") + Rate,
                Refused && E.rfind("line 4:", 0) == 0 && E.find("rate is 0.5..2") != std::string::npos, E);
        }
        for (const char* Amount : {"2items", "2.5"})
        {
            Cast Bad;
            const bool Refused = !Bad.Parse(Head + "step start\ngive TOKEN " + Amount + "\nend\n", E);
            Check(std::string("a gift amount must be a complete integer token: ") + Amount,
                Refused && E.rfind("line 5:", 0) == 0 && E.find("give amount is 1..999") != std::string::npos, E);
        }

        struct ValidVoice { const char* Arguments; int Pitch; double Rate; };
        const ValidVoice Voices[] = {{"0 .5", 0, 0.5}, {"11 2", 11, 2.0}, {"7 1.05e0", 7, 1.05}};
        for (const auto& Voice : Voices)
        {
            Cast Good;
            const bool Loaded = Good.Parse(Head + "voice " + Voice.Arguments + "\nstep start\nsay hi\nend\n", E);
            const Script* S = Loaded ? Good.Find("Guide") : nullptr;
            Check(std::string("valid voice bounds and numeric forms retain their values: ") + Voice.Arguments,
                S && S->Pitch == Voice.Pitch && S->Rate == Voice.Rate, E);
        }
        Cast Gift;
        const bool Loaded = Gift.Parse(Head + "step start\ngive TOKEN +999\nend\n", E);
        const Script* S = Loaded ? Gift.Find("Guide") : nullptr;
        const Step* Start = S ? S->Find("start") : nullptr;
        Check("an explicit plus sign and the inclusive gift maximum remain valid", Start && !Start->Nodes.empty()
            && Start->Nodes[0].K == Node::Kind::Give && Start->Nodes[0].Text == "TOKEN" && Start->Nodes[0].Amount == 999, E);
    }

    // ---- restored cursors must be nonnegative before a conversation resumes
    {
        Cast Synthetic;
        std::string E;
        const bool Loaded = Synthetic.Parse("DCS 1\ncast RESTORE\nwho Guide\nstep start\ngive TOKEN 1\nsay Ready.\nend\n", E);
        const Script* S = Loaded ? Synthetic.Find("Guide") : nullptr;
        const Step* Start = S ? S->Find("start") : nullptr;
        const bool ScriptReady = Start && Start->Nodes.size() == 3;
        struct RestoreCase { const char* Saved; const char* Expected; const char* Label; };
        const RestoreCase Cases[] = {
            {"start:-1 gave_TOKEN remembered", "start:0", "negative cursor -1 restarts safely and retains gift suppression"},
            {"start:-20 gave_TOKEN remembered", "start:0", "negative cursor -20 restarts safely and retains gift suppression"},
            {"start:1 gave_TOKEN remembered", "start:1", "a valid saved cursor and flags retain their position"},
            {"missing:1 gave_TOKEN remembered", "start:0", "an unknown step still falls back to start with flags intact"},
            {"start gave_TOKEN remembered", "start:0", "legacy omitted-node saves still restore cursor zero and flags"}
        };
        for (const auto& Saved : Cases)
        {
            Conversation C;
            C.Bind(S);
            C.Restore(Saved.Saved);
            // Both expected positions are known nonnegative nodes in this three-node script. Never resume a
            // negative baseline cursor: a failed safety assertion must not cause an out-of-range Talk access.
            const bool Safe = ScriptReady && C.Where() == Saved.Expected;
            Beat B;
            if (Safe) B = C.Talk();
            Check(Saved.Label, Safe && C.Has("gave_TOKEN") && C.Has("remembered")
                && !B.Over && B.Text == "Ready." && B.Gifts.empty(), E);
        }
    }

    // ---- pending choices belong to the currently bound, unrestored conversation only
    {
        Cast Synthetic;
        std::string E;
        const bool Loaded = Synthetic.Parse("DCS 1\ncast LIFECYCLE\nwho A\nstep start\nask A question? | Continue=shared\nend\n"
            "step shared\nsay A answer.\nend\nwho B\nstep start\nsay Greeting.\nask B question? | Proceed=shared\nend\n"
            "step shared\ngive TOKEN 1\nsay Answer.\nend\n", E);
        const Script* A = Loaded ? Synthetic.Find("A") : nullptr;
        const Script* B = Loaded ? Synthetic.Find("B") : nullptr;
        Conversation C;
        C.Bind(A);
        const Beat PendingA = C.Talk();
        C.Bind(B);
        const Beat StaleBind = C.Picked(0);
        Check("binding another script invalidates the previous script's pending choice", A && B
            && PendingA.Choices.size() == 1 && StaleBind.Over && StaleBind.Gifts.empty() && !C.Has("gave_TOKEN"), E);
        const Beat Greeting = C.Talk();
        const Beat Question = C.Talk();
        const Beat Answer = C.Picked(0);
        C.Talk();
        const Beat AgainGreeting = C.Talk();
        const Beat AgainQuestion = C.Talk();
        const Beat AgainAnswer = C.Picked(0);
        Check("the new script's own fresh choice still gives its token once", Greeting.Text == "Greeting."
            && Question.Choices == std::vector<std::string>{"Proceed"} && Answer.Text == "Answer."
            && Answer.Gifts.size() == 1 && Answer.Gifts[0].first == "TOKEN" && Answer.Gifts[0].second == 1
            && AgainGreeting.Text == "Greeting." && AgainQuestion.Choices == std::vector<std::string>{"Proceed"}
            && AgainAnswer.Text == "Answer." && AgainAnswer.Gifts.empty() && C.Has("gave_TOKEN"));

        Conversation Restored;
        Restored.Bind(B);
        Restored.Talk();
        const Beat PendingRestore = Restored.Talk();
        Restored.Restore("start:0 remembered");
        const Beat StaleRestore = Restored.Picked(0);
        Check("restore invalidates an old pending choice and retains restored flags", B && PendingRestore.Choices.size() == 1
            && StaleRestore.Over && StaleRestore.Gifts.empty() && Restored.Has("remembered") && !Restored.Has("gave_TOKEN"));
        const Beat RestoredGreeting = Restored.Talk();
        const Beat RestoredQuestion = Restored.Talk();
        const Beat RestoredAnswer = Restored.Picked(0);
        Check("fresh choices after restore still follow the script and emit the gift", RestoredGreeting.Text == "Greeting."
            && RestoredQuestion.Choices == std::vector<std::string>{"Proceed"} && RestoredAnswer.Text == "Answer."
            && RestoredAnswer.Gifts.size() == 1 && RestoredAnswer.Gifts[0].first == "TOKEN"
            && RestoredAnswer.Gifts[0].second == 1 && Restored.Has("remembered") && Restored.Has("gave_TOKEN"));

        Conversation Paid;
        Paid.Bind(B);
        Paid.Talk(); Paid.Talk();
        Paid.Restore("start:0 remembered gave_TOKEN");
        const Beat PaidStale = Paid.Picked(0);
        const Beat PaidGreeting = Paid.Talk();
        const Beat PaidQuestion = Paid.Talk();
        const Beat PaidAnswer = Paid.Picked(0);
        Check("clearing a restored pending choice preserves the existing gift guard", B && PaidStale.Over && PaidStale.Gifts.empty()
            && PaidGreeting.Text == "Greeting." && PaidQuestion.Choices == std::vector<std::string>{"Proceed"}
            && PaidAnswer.Text == "Answer." && PaidAnswer.Gifts.empty() && Paid.Has("remembered") && Paid.Has("gave_TOKEN"));
    }

    // ---- Curator Vell: the quest branch, remembered across talks
    {
        Conversation C;
        C.Bind(G.Find("Curator Vell"));
        Beat B = C.Talk();
        Check("the first talk opens with the welcome", !B.Over && B.Text.rfind("Welcome", 0) == 0 && B.Choices.empty(), B.Text);
        B = C.Talk();
        Check("then the Heartstone", B.Text.find("Heartstone") != std::string::npos);
        B = C.Talk();
        Check("then the question with two choices", B.Choices.size() == 2 && B.Choices[0] == "Of course" && B.Choices[1] == "Not now");
        B = C.Picked(1);
        Check("'Not now' says come back and ends", B.Text.rfind("Come back", 0) == 0 && !B.Over);
        B = C.Talk();
        Check("the talk is over after the end", B.Over);
        Check("nothing was set", C.Flags().empty());
        // talk again: the same welcome; accept this time
        C.Talk(); C.Talk(); C.Talk();
        B = C.Picked(0);
        Check("'Of course' sets the quest flag and thanks you", C.Has("heartstone") && B.Text.rfind("Thank you", 0) == 0, B.Text);
        Check("and ends", C.Talk().Over);
        B = C.Talk();
        Check("the next talk starts at 'waiting' through the if", B.Text.rfind("Any word", 0) == 0, B.Text);
        const std::string Saved = C.Save();
        Conversation D;
        D.Bind(G.Find("Curator Vell"));
        D.Restore(Saved);
        Check("a conversation saves its place and flags in one line", Saved.find("heartstone") != std::string::npos && D.Has("heartstone") && D.Where() == C.Where(), Saved);
        B = C.Talk();
        B = C.Picked(1);
        Check("'I have it' sets done and hands over the plate", C.Has("heartstone_done") && B.Text.find("Frame Plate") != std::string::npos
            && B.Gifts.size() == 1 && B.Gifts[0].first == "FRAME_PLATE" && B.Gifts[0].second == 1 && C.Has("gave_FRAME_PLATE"), B.Text);
        C.Talk();
        B = C.Talk();
        Check("after that, thanks every time", B.Text.rfind("The Choir sang", 0) == 0, B.Text);
    }

    // ---- the Echo Choir: a flag set on one character does not leak into another
    {
        Conversation C;
        C.Bind(G.Find("Echo Choir"));
        Beat B = C.Talk();
        Check("the Choir is silent until the Heartstone is back", B.Text == "..." && !C.Has("heartstone_done"));
        Conversation D;
        D.Bind(G.Find("Echo Choir"));
        D.Restore("start:0 heartstone_done");   // the host copies realm-wide flags in when it binds
        Check("with the flag, the Choir sings", D.Talk().Text.find("sing") != std::string::npos);
    }

    // ---- a three-way ask
    {
        Conversation C;
        C.Bind(G.Find("Frame-Hanger Twins"));
        C.Talk(); C.Talk();
        Beat B = C.Talk();
        Check("three choices", B.Choices.size() == 3);
        Check("the middle one leads to the vats", C.Picked(1).Text.find("Vats are") == 0);
    }

    // ---- an unbound or finished conversation is harmless
    {
        Conversation C;
        Check("unbound: over at once", C.Talk().Over && C.Picked(0).Over);
    }

    // ---- gifts pay once and name items of the realm's catalog
    {
        Cast B;
        std::string E;
        Check("a gift needs an item", !B.Parse("DCS 1\ncast X\nwho A\nstep start\ngive\n", E) && E.find("item id") != std::string::npos, E);
        Check("a gift amount is bounded", !B.Parse("DCS 1\ncast X\nwho A\nstep start\ngive X 1000\n", E) && E.find("1..999") != std::string::npos, E);
        Cast P;
        P.Parse(ReadAll(Dir + "/parcels.dcs"), E);
        Conversation H;
        H.Bind(P.Find("Beekeeper Hollis"));
        H.Restore("start:0 route");
        Beat Bt = H.Talk();
        Check("Hollis hands over two honey jars with the stamped route", Bt.Gifts.size() == 1 && Bt.Gifts[0].first == "HONEY_JAR" && Bt.Gifts[0].second == 2 && H.Has("route_done"), Bt.Text);
        H.Talk();
        Bt = H.Talk();
        Check("and never twice", Bt.Gifts.empty() && Bt.Text.find("honey's holding") != std::string::npos, Bt.Text);
        // every gift in every cast names an item of that realm's catalog
        for (const char* F : {"gallery-city", "parcels", "bricks", "labyrinth", "world-zero"})
        {
            Cast C;
            C.Parse(ReadAll(Dir + "/" + F + ".dcs"), E);
            const std::string Dic = ReadAll(Dir + "/../Inventory/" + F + ".dic");
            bool AllKnown = true;
            int Gifts = 0;
            for (const Script& S : C.Scripts) for (const Step& T : S.Steps) for (const Node& N : T.Nodes)
                if (N.K == Node::Kind::Give) { ++Gifts; AllKnown &= Dic.find("item " + N.Text + " ") != std::string::npos; }
            Check(std::string(F) + ": every gift is an item of its realm's catalog", AllKnown && Gifts >= 3, std::to_string(Gifts));
        }
    }

    // ---- every shipped cast parses, and each has a quest chain that sets a flag
    for (const char* F : {"parcels", "bricks", "labyrinth", "world-zero"})
    {
        Cast C;
        std::string E;
        const bool Loaded = C.Parse(ReadAll(Dir + "/" + F + ".dcs"), E);
        Check(std::string("the ") + F + " cast parses", Loaded, E);
        if (!Loaded) continue;
        int Flags = 0, Asks = 0;
        for (const Script& S : C.Scripts) for (const Step& T : S.Steps) for (const Node& N : T.Nodes) { Flags += N.K == Node::Kind::Set; Asks += N.K == Node::Kind::Ask; }
        const bool Hub = std::string(F) == "world-zero";   // the six cross-realm NPCs (REALM-CASTS build order 1)
        Check(std::string(F) + (Hub ? ": six cross-realm roles, flags and questions" : ": at least ten roles, flags and questions"),
              (Hub ? C.Scripts.size() == 6 : C.Scripts.size() >= 10) && Flags >= 5 && Asks >= (Hub ? 6 : 8), std::to_string(C.Scripts.size()) + " " + std::to_string(Flags) + " " + std::to_string(Asks));
    }
    {
        // Zee's stock follows the realms visited: the realm casts set visited_* and Zee reads them through the
        // shared flags; the first matching branch wins, so the most recent realm must be tested first.
        Cast Z;
        std::string E;
        Z.Parse(ReadAll(Dir + "/world-zero.dcs"), E);
        const Script* S = Z.Find("Wandering Merchant Zee");
        Conversation Fresh, Back;
        bool ScriptFound = S != nullptr;
        std::string First, Stock;
        if (S)
        {
            Fresh.Bind(S); First = Fresh.Talk().Text;
            Back.Bind(S); Back.Restore("start:0 visited_gallery"); Stock = Back.Talk().Text;
        }
        Check("Zee without travel has no stock; after the galleries, gallery goods", ScriptFound && First.find("Stock follows") != std::string::npos && Stock.find("galleries") != std::string::npos, First + " | " + Stock);
    }
    {
        // The Riddler's door and the Apprentice share a realm-wide flag: the host copies it in on bind.
        Cast L;
        std::string E;
        L.Parse(ReadAll(Dir + "/labyrinth.dcs"), E);
        Conversation R;
        R.Bind(L.Find("Gate Riddler"));
        R.Talk(); R.Talk(); R.Talk();
        Check("the right answer opens the door", R.Picked(0).Text.find("The door is yours") != std::string::npos && R.Has("riddle_done"));
        Conversation A;
        A.Bind(L.Find("The Architect's Apprentice"));
        A.Restore("start:0 " + std::string("riddle_done"));
        Check("and the Apprentice tells the story once it is open", A.Talk().Text.find("cut it") != std::string::npos);
    }

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
