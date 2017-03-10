#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Clone multiple Virtual Machines in vSphere.

Usage:
    clone_vms.py [options]
    clone_vms.py --version
    clone_vms.py (-h | --help)

Options:
    -h, --help          Prints this page
    --version           Prints current version
    --no-color          Do not color terminal output
    -v, --verbose       Emit debugging logs to terminal
    -f, --file FILE     Name of JSON file with server connection information

"""

import logging

from docopt import docopt

from adles.utils import prompt_y_n_question, user_input, pad, default_prompt, script_setup
from adles.vsphere.vm_utils import clone_vm
from adles.vsphere.folder_utils import traverse_path, format_structure, retrieve_items

__version__ = "0.5.1"
args = docopt(__doc__, version=__version__, help=True)
server = script_setup('clone_vms.log', args, (__file__, __version__))

vm = None
folder_from = None
vms = []
vm_names = []

# Single-vm source
if prompt_y_n_question("Do you want to clone from a single VM?"):
    v, v_name = user_input("Name of or path to the VM or template you wish to clone: ", "VM",
                            lambda x: traverse_path(server.get_folder(), x) if '/' in x else server.get_vm(x))
    vms.append(v)
    vm_names.append(str(input("Base name for instances to be created: ")))

# Multi-VM source
else:
    folder_from, from_name = user_input("Name of or path to the folder you want to clone all VMs in: ", "folder",
                            lambda x: traverse_path(server.get_folder(), x) if '/' in x else server.get_folder(x))
    v, _ = retrieve_items(folder_from)  # Get VMs in the folder, ignore any folders
    vms.extend(v)
    logging.info("%d VMs found in source folder %s\n%s", len(v), from_name, format_structure(v))
    if not prompt_y_n_question("Keep the same names? "):
        names = []
        for i in range(len(v)):
            names.append(str(input("Enter base name for VM %d: " % i)))
    else:
        names = list(map(lambda x: x.name, v))  # Same names as sources
    vm_names.extend(names)

create_in, create_in_name = user_input("Name of or path to the folder in which to create VMs: ", "folder",
                             lambda x: traverse_path(server.get_folder(), x) if '/' in x else server.get_folder(x))

instance_folder_base = None
if prompt_y_n_question("Do you want to create a folder for each instance? "):
    instance_folder_base = str(input("Enter instance folder base name: "))

num_instances = int(input("Number of instances to be created: "))

pool = server.get_pool().name
pool = default_prompt(prompt="Resource pool to assign VMs to", default=pool)

logging.info("Creating %d instances under folder %s", num_instances, create_in_name)
for instance in range(num_instances):
    for vm, name in zip(vms, vm_names):
        spec = server.gen_clone_spec(pool_name=pool)  # Generate clone specification
        if instance_folder_base:  # Create instance folders for a nested clone
            f = server.create_folder(instance_folder_base + pad(instance), create_in=create_in)
            vm_name = name
            clone_vm(vm=vm, folder=f, name=vm_name, clone_spec=spec)  # Clone the VM using the generated spec
        else:
            vm_name = name + pad(value=instance, length=2)  # Append instance number, since it's a flat clone
            clone_vm(vm=vm, folder=create_in, name=vm_name, clone_spec=spec)  # Clone the VM using the generated spec
