import os
import json
import shutil
from ftplib import FTP, error_perm

HOME = os.path.expanduser("~")
CONFIG_FOLDER = os.path.join(HOME, ".rc")

def format_path(path: str) -> str:
    path = os.path.expanduser(path)
    return path.replace("\\", "/")

def connect_to_server() -> FTP:
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    print(f"Syncing to remote at '{data['ftp_config']['ip']}'")
    ftp = FTP(data["ftp_config"]["ip"], timeout=5)
    ftp.login(user=data["ftp_config"]["user"], passwd=data["ftp_config"]["passwd"])
    return ftp

def create_config() -> None:
    os.mkdir(CONFIG_FOLDER)
    os.mkdir(os.path.join(CONFIG_FOLDER, "data"))
    os.mkdir(os.path.join(CONFIG_FOLDER, "tmp"))
    with open(CONFIG_FOLDER + "/config.json", "w") as conf_file:
        json.dump({"ftp_config": {"ip": "", "user": "", "passwd": "", "port": 21}, "local_conf": {}}, conf_file, indent=2)

def get_local_folder_structure(path: str) -> dict:
    dirs = []
    for (_, dirnames, _) in os.walk(os.path.expanduser(path)):
        dirs = dirnames
        break
    if dirs:
        struct = {}
        for d in dirs:
            struct[d] = get_local_folder_structure(path + "/" + d)
        return struct
    return {}

def create_local_folder_structure(path: str, struct: dict) -> None:
    if not os.path.isdir(path):
        os.mkdir(path)
    for key in struct:
        create_local_folder_structure(os.path.join(path, key), struct[key])

def create_server_folder_structure(name: str, struct: dict, ftp: FTP) -> None:
    try:
        ftp.mkd(name)
    except error_perm:
        pass
    ftp.cwd(name)
    for key in struct:
        create_server_folder_structure(key, struct[key], ftp)
    ftp.cwd("..")

def get_filepaths(path: str, local: bool = False) -> list[str]:
    f = []
    for (dirpath, _, filenames) in os.walk(path):
        for file in filenames:
            name = os.path.join(dirpath, file)
            if local:
                name = name[len(path)+1:]
            f.append(format_path(name))
    return f

def get_mtimes(path: str) -> dict[str, int]:
    files = get_filepaths(path)
    names = get_filepaths(path, True)
    data = {}
    for i, f in enumerate(files):
        data[names[i]] = os.path.getmtime(f)
    return data

def get_file_bytes(ftp: FTP, file: str) -> bytes:
    data = []

    def callback(b):
        data.append(b)
    
    ftp.retrbinary(f"RETR {file}", callback)
    b = data.pop(0)
    for block in data:
        if type(block) == bytes:
            b = b + block
    return b

def create_backup(dir: str) -> None:
    print("Creating backup")
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    path = data["local_conf"][dir]
    try:
        shutil.rmtree(os.path.join(CONFIG_FOLDER, "backup", dir))
    except FileNotFoundError:
        pass
    shutil.copytree(path, os.path.join(CONFIG_FOLDER, "backup", dir))

def load_backup(dir: str) -> None:
    print(f"Loading backup of '{dir}'")
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    path = data["local_conf"][dir]
    try:
        shutil.rmtree(os.path.join(CONFIG_FOLDER, "tmp", dir))
    except FileNotFoundError:
        pass
    shutil.copytree(path, os.path.join(CONFIG_FOLDER, "tmp", dir))
    shutil.rmtree(path)
    shutil.copytree(os.path.join(CONFIG_FOLDER, "backup", dir), path)
    shutil.rmtree(os.path.join(CONFIG_FOLDER, "backup", dir))
    shutil.copytree(os.path.join(CONFIG_FOLDER, "tmp", dir), os.path.join(CONFIG_FOLDER, "backup", dir))
