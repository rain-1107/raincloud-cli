#! /usr/bin/python3

import os
import sys
import json
import shutil
from ftplib import error_perm
import util
import ftp_util
from const import CONFIG_FOLDER, HOME 

# TODO: create raincloud server 'protocol' at https://github.com/rain-1107/raincloud-server
# TODO: create ability to change remote server type from ftp to raincloud

def set_ftp() -> None:
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
        data["saves"].append({"name": names[i], "path": util.format_path(f)})
        print(f"Added '{names[i]}' at '{folders[i]}'")
    with open(CONFIG_FOLDER + "/config.json", "w") as fp:
        json.dump(data, fp, indent=2)

def remove_folders() -> None:
    names = sys.argv[2:]
    data: dict = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for n in names:
        try:
            data["saves"].pop(util.get_saves().index(n))
        except ValueError:
            pass
    with open(CONFIG_FOLDER + "/config.json", "w") as fp:
        json.dump(data, fp, indent=2)

def list_folders() -> None:
    total = 0
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    for name in util.get_saves():
        total += 1
        print(f"{name} - '{util.get_path(name)}'")
    print(f"Total: {total}")

def reset_config() -> None:
    shutil.rmtree(CONFIG_FOLDER)
    util.create_config()
    print("Config reset")
 
def sync_folders_ftp() -> None:
    data = json.load(open(os.path.join(CONFIG_FOLDER, "config.json"), "r"))
    if not data["ftp_config"]["ip"]:
        print("No remote set")
        return
    ftp = ftp_util.connect_to_server()
    print("Connected to server")
    items = ftp.nlst()
    if "raincloud" not in items:
        ftp.mkd("raincloud")
    ftp.cwd("raincloud")
    items = ftp.nlst()
    for dir in util.get_saves():
        print(f"Syncing '{dir}'")
        if dir not in items:
            # Upload all
            mtime_data = util.get_mtimes(util.get_path(dir))
            folder = util.get_folder_structure(util.get_path(dir)) 
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "w") as dir_data:
                json.dump({"file_data": mtime_data, "folder_structure": folder}, dir_data)            
            ftp_util.create_folder_structure(dir, folder, ftp)
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "rb") as mtime_file:
                ftp.storbinary(f"STOR {dir}.json", mtime_file)
            ftp.cwd(dir)
            paths = util.get_filepaths(util.get_path(dir))
            names = util.get_filepaths(util.get_path(dir), local = True)
            for i, f in enumerate(paths):
                with open(f, "rb") as fp:
                    print(f"Uploading '{names[i]}'")
                    ftp.storbinary(f"STOR {names[i]}", fp)
        else:
            ftp.cwd(dir)
            # Individual folder logic
            try:
                util.create_backup(dir)
            except:
                buf = input("Backup failed. \n Do you wish to continue? [y/n]")
                if buf.lower() != "y":
                    print(f"Skipping '{dir}'")
                    continue
            mtime_data = util.get_mtimes(util.get_path(dir))
            folder = util.get_folder_structure(util.get_path(dir))
            with open(os.path.join(CONFIG_FOLDER, "data", f"{dir}.json"), "w") as dir_data:
                json.dump({"file_data": mtime_data, "folder_structure": folder}, dir_data)  
            with open(os.path.join(CONFIG_FOLDER, "tmp", f"{dir}.json"), "wb") as server_mtime:
                ftp.cwd("..")
                file_data = ftp_util.get_file_bytes(ftp, f"{dir}.json")
                ftp.cwd(dir)
                server_mtime.write(file_data)
                server_mtime.close()
            server_data = json.load(open(os.path.join(CONFIG_FOLDER, "tmp", f"{dir}.json"), "r"))
            util.create_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir), folder)
            util.create_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir), server_data["folder_structure"])
            ftp.cwd("..")
            new_structure = util.get_folder_structure(os.path.join(CONFIG_FOLDER, "tmp", dir))
            ftp_util.create_folder_structure(dir, new_structure, ftp)
            ftp.cwd(dir)
            util.create_folder_structure(util.get_path(dir), new_structure)
            paths = util.get_filepaths(util.get_path(dir))
            names = util.get_filepaths(util.get_path(dir), local = True)
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
                    f_data = ftp_util.get_file_bytes(ftp, n)
                    with open(paths[i], "wb") as fp:
                        fp.write(f_data)
                    os.utime(paths[i], (server_data["file_data"][n], server_data["file_data"][n]))
            for file in server_data["file_data"]:
                if file not in names:
                    print(f"Downloading '{file}' (New)") 
                    f_data = ftp_util.get_file_bytes(ftp, file)
                    with open(os.path.join(util.get_path(dir), file), "wb") as fp:
                        fp.write(f_data)
                    os.utime(os.path.join(util.get_path(dir), file), (server_data["file_data"][file], server_data["file_data"][file]))
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
        if dir not in data["saves"]:
            continue
        com = input(f"Are you sure you want to load backup of '{dir}'? [y/n]")
        if com.lower() != "y":
            continue
        util.load_backup(dir)

def config() -> None:
    args = sys.argv[2:]
    if len(args) == 0:
        data: dict = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
        print(data)
        return
    if args[0].lower() == "set":
        if args[1].lower() == "remote":
            ...
        if args[1].lower() == "ftp":
            set_ftp()
            return
        print(f"'{args[1]}' is not a config option")
        return
    print(args)

def main() -> None:
    if not os.path.isdir(CONFIG_FOLDER):
        print("No config file found. Creating config folder")
        util.create_config()
    if len(sys.argv) < 2:
        print("No arguments found")
        return
    if sys.argv[1].lower() == "config":
        config()
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
            sync_folders_ftp()
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
