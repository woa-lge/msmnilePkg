#!/bin/python3

# @file
# This script help you build any devices in any platforms in this repo.
#
# Copyright (c) DuoWoa Authors.
# SPDX-License-Identifier: BSD-2-Clause-Patent#
##

# TODO Port to windows if possible.
import argparse
import os,sys
import shutil
import json
import Levenshtein


class Target:
    def __init__(self, device, platform, package, bootshim_uefi_base, bootshim_uefi_size, secureboot, buildtype):
        self.device = device
        self.platform = platform
        self.package = package
        self.bootshim_uefi_base = bootshim_uefi_base
        self.bootshim_uefi_size = bootshim_uefi_size
        self.secureboot = secureboot
        self.buildtype = buildtype

        if self.secureboot is None:
            self.secureboot = 0;

        if self.buildtype is None:
            self.buildtype = "RELEASE";

        if self.buildtype != "RELEASE" and self.buildtype != "DEBUG":
            print(f"Unknown build type \"{self.buildtype}\", change to RELEASE by default.")
            self.buildtype = "RELEASE"


    def merge(self, target_b):
        if self.device is None:
            self.device = target_b.device

        if self.platform is None:
            self.platform = target_b.platform

        if self.package is None:
            self.package = target_b.package

        if self.bootshim_uefi_base is None:
            self.bootshim_uefi_base = target_b.bootshim_uefi_base

        if self.bootshim_uefi_size is None:
            self.bootshim_uefi_size = target_b.bootshim_uefi_size


    def print_content(self):
        print("Target Info: ")
        print("device", self.device)
        print("platform", self.platform)
        print("package", self.package)
        print("bootshim_uefi_base", self.bootshim_uefi_base)
        print("bootshim_uefi_size", self.bootshim_uefi_size)


def is_system_supported():
    return os.name == "posix"


def build_bootshim(this_target):
    bootshim_cmd = os.path.abspath("build_boot_shim.sh") + " -a " + str(this_target.bootshim_uefi_base) + " -b " + str(
        this_target.bootshim_uefi_size)
    return os.system(bootshim_cmd)


def prepare_build(buildtype, package_name):
    stuart_setup_cmd = "python3 " + os.path.join("Platforms", package_name,
                                                         "PlatformBuild.py") + " --setup -t " + buildtype
    stuart_update_cmd = "python3 " + os.path.join("Platforms", package_name,
                                                          "PlatformBuild.py") + " --update -t " + buildtype
    os.system(stuart_setup_cmd)
    os.system(stuart_update_cmd)


def get_devices_list(package_name):
    return os.listdir(os.path.join("Platforms", package_name, "Device"))


def get_platforms_list():
    return os.listdir("Silicon/QC")


# Check is args provided by you available.
def check_args(this_target):
    usage = "Usage: build_uefi.py -d <target_device> [-psth]\n"
    available_devices_msg = "Available devices:"
    available_platforms_msg = "Available platforms:"
    available_platforms_list = get_platforms_list()
    link_msg = "See \033[32mhttps://github.com/woa-msmnile/msmnilePkg#target-list\033[0m for all available devices."

    if this_target.platform is not None and this_target.package is not None:
        current_platform_msg = "\033[33mCurrent platform: " + this_target.platform + "\033[0m"
        available_devices_list = get_devices_list(this_target.package)

        # check if target_device illegal
        device_available = False
        for this_device in available_devices_list:
            if this_device == this_target.device or this_target.device == "all":
                device_available = True
                return device_available

        # if illegal, print all supported devices.
        if not device_available:
            print(usage)
            print(available_devices_msg)
            print(current_platform_msg)
            for this_device in available_devices_list:
                print("\t" + this_device)
            if this_target.device is None:
                print("\nPlease provide target device.")
            else:
                print("\nThe target device \033[1;33;41m" + this_target.device + "\033[0m is not supported.")
            exit(link_msg)

    elif this_target.package is None:  # if package == None, that means parse failed before,
        #   which means platform provided is unsupported.
        print(usage)
        print(available_platforms_msg)
        for this_platform in available_platforms_list:
            print("\t" + this_platform)
        exit(link_msg)
    print()


