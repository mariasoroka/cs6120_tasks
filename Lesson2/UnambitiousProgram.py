# This program finds all the labels for each function in each program and prints them

import json
import sys

args = sys.argv


for filename in args[1:]:
    print(filename)
    func_names = []
    func_labels = []
    with open(filename) as f:
        d = json.load(f)
        for func in d['functions']:
            name = func['name']
            func_names.append(name)
            func_labels_list = []
            for inst in func['instrs']:
                if 'label' in inst:
                    func_labels_list.append(inst['label'])

            func_labels.append(func_labels_list)

    for i in range(len(func_names)):
        print(func_names[i])
        print(func_labels[i])
        print()
            