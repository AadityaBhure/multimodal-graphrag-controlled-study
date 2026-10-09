"""Reproduce the project-local Windows build of unmodified pcst_fast 1.0.10."""
from pathlib import Path
import io,sys,sysconfig,subprocess,shutil,tarfile
import requests,pybind11
ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.prefix==sys.base_prefix:raise RuntimeError('Use the project .venv interpreter')
    work=ROOT/'artifacts/phase7/pcst-source';work.mkdir(parents=True,exist_ok=True)
    metadata=requests.get('https://pypi.org/pypi/pcst_fast/1.0.10/json',timeout=30);metadata.raise_for_status()
    row=next(r for r in metadata.json()['urls'] if r['packagetype']=='sdist')
    response=requests.get(row['url'],timeout=60);response.raise_for_status()
    import hashlib
    assert hashlib.sha256(response.content).hexdigest()==row['digests']['sha256']
    with tarfile.open(fileobj=io.BytesIO(response.content),mode='r:gz') as archive:archive.extractall(work,filter='data')
    compiler=shutil.which('g++')
    if not compiler:raise RuntimeError('GNU C++ compiler unavailable; install official pcst_fast with a supported build toolchain')
    source=work/'pcst_fast-1.0.10/src';target=Path(sysconfig.get_path('platlib'))
    subprocess.run([compiler,'-O2','-shared','-std=c++17','-static-libgcc','-static-libstdc++','-I'+pybind11.get_include(),'-I'+sysconfig.get_path('include'),str(source/'pcst_fast.cc'),str(source/'pcst_fast_pybind.cc'),str(Path(sys.base_prefix)/'python312.dll'),'-o',str(target/'pcst_fast.pyd')],check=True)
    runtime=Path(compiler).parent/'libwinpthread-1.dll'
    if runtime.exists():shutil.copy2(runtime,target/runtime.name)
    print('Official pcst_fast built in',target)
if __name__=='__main__':main()
