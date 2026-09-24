#define _WIN32_WINNT 0x0A00
#define DIRECTINPUT_VERSION 0x0800
#include <windows.h>
#include <mmsystem.h>
#include <dinput.h>
#include <tlhelp32.h>
#include <array>
#include <cstdio>
#include <string>
#include <vector>
#include "companion_protocol.h"

// Poll physical controllers in this separate process. Loading DirectInput inside
// game.exe is enough to change DOA5LR's active input path on the test machine.
class PhysicalPadReader {
    struct Device {
        GUID id{};
        IDirectInputDevice8W* input = nullptr;
        bool useAxes = false;
        std::array<int, 128> buttons{};
        unsigned successfulPolls = 0;
        std::wstring name;
        std::wstring model;
    };

    HMODULE systemDll = nullptr;
    IDirectInput8W* directInput = nullptr;
    HWND window = nullptr;
    std::wstring profiles;
    std::vector<Device> devices;
    ULONGLONG lastEnumeration = 0;
    bool probe = false;

    using CreateFn = HRESULT(WINAPI*)(HINSTANCE, DWORD, REFIID, LPVOID*, LPUNKNOWN);

    static void put(std::array<BYTE, 256>& keys, int scan, bool pressed) {
        if (pressed && scan > 0 && scan < 256) keys[scan] = 0x80;
    }

    static BOOL CALLBACK onDevice(const DIDEVICEINSTANCEW* info, void* context) {
        auto* self = static_cast<PhysicalPadReader*>(context);
        for (const auto& existing : self->devices)
            if (existing.id == info->guidInstance) return DIENUM_CONTINUE;
        if (self->devices.size() >= 16) return DIENUM_STOP;

        IDirectInputDevice8W* input = nullptr;
        HRESULT createResult = self->directInput->CreateDevice(info->guidInstance, &input, nullptr);
        if (FAILED(createResult)) {
            if (self->probe) wprintf(L"%ls: CreateDevice=0x%08lX\n", info->tszProductName,
                                     (unsigned long)createResult);
            return DIENUM_CONTINUE;
        }
        DIPROPDWORD id{};
        id.diph.dwSize = sizeof(id);
        id.diph.dwHeaderSize = sizeof(id.diph);
        id.diph.dwHow = DIPH_DEVICE;
        HRESULT propertyResult = input->GetProperty(DIPROP_VIDPID, &id.diph);
        if (FAILED(propertyResult)) {
            if (self->probe) wprintf(L"%ls: VID/PID=0x%08lX\n", info->tszProductName,
                                     (unsigned long)propertyResult);
            input->Release();
            return DIENUM_CONTINUE;
        }
        wchar_t model[64];
        swprintf(model, 64, L"VID_%04X&PID_%04X", LOWORD(id.dwData), HIWORD(id.dwData));
        int enabled = GetPrivateProfileIntW(model, L"Enabled", 0, self->profiles.c_str());
        if (self->probe) wprintf(L"%ls [%ls] : profil=%d\n", info->tszProductName, model, enabled);
        if (enabled != 1) {
            input->Release();
            return DIENUM_CONTINUE;
        }

        HRESULT format = input->SetDataFormat(&c_dfDIJoystick2);
        HRESULT cooperative = SUCCEEDED(format)
            ? input->SetCooperativeLevel(self->window, DISCL_BACKGROUND | DISCL_NONEXCLUSIVE)
            : E_FAIL;
        if (FAILED(format) || FAILED(cooperative)) {
            if (self->probe)
                wprintf(L"%ls [%ls]: format=0x%08lX coop=0x%08lX\n",
                        info->tszProductName, model, (unsigned long)format, (unsigned long)cooperative);
            input->Release();
            return DIENUM_CONTINUE;
        }

        Device device;
        device.id = info->guidInstance;
        device.input = input;
        device.name = info->tszProductName;
        device.model = model;
        for (int button = 0; button < 128; ++button) {
            wchar_t key[24];
            swprintf(key, 24, L"Button%d", button);
            int scan = GetPrivateProfileIntW(model, key, 0, self->profiles.c_str());
            device.buttons[button] = scan > 0 && scan < 256 ? scan : 0;
        }

        // A per-axis range is accepted by more HID devices than a device-wide range.
        DIPROPRANGE range{};
        range.diph.dwSize = sizeof(range);
        range.diph.dwHeaderSize = sizeof(range.diph);
        range.diph.dwHow = DIPH_BYOFFSET;
        range.lMin = -32768;
        range.lMax = 32767;
        range.diph.dwObj = DIJOFS_X;
        bool xRange = SUCCEEDED(input->SetProperty(DIPROP_RANGE, &range.diph));
        range.diph.dwObj = DIJOFS_Y;
        bool yRange = SUCCEEDED(input->SetProperty(DIPROP_RANGE, &range.diph));
        device.useAxes = xRange && yRange &&
            GetPrivateProfileIntW(model, L"UseLeftStick", 1, self->profiles.c_str()) != 0;

        input->Acquire();
        self->devices.push_back(device);
        if (self->probe)
            wprintf(L"Trouv\x00E9 : %ls [%ls], stick=%ls\n", device.name.c_str(),
                    device.model.c_str(), device.useAxes ? L"oui" : L"non");
        return DIENUM_CONTINUE;
    }

