// SPDX-License-Identifier: MIT
#pragma once
#include <charconv>
#include <cstdint>
#include <limits>
#include <string>
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
}}
