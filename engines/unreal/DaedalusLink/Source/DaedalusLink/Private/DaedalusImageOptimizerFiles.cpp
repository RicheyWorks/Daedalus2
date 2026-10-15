// SPDX-License-Identifier: MIT
#include "DaedalusImageOptimizerFiles.h"

#if PLATFORM_WINDOWS
#include "Framework/Application/SlateApplication.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
#include <commdlg.h>
#include "Windows/HideWindowsPlatformTypes.h"

#pragma comment(lib, "Comdlg32.lib")

namespace
{
    constexpr int32 MaxImages = 8;
    constexpr int32 MaxImageBytes = 8 * 1024 * 1024;
    constexpr int64 MaxFrameBytes = 24LL * 1024 * 1024;
    constexpr int32 MaxOutputBytes = 32 * 1024 * 1024; // The native client also checks the aggregate job budget.
    constexpr int32 DialogCharacters = 32768;
    constexpr int32 MaxPathCharacters = 4096;
    constexpr int32 MaxAncestorDirectories = 128;

    class FLocalHandle
    {
    public:
        explicit FLocalHandle(HANDLE In) : Handle(In) {}
        ~FLocalHandle() { Close(); }
        FLocalHandle(const FLocalHandle&) = delete;
        FLocalHandle& operator=(const FLocalHandle&) = delete;
        bool Valid() const { return Handle != INVALID_HANDLE_VALUE && Handle != nullptr; }
        HANDLE Get() const { return Handle; }
        bool Close()
        {
            if (!Valid()) return true;
            const HANDLE Closing = Handle;
            Handle = INVALID_HANDLE_VALUE;
            return ::CloseHandle(Closing) != 0;
        }
    private:
        HANDLE Handle = INVALID_HANDLE_VALUE;
    };

    // This guard only owns the handle created by CREATE_NEW. No cleanup ever reopens a name.
    class FNewSibling
    {
    public:
        explicit FNewSibling(HANDLE In) : File(In) {}
        ~FNewSibling() { if (File.Valid() && !bCommitted) SetDisposition(true); }
        FNewSibling(const FNewSibling&) = delete;
        FNewSibling& operator=(const FNewSibling&) = delete;
        bool Valid() const { return File.Valid(); }
        HANDLE Get() const { return File.Get(); }
        bool ArmCleanup() { return SetDisposition(true); }
        bool Commit(HANDLE Parent, const FString& Leaf)
        {
            if (Parent == INVALID_HANDLE_VALUE || Parent == nullptr || Leaf.IsEmpty() || Leaf.Contains(TEXT("\\"))
                || Leaf.Contains(TEXT("/")) || Leaf.Contains(TEXT(":"))) return false;
            if (!SetDisposition(false)) return false;
            TArray<uint8> Storage;
            Storage.SetNumZeroed(static_cast<int32>(sizeof(FILE_RENAME_INFO) + static_cast<SIZE_T>(Leaf.Len()) * sizeof(WCHAR)));
            FILE_RENAME_INFO* Rename = reinterpret_cast<FILE_RENAME_INFO*>(Storage.GetData());
            Rename->ReplaceIfExists = 0;
            Rename->RootDirectory = Parent;
            Rename->FileNameLength = static_cast<DWORD>(Leaf.Len() * sizeof(WCHAR));
            FMemory::Memcpy(Rename->FileName, *Leaf, Rename->FileNameLength);
            if (!::SetFileInformationByHandle(File.Get(), FileRenameInfo, Rename, static_cast<DWORD>(Storage.Num())))
            { SetDisposition(true); return false; }
            bCommitted = true;
            return File.Close();
        }
    private:
        bool SetDisposition(bool bDelete)
        {
            FILE_DISPOSITION_INFO Disposition = {};
            Disposition.DeleteFile = bDelete ? 1 : 0;
            return ::SetFileInformationByHandle(File.Get(), FileDispositionInfo, &Disposition, static_cast<DWORD>(sizeof(Disposition))) != 0;
        }
        FLocalHandle File;
        bool bCommitted = false;
    };

    HWND DialogOwner()
    {
        if (!IsInGameThread() || !FSlateApplication::IsInitialized()) return nullptr;
        // Slate already knows the active game window; no editor/window enumeration is used.
        const void* Owner = FSlateApplication::Get().FindBestParentWindowHandleForDialogs(TSharedPtr<SWidget>());
        return static_cast<HWND>(const_cast<void*>(Owner));
    }

