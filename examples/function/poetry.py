import platform
import shutil
import subprocess
import os
import sys


def add_plugins():
    cmds = []
    cmds.append(["poetry", "-q", "self", "add", "poetry-bumpversion"])
    cmds.append(["poetry", "-q", "self", "add", "poetry-plugin-export"])
    cmds.append(["poetry", "-q", "self", "add", "update"])
    for cmd in cmds:
        subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)


def start_function():
    add_plugins()
    cmds = []
    cmds.append(
        [
            "poetry",
            "-q",
            "export",
            "-f",
            "requirements.txt",
            "--without-hashes",
            "-o",
            "requirements.txt",
        ]
    )
    if platform.system() == "Linux" or platform.system() == "Darwin":
        azurite_data_dir = os.environ.get("HOME") + "/.local/share/azurite"
    elif platform.system() == "Windows":
        azurite_data_dir = (
            os.environ.get("APPDATA").replace("\\", "/").lower() + "/azurite"
        )
    if not os.path.exists(azurite_data_dir):
        os.makedirs(azurite_data_dir)
    azurite_stop = False
    if not subprocess.run(
        ["docker", "ps", "-f", "name=azurite", "--format", "{{.Names}}"],
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout:
        cmds.append(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                "azurite",
                "-v",
                azurite_data_dir + ":/data",
                "-p",
                "10000:10000",
                "-p",
                "10001:10001",
                "-p",
                "10002:10002",
                "mcr.microsoft.com/azure-storage/azurite",
            ]
        )
        azurite_stop = True
    for cmd in cmds:
        subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)
    try:
        subprocess.run(
            ["func", "start"], text=True, check=True, stderr=subprocess.STDOUT
        )
    except:
        if azurite_stop:
            azurite_stop = subprocess.run(
                ["docker", "stop", "azurite"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if azurite_stop.returncode != 0:
                print(azurite_stop.stdout)
        exit(1)


def build():
    add_plugins()
    cmds = []
    packages_path = "./.python_packages/lib/site-packages"
    cmds.append(["pip", "install", "-q", "--upgrade", "pip"])
    cmds.append(
        [
            "poetry",
            "-q",
            "export",
            "-f",
            "requirements.txt",
            "--without-hashes",
            "-o",
            "requirements.txt",
        ]
    )
    cmds.append(
        [
            "pip",
            "install",
            "-q",
            "--target=" + packages_path,
            "-r",
            "requirements.txt",
        ]
    )
    for cmd in cmds:
        subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)

    search = "#!{0}".format(os.path.abspath(str(sys.executable)))
    for root, dirs, files in os.walk(packages_path):
        # Remove __pycache__ folders
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"))
        for file in files:
            # Remove .pyc, .pyo files
            if file.endswith(".pyc") or file.endswith(".pyo"):
                shutil.rmtree(os.path.join(root, file))
            # Use generic python interpreter for packaged executable modules
            if root.endswith("bin"):
                with open(os.path.join(root, file), "r") as f:
                    data = f.read()
                    if search in data:
                        data = data.replace(search, "#!/usr/bin/env python")
                    with open(os.path.join(root, file), "w") as f:
                        f.write(data)

    subprocess.run(
        ["poetry", "build", "-f", "sdist"],
        text=True,
        check=True,
        stderr=subprocess.STDOUT,
    )
    shutil.rmtree("./.python_packages")

    # Build zip archive on Linux and MacOS
    if platform.system() == "Linux" or platform.system() == "Darwin":
        pkg = subprocess.run(
            ["poetry", "version"],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.split(" ")
        pkg = "-".join([pkg[0].replace("-", "_"), pkg[1].lower()]).strip()
        subprocess.run(
            ["tar", "-xzf", pkg + ".tar.gz"],
            cwd="./dist",
            text=True,
            check=True,
            stderr=subprocess.STDOUT,
        )
        subprocess.run(
            ["zip", "-qr", "../" + pkg + ".zip", "."],
            cwd="./dist/" + pkg,
            text=True,
            check=True,
            stderr=subprocess.STDOUT,
        )
        print("  - Built \033[0;32m" + pkg + ".zip\033[0m")
        shutil.rmtree("./dist/" + pkg)