def device_error_exit(device_name, possible_devices_list):
    usage = "Usage: build_uefi.py -d <target_device> [-psth]\n"
    help_msg = "Use \033[33mbuild_uefi.py --help\033[0m for details"
    not_found_msg = "Target device not found."
    link_msg = "See \033[32mhttps://github.com/woa-msmnile/msmnilePkg#target-list\033[0m for all devices available."
    print(usage)
    if not possible_devices_list:
        print(help_msg)
        print(not_found_msg)
    else:
        possible_devices_msg = "Target device \033[31m" + device_name + "\033[0m not found, did you mean: "
        print(possible_devices_msg)
        for dev_name in possible_devices_list:
            print('\t' + dev_name)
    print()
    print(link_msg)
    exit()


# This function get a file object and return a target object.
# The file must be a json file.
def parse_cfg(pfile):
    this_target = Target(None, None, None, None, None, None, None)
    cfg_dict = json.load(pfile)
    this_target.platform = cfg_dict["platform"]
    this_target.package = cfg_dict["package"]
    this_target.bootshim_uefi_base = cfg_dict["bootshim"]["UEFI_BASE"]
    this_target.bootshim_uefi_size = cfg_dict["bootshim"]["UEFI_SIZE"]
    return this_target


# Build uefi for a single device
def build_single_device(this_target):
    # Print args
    this_target.print_content()
    # Check args
    check_args(this_target)
    # Prepare Environment
    build_bootshim(this_target)
    prepare_build(this_target.buildtype, this_target.package)
#    os.environ['CLANGDWARF_BIN'] = '/usr/lib/llvm-38/bin/'
#    os.environ['CLANGDWARF_AARCH64_PREFIX']='aarch64-linux-gnu-'

    # Start Actual Build
    os.system("python3 " + os.path.join("Platforms", this_target.package, "PlatformBuild.py")
              + " TARGET=" + this_target.buildtype + " TARGET_DEVICE=" + this_target.device + " SEC_BOOT=" + str(this_target.secureboot))

    # Check if build successfully
    # if CI mode enabled, copy .FD and .img into CI upload directory.
    if os.getenv("WM_CI_BUILD") == "true":
        print("Buiding in CI...")
        # Copy build NOSB output into ci upload dir.
        ci_copy_fd_after_single_device_building(this_target)
        # In CI Environment, we build SB and NOSB at same time, build SB here.
        this_target.secureboot = 1
        os.system("python3 " + os.path.join("Platforms", this_target.package, "PlatformBuild.py")
              + " TARGET=" + this_target.buildtype + " TARGET_DEVICE=" + this_target.device + " SEC_BOOT=" + str(this_target.secureboot))
        # Copy build SB output into ci upload dir.
        ci_copy_fd_after_single_device_building(this_target)
        # Move secureboot status back.
        this_target.secureboot = 0


def ci_copy_fd_after_single_device_building(this_target):
    # Copy FD and image into artifacts directory
    # If build successfully, there should be XXXX.fd under <OutputDir>/<package>/<buildtype>_<TOOLCHAIN>/FV/<Platform>_EFI.fd
    secureboot_suffix = "SB" if this_target.secureboot != 0 else "NOSB"
    build_output_path = os.path.join("Build", this_target.package)

    # CI will compress this directory and upload after finishing all build tasks.
    ci_upload_dir = os.path.join(build_output_path, "ci_artifacts", this_target.device)

    # File paths, fd and img
    input_fd_path = os.path.join(build_output_path, this_target.buildtype + "_CLANGDWARF", "FV", this_target.platform.upper() + "_EFI.fd")
    input_img_path = os.path.join(build_output_path, this_target.device + ".img")
    output_fd_path = os.path.join(ci_upload_dir, this_target.platform.upper() + "_EFI_" + secureboot_suffix + ".fd")
    output_img_path = os.path.join(ci_upload_dir, this_target.device + "_" + secureboot_suffix + ".img")

    # Create output directory
    os.makedirs(ci_upload_dir, exist_ok=True)

    # Copy to destination
    try:
        # move FD to upload path
        shutil.move(input_fd_path, output_fd_path)
        print("Successfully move", input_fd_path, "to", output_fd_path)
        # move img to upload path
        shutil.move(input_img_path, output_img_path)
        print("Successfully move", input_img_path, "to", output_img_path)
    except Exception as e:
        print("Build process may be failed!\n Exception: ", e)
        sys.exit(1)


