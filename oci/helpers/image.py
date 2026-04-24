import argparse
from io import BufferedRandom
import subprocess
import sys
import json
import tempfile
import shutil
import threading
import re
import queue
from typing import IO

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Registry:
    registry_process: subprocess.Popen[bytes]
    log_thread: threading.Thread
    port: int

    def __init__(self, crane_path: str, log_file: BufferedRandom):
        """Starts a local crane registry and logs its output."""
        self.registry_process = subprocess.Popen(
            [
                crane_path,
                "registry",
                "serve",
                # Use localhost to prevent binding to all interfaces by default (insecure)
                # Use port 0 to let the OS pick an available port
                "--address",
                "localhost:0",
            ],
            stderr=subprocess.PIPE,
            text=False,
        )
        if not self.registry_process.stderr:
            raise Exception("Failed to start registry server, no stderr")

        def log_reader(
            stderr: IO[bytes],
            log_file: BufferedRandom,
            port_queue: queue.SimpleQueue[int],
        ):
            # e.g.
            # 2025/01/25 00:00:00 serving on port 54011
            port_pattern = re.compile(r"serving on port (\d+)")
            port = -1
            while True:
                line = stderr.readline(1000)
                log_file.write(line)
                log_file.flush()
                line_str = line.decode("utf-8")
                match = port_pattern.search(line_str)
                if match:
                    port = int(match.group(1))
                    port_queue.put(port)
                    break
            shutil.copyfileobj(stderr, log_file)
            # if we exited the loop without a port, that means it failed to start
            if port == -1:
                port_queue.put(-1)

        port_queue: queue.SimpleQueue[int] = queue.SimpleQueue()
        self.log_thread = threading.Thread(
            target=log_reader, args=(self.registry_process.stderr, log_file, port_queue)
        )
        self.log_thread.start()

        # Block waiting for the port to be read
        self.port = port_queue.get()
        if self.port == -1:
            raise Exception(
                "Failed to start registry server, it exited without announcing a port number"
            )

    def stop(self):
        """Stops the local crane registry."""
        self.registry_process.terminate()
        self.registry_process.wait()
        self.log_thread.join()

def build_image(crane_path, registry_port, base_image_path, tar_files, entrypoint, cmd, output, user, workdir, name, envs):
    # get last part of base_image path
    base_image = base_image_path.split("/")[-1]
    registry_base_image = f"localhost:{registry_port}/{base_image}"
    registry_image = f"localhost:{registry_port}/{name}"

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
    registry = None

    try:
        registry = Registry(args.crane, log_file)
        build_image(args.crane, registry.port, args.base, args.tars, args.entrypoint, args.cmd, args.output, args.user, args.workdir, args.name, args.env)
    except subprocess.CalledProcessError as e:
        eprint(f"Error: {e}")
    except Exception as e:
        eprint(f"Error: {e}")
    finally:
        if registry:
            registry.stop()
            log_file.seek(0)
            shutil.copyfileobj(log_file, sys.stderr.buffer)
        log_file.close()
