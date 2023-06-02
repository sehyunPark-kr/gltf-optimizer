import os
import shutil
import subprocess
import sys
import time
import json
import getopt

import concurrent.futures

from pathlib import Path
from shutil import copy

from config import Config, parse_config
#----------------------------------------------

def run(base_model_input_path, final_output_path, config_file, update_mode):
    start_time = time.time()
    
#----------------------------------------------
    # Initialize

    # Read config JSON
    with open(config_file, 'r') as file:
        config = parse_config(json.load(file))

    # Check target base models
    target_base_model_file_paths = get_all_file_paths(base_model_input_path, ['glb', 'gltf'], True)
    if not target_base_model_file_paths:
        print("At least 1 model file(glb/gltf) is required.")
        sys.exit(2)

#----------------------------------------------
    # Check if the file already exists in the output folder. In update mode 
    if update_mode:
        target_base_model_file_paths = get_not_exist_file_paths(config, target_base_model_file_paths, final_output_path)
        if len(target_base_model_file_paths) == 0:
            print("All modeling already exists in the output path. Clear --update to run nonetheless")
            sys.exit(2)

    print("\n\n-----------------------\n")
    for file_path in target_base_model_file_paths:
        print("{}".format(file_path))
    print("\n-----------------------\n\n")

#----------------------------------------------
    # Get current path
    if getattr(sys, "frozen", False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    # Create 'workspace' folder in the current execution path
    workspace_root_path = "{}/workspace".format(bundle_dir)
    make_directory(workspace_root_path)
    # Create a folder in 'workspace' with the current timestamp
    workspace_path = "{}/{}".format(workspace_root_path, time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time())))
    make_directory(workspace_path)
    # Convert the base file to texture-separated gltf and create a base folder to save it
    base_model_copy_path = "{}/{}".format(workspace_path, 'base')
    make_directory(base_model_copy_path)

#----------------------------------------------
    # Convert base file to texture-separated gltf with base folder path
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = [(base_model_copy_path, file_path) for file_path in target_base_model_file_paths]
        futures = [executor.submit(copy_base_model_and_convert_gltf, *task) for task in tasks]
        concurrent.futures.wait(futures)

#----------------------------------------------
    # Optimize Texture
    optimize_textures(config, base_model_copy_path, workspace_path)
    
#----------------------------------------------
    # Optimize Mesh
    texture_path = "{}/{}".format(workspace_path, config.texture_settings[0].max_size)
    optimize_models(config, base_model_copy_path, workspace_path, texture_path)
    
#--------------------------------------------
    # Remove unnecessary assets
    
    for file_path in get_all_file_paths(workspace_path, [".bin", ".png"], False):
        os.remove(file_path)
    remove_directory(base_model_copy_path)

#--------------------------------------------
    # Move output path

    for file_path in os.listdir(workspace_path):
        path = Path(file_path)
        if path.suffix and not (path.suffix in config.output_exts):
            continue
           
        source_file_path = os.path.join(workspace_path, file_path)
        destination_file_path = os.path.join(final_output_path, file_path)
        if os.path.exists(destination_file_path):
            if os.path.isdir(destination_file_path):
                shutil.rmtree(destination_file_path)
            elif os.path.isfile(destination_file_path):
                os.remove(destination_file_path)

        shutil.move(source_file_path, destination_file_path)

    # shutil.rmtree(workspace_path)

#--------------------------------------------
    # Print total time
    end_time = time.time()
    execution_time = end_time - start_time
    print("total execution time: {:.2f}s".format(execution_time))

#--------------------------------------------
def get_all_file_paths(directory, extensions, deep):
    file_paths = []

    if deep:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(tuple(extensions)):
                    file_paths.append(os.path.abspath(os.path.join(root, file)))
    else:
        for file in os.listdir(directory):
            if file.endswith(tuple(extensions)):
                path = os.path.abspath(os.path.join(directory, file))
                if os.path.isfile(path):
                    file_paths.append(os.path.abspath(os.path.join(directory, file)))

    return file_paths

def convert_file_path(file, path, ext):
    file_name = os.path.splitext(os.path.basename(file))[0]
    output_name = f"{file_name}{ext}"
    output_path = os.path.join(path, output_name)
    return output_path