    bool LocalPath(const FString& Path)
    {
        // Reject devices, UNC/network paths and ambiguous drive-relative paths.
        if (Path.Len() < 3 || Path.Len() >= MaxPathCharacters || Path[1] != TEXT(':') || Path[2] != TEXT('\\')) return false;
        if (!((Path[0] >= TEXT('A') && Path[0] <= TEXT('Z')) || (Path[0] >= TEXT('a') && Path[0] <= TEXT('z')))) return false;
        for (int32 I = 2; I < Path.Len(); ++I)
            if (Path[I] < 32 || Path[I] == TEXT(':') || Path[I] == TEXT('/') || Path[I] == TEXT('*') || Path[I] == TEXT('?')
                || Path[I] == TEXT('<') || Path[I] == TEXT('>') || Path[I] == TEXT('|') || Path[I] == TEXT('"')) return false;
        int32 Start = 3;
        for (int32 I = Start; I <= Path.Len() && Start < Path.Len(); ++I)
        {
            if (I != Path.Len() && Path[I] != TEXT('\\')) continue;
            const FString Part = Path.Mid(Start, I - Start);
            if (Part.IsEmpty() || Part.EndsWith(TEXT(".")) || Part.EndsWith(TEXT(" "))) return false;
            int32 Dot = INDEX_NONE;
            Part.FindChar(TEXT('.'), Dot);
            const FString Stem = (Dot == INDEX_NONE ? Part : Part.Left(Dot)).ToUpper();
            if (Stem == TEXT("CON") || Stem == TEXT("PRN") || Stem == TEXT("AUX") || Stem == TEXT("NUL")
                || (Stem.Len() == 4 && (Stem.StartsWith(TEXT("COM")) || Stem.StartsWith(TEXT("LPT"))) && Stem[3] >= TEXT('1') && Stem[3] <= TEXT('9'))) return false;
            Start = I + 1;
        }
        const FString Root = Path.Left(3);
        const UINT Drive = ::GetDriveTypeW(*Root);
        return Drive == DRIVE_FIXED || Drive == DRIVE_REMOVABLE || Drive == DRIVE_RAMDISK;
    }

    bool FinalPath(HANDLE File, DWORD VolumeFormat, FString& Out)
    {
        TArray<WCHAR> Buffer;
        Buffer.SetNumZeroed(MaxPathCharacters + 64);
        const DWORD Length = ::GetFinalPathNameByHandleW(File, Buffer.GetData(), static_cast<DWORD>(Buffer.Num()), FILE_NAME_NORMALIZED | VolumeFormat);
        if (Length == 0 || Length >= static_cast<DWORD>(Buffer.Num())) return false;
        Out = FString(static_cast<int32>(Length), Buffer.GetData());
        return true;
    }

    bool FinalLocalPaths(HANDLE File, FString& DosPath, FString& VolumePath)
    {
        if (::GetFileType(File) != FILE_TYPE_DISK || !FinalPath(File, VOLUME_NAME_DOS, DosPath)
            || !DosPath.StartsWith(TEXT("\\\\?\\"))) return false;
        DosPath.RightChopInline(4);
        if (!LocalPath(DosPath) || !FinalPath(File, VOLUME_NAME_GUID, VolumePath)
            || !VolumePath.StartsWith(TEXT("\\\\?\\Volume{")) || VolumePath.Len() < 49
            || VolumePath[47] != TEXT('}') || VolumePath[48] != TEXT('\\')) return false;
        for (int32 I = 11; I < 47; ++I)
        {
            const TCHAR C = VolumePath[I];
            if (I == 19 || I == 24 || I == 29 || I == 34) { if (C != TEXT('-')) return false; }
            else if (!((C >= TEXT('0') && C <= TEXT('9')) || (C >= TEXT('a') && C <= TEXT('f')) || (C >= TEXT('A') && C <= TEXT('F')))) return false;
        }
        const UINT Drive = ::GetDriveTypeW(*VolumePath.Left(49));
        return Drive == DRIVE_FIXED || Drive == DRIVE_REMOVABLE || Drive == DRIVE_RAMDISK;
    }