    void refresh() {
        if (!directInput) return;
        ULONGLONG now = GetTickCount64();
        if (lastEnumeration && now - lastEnumeration < 1000) return;
        lastEnumeration = now;
        for (size_t i = 0; i < devices.size();) {
            if (SUCCEEDED(directInput->GetDeviceStatus(devices[i].id))) {
                ++i;
                continue;
            }
            devices[i].input->Unacquire();
            devices[i].input->Release();
            devices.erase(devices.begin() + i);
        }
        HRESULT enumerate = directInput->EnumDevices(DI8DEVCLASS_GAMECTRL, onDevice, this,
                                                      DIEDFL_ATTACHEDONLY);
        if (probe && FAILED(enumerate))
            wprintf(L"EnumDevices=0x%08lX\n", (unsigned long)enumerate);
    }

public:
    PhysicalPadReader(const std::wstring& gameDirectory, bool probeMode) : probe(probeMode) {
        profiles = gameDirectory;
        if (!profiles.empty() && profiles.back() != L'\\' && profiles.back() != L'/') profiles += L'\\';
        profiles += L"DOA5LR-ControllerProfiles.ini";
        window = CreateWindowExW(0, L"STATIC", L"DOA5LR InputLab controller reader",
                                 WS_OVERLAPPED, 0, 0, 1, 1, nullptr, nullptr,
                                 GetModuleHandleW(nullptr), nullptr);
        wchar_t system[MAX_PATH];
        UINT length = GetSystemDirectoryW(system, MAX_PATH);
        if (!length || length >= MAX_PATH) return;
        std::wstring path = std::wstring(system) + L"\\dinput8.dll";
        systemDll = LoadLibraryExW(path.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
        if (!systemDll) return;
        auto create = reinterpret_cast<CreateFn>(GetProcAddress(systemDll, "DirectInput8Create"));
        if (create)
            create(GetModuleHandleW(nullptr), DIRECTINPUT_VERSION, IID_IDirectInput8W,
                   reinterpret_cast<void**>(&directInput), nullptr);
    }

    ~PhysicalPadReader() {
        for (auto& device : devices) {
            device.input->Unacquire();
            device.input->Release();
        }
        if (directInput) directInput->Release();
        if (systemDll) FreeLibrary(systemDll);
        if (window) DestroyWindow(window);
    }

    bool ready() const { return directInput && window; }
    const std::wstring& profilePath() const { return profiles; }

    std::array<BYTE, 256> read() {
        std::array<BYTE, 256> keys{};
        refresh();
        for (auto& device : devices) {
            DIJOYSTATE2 state{};
            device.input->Poll();
            HRESULT hr = device.input->GetDeviceState(sizeof(state), &state);
            if (hr == DIERR_INPUTLOST || hr == DIERR_NOTACQUIRED) {
                device.input->Acquire();
                device.input->Poll();
                hr = device.input->GetDeviceState(sizeof(state), &state);
            }
            if (FAILED(hr)) continue;
            ++device.successfulPolls;
            DWORD pov = state.rgdwPOV[0];
            bool validPov = LOWORD(pov) != 0xffff && pov < 36000;
            put(keys, 17, (validPov && (pov >= 31500 || pov <= 4500)) ||
                          (device.useAxes && state.lY < -16000));
            put(keys, 31, (validPov && pov >= 13500 && pov <= 22500) ||
                          (device.useAxes && state.lY > 16000));
            put(keys, 30, (validPov && pov >= 22500 && pov <= 31500) ||
                          (device.useAxes && state.lX < -16000));
            put(keys, 32, (validPov && pov >= 4500 && pov <= 13500) ||
                          (device.useAxes && state.lX > 16000));
            for (int i = 0; i < 128; ++i)
                put(keys, device.buttons[i], (state.rgbButtons[i] & 0x80) != 0);
        }
        return keys;
    }

    void report() const {
        if (devices.empty()) wprintf(L"Aucun profil de manette actif d\x00E9tect\x00E9.\n");
        for (const auto& device : devices)
            wprintf(L"%ls [%ls] : %u lectures r\x00E9ussies\n", device.name.c_str(),
                    device.model.c_str(), device.successfulPolls);
    }
};

static void publish(companion::SharedState* shared, const std::array<BYTE, 256>& keys,
                    bool alive = true) {
    static std::array<BYTE,256> previous{};
    static DWORD lastChange=0;
    DWORD now=GetTickCount();
    if(memcmp(previous.data(),keys.data(),keys.size())!=0){previous=keys;lastChange=now;}
    InterlockedIncrement(&shared->sequence);
    shared->magic = companion::kMagic;
    shared->version = companion::kVersion;
    shared->tick = alive ? now : 0;
    shared->changeTick = alive ? lastChange : 0;
    shared->writerPid = alive ? GetCurrentProcessId() : 0;
    memcpy(shared->keys, keys.data(), keys.size());
    MemoryBarrier();
    InterlockedIncrement(&shared->sequence);
}

// The bridge starts this process from game.exe. A SYNCHRONIZE handle remains
// signaled after that parent exits, including when the game is force-closed.
static HANDLE openGameParent() {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) return nullptr;
    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    DWORD parentPid = 0;
    if (Process32FirstW(snapshot, &entry)) do {
        if (entry.th32ProcessID == GetCurrentProcessId()) {
            parentPid = entry.th32ParentProcessID;
            break;
        }
    } while (Process32NextW(snapshot, &entry));
    HANDLE parent = nullptr;
    if (parentPid && Process32FirstW(snapshot, &entry)) do {
        if (entry.th32ProcessID == parentPid && _wcsicmp(entry.szExeFile, L"game.exe") == 0) {
            parent = OpenProcess(SYNCHRONIZE, FALSE, parentPid);
            break;
        }
    } while (Process32NextW(snapshot, &entry));
    CloseHandle(snapshot);
    return parent;
}

