#pragma once

#include <windows.h>
#include <cstdint>

// Shared by the out-of-process controller reader and the in-game keyboard bridge.
// One writer owns the mapping. A reader accepts a snapshot only when sequence is
// even and unchanged around the copy, and GetTickCount() - tick is recent.
namespace companion {

constexpr wchar_t kMapName[] = L"Local\\DOA5LRInputLabPad_v2";
constexpr wchar_t kWriterMutexName[] = L"Local\\DOA5LRInputLabPadWriter_v2";
constexpr wchar_t kStopEventName[] = L"Local\\DOA5LRInputLabPadStop_v2";
constexpr std::uint32_t kMagic = 0x35504C49; // "ILP5"
constexpr std::uint32_t kVersion = 2;
constexpr DWORD kMaxAgeMs = 500;

struct alignas(4) SharedState {
    std::uint32_t magic;
    std::uint32_t version;
    volatile LONG sequence; // Odd while writing, even when a complete snapshot is ready.
    DWORD tick;
    DWORD changeTick; // Last change of any mapped controller command.
    DWORD writerPid;
    BYTE keys[256];         // Native DOA5LR DirectInput keyboard scan codes (0 or 0x80).
};

static_assert(sizeof(SharedState) == 280, "Shared controller protocol layout changed");

} // namespace companion
