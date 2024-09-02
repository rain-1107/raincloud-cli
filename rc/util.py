import os
import json
import shutil
from const import *

def format_path(path: str) -> str:
    path = os.path.expanduser(path)
    return path.replace("\\", "/")

def create_config() -> None:
    os.mkdir(CONFIG_FOLDER)
    os.mkdir(os.path.join(CONFIG_FOLDER, "data"))
    os.mkdir(os.path.join(CONFIG_FOLDER, "tmp"))
    with open(CONFIG_FOLDER + "/config.json", "w") as conf_file:
        json.dump({"ftp_config": {"ip": "", "user": "", "passwd": "", "port": 21}, "saves": []}, conf_file, indent=2)
 
def get_saves() -> list[str]:
    saves = []
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r")) 
    for s in data["saves"]:
        saves.append(s["name"])
    return saves

def get_path(save: str) -> str:
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for i, s in enumerate(data["saves"]):
        if save == data["saves"][i]["name"]:
            return data["saves"][i]["path"]
    raise Exception("Save does not exist.")

def get_folder_structure(path: str) -> dict:
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

def create_folder_structure(path: str, struct: dict) -> None:
    if not os.path.isdir(path):
        os.mkdir(path)
    for key in struct:
        create_local_folder_structure(os.path.join(path, key), struct[key])

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

def create_backup(dir: str) -> None:
    print("Creating backup")
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    path = get_path(dir)
    try:
        shutil.rmtree(os.path.join(CONFIG_FOLDER, "backup", dir))
    except FileNotFoundError:
        pass
    shutil.copytree(path, os.path.join(CONFIG_FOLDER, "backup", dir))

def load_backup(dir: str) -> None:
    print(f"Loading backup of '{dir}'")
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    path = get_path(dir)
    try:
        shutil.rmtree(os.path.join(CONFIG_FOLDER, "tmp", dir))
    except FileNotFoundError:
        pass
    shutil.copytree(path, os.path.join(CONFIG_FOLDER, "tmp", dir))
    shutil.rmtree(path)
    shutil.copytree(os.path.join(CONFIG_FOLDER, "backup", dir), path)
    shutil.rmtree(os.path.join(CONFIG_FOLDER, "backup", dir))
    shutil.copytree(os.path.join(CONFIG_FOLDER, "tmp", dir), os.path.join(CONFIG_FOLDER, "backup", dir))