def get_not_exist_file_paths(config, target_base_model_file_paths, final_output_path):

    suffixs = []
    for model_setting in config.model_settings:
        suffixs.append(model_setting.suffix)

    target_paths = []
    for file_path in target_base_model_file_paths:
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        is_not_exist_file = False
        for ext in config.output_exts:
            for suffix in suffixs:
                output_path = "{}/{}{}{}".format(final_output_path, file_name, suffix, ext)
                if not os.path.exists(output_path):
                    is_not_exist_file = True
                    break
        if is_not_exist_file:
            target_paths.append(file_path)
            
    return target_paths

#--------------------------------------------
def make_directory(path):
    os.makedirs(path, exist_ok=True)

def remove_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    else:
        print(f"Directory not found: {directory}")
        
#--------------------------------------------
def contains_substring(string_array, target_string):
    return any(string in target_string for string in string_array)

#--------------------------------------------
def copy_base_model_and_convert_gltf(base_model_copy_path, file_path):
    command_separate_gltf = "gltf-pipeline -i {} -o {} -t --keepUnusedElements --keepLegacyExtensions"
    gltf_path = convert_file_path(file_path, base_model_copy_path, ".gltf")
    subprocess.run(command_separate_gltf.format(file_path, gltf_path), shell=True)

#--------------------------------------------
def optimize_textures(config, base_model_copy_path, workspace_path):
    for texture_setting in config.texture_settings:
        texture_path = "{}/{}".format(workspace_path, texture_setting.max_size)
        make_directory(texture_path)
        texture_file_paths = get_all_file_paths(base_model_copy_path, [".png"], False)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Texture Copy
            copy_tasks = [(texture_path, file_path) for file_path in texture_file_paths]
            copy_futures = [executor.submit(texture_copy, *task) for task in copy_tasks]
            concurrent.futures.wait(copy_futures)
            
            # Texture Resize
            resize_tasks = [(texture_setting, texture_path, file_path) for file_path in texture_file_paths]
            resize_futures = [executor.submit(texture_resize, *task) for task in resize_tasks]
            concurrent.futures.wait(resize_futures)
            
            # Texture Convert KTX2
            convert_tasks = [(texture_setting, texture_path, file_path) for file_path in get_all_file_paths(texture_path, [".png"], False)]
            convert_futures = [executor.submit(to_ktx, *task) for task in convert_tasks]
            concurrent.futures.wait(convert_futures)
      
#--------------------------------------------
def texture_copy(texture_path, file_path):
    command_copy_to_dest = "cp {} {}"
    copy_path = convert_file_path(file_path, texture_path, ".png")
    subprocess.run(command_copy_to_dest.format(file_path, copy_path), shell=True)

#--------------------------------------------
def texture_resize(ts, texture_path, file_path):
    copy_path = convert_file_path(file_path, texture_path, ".png")
    subprocess.run(ts.command_resize.format(copy_path), shell=True)
    subprocess.run(ts.command_resize_scale.format(copy_path), shell=True)

#--------------------------------------------
def to_ktx(ts, texture_path, file_path):
    ktx_path = convert_file_path(file_path, texture_path, ".ktx2")
    if ts.keywords and contains_substring(ts.keywords, file_path): # LightMap
        if ts.default_format == "uastc":
            subprocess.run(ts.command_etc1.format(ktx_path, file_path), shell=True)
        else:
            subprocess.run(ts.command_uastc.format(ktx_path, file_path), shell=True)
    else: 
        if ts.default_format == "uastc":
            subprocess.run(ts.command_uastc.format(ktx_path, file_path), shell=True)
        else:
            subprocess.run(ts.command_etc1.format(ktx_path, file_path), shell=True)

    os.remove(file_path)

#--------------------------------------------

def optimize_models(config, base_model_copy_path, workspace_path, texture_path):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for model_setting in config.model_settings:
            
            file_paths = get_all_file_paths(base_model_copy_path, [".gltf"], False)
            for file_path in file_paths:
                future = executor.submit(
                    optimize_model, model_setting, file_path, workspace_path, texture_path
                )
                futures.append(future)

        concurrent.futures.wait(futures)