    FString ChildPath(const FString& Parent, const FString& Leaf)
    {
        return Parent + (Parent.EndsWith(TEXT("\\")) ? TEXT("") : TEXT("\\")) + Leaf;
    }

    /** No-delete sharing pins each directory identity through leaf I/O, rename and cleanup.
     * Reparse points, mount points, mapped/network drives and unresolvable paths fail closed.
     */
    class FDirectoryLocks
    {
    public:
        bool AcquireParent(const FString& Path)
        {
            if (!LocalPath(Path)) return false;
            int32 LastSlash = INDEX_NONE;
            if (!Path.FindLastChar(TEXT('\\'), LastSlash) || LastSlash < 2 || LastSlash == Path.Len() - 1) return false;
            if (!Add(Path.Left(3), FString())) return false;
            int32 Start = 3;
            for (int32 At = 3; At <= LastSlash; ++At)
            {
                if (At != LastSlash && Path[At] != TEXT('\\')) continue;
                const FString Part = Path.Mid(Start, At - Start);
                if (Part.IsEmpty() || !Add(Path.Left(At), ChildPath(Directories.Last().VolumePath, Part))) return false;
                Start = At + 1;
            }
            return StillValid();
        }

        bool StillValid() const
        {
            if (Directories.IsEmpty()) return false;
            for (const FDirectory& Directory : Directories)
            {
                BY_HANDLE_FILE_INFORMATION Info = {};
                FString Dos, Volume;
                if (!::GetFileInformationByHandle(Directory.File->Get(), &Info)
                    || (Info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0 || (Info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0
                    || !FinalLocalPaths(Directory.File->Get(), Dos, Volume)
                    || !Dos.Equals(Directory.DosPath, ESearchCase::IgnoreCase) || !Volume.Equals(Directory.VolumePath, ESearchCase::IgnoreCase)) return false;
            }
            return true;
        }

        HANDLE ParentHandle() const { return Directories.IsEmpty() ? INVALID_HANDLE_VALUE : Directories.Last().File->Get(); }
        FString StableChild(const FString& Leaf) const { return Directories.IsEmpty() ? FString() : ChildPath(Directories.Last().VolumePath, Leaf); }
        bool OwnsRegularLeaf(HANDLE File, const FString& Leaf) const
        {
            BY_HANDLE_FILE_INFORMATION Info = {};
            FString Dos, Volume;
            return !Directories.IsEmpty() && ::GetFileInformationByHandle(File, &Info)
                && (Info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) == 0
                && FinalLocalPaths(File, Dos, Volume)
                && Dos.Equals(ChildPath(Directories.Last().DosPath, Leaf), ESearchCase::IgnoreCase)
                && Volume.Equals(StableChild(Leaf), ESearchCase::IgnoreCase);
        }

    private:
        struct FDirectory
        {
            TUniquePtr<FLocalHandle> File;
            FString DosPath;
            FString VolumePath;
        };
        TArray<FDirectory> Directories;

        bool Add(const FString& Path, const FString& ExpectedVolumePath)
        {
            if (Directories.Num() >= MaxAncestorDirectories || (!Directories.IsEmpty() && !StillValid())) return false;
            FDirectory Directory;
            // Deliberately omit FILE_SHARE_DELETE. OPEN_REPARSE_POINT applies to this component,
            // while previously retained ancestors prevent replacement of its pathname.
            Directory.File = MakeUnique<FLocalHandle>(::CreateFileW(*Path, FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, nullptr));
            if (!Directory.File->Valid()) return false;
            BY_HANDLE_FILE_INFORMATION Info = {};
            if (!::GetFileInformationByHandle(Directory.File->Get(), &Info)
                || (Info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0 || (Info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0
                || !FinalLocalPaths(Directory.File->Get(), Directory.DosPath, Directory.VolumePath)
                || !Directory.DosPath.Equals(Path, ESearchCase::IgnoreCase)
                || (!ExpectedVolumePath.IsEmpty() && !Directory.VolumePath.Equals(ExpectedVolumePath, ESearchCase::IgnoreCase))) return false;
            Directories.Add(MoveTemp(Directory));
            return true;
        }
    };

    bool TakeDialogString(const TArray<WCHAR>& Buffer, int32& At, FString& Out)
    {
        const int32 Start = At;
        while (At < Buffer.Num() && Buffer[At] != L'\0') ++At;
        if (At >= Buffer.Num()) return false;
        Out = FString(At - Start, Buffer.GetData() + Start);
        ++At;
        return true;
    }

    bool ReadSelection(const TArray<WCHAR>& Buffer, TArray<FString>& Paths)
    {
        int32 At = 0;
        FString First;
        if (!TakeDialogString(Buffer, At, First) || First.IsEmpty() || !LocalPath(First) || At >= Buffer.Num()) return false;
        if (Buffer[At] == L'\0') { Paths.Add(MoveTemp(First)); return true; }
        while (At < Buffer.Num() && Buffer[At] != L'\0')
        {
            FString Name;
            if (!TakeDialogString(Buffer, At, Name) || Name.IsEmpty() || Name == TEXT(".") || Name == TEXT("..")
                || Name.Contains(TEXT("\\")) || Name.Contains(TEXT("/")) || Name.Contains(TEXT(":")) || Paths.Num() >= MaxImages) return false;
            FString Full = First;
            if (!Full.EndsWith(TEXT("\\"))) Full += TEXT("\\");
            Full += Name;
            if (!LocalPath(Full)) return false;
            Paths.Add(MoveTemp(Full));
        }
        return At < Buffer.Num() && !Paths.IsEmpty();
    }

    uint8 DetectedImageType(const TArray<uint8>& Bytes)
    {
        static const uint8 Png[] = { 137, 80, 78, 71, 13, 10, 26, 10 };
        if (Bytes.Num() >= 8 && FMemory::Memcmp(Bytes.GetData(), Png, 8) == 0) return 1;
        if (Bytes.Num() >= 3 && Bytes[0] == 0xff && Bytes[1] == 0xd8 && Bytes[2] == 0xff) return 2;
        return 0;
    }

    FString DisplayName(const FString& Path)
    {
        FString Name = FPaths::GetCleanFilename(Path);
        for (int32 I = 0; I < Name.Len(); ++I) if (Name[I] < 32 || Name[I] == 127) Name[I] = TEXT('_');
        return Name.Left(128);
    }

    bool ReadImage(const FString& Path, FDaedalusImageOptimizerImage& Out)
    {
        const FString Ext = FPaths::GetExtension(Path).ToLower();
        if (Ext != TEXT("png") && Ext != TEXT("jpg") && Ext != TEXT("jpeg")) return false;
        FDirectoryLocks Parents;
        if (!Parents.AcquireParent(Path)) return false;
        const FString Leaf = FPaths::GetCleanFilename(Path);
        const FString StablePath = Parents.StableChild(Leaf);
        FLocalHandle File(::CreateFileW(*StablePath, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!File.Valid() || !Parents.StillValid() || !Parents.OwnsRegularLeaf(File.Get(), Leaf)) return false;
        BY_HANDLE_FILE_INFORMATION Info = {};
        LARGE_INTEGER Size = {};
        if (!::GetFileInformationByHandle(File.Get(), &Info) || (Info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0
            || !::GetFileSizeEx(File.Get(), &Size) || Size.QuadPart < 1 || Size.QuadPart > MaxImageBytes) return false;
        Out.Bytes.SetNumUninitialized(static_cast<int32>(Size.QuadPart));
        int32 At = 0;
        while (At < Out.Bytes.Num())
        {
            const DWORD Wanted = static_cast<DWORD>(FMath::Min(1024 * 1024, Out.Bytes.Num() - At));
            DWORD Read = 0;
            if (!::ReadFile(File.Get(), Out.Bytes.GetData() + At, Wanted, &Read, nullptr) || Read != Wanted) return false;
            At += static_cast<int32>(Read);
        }
        uint8 Extra = 0;
        DWORD Read = 0;
        LARGE_INTEGER FinalSize = {};
        if (!::ReadFile(File.Get(), &Extra, 1, &Read, nullptr) || Read != 0 || !::GetFileSizeEx(File.Get(), &FinalSize) || FinalSize.QuadPart != Size.QuadPart) return false;
        Out.Type = DetectedImageType(Out.Bytes);
        if ((Out.Type == 1 && Ext != TEXT("png")) || (Out.Type == 2 && Ext != TEXT("jpg") && Ext != TEXT("jpeg")) || Out.Type == 0) return false;
        Out.DisplayName = DisplayName(Path);
        return true;
    }
}
#endif

bool DaedalusImageOptimizerFiles::Supported()
{
#if PLATFORM_WINDOWS
    return true;
#else
    return false;
#endif
}

bool DaedalusImageOptimizerFiles::SelectImages(TArray<FDaedalusImageOptimizerImage>& Out, FString& Error)
{
    Out.Reset();
    Error.Reset();
#if PLATFORM_WINDOWS
    const HWND Owner = DialogOwner();
    if (!Owner) { Error = TEXT("Open the image workbench in a game window before choosing files."); return false; }
    TArray<WCHAR> Buffer;
    Buffer.SetNumZeroed(DialogCharacters);
    OPENFILENAMEW Dialog = {};
    Dialog.lStructSize = static_cast<DWORD>(sizeof(Dialog));
    Dialog.hwndOwner = Owner;
    Dialog.lpstrFilter = L"Images (PNG or JPEG)\0*.png;*.jpg;*.jpeg\0\0";
    Dialog.lpstrFile = Buffer.GetData();
    Dialog.nMaxFile = static_cast<DWORD>(Buffer.Num());
    Dialog.lpstrTitle = L"Choose up to 8 images for Image Optimizer";
    Dialog.Flags = OFN_EXPLORER | OFN_ALLOWMULTISELECT | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_DONTADDTORECENT | OFN_HIDEREADONLY;
    if (!::GetOpenFileNameW(&Dialog))
    {
        if (::CommDlgExtendedError() != 0) Error = TEXT("The file chooser could not complete. Choose fewer images or shorter local filenames.");
        return false;
    }
    TArray<FString> Paths;
    if (!ReadSelection(Buffer, Paths) || Paths.Num() > MaxImages) { Error = TEXT("Choose 1 to 8 images from a local drive."); return false; }
    TArray<FDaedalusImageOptimizerImage> Pending;
    int64 FrameBytes = 15; // IOP1 magic/count/settings; each image adds its type and byte count.
    for (const FString& Path : Paths)
    {
        FDaedalusImageOptimizerImage Image;
        if (!ReadImage(Path, Image)) { Error = TEXT("Each image must be a readable PNG or JPEG, match its extension, and be at most 8 MiB."); return false; }
        FrameBytes += 5 + Image.Bytes.Num();
        if (FrameBytes > MaxFrameBytes) { Error = TEXT("Choose a smaller batch. Images and request framing must fit within 24 MiB."); return false; }
        Pending.Add(MoveTemp(Image));
    }
    Out = MoveTemp(Pending);
    return true;
#else
    Error = TEXT("Image selection is available on Windows only.");
    return false;
#endif
}

bool DaedalusImageOptimizerFiles::SaveImage(const TArray<uint8>& Bytes, uint8 Type, int32 Index, FString& Error)
{
    return SaveImage(Bytes, Type, Index, Error, []() { return true; });
}

bool DaedalusImageOptimizerFiles::SaveImage(const TArray<uint8>& Bytes, uint8 Type, int32 Index, FString& Error,
    TFunctionRef<bool()> IsStillAllowed)
{
    Error.Reset();
#if PLATFORM_WINDOWS
    const auto StillAllowed = [&Error, IsStillAllowed]()
    {
        if (IsStillAllowed()) return true;
        Error = TEXT("Export no longer belongs to the open terminal.");
        return false;
    };
    if (!StillAllowed()) return false;
    // This is a bounded signature/type envelope check, not structural image decoding.
    if (Index < 1 || Index > MaxImages || (Type != 1 && Type != 2) || Bytes.IsEmpty()
        || Bytes.Num() > MaxOutputBytes || DetectedImageType(Bytes) != Type)
    { Error = TEXT("The companion did not return the expected PNG or JPEG within the 32 MiB output limit."); return false; }
    const HWND Owner = DialogOwner();
    if (!Owner) { Error = TEXT("Open the image workbench in a game window before exporting."); return false; }
    TArray<WCHAR> Buffer;
    Buffer.SetNumZeroed(DialogCharacters);
    const FString Suggested = FString::Printf(TEXT("image-%d.%s"), Index, Type == 1 ? TEXT("png") : TEXT("jpg"));
    FMemory::Memcpy(Buffer.GetData(), *Suggested, Suggested.Len() * sizeof(WCHAR));
    OPENFILENAMEW Dialog = {};
    Dialog.lStructSize = static_cast<DWORD>(sizeof(Dialog));
    Dialog.hwndOwner = Owner;
    Dialog.lpstrFilter = Type == 1 ? L"PNG image\0*.png\0\0" : L"JPEG image\0*.jpg;*.jpeg\0\0";
    Dialog.lpstrDefExt = Type == 1 ? L"png" : L"jpg";
    Dialog.lpstrFile = Buffer.GetData();
    Dialog.nMaxFile = static_cast<DWORD>(Buffer.Num());
    Dialog.lpstrTitle = L"Export optimized image to a new file";
    Dialog.Flags = OFN_EXPLORER | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_DONTADDTORECENT | OFN_HIDEREADONLY;
    const bool bSelected = ::GetSaveFileNameW(&Dialog) != FALSE;
    // Modal dialogs may dispatch ownership/close events before returning to this stack.
    if (!StillAllowed()) return false;
    if (!bSelected)
    {
        if (::CommDlgExtendedError() != 0) Error = TEXT("The save chooser could not complete. Choose a shorter local filename.");
        return false;
    }
    int32 At = 0;
    FString Destination;
    if (!TakeDialogString(Buffer, At, Destination) || !LocalPath(Destination))
    { Error = TEXT("Choose a new image filename on a local drive."); return false; }
    const FString Extension = FPaths::GetExtension(Destination).ToLower();
    if ((Type == 1 && Extension != TEXT("png")) || (Type == 2 && Extension != TEXT("jpg") && Extension != TEXT("jpeg")))
    { Error = TEXT("The new filename must keep the output's PNG or JPEG extension."); return false; }
    FDirectoryLocks Parents; // Declared before the temporary so cleanup runs under all retained locks.
    if (!Parents.AcquireParent(Destination)) { Error = TEXT("Choose a local folder without links or mount points and with a shorter directory chain."); return false; }
    const FString Leaf = FPaths::GetCleanFilename(Destination);
    const FString TemporaryLeaf = TEXT(".daedalus-") + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp");
    const FString TemporaryPath = Parents.StableChild(TemporaryLeaf);
    if (!StillAllowed()) return false;
    FNewSibling Temporary(::CreateFileW(*TemporaryPath, GENERIC_WRITE | DELETE | FILE_READ_ATTRIBUTES, 0, nullptr, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    if (!Temporary.Valid()) { Error = TEXT("A new image file could not be created in that location."); return false; }
    if (!Parents.StillValid() || !Parents.OwnsRegularLeaf(Temporary.Get(), TemporaryLeaf) || !Temporary.ArmCleanup())
    { Error = TEXT("A private local image file could not be prepared safely. Nothing was exported."); return false; }
    int32 Written = 0;
    while (Written < Bytes.Num())
    {
        if (!StillAllowed()) return false;
        const DWORD Wanted = static_cast<DWORD>(FMath::Min(1024 * 1024, Bytes.Num() - Written));
        DWORD Count = 0;
        if (!::WriteFile(Temporary.Get(), Bytes.GetData() + Written, Wanted, &Count, nullptr) || Count != Wanted)
        { Error = TEXT("The image could not be fully saved. No existing file was replaced."); return false; }
        Written += static_cast<int32>(Count);
    }
    if (!StillAllowed()) return false;
    if (!::FlushFileBuffers(Temporary.Get())) { Error = TEXT("The image could not be fully saved. No existing file was replaced."); return false; }
    if (!StillAllowed()) return false;
    // Rename the still-owned identity relative to its pinned parent. ReplaceIfExists remains false;
    // a destination created after the dialog survives, and cleanup never follows a reused temp name.
    if (!Parents.StillValid() || !Temporary.Commit(Parents.ParentHandle(), Leaf))
    { Error = TEXT("The image could not be committed. Choose a new filename; existing files are never replaced."); return false; }
    return true;
#else
    (void)Bytes;
    (void)Type;
    (void)Index;
    (void)IsStillAllowed;
    Error = TEXT("Image export is available on Windows only.");
    return false;
#endif
}
