# Optional InsightFace setup on Windows

This project already works with the fallback face pipeline, but `insightface` can be enabled on a Windows machine if the C++ toolchain is available.

## Why the extra setup is needed

`insightface` on PyPI is published as a source distribution here, so pip must compile part of the package on Windows. When that happens, MSVC build tools are required. In this workspace, the install failed until the compiler toolchain was available.

## Install Visual Studio Build Tools

Install the **Desktop development with C++** workload from Visual Studio Build Tools.

Official workload/component IDs:

- `Microsoft.VisualStudio.Workload.VCTools`
- `Microsoft.VisualStudio.Component.VC.CoreBuildTools`
- `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`
- `Microsoft.VisualStudio.Component.Windows11SDK.22621`

Microsoft docs:

- https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=visualstudio
- https://learn.microsoft.com/en-us/cpp/build/vscpp-step-0-installation?view=msvc-160
- https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line?view=msvc-160

## Verify the toolchain

Open a new PowerShell window and confirm these commands are available:

```powershell
Get-Command cl.exe
Get-Command msbuild.exe
```

## Install the optional ML packages

From `backend/`:

```powershell
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install insightface==0.7.3 onnxruntime==1.25.1
```

## Test it

Run:

```powershell
python scripts/test_insightface.py
```

Put a clear face photo in `backend/any_photo.jpg` first.

## Current status in this repo

- `mtcnn[tensorflow]` is already installed and working.
- `keras-facenet` is installed and working.
- `insightface` remains optional and only works after the C++ build tools are installed.
