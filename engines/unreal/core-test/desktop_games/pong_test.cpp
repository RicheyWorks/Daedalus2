// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPongCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace daedalus::desktop;
int main(int argc,char** argv) {
    int checks=0,failed=0;
    auto check=[&](bool ok,const char* what) { ++checks; if(!ok) {++failed; std::cerr<<"FAIL "<<what<<'\n';} };
    std::ifstream f(argc>1 ? argv[1] : "pong_parity.txt"); check(bool(f),"source fixture exists");
    std::string line; int cases=0;
    while(std::getline(f,line)) {
        if(line.empty() || line[0]=='#' || line=="PONG 1") continue;
        std::istringstream row(line); std::string name; PongGame g,expected; Input i;
        row>>name>>g.S.PlayerY>>g.S.ComputerY>>g.S.BallX>>g.S.BallY>>g.S.BallVX>>g.S.BallVY>>g.S.PlayerScore>>g.S.ComputerScore
           >>i.Up>>i.Down>>i.AxisY>>expected.S.PlayerY>>expected.S.ComputerY>>expected.S.BallX>>expected.S.BallY
           >>expected.S.BallVX>>expected.S.BallVY>>expected.S.PlayerScore>>expected.S.ComputerScore;
        check(!row.fail(),"fixture parses"); g.Step(i); ++cases;
        check(g.S.PlayerY==expected.S.PlayerY && g.S.ComputerY==expected.S.ComputerY && g.S.BallX==expected.S.BallX &&
              g.S.BallY==expected.S.BallY && g.S.BallVX==expected.S.BallVX && g.S.BallVY==expected.S.BallVY &&
              g.S.PlayerScore==expected.S.PlayerScore && g.S.ComputerScore==expected.S.ComputerScore,"latest source numeric parity");
    }
    check(cases==11,"all source cases replayed");
    PongGame g; Input up; up.Up=true; g.S.PlayerY=2; g.Step(up); check(g.S.PlayerY==0,"enhancement keyboard clamps");
    g.Reset(0); g.S.BallX=60; g.S.BallY=300; g.S.BallVX=5; g.Step({}); check(g.S.BallVX==5,"enhancement outgoing paddle does not reflip");
    g.Reset(0); g.S.BallY=593; g.S.BallVY=-3; g.Step({}); check(g.S.BallVY==-3,"enhancement outgoing wall does not reflip");
    g.S.PlayerScore=99; g.Reset(42); check(g.S.PlayerScore==0 && g.S.BallX==400 && g.S.PlayerY==250,"restart clears complete state");
    Frame frame; g.Render(frame); check(frame.Commands.size()==6 && frame.Width==800 && frame.Height==600,"source presentation frame");
    g.S.ComputerScore=std::numeric_limits<std::int64_t>::max(); g.S.BallX=1;g.S.BallVX=-5;g.Step({});
    check(g.S.ComputerScore==std::numeric_limits<std::int64_t>::max(),"score overflow bounded");
    std::cout<<"Pong: "<<checks-failed<<'/'<<checks<<" checks passed\n";
    return failed ? 1 : 0;
}
