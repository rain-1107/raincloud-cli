import os
import sys
import json
from time import time
import shutil
from ftplib import FTP
from util import *

def set_remote() -> None:
    print("Please note that all data is kept in plain text")
    ip = input("Enter ftp server ip: ")
    user = input("Enter ftp server user: ")
    passwd = input("Enter ftp server password: ")
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    data["ftp_config"] = {"ip": ip, "user": user, "passwd": passwd, "port": 21}
    with open(CONFIG_FOLDER + "/config.json", "w") as fp:
        json.dump(data, fp, indent=2)

def add_folder() -> None:
    folders = sys.argv[2:]
    names = []
    for f in folders.copy():
        if os.path.isdir(f):
            names.append(input(f"Enter ID/Name for folder '{f}': "))
        else:
            print(f"Folder not found '{f}'")
            folders.remove(f)
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r")) 
    for i, f in enumerate(folders):
        data["local_conf"][names[i]] = format_path(f)
        print(f"Added '{names[i]}' at '{folders[i]}'")
    with open(CONFIG_FOLDER + "/config.json", "w") as fp:
        json.dump(data, fp, indent=2)

def remove_folders() -> None:
    names = sys.argv[2:]
    data: dict = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for n in names:
        if n in data["local_conf"]:
            data["local_conf"].pop(n)
    with open(CONFIG_FOLDER + "/config.json", "w") as fp:
        json.dump(data, fp, indent=2)

def list_folders() -> None:
    total = 0
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for name in data["local_conf"]:
        total += 1
        print(f"{name} - '{data['local_conf'][name]}'")
    print(f"Total: {total}")

def reset_config() -> None:
    shutil.rmtree(CONFIG_FOLDER)
    create_config()
    print("Config reset")
 
def sync_folders() -> None:
    data = json.load(open(os.path.join(CONFIG_FOLDER, "config.json"), "r"))
    if not data["ftp_config"]["ip"]:
        print("No remote set")
        return
    ftp = connect_to_server()
    print("Connected to server")
    items = ftp.nlst()
    if "raincloud" not in items:
        ftp.mkd("raincloud")
    ftp.cwd("raincloud")
    items = ftp.nlst()
    for dir in data["local_conf"]:
        print(f"Syncing '{dir}'")
        if dir not in items:
            # Upload all
            mtime_data = get_mtimes(data["local_conf"][dir])
            folder = get_local_folder_structure(data["local_conf"][dir]) 
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "w") as dir_data:
                json.dump({"file_data": mtime_data, "folder_structure": folder}, dir_data)            
            create_server_folder_structure(dir, folder, ftp)
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "rb") as mtime_file:
                ftp.storbinary(f"STOR {dir}.json", mtime_file)
            ftp.cwd(dir)
            paths = get_filepaths(data["local_conf"][dir])
            names = get_filepaths(data["local_conf"][dir], local = True)
            for i, f in enumerate(paths):
                with open(f, "rb") as fp:
                    print(f"Uploading '{names[i]}'")
                    ftp.storbinary(f"STOR {names[i]}", fp)
        else:
            ftp.cwd(dir)
            # Individual folder logic
            try:
                create_backup(dir)
            except:
                buf = input("Backup failed. \n Do you wish to continue? [y/n]")
                if buf.lower() != "y":
                    print(f"Skipping '{dir}'")
                    continue
            mtime_data = get_mtimes(data["local_conf"][dir])
            folder = get_local_folder_structure(data["local_conf"][dir])
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "w") as dir_data:
                json.dump({"file_data": mtime_data, "folder_structure": folder}, dir_data)  
            with open(os.path.join(CONFIG_FOLDER, "tmp", f"{dir}.json"), "wb") as server_mtime:
                ftp.cwd("..")
                file_data = get_file_bytes(ftp, f"{dir}.json")
                ftp.cwd(dir)
                server_mtime.write(file_data)
                server_mtime.close()
            server_data = json.load(open(os.path.join(CONFIG_FOLDER, "tmp", f"{dir}.json"), "r"))
            create_local_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir), folder)
            create_local_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir), server_data["folder_structure"])
            new_structure = get_local_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir))
            create_server_folder_structure(dir, new_structure, ftp)
            create_local_folder_structure(data["local_conf"][dir], new_structure)
            paths = get_filepaths(data["local_conf"][dir])
            names = get_filepaths(data["local_conf"][dir], local = True)
            for i, n in enumerate(names):
                if n not in server_data["file_data"] or mtime_data[n] > server_data["file_data"][n]: # upload
                    print(f"Uploading '{n}'")
                    try:
                        ftp.delete(n)
                    except error_perm:
                        pass
                    with open(paths[i], "rb") as fp:
                        ftp.storbinary(f"STOR {n}", fp)
                elif mtime_data[n] < server_data["file_data"][n]: # download
                    print(f"Downloading '{n}'")
                    f_data = get_file_bytes(ftp, n)
                    with open(paths[i], "wb") as fp:
                        fp.write(f_data)
                    os.utime(paths[i], (server_data["file_data"][n], server_data["file_data"][n]))
            for file in server_data["file_data"]:
                if file not in names:
                    print(f"Downloading '{file}' (New)") 
                    f_data = get_file_bytes(ftp, file)
                    with open(os.path.join(data["local_conf"][dir], file), "wb") as fp:
                        fp.write(f_data)
                    os.utime(os.path.join(data["local_conf"][dir], file), (server_data["file_data"][file], server_data["file_data"][file]))
            # -----------------------
            ftp.cwd("..")
            # ftp.delete(f"STOR {dir}.json")
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "rb") as dir_conf:
                ftp.storbinary(f"STOR {dir}.json", dir_conf)
        print(f"'{dir}' synced.")
    ftp.quit()
    print("Finished syncing")

def lbackups():
    dirs = sys.argv[2:]
    data: dict = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for dir in dirs:
        if dir not in data["local_conf"]:
            continue
        com = input(f"Are you sure you want to load backup of '{dir}'? [y/n]")
        if com.lower() != "y":
            continue
        load_backup(dir)

def main() -> None:
    if not os.path.isdir(CONFIG_FOLDER):
        print("No config file found. Creating config folder")
        create_config()
    if len(sys.argv) < 2:
        print("No arguments found")
        return
    if sys.argv[1].lower() == "remote":
        set_remote()
        return
    if sys.argv[1].lower() == "add":
        add_folder()
        return
    if sys.argv[1].lower() == "remove":
        remove_folders()
        return
    if sys.argv[1].lower() == "list":
        list_folders()
        return
    if sys.argv[1].lower() == "reset":
        reset_config()
        return
    if sys.argv[1].lower() == "sync":
        try:
            sync_folders()
        except TimeoutError:
            print("Connection timed out.")
        return
    if sys.argv[1].lower() == "lbackup":
        lbackups()
        return
    if sys.argv[1].lower() == "help":
        print("""Command list
remote - set the ftp server ip, user and password
add [args] - add directories to be tracked (by path)
remove [args] - remove directories (by ID/Name)
sync - syncs all folders with remote server
list - list all directories being tracked
reset - fully resets config (including saved directories)
lbackup [args] - swaps backup with files in directory (by ID/name)""")
        return
    print(f"Unrecognized command '{sys.argv[1]}'")


if __name__ == '__main__':
    main()
