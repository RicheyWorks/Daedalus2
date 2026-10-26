// SPDX-License-Identifier: MIT
#include "DaedalusLocalSvgFiles.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

namespace DaedalusLocalSvgFiles
{
    namespace
    {
        bool ValidKind(Kind Type) { return Type==Kind::Blueprint || Type==Kind::Storyboard; }
        bool ValidId(const FString& Id)
        {
            if (Id.Len()!=32) return false;
            bool Nonzero=false;
            for (int32 I=0;I<Id.Len();++I)
            {
                const TCHAR C=Id[I];
                if (!((C>='0' && C<='9') || (C>='a' && C<='f'))) return false;
                if (C!='0') Nonzero=true;
            }
            return Nonzero;
        }
        bool Refuse(Kind Type,FString& Error,const TCHAR* Why)
        {
            Error=Why;
            if (Type==Kind::Storyboard) Error.ReplaceInline(TEXT("blueprint"),TEXT("flipbook"));
            return false;
        }
#if PLATFORM_WINDOWS
        FString Folder(Kind Type)
        {
            return Type==Kind::Blueprint?
                FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("Daedalus"),TEXT("BlueprintPrints"))):
                FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("Daedalus"),TEXT("GalleryMotif"),TEXT("Storyboards")));
        }
        class Handle
        {
        public:
            explicit Handle(HANDLE File):Value(File) {}
            ~Handle() { Close(); }
            Handle(const Handle&)=delete; Handle& operator=(const Handle&)=delete;
            bool Valid() const { return Value!=INVALID_HANDLE_VALUE && Value!=nullptr; }
            HANDLE Get() const { return Value; }
            bool Close() { if (!Valid()) return true; const HANDLE Previous=Value; Value=INVALID_HANDLE_VALUE; return ::CloseHandle(Previous)!=0; }
        private:
            HANDLE Value;
        };
#endif
    }
    FString Filename(Kind Type,const FString& Id)
    {
        if (!ValidKind(Type) || !ValidId(Id)) return FString();
        return (Type==Kind::Blueprint?TEXT("Blueprint_"):TEXT("Storyboard_"))+Id+TEXT(".svg");
    }
    bool WriteNewVerified(Kind Type,const FString& Id,const std::string& Bytes,FString& Error)
    {
        if (!ValidKind(Type)) { Error=TEXT("The print kind is unavailable. No print was started."); return false; }
        if (!ValidId(Id) || Bytes.empty() || Bytes.size()>MaxBytes)
            return Refuse(Type,Error,TEXT("The print could not be prepared. Your blueprint is unchanged."));
#if PLATFORM_WINDOWS
        const FString Directory=Folder(Type),Path=FPaths::Combine(Directory,Filename(Type,Id));
        if (!IFileManager::Get().MakeDirectory(*Directory,true)) return Refuse(Type,Error,TEXT("The print folder could not be prepared. Your blueprint is unchanged."));
        // Extracted unchanged from Blueprint Press's fresh-file protocol.
        // UE5.8's generic writer does not honor NoReplaceExisting; CREATE_NEW
        // does. Never delete/reuse a failed fresh file, including partial bytes.
        Handle File(::CreateFileW(*Path,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!File.Valid()) return Refuse(Type,Error,TEXT("A fresh print could not be created. Earlier files were not changed."));
        DWORD Written=0; const DWORD Size=static_cast<DWORD>(Bytes.size());
        const bool Wrote=::WriteFile(File.Get(),Bytes.data(),Size,&Written,nullptr)!=0 && Written==Size;
        const bool Flushed=Wrote && ::FlushFileBuffers(File.Get())!=0; const bool Closed=File.Close();
        if (!Wrote || !Flushed || !Closed) return Refuse(Type,Error,TEXT("The print could not be completed. Any fresh file is kept for review; your blueprint stays unchanged."));
        Handle Readback(::CreateFileW(*Path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!Readback.Valid()) return Refuse(Type,Error,TEXT("The print could not be confirmed. The new file is kept for review; your blueprint stays unchanged."));
        LARGE_INTEGER Length={};
        if (!::GetFileSizeEx(Readback.Get(),&Length) || Length.QuadPart!=static_cast<LONGLONG>(Bytes.size()))
            return Refuse(Type,Error,TEXT("Print readback length did not match. The new file is kept for review; no earlier print was changed."));
        std::string Back(Bytes.size(),'\0'); DWORD Received=0;
        const bool Read=::ReadFile(Readback.Get(),&Back[0],Size,&Received,nullptr)!=0 && Received==Size;
        const bool ReadClosed=Readback.Close();
        if (!Read || !ReadClosed || Back!=Bytes) return Refuse(Type,Error,TEXT("Exact print readback was not confirmed. The file is kept for review; your blueprint stays unchanged."));
        return true;
#else
        if (Type==Kind::Storyboard)
            return Refuse(Type,Error,TEXT("Local storyboard printing needs Windows in this edition. Your flipbook stays unchanged."));
        return Refuse(Type,Error,TEXT("Local blueprint printing needs Windows in this edition. Your workshop remains editable."));
#endif
    }
}
