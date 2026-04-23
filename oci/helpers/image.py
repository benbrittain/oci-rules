import argparse
from io import BufferedRandom
import subprocess
import sys
import json
import tempfile
import shutil

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

def build_image(crane_path, base_image_path, tar_files, entrypoint, cmd, output, user, workdir, name, envs):
    # get last part of base_image path
    base_image = base_image_path.split("/")[-1]
    registry_base_image = f"localhost:{REGISTRY_PORT}/{base_image}"
    registry_image = f"localhost:{REGISTRY_PORT}/{name}"

    # Push the base image to the local registry
    push_base_image_command = [crane_path, 'push', base_image_path, registry_base_image]
    eprint(f"Pushing base image: {push_base_image_command}")
    subprocess.run(push_base_image_command, check=True)

    # Delete the cached image from the local registry.
    # It is ok if the command fails since the image may not be cached.
    delete_image_command = [crane_path, 'delete', registry_image]
    eprint(f"Deleting image: {delete_image_command}")                                      
    subprocess.run(delete_image_command)

    # Append all layers to the base image
    append_layer_command = [crane_path, 'append', '-t', registry_image, '-f', ",".join(tar_files), '-b', registry_base_image]
    eprint(f"Appending layers: {append_layer_command}")
    subprocess.run(append_layer_command, check=True)

    # crane has a bug where it deletes Cmd if you only override entrypoint.
    # so get the config of the base image and use it as the default
    # https://github.com/google/go-containerregistry/issues/2041
    base_config_command = [crane_path, "config", registry_base_image]
    eprint(f"Getting base config: {base_config_command}")
    base_config = json.loads(subprocess.run(base_config_command, check=True, stdout=subprocess.PIPE).stdout.decode("utf-8"))["config"]
    base_cmd = base_config.get("Cmd")
    base_entrypoint = base_config.get("Entrypoint")
    if base_cmd is not None:
        base_cmd = ",".join(base_cmd)
    if base_entrypoint is not None:
        base_entrypoint = ",".join(base_entrypoint)
    cmd = cmd or base_cmd
    entrypoint = entrypoint or base_entrypoint


    args = []
    if envs is not None:
        for env in envs:
            args.append(f"--env={env}")
    if entrypoint is not None:
        args.append(f"--entrypoint={entrypoint}")
    if cmd is not None:
        args.append(f"--cmd={cmd}")
    if user is not None:
        args.append(f"--user={user}")
    if workdir is not None:
        args.append(f"--workdir={workdir}")

    # Use the mutate command to output the image without doing any mutation
    # crate mutate does not support directly writing oci with the -o flag
    # so we must mutate then pull --format=oci
    config_command = [crane_path, 'mutate', registry_image] + args
    eprint(f"Generating new image: {config_command}")
    subprocess.run(config_command, check=True)

    pull_command = [crane_path, 'pull', '--format=oci', registry_image, output]
    eprint(f"Pulling mutated image back to filesystem: {pull_command}")
    subprocess.run(pull_command, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build OCI image using Crane")
    parser.add_argument("--crane", required=True, help="Path to the crane binary")
    parser.add_argument("--base", required=True, help="Base OCI image")
    parser.add_argument("--tars", nargs='+', required=False, help="Paths to tar files representing layers", default=[])
    parser.add_argument("--env", action="append", required=False, help="Environment variables")
    parser.add_argument("--entrypoint", help="Entrypoint for the OCI image")
    parser.add_argument("--cmd", help="Command for the OCI image")
    parser.add_argument("--output", required=True, help="Path to the output OCI image directory")
    parser.add_argument("--name", required=True, help="Name of the OCI image")
    parser.add_argument("--user", help="User")
    parser.add_argument("--workdir", help="Working directory")
    args = parser.parse_args()

    log_file = tempfile.TemporaryFile()
    registry_process = None

    try:
        registry_process = start_registry(args.crane, log_file)
        build_image(args.crane, args.base, args.tars, args.entrypoint, args.cmd, args.output, args.user, args.workdir, args.name, args.env)
    except subprocess.CalledProcessError as e:
        eprint(f"Error: {e}")
    finally:
        if registry_process:
            stop_registry(registry_process)
            log_file.seek(0)
            shutil.copyfileobj(log_file, sys.stderr.buffer)
        log_file.close()
