"""Recover verified v1.0 delta/branding inputs without executing the installer.

Optional import dependency: python -m pip install dnfile==0.18.0
Requires 7-Zip/NanaZip with .NET Single File Application extraction support.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

RESOURCE_HASH = "e19b48d8f9aefce875b6e5e76a415df224f320d2e6d6fcc23bc0f667f481babb"
ASSEMBLY = "Dementium-II-zh-CN-Setup.dll"
PAYLOADS = ("patch.rom.gz", "patch.exe.gz", "resource-patches.gz", "installer.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def import_inputs(installer, root, seven_zip):
    release = json.loads((root / "assets/releases/v1.0.json").read_text(encoding="utf-8"))
    raw = installer.read_bytes()
    if len(raw) != release["size"] or digest(raw) != release["sha256"]:
        raise ValueError("Legacy installer identity differs from assets/releases/v1.0.json; writes=NONE")
    import dnfile
    # Only the extractor is run. The untrusted-input slot is never executed.
    with tempfile.TemporaryDirectory(prefix="dementium-legacy-") as temp:
        subprocess.run([str(seven_zip), "x", str(installer.resolve()), "-o" + temp,
                        ASSEMBLY, "-y"], check=True, capture_output=True)
        assembly = Path(temp) / ASSEMBLY
        pe = dnfile.dnPE(str(assembly))
        extracted = {}
        try:
            for resource in pe.net.resources:
                name = str(resource.name)
                if name in PAYLOADS:
                    if not isinstance(resource.data, bytes):
                        raise ValueError("Unexpected legacy payload resource type")
                    extracted[name] = resource.data
                elif name.endswith(".g.resources"):
                    for entry in resource.data.entries:
                        if entry.name in ("branding/logo.png", "branding/app.ico"):
                            # ResourceSet.data includes a 4-byte stream length;
                            # ResourceSet.value contains the original image bytes.
                            extracted[entry.name] = entry.value
        finally:
            pe.close()
        required = set(PAYLOADS) | {"branding/logo.png", "branding/app.ico"}
        if set(extracted) != required or digest(extracted["resource-patches.gz"]) != RESOURCE_HASH:
            raise ValueError("Legacy embedded payload identity mismatch; writes=NONE")
        branding = json.loads((root / "installer/branding-inputs.json").read_text(encoding="utf-8"))
        for name in ("branding/logo.png", "branding/app.ico"):
            key = "installer/" + name
            expected = next(value for path, value in branding.items() if path.replace(chr(92), "/") == key)
            if digest(extracted[name]) != expected:
                raise ValueError("Legacy branding identity mismatch; writes=NONE")
        output = root / "build/installer/old-v1.0"
        output.mkdir(parents=True, exist_ok=True)
        for name, data in extracted.items():
            target = root / "installer" / name if name.startswith("branding/") else output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if digest(target.read_bytes()) != digest(data):
                raise IOError("Recovered input readback mismatch: " + str(target))
        report = dict(installer=str(installer.resolve()), installer_sha256=digest(raw),
                      game_launch="NEVER", installer_execution="NEVER", result="PASS",
                      resources={name: digest(data) for name, data in sorted(extracted.items())})
        (output / "import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, default=Path.home() / "Downloads/Dementium-II-CN-v1.0.exe")
    parser.add_argument("--seven-zip", type=Path)
    args = parser.parse_args()
    executable = args.seven_zip or shutil.which("7z") or shutil.which("7za")
    if not executable:
        parser.error("Specify --seven-zip with a supported 7-Zip/NanaZip executable")
    report = import_inputs(args.installer, Path(__file__).resolve().parents[1], executable)
    print("LEGACY_IMPORT resources=%d installer_execution=NEVER sha256=%s result=PASS" %
          (len(report["resources"]), report["installer_sha256"]))


if __name__ == "__main__":
    main()
