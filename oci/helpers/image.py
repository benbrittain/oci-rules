import argparse
from io import BufferedRandom
import subprocess
import sys
import tempfile

REGISTRY_PORT = 61978

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def start_registry(crane_path: str, log_file: BufferedRandom):
    """Starts a local crane registry and logs its output."""
    log = log_file
    registry_process = subprocess.Popen([crane_path, "registry", "serve", "--address", ":{}".format(REGISTRY_PORT)], stdout=log, stderr=log)
    return registry_process

def stop_registry(registry_process):
    """Stops the local crane registry."""
    registry_process.terminate()
    registry_process.wait()

def build_image(crane_path, base_image_path, tar_files, entrypoint, cmd, output, name, envs):
    # get last part of base_image path
    base_image = base_image_path.split("/")[-1]
    registry_base_image = f"localhost:{REGISTRY_PORT}/{base_image}"

    push_base_image_command = [crane_path, 'push', base_image_path, registry_base_image]
    eprint(f"Pushing base image: {push_base_image_command}")
    subprocess.run(push_base_image_command, check=True)

    registry_image = f"localhost:{REGISTRY_PORT}/{name}"
    delete_image_command = [crane_path, 'delete', registry_image]
    eprint(f"Deleting image: {delete_image_command}")                                      
    subprocess.run(delete_image_command, check=True)

    append_layer_command = [crane_path, 'append', '-t', registry_image, '-f', ",".join(tar_files), '-b', registry_base_image]
    eprint(f"Appending layers: {append_layer_command}")
    subprocess.run(append_layer_command, check=True)

    args = []
    for env in envs:
        eprint(env)
        args.append(f"--env={env}")
    if entrypoint:
        args.append(f"--entrypoint={entrypoint}")
    if cmd:
        args.append(f"--cmd={cmd}")
    if cmd:
        config_command = [crane_path, 'mutate', '--cmd', cmd, registry_image]
        eprint(f"Setting entrypoint: {config_command}")
        subprocess.run(config_command, check=True)



    # Use the mutate command to output the image without doing any mutation
    config_command = [crane_path, 'mutate', registry_image, '-o', output] + args
    eprint(f"Generating new image: {config_command}")
    subprocess.run(config_command, check=True)

    config_command = [crane_path, 'validate', '--tarball', output]
    eprint(f"Validating tarball is a well formed image: {config_command}")
    subprocess.run(config_command, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build OCI image using Crane")
    parser.add_argument("--crane", required=True, help="Path to the crane binary")
    parser.add_argument("--base", required=True, help="Base OCI image")
    parser.add_argument("--tars", nargs='+', required=True, help="Paths to tar files representing layers")
    parser.add_argument("--env", nargs='+', required=False, help="Environment variables")
    parser.add_argument("--entrypoint", nargs='+', help="Entrypoint for the OCI image")
    parser.add_argument("--cmd", nargs='+', help="Command for the OCI image")
    parser.add_argument("--output", required=True, help="Path to the output tar file")
    parser.add_argument("--name", required=True, help="Name of the OCI image")
    args = parser.parse_args()

    log_file = tempfile.TemporaryFile()
    registry_process = None

    try:
        registry_process = start_registry(args.crane, log_file)
        build_image(args.crane, args.base, args.tars, ' '.join(args.entrypoint) if args.entrypoint else None, ' '.join(args.cmd) if args.cmd else None, args.output, args.name, args.env)
    except subprocess.CalledProcessError as e:
        eprint(f"Error: {e}", file=sys.stderr)
    finally:
        if registry_process:
            stop_registry(registry_process)
            eprint(log_file.read())
