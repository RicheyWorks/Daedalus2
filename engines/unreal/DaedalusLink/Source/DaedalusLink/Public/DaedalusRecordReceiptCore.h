// SPDX-License-Identifier: MIT
#pragma once
#include <charconv>
#include <cstdint>
#include <limits>
#include <string>
#include <utility>
#include <vector>
#include "DaedalusLandRegistryCore.h"
namespace daedalus { namespace records {
struct WriteExpectation {std::string Realm,Key,SHA256;std::uint64_t StoreRevision=0;};
struct WriteReply {std::string Result,Realm,Key,RevisionHeader,HeaderSHA256,BodySHA256;};
inline bool Hash(const std::string& Value){
    if(Value.size()!=64)return false;
    for(char C:Value)if(!((C>='0'&&C<='9')||(C>='a'&&C<='f')))return false;
    return true;
}
inline bool Revision(const std::string& Text,std::uint64_t& Out){
    if(Text.empty()||Text.size()>19||(Text.size()>1&&Text[0]=='0'))return false;
    for(char C:Text)if(C<'0'||C>'9')return false;
    std::uint64_t Value=0;auto Parsed=std::from_chars(Text.data(),Text.data()+Text.size(),Value);
    if(Parsed.ec!=std::errc()||Parsed.ptr!=Text.data()+Text.size()||Value>static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()))return false;
    Out=Value;return true;
}
inline bool ParseWriteReply(const std::string& Json,const std::string& RevisionHeader,const std::string& HashHeader,WriteReply& Out){
    // This endpoint's identifier/hash fields are ASCII and need no JSON escapes.
    // Restrict the reused reader's broader escape grammar at this DTO boundary.
    if(Json.size()>4096||Json.find('\\')!=std::string::npos)return false;
    landreg::Value Root;std::string Error;
    if(!landreg::Reader(Json).Parse(Root,Error)||Root.K!=landreg::Value::Object||Root.O.size()!=5)return false;
    for(std::size_t I=0;I<Root.O.size();++I)
        for(std::size_t J=I+1;J<Root.O.size();++J)if(Root.O[I].first==Root.O[J].first)return false;
    WriteReply Next;Next.RevisionHeader=RevisionHeader;Next.HeaderSHA256=HashHeader;
    for(const auto& Field:Root.O){
        if(Field.first=="revision"){
            std::uint64_t BodyRevision=0,HeaderRevision=0;
            if(Field.second.K!=landreg::Value::Number||!Revision(Field.second.S,BodyRevision)||!Revision(RevisionHeader,HeaderRevision)||BodyRevision!=HeaderRevision)return false;
        }else{
            if(Field.second.K!=landreg::Value::String)return false;
            if(Field.first=="result")Next.Result=Field.second.S;
            else if(Field.first=="realm")Next.Realm=Field.second.S;
            else if(Field.first=="key")Next.Key=Field.second.S;
            else if(Field.first=="sha256")Next.BodySHA256=Field.second.S;
            else return false;
        }
    }
    if(Next.Result.empty()||Next.Realm.empty()||Next.Key.empty()||Next.BodySHA256.empty())return false;
    Out=std::move(Next);return true;
}
// Caller supplies parsed, duplicate-free fields from a completed no-redirect request.
// Failure is an unconfirmed write outcome: never cancel/republish a ledger candidate.
inline bool ConfirmWrite(bool TransportOK,int HttpStatus,const WriteExpectation& Expected,const WriteReply& Reply,std::uint64_t& CommittedStoreRevision){
    if(!TransportOK||HttpStatus!=200||Expected.Realm.empty()||Expected.Key.empty()||!Hash(Expected.SHA256))return false;
    if(Reply.Result!="UPDATED"&&Reply.Result!="REPLAY")return false;
    if(Reply.Realm!=Expected.Realm||Reply.Key!=Expected.Key||Reply.HeaderSHA256!=Expected.SHA256||Reply.BodySHA256!=Expected.SHA256)return false;
    std::uint64_t Observed=0;
    if(Expected.StoreRevision>=static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())||!Revision(Reply.RevisionHeader,Observed)||Observed!=Expected.StoreRevision+1)return false;
    CommittedStoreRevision=Observed;return true;
}
// A successful GET of the pinned record can reconcile a lost PUT reply.
// Compare actual candidate bytes, not just a claimed domain revision or UI balance.
inline bool ConfirmReadBack(bool TransportOK,int HttpStatus,const WriteExpectation& Expected,
    const std::vector<std::uint8_t>& Candidate,const std::vector<std::uint8_t>& Returned,
    const std::string& RevisionHeader,const std::string& HashHeader,std::uint64_t& CommittedStoreRevision){
    if(Candidate.empty()||Candidate.size()>8*1024*1024||Candidate!=Returned)return false;
    const WriteReply Reply{"REPLAY",Expected.Realm,Expected.Key,RevisionHeader,HashHeader,Expected.SHA256};
    return ConfirmWrite(TransportOK,HttpStatus,Expected,Reply,CommittedStoreRevision);
}
}}