# Build uefi for all devices in one platform.
def build_all_devices(this_target):
    # device == "all" here.
    check_args(this_target)
    device_list = get_devices_list(this_target.package)
    for device_name in device_list:
        this_target.device = device_name
        build_single_device(this_target)


# Build all uefi for all devices.
def build_all_platforms(all_the_targets):
    # platform =="all" here.
    # Traverse all platforms here
    for this_target in all_the_targets:
        this_target.device = "all"
        build_all_devices(this_target)


# Align all strings in a list to a fixed length.
# The rest part will be fill with placeholder
#  and return a list.
def string_to_fixed_len(this_list, max_length, ph=" "):
    if max_length < max([len(i) for i in this_list]):
        max_length = max([len(i) for i in this_list])
    # Find the longest device name.
    aligned_string_list = []
    for this_string in this_list:
        # Fill the rest part with ' '
        aligned_string_list.append(this_string + (max_length - len(this_string)) * ph)
    return aligned_string_list


# Find out all devices.
def find_device_by_name(device_name):
    if device_name is None:
        return None
    # Get all targets from cfg files.
    this_all_targets = []
    get_all_target(this_all_targets)

    for this_target in this_all_targets:
        device_list = get_devices_list(this_target.package)
        if device_list.count(device_name):  # count != 0
            des_target = this_target
            des_target.device = device_name
            return des_target

    # if the given name was not found, provide a guess by calculating
    # Levenshtein distance
    possible_dict = {}
    device_list = []
    for this_target in this_all_targets:
        device_list.extend(get_devices_list(this_target.package))

    device_list = string_to_fixed_len(device_list, 0)
    for device_name_in_list in device_list:
        possible_dict[device_name_in_list] = Levenshtein.distance(device_name, device_name_in_list)

    # Sort
    possible_dict = dict(sorted(possible_dict.items(), key=lambda x: x[1], reverse=False))
    possible_list = []
    for i in range(len(possible_dict)):
        if list(possible_dict.values())[i] - list(possible_dict.values())[0] < 1:
            possible_list.append(list(possible_dict.keys())[i])
    # Debug Use
    #    for _key,_val in possible_dict.items():
    #        print(_key, _val)
    #
    #    print()
    #    for i in possible_list:
    #        print(i)
    return possible_list


# Parse config files in folder.
def get_all_target(this_all_targets):
    config_dir = "build_cfg"
    config_list = os.listdir(config_dir)
    for this_config in config_list:
        if this_config[-5:] == ".json":
            pfile = open(os.path.join(config_dir, this_config), "r")
            this_all_targets.append(parse_cfg(pfile))
            pfile.close()


# main
if __name__ == '__main__':
    # Check host os
    if not is_system_supported():
        exit("Building is not supported on your host system!")

    # Parse Args
    parser = argparse.ArgumentParser(description='Build Uefi for target device.')
    parser.add_argument('-d', type=str, default=None, help="target device")
    parser.add_argument('-p', type=str, default=None, help="target platform")
    parser.add_argument('-s', type=int, default=None, help="secureboot status, should be 1 or 0")
    parser.add_argument('-t', type=str, default=None, help="uefi build type, should be DEBUG or RELEASE")
    args = parser.parse_args()

    # Initial target object
    current_target = Target(args.d, args.p, None, None, None, args.s, args.t)

    destination_target = find_device_by_name(current_target.device) if (
            current_target.platform != "all" and current_target.device != "all") else current_target
    if type(destination_target) != Target:
        device_error_exit(current_target.device, destination_target)  # destination_target is possible_device_list here.
    current_target.merge(destination_target)

    # Parse Config Files
    all_targets = []
    get_all_target(all_targets)

    # Build all devices in one platform
    if current_target.platform == "all":
        build_all_platforms(all_targets)    # Commonly we use this in CI.
    elif current_target.device == "all":
        # Find current target from config and merge.
        for the_target in all_targets:
            if the_target.platform == current_target.platform:
                current_target.merge(the_target)
                break
        build_all_devices(current_target)
    else:
        build_single_device(current_target)
