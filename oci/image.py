import argparse
from io import BufferedRandom
import subprocess
import sys
import tempfile

REGISTRY_PORT = 61978

def start_registry(crane_path: str, log_file: BufferedRandom):
    """Starts a local crane registry and logs its output."""
    log = log_file
    registry_process = subprocess.Popen([crane_path, "registry", "serve", "--address", ":{}".format(REGISTRY_PORT)], stdout=log, stderr=log)
    return registry_process

def stop_registry(registry_process):
    """Stops the local crane registry."""
    registry_process.terminate()
    registry_process.wait()

def build_image(crane_path, base_image_path, tar_files, entrypoint, output, name):
    # get last part of base_image path
    base_image = base_image_path.split("/")[-1]
    fully_qualified_base_image = f"localhost:{REGISTRY_PORT}/{base_image}"
    push_base_image_command = [crane_path, 'push', base_image_path, fully_qualified_base_image]
    print(f"Pushing base image: {push_base_image_command}")
    subprocess.run(push_base_image_command, check=True)

    fully_qualified_new_image = f"localhost:{REGISTRY_PORT}/{name}"
    append_layer_command = [crane_path, 'append', '-t', fully_qualified_new_image, '-f', ",".join(tar_files), '-b', fully_qualified_base_image]
    print(f"Appending layers: {append_layer_command}")
    subprocess.run(append_layer_command, check=True)

    # Set the entrypoint if provided
    if entrypoint:
        config_command = [crane_path, 'mutate', '--entrypoint', entrypoint, fully_qualified_new_image, '-o', output]
        print(f"Setting entrypoint: {config_command}")
        subprocess.run(config_command, check=True)

    # Save the final image to a tar file
    # export_command = [crane_path, 'export', fully_qualified_new_image, output]
    # print(f"Exporting image: {export_command}")
    # subprocess.run(export_command, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build OCI image using Crane")
    parser.add_argument("--crane", required=True, help="Path to the crane binary")
    parser.add_argument("--base", required=True, help="Base OCI image")
    parser.add_argument("--tars", nargs='+', required=True, help="Paths to tar files representing layers")
    parser.add_argument("--entrypoint", nargs='+', help="Entrypoint for the OCI image")
    parser.add_argument("--output", required=True, help="Path to the output tar file")
    parser.add_argument("--name", required=True, help="Name of the OCI image")
    args = parser.parse_args()

    log_file = tempfile.TemporaryFile()
    registry_process = None

    try:
        registry_process = start_registry(args.crane, log_file)
        build_image(args.crane, args.base, args.tars, ' '.join(args.entrypoint) if args.entrypoint else None, args.output, args.name)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if registry_process:
            stop_registry(registry_process)
            print(log_file.read())