int wmain(int argc, wchar_t** argv) {
    bool probe = argc == 3 && wcscmp(argv[2], L"--probe") == 0;
    if (argc < 2 || argc > 3 || (argc == 3 && !probe)) {
        fwprintf(stderr, L"Usage: companion_reader.exe <dossier du jeu> [--probe]\n");
        return 2;
    }
    // The bridge's CreateProcess command may pass a folder with a trailing
    // backslash inside quotes. Fall back to this executable's directory if
    // that argument was parsed with a trailing quote.
    std::wstring gameDirectory=argv[1];
    std::wstring requested=gameDirectory;
    if(!requested.empty() && requested.back()!=L'\\' && requested.back()!=L'/')requested+=L'\\';
    requested+=L"DOA5LR-ControllerProfiles.ini";
    if(GetFileAttributesW(requested.c_str())==INVALID_FILE_ATTRIBUTES){
        wchar_t self[MAX_PATH];DWORD length=GetModuleFileNameW(nullptr,self,MAX_PATH);
        if(length && length<MAX_PATH){gameDirectory=self;gameDirectory.resize(gameDirectory.find_last_of(L"\\/")+1);}
    }
    PhysicalPadReader reader(gameDirectory, probe);
    if (!reader.ready()) {
        fwprintf(stderr, L"Impossible d'initialiser DirectInput dans le processus compagnon.\n");
        return 3;
    }
    DWORD attrs = GetFileAttributesW(reader.profilePath().c_str());
    if (attrs == INVALID_FILE_ATTRIBUTES || (attrs & FILE_ATTRIBUTE_DIRECTORY)) {
        fwprintf(stderr, L"Profil introuvable : %ls\n", reader.profilePath().c_str());
        return 4;
    }

    HANDLE writer = CreateMutexW(nullptr, TRUE, companion::kWriterMutexName);
    if (!writer || GetLastError() == ERROR_ALREADY_EXISTS) {
        fwprintf(stderr, L"Un lecteur de manette DOA5LR est d\x00E9j\x00E0 actif.\n");
        if (writer) CloseHandle(writer);
        return 5;
    }
    HANDLE mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                                        sizeof(companion::SharedState), companion::kMapName);
    auto* shared = mapping ? static_cast<companion::SharedState*>(
        MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(companion::SharedState))) : nullptr;
    if (!shared) {
        fwprintf(stderr, L"Impossible de cr\x00E9er la m\x00E9moire partag\x00E9e.\n");
        if (mapping) CloseHandle(mapping);
        ReleaseMutex(writer);
        CloseHandle(writer);
        return 6;
    }
    HANDLE stop = CreateEventW(nullptr, TRUE, FALSE, companion::kStopEventName);
    if (stop) ResetEvent(stop);
    HANDLE gameParent = probe ? nullptr : openGameParent();
    // The game can retain a mapping after a previous helper was terminated
    // mid-write. Reset its sequence while our single-writer mutex is held.
    InterlockedExchange(&shared->sequence, 1);
    shared->magic = 0;
    shared->tick = 0;
    shared->writerPid = 0;
    memset(shared->keys, 0, sizeof(shared->keys));
    MemoryBarrier();
    InterlockedExchange(&shared->sequence, 2);
    publish(shared, {});

    // This hidden companion needs a precise wait interval on Windows 10/11.
    // Keep the request scoped to this process and restore it on exit.
    PROCESS_POWER_THROTTLING_STATE throttle{};
    throttle.Version=PROCESS_POWER_THROTTLING_CURRENT_VERSION;
    throttle.ControlMask=PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION;
    throttle.StateMask=0;
    SetProcessInformation(GetCurrentProcess(),ProcessPowerThrottling,&throttle,sizeof(throttle));
    bool preciseTimer=timeBeginPeriod(1)==TIMERR_NOERROR;
    DWORD start = GetTickCount();
    while (true) {
        MSG msg;
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) goto done;
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        publish(shared, reader.read());
        if (probe && GetTickCount() - start >= 2000) break;
        if (gameParent && WaitForSingleObject(gameParent, 0) == WAIT_OBJECT_0) break;
        if (stop && WaitForSingleObject(stop, 1) == WAIT_OBJECT_0) break;
        if (!stop) Sleep(1);
    }
done:
    if (probe) reader.report();
    if (preciseTimer) timeEndPeriod(1);
    publish(shared, {}, false); // Also reject a cleanly stopped writer immediately.
    if (gameParent) CloseHandle(gameParent);
    if (stop) CloseHandle(stop);
    UnmapViewOfFile(shared);
    CloseHandle(mapping);
    ReleaseMutex(writer);
    CloseHandle(writer);
    return 0;
}