def optimize_model(ms, file_path, workspace_path, texture_path):
    command_move_to_dest = "mv {} {}"

    copy_to_glb_path = convert_file_path(file_path, workspace_path, "{}.glb".format(ms.suffix))
    subprocess.run(ms.command_glb.format(file_path, copy_to_glb_path), shell=True)

    with open(file_path, 'r') as file:
        gltf_data = json.load(file)

    buffers = gltf_data.get("buffers", [])
    if len(buffers) > 0:
        extensionsUsed = gltf_data.get("extensionsUsed", [])
        extensionsUsed.append("KHR_texture_basisu")
        extensionsUsed.append("KHR_draco_mesh_compression")
        extensionsRequired = gltf_data.get("extensionsRequired", [])
        extensionsRequired.append("KHR_texture_basisu")
        extensionsRequired.append("KHR_draco_mesh_compression")
        samplers = gltf_data.get("samplers", [])
        textures = gltf_data.get("textures", [])
        materials = gltf_data.get("materials", [])

        if ms.tolerance != -1:
            subprocess.run(ms.command_weld.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        if ms.ratio != -1:
            subprocess.run(ms.command_simplify.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        subprocess.run(ms.command_draco.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        copy_to_gltf_path = convert_file_path(file_path, workspace_path, "{}.gltf".format(ms.suffix))
        subprocess.run(ms.command_separate_gltf.format(copy_to_glb_path, copy_to_gltf_path), shell=True)

        with open(copy_to_gltf_path, 'r') as file:
            gltf_data = json.load(file)

        images = gltf_data.get("images", [])
        for image in images:
            image["mimeType"] = "image/ktx2"
            image["uri"] = image["uri"].replace(".png", ".ktx2")

        gltf_data["extensionsUsed"] = extensionsUsed
        gltf_data["extensionsRequired"] = extensionsRequired
        gltf_data["samplers"] = samplers
        gltf_data["textures"] = textures
        gltf_data["materials"] = materials

        with open(copy_to_gltf_path, 'w') as file:
            json.dump(gltf_data, file, indent=4)
    else:
        copy_to_gltf_path = convert_file_path(file_path, workspace_path, "{}.gltf".format(ms.suffix))
        subprocess.run(ms.command_separate_gltf.format(copy_to_glb_path, copy_to_gltf_path), shell=True)

#--------------------------------------------
    # After moving gltf, convert it to glb and put it back
    # moving gltf
    move_gltf_path = convert_file_path(copy_to_gltf_path, texture_path, ".gltf")
    subprocess.run(command_move_to_dest.format(copy_to_gltf_path, move_gltf_path), shell=True)

    # convert glb
    glb_file_path = convert_file_path(copy_to_gltf_path, texture_path, ".glb")
    subprocess.run(ms.command_glb_separate.format(move_gltf_path, glb_file_path), shell=True)

    # put it back
    workspace_glb_path = convert_file_path(move_gltf_path, workspace_path, ".glb")
    subprocess.run(command_move_to_dest.format(glb_file_path, workspace_glb_path), shell=True)

    # put it back
    workspace_gltf_path_back = convert_file_path(glb_file_path, workspace_path, ".gltf")
    subprocess.run(command_move_to_dest.format(move_gltf_path, workspace_gltf_path_back), shell=True)
        
#--------------------------------------------

#----------------------------------------------
# CLI
def main(argv):

    FILE_NAME     = argv[0] 
    INPUT_PATH = ""
    OUTPUT_PATH = ""
    CONPIG_PATH  = ""        
    UPDATE_MODE = False
    
    try:
        opts, etc_args = getopt.getopt(argv[1:], \
                                 "hi:c:", ["help", "path=", "output=", "config=", "update"])

    except getopt.GetoptError: 
        print(FILE_NAME, '--path <input gltf path> --output <output gltf path> --config <config json path)> --update')
        sys.exit(2)

    for opt, arg in opts: 
        if opt in ("-h", "--help"): 
            print(FILE_NAME, '--config <config path>)>')
            sys.exit()

        elif opt in ("--p", "--path"): 
            INPUT_PATH = os.path.abspath(arg)

        elif opt in ("--o", "--output"): 
            OUTPUT_PATH = os.path.abspath(arg)

        elif opt in ("--c", "--config"): 
            CONPIG_PATH = os.path.abspath(arg)

        elif opt in ("--u", "--update"): 
            UPDATE_MODE = os.path.abspath(arg)

    if len(INPUT_PATH) < 1: 
        print(FILE_NAME, "--path option is mandatory") 
        sys.exit(2)

    if len(OUTPUT_PATH) < 1: 
        print(FILE_NAME, "--output option is mandatory") 
        sys.exit(2)

    if len(CONPIG_PATH) < 1: 
        print(FILE_NAME, "--config option is mandatory") 
        sys.exit(2)
        
    run(INPUT_PATH, OUTPUT_PATH, CONPIG_PATH, UPDATE_MODE)

if __name__ == "__main__":
    main(sys.argv)
