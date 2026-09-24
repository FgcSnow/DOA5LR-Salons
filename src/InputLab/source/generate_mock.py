import pathlib,re,sys
h=pathlib.Path(sys.argv[1]).read_text();out=[]
for suffix in ['A','W']:
 interface='IDirectInputDevice8'+suffix;cls='Mock'+suffix
 text=h.split('DECLARE_INTERFACE_('+interface+',',1)[1].split('};',1)[0]
 out.append(f'class {cls} final : public {interface} {{ public: LONG refs=1; bool fail=false;')
 for m in re.finditer(r'STDMETHOD(?:_\((\w+),(\w+)\)|\((\w+)\))\(THIS(_\s+.*?)?\) PURE;',text):
  ret,name=m[1] or 'HRESULT',m[2] or m[3];args=(m[4] or '')[1:].strip();body='return E_NOTIMPL;'
  if name=='AddRef':body='return ++refs;'
  elif name=='Release':body='LONG n=--refs;if(!n){mockDeleted++;delete this;}return n;'
  elif name=='GetDeviceState':body='if(fail)return DIERR_INPUTLOST;if(cbData!=256)return DIERR_INVALIDPARAM;memset(lpvData,0,256);((BYTE*)lpvData)[200]=0x80;return S_OK;'
  elif name=='SetDataFormat':body='return S_OK;'
  elif name=='GetDeviceData':body='if(fail)return DIERR_INPUTLOST;if(!pdwInOut)return E_POINTER;if(rgdod&&*pdwInOut>=2){memset(rgdod,0,2*cbObjectData);rgdod[0].dwOfs=200;rgdod[0].dwData=0x80;rgdod[0].dwTimeStamp=345;rgdod[0].dwSequence=456;rgdod[0].uAppData=567;rgdod[1].dwOfs=200;rgdod[1].dwTimeStamp=346;rgdod[1].dwSequence=457;rgdod[1].uAppData=568;}*pdwInOut=2;return S_OK;'
  out.append(f'{ret} STDMETHODCALLTYPE {name}({args}) noexcept override {{{body}}}')
 out.append('};')
pathlib.Path(__file__).with_name('mocks.generated.h').write_text('\n'.join(out))
