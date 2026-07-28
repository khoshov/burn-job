"""Utility script to convert HuggingFace / Safetensors model directory to GGUF format for llama.cpp."""

import os
import sys
import argparse
import subprocess

def convert_hf_dir_to_gguf(model_dir: str, output_path: str = None, outtype: str = "f16") -> str:
    """Convert Hugging Face / Safetensors model directory to GGUF file."""
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Model directory does not exist: {model_dir}")

    if output_path is None:
        model_name = os.path.basename(model_dir.rstrip(" /"))
        output_path = os.path.join(model_dir, f"{model_name.lower().replace(' ', '_')}.gguf")

    print(f"[*] Target Model Directory: {model_dir}")
    print(f"[*] Target GGUF File Path:  {output_path}")

    # Check if llama.cpp convert script or gguf converter is available
    try:
        import gguf
        print("[+] 'gguf' package is available.")
    except ImportError:
        print("[!] 'gguf' package is missing. Installing gguf...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gguf"], check=False)

    # Search for convert_hf_to_gguf.py in system or virtualenv
    convert_script = None
    possible_scripts = [
        "convert_hf_to_gguf.py",
        os.path.join(sys.prefix, "bin", "convert_hf_to_gguf.py"),
        os.path.expanduser("~/.local/bin/convert_hf_to_gguf.py"),
    ]
    for s in possible_scripts:
        if os.path.exists(s):
            convert_script = s
            break

    if not convert_script:
        # Download convert_hf_to_gguf.py from llama.cpp repository if not found
        script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
        os.makedirs(script_dir, exist_ok=True)
        local_script = os.path.join(script_dir, "convert_hf_to_gguf.py")
        if not os.path.exists(local_script):
            import urllib.request
            url = "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_hf_to_gguf.py"
            print(f"[*] Downloading convert_hf_to_gguf.py script from llama.cpp repository...")
            try:
                urllib.request.urlretrieve(url, local_script)
                print(f"[+] Downloaded converter to {local_script}")
            except Exception as e:
                print(f"[-] Failed to download converter: {e}")
                raise
        convert_script = local_script

    cmd = [
        sys.executable,
        convert_script,
        model_dir,
        "--outfile", output_path,
        "--outtype", outtype,
    ]
    print(f"[*] Running conversion command: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"[SUCCESS] Model successfully converted to GGUF: {output_path}")
        return output_path
    else:
        raise RuntimeError(f"Conversion failed with return code {res.returncode}")


def main():
    parser = argparse.ArgumentParser(description="Convert HuggingFace Safetensors Model to GGUF for llama.cpp")
    parser.add_argument("--model-dir", default="Qwen3-4B ", help="Directory containing model safetensors & config.json")
    parser.add_argument("--outfile", help="Output .gguf file path")
    parser.add_argument("--outtype", default="f16", choices=["f32", "f16", "bf16", "q8_0"], help="Precision output type")
    args = parser.parse_args()

    convert_hf_dir_to_gguf(args.model_dir, args.outfile, args.outtype)


if __name__ == "__main__":
    main()
