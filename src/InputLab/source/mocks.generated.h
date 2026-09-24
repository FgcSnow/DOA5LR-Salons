class MockA final : public IDirectInputDevice8A { public: LONG refs=1; bool fail=false;
HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void** ppvObject) noexcept override {return E_NOTIMPL;}
ULONG STDMETHODCALLTYPE AddRef() noexcept override {return ++refs;}
ULONG STDMETHODCALLTYPE Release() noexcept override {LONG n=--refs;if(!n){mockDeleted++;delete this;}return n;}
HRESULT STDMETHODCALLTYPE GetCapabilities(LPDIDEVCAPS lpDIDevCaps) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumObjects(LPDIENUMDEVICEOBJECTSCALLBACKA lpCallback, LPVOID pvRef, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetProperty(REFGUID rguidProp, LPDIPROPHEADER pdiph) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetProperty(REFGUID rguidProp, LPCDIPROPHEADER pdiph) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Acquire() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Unacquire() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetDeviceState(DWORD cbData, LPVOID lpvData) noexcept override {if(fail)return DIERR_INPUTLOST;if(cbData!=256)return DIERR_INVALIDPARAM;memset(lpvData,0,256);((BYTE*)lpvData)[200]=0x80;return S_OK;}
HRESULT STDMETHODCALLTYPE GetDeviceData(DWORD cbObjectData, LPDIDEVICEOBJECTDATA rgdod, LPDWORD pdwInOut, DWORD dwFlags) noexcept override {if(fail)return DIERR_INPUTLOST;if(!pdwInOut)return E_POINTER;if(rgdod&&*pdwInOut>=2){memset(rgdod,0,2*cbObjectData);rgdod[0].dwOfs=200;rgdod[0].dwData=0x80;rgdod[0].dwTimeStamp=345;rgdod[0].dwSequence=456;rgdod[0].uAppData=567;rgdod[1].dwOfs=200;rgdod[1].dwTimeStamp=346;rgdod[1].dwSequence=457;rgdod[1].uAppData=568;}*pdwInOut=2;return S_OK;}
HRESULT STDMETHODCALLTYPE SetDataFormat(LPCDIDATAFORMAT lpdf) noexcept override {return S_OK;}
HRESULT STDMETHODCALLTYPE SetEventNotification(HANDLE hEvent) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetCooperativeLevel(HWND hwnd, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetObjectInfo(LPDIDEVICEOBJECTINSTANCEA pdidoi, DWORD dwObj, DWORD dwHow) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetDeviceInfo(LPDIDEVICEINSTANCEA pdidi) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE RunControlPanel(HWND hwndOwner, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Initialize(HINSTANCE hinst, DWORD dwVersion, REFGUID rguid) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE CreateEffect(REFGUID rguid, LPCDIEFFECT lpeff, LPDIRECTINPUTEFFECT *ppdeff, LPUNKNOWN punkOuter) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumEffects(LPDIENUMEFFECTSCALLBACKA lpCallback, LPVOID pvRef, DWORD dwEffType) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetEffectInfo(LPDIEFFECTINFOA pdei, REFGUID rguid) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetForceFeedbackState(LPDWORD pdwOut) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SendForceFeedbackCommand(DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumCreatedEffectObjects(LPDIENUMCREATEDEFFECTOBJECTSCALLBACK lpCallback, LPVOID pvRef, DWORD fl) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Escape(LPDIEFFESCAPE pesc) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Poll() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SendDeviceData(DWORD cbObjectData, LPCDIDEVICEOBJECTDATA rgdod, LPDWORD pdwInOut, DWORD fl) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumEffectsInFile(LPCSTR lpszFileName,LPDIENUMEFFECTSINFILECALLBACK pec,LPVOID pvRef,DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE WriteEffectToFile(LPCSTR lpszFileName,DWORD dwEntries,LPDIFILEEFFECT rgDiFileEft,DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE BuildActionMap(LPDIACTIONFORMATA lpdiaf, LPCSTR lpszUserName, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetActionMap(LPDIACTIONFORMATA lpdiaf, LPCSTR lpszUserName, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetImageInfo(LPDIDEVICEIMAGEINFOHEADERA lpdiDevImageInfoHeader) noexcept override {return E_NOTIMPL;}
};
class MockW final : public IDirectInputDevice8W { public: LONG refs=1; bool fail=false;
HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void** ppvObject) noexcept override {return E_NOTIMPL;}
ULONG STDMETHODCALLTYPE AddRef() noexcept override {return ++refs;}
ULONG STDMETHODCALLTYPE Release() noexcept override {LONG n=--refs;if(!n){mockDeleted++;delete this;}return n;}
HRESULT STDMETHODCALLTYPE GetCapabilities(LPDIDEVCAPS lpDIDevCaps) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumObjects(LPDIENUMDEVICEOBJECTSCALLBACKW lpCallback, LPVOID pvRef, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetProperty(REFGUID rguidProp, LPDIPROPHEADER pdiph) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetProperty(REFGUID rguidProp, LPCDIPROPHEADER pdiph) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Acquire() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Unacquire() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetDeviceState(DWORD cbData, LPVOID lpvData) noexcept override {if(fail)return DIERR_INPUTLOST;if(cbData!=256)return DIERR_INVALIDPARAM;memset(lpvData,0,256);((BYTE*)lpvData)[200]=0x80;return S_OK;}
HRESULT STDMETHODCALLTYPE GetDeviceData(DWORD cbObjectData, LPDIDEVICEOBJECTDATA rgdod, LPDWORD pdwInOut, DWORD dwFlags) noexcept override {if(fail)return DIERR_INPUTLOST;if(!pdwInOut)return E_POINTER;if(rgdod&&*pdwInOut>=2){memset(rgdod,0,2*cbObjectData);rgdod[0].dwOfs=200;rgdod[0].dwData=0x80;rgdod[0].dwTimeStamp=345;rgdod[0].dwSequence=456;rgdod[0].uAppData=567;rgdod[1].dwOfs=200;rgdod[1].dwTimeStamp=346;rgdod[1].dwSequence=457;rgdod[1].uAppData=568;}*pdwInOut=2;return S_OK;}
HRESULT STDMETHODCALLTYPE SetDataFormat(LPCDIDATAFORMAT lpdf) noexcept override {return S_OK;}
HRESULT STDMETHODCALLTYPE SetEventNotification(HANDLE hEvent) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetCooperativeLevel(HWND hwnd, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetObjectInfo(LPDIDEVICEOBJECTINSTANCEW pdidoi, DWORD dwObj, DWORD dwHow) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetDeviceInfo(LPDIDEVICEINSTANCEW pdidi) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE RunControlPanel(HWND hwndOwner, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Initialize(HINSTANCE hinst, DWORD dwVersion, REFGUID rguid) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE CreateEffect(REFGUID rguid, LPCDIEFFECT lpeff, LPDIRECTINPUTEFFECT *ppdeff, LPUNKNOWN punkOuter) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumEffects(LPDIENUMEFFECTSCALLBACKW lpCallback, LPVOID pvRef, DWORD dwEffType) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetEffectInfo(LPDIEFFECTINFOW pdei, REFGUID rguid) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetForceFeedbackState(LPDWORD pdwOut) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SendForceFeedbackCommand(DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumCreatedEffectObjects(LPDIENUMCREATEDEFFECTOBJECTSCALLBACK lpCallback, LPVOID pvRef, DWORD fl) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Escape(LPDIEFFESCAPE pesc) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE Poll() noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SendDeviceData(DWORD cbObjectData, LPCDIDEVICEOBJECTDATA rgdod, LPDWORD pdwInOut, DWORD fl) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE EnumEffectsInFile(LPCWSTR lpszFileName,LPDIENUMEFFECTSINFILECALLBACK pec,LPVOID pvRef,DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE WriteEffectToFile(LPCWSTR lpszFileName,DWORD dwEntries,LPDIFILEEFFECT rgDiFileEft,DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE BuildActionMap(LPDIACTIONFORMATW lpdiaf, LPCWSTR lpszUserName, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE SetActionMap(LPDIACTIONFORMATW lpdiaf, LPCWSTR lpszUserName, DWORD dwFlags) noexcept override {return E_NOTIMPL;}
HRESULT STDMETHODCALLTYPE GetImageInfo(LPDIDEVICEIMAGEINFOHEADERW lpdiDevImageInfoHeader) noexcept override {return E_NOTIMPL;}
};