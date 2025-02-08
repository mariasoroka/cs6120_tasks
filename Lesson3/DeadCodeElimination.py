import json
import sys
import copy

# Is the instruction a terminator?
def is_terminator(inst):
    return inst['op'] in ['br', 'ret', 'jmp']

# Can arguments be permuted?
def is_commutative(op):
    return op in ['add', 'mul', 'eq', 'and', 'or', 'fadd', 'fmul', 'feq']

# Is the instruction an expression or an assignment?
def is_expression(dest, cloud, table):
    num = cloud[dest]
    for key in table:
        if table[key][0] == num:
            if ('const' not in key) and ('input' not in key):
                return True
    return False

# Simple dead code elimination that deletes unused variables
def delete_unused_variables(json_data):
    json_data_local = copy.deepcopy(json_data)
    for func in json_data_local['functions']:
        used_labels = set()
        for inst in func['instrs']:
            if 'args' in inst:
                for arg in inst['args']:
                    used_labels.add(arg)

        new_instr = [instr for instr in func['instrs'] if (('dest' not in instr) or ('dest' in instr  and instr['dest'] in used_labels))]
        func['instrs'] = new_instr
    return json_data_local

# Simple dead code elimination that deletes repetitive assignments to the same variable
def delete_unused_assignments(json_data):
    json_data_local = copy.deepcopy(json_data)
    for func in json_data_local['functions']:
        used = set()
        do_not_remove = set()
        new_instrs = []
        for inst in reversed(func['instrs']):
            if 'label' in inst:
                # If it is a label, start a new block from the next instruction
                new_instrs.append(inst)
                used = set()
                do_not_remove = set()

            elif is_terminator(inst):
                # if it is a terminator, it is a first instruction of the new block
                new_instrs.append(inst)
                used = set()
                do_not_remove = set()
                # add all the arguments to the sets
                if 'args' in inst:
                    for arg in inst['args']:
                        used.add(arg)
                        do_not_remove.add(arg)


            else:
                # Here we are in the middle of the block
                if 'dest' not in inst:
                    # if there is no destination, just add the instruction
                    new_instrs.append(inst)
                else:
                    if inst['dest'] not in used:
                        # if the destination is not used further in the block, keep the instruction
                        new_instrs.append(inst)

                    elif inst['dest'] in do_not_remove:
                        # if the destination is in do_not_remove set, keep the instruction
                        new_instrs.append(inst)
                        do_not_remove.remove(inst['dest'])

                if 'args' in inst:
                    # if there are arguments, add them to the sets
                    for arg in inst['args']:
                        used.add(arg)
                        do_not_remove.add(arg)
                    
        func['instrs'] = list(reversed(new_instrs))
    return json_data_local

# Function that finds a new name for a variable s.t. the new name was not used before
def find_new_name(instr_name, instr_type, cloud, rename):
    if instr_name in rename:
        add_string = str(rename[instr_name][0]) 
        rename[instr_name] = (rename[instr_name][0] + 1, instr_type)
    else:
        add_string = '0'
        rename[instr_name] = (1, instr_type)

    # Iterate while not found a new name
    while instr_name + add_string in cloud:
        add_string = str(rename[instr_name][0])
        rename[instr_name] = (rename[instr_name][0] + 1, instr_type)
    
    return instr_name + add_string

# Local value numbering optimization
def local_value_numbering_optimization(json_data):
    local_json_data = copy.deepcopy(json_data)

    # Treat each function independently
    for func in local_json_data['functions']:
        cloud = {}
        table = {}
        num2var = {}
        rename = {}
        new_instrs = []

        # Add arguments to the cloud and table
        if 'args' in func:
            for i, arg in enumerate(func['args']):
                cloud[arg['name']] = i
                num2var[i] = arg['name']
                table[('input', str(i),)] = i, arg['name']

        for instr_i, instr in enumerate(func['instrs']):
            # Start new block
            if 'label' in instr or is_terminator(instr):
                # Map all renamed variables back to the old names
                for name in rename.keys():
                    new_instr = instr_new = {"args": [
                                    name + str(rename[name][0] - 1)
                                ],
                                "dest": name,
                                "op": "id",
                                "type": rename[name][1]
                                }
                    new_instrs.append(instr_new)
                # Make all the existing variables opaque
                table = {}
                num2var = {}
                rename = {}
                for i, key in enumerate(cloud):
                    table[('input',  str(i),)] = i, key
                    cloud[key] = i
                    num2var[i] = key

                new_instrs.append(instr)

            # Staying in the same block
            else: 
                value = (instr['op'],)

                # If it is a function call, make it unique
                if instr['op'] == 'call':
                    for function in instr['funcs']:
                        value += (function, str(instr_i),)
                # If it is an allocation, make it unique
                elif instr['op'] == 'alloc':
                    value += (str(instr_i),)
                # Collect all the arguments and sort them if the operation is commutative
                if 'args' in instr:
                    new_args = []
                    for arg in instr['args']:
                        if arg in rename:
                            add_string = str(rename[arg][0] - 1)
                            new_args.append(arg + add_string)
                        else:
                            new_args.append(arg)
                    instr['args'] = new_args

                    if is_commutative(instr['op']):
                        unsorted_list = []
                        for arg in instr['args']:
                            unsorted_list.append(cloud[arg])
                        unsorted_list.sort()
                        value += tuple(unsorted_list)
                    else:
                        for arg in instr['args']:
                            value += (cloud[arg],)
                # Collect values
                if 'value' in instr:
                    value += (instr['value'],)
                # If it is a const instruction, make it unique
                if instr['op'] == 'const':
                    value  += (str(instr_i),)
                # Encode language semantics and treat id instructions separately
                if instr['op'] == 'id':
                    num = cloud[instr['args'][0]]
                    arg = num2var[num]
                    
                    if instr['dest'] in cloud:        
                        dest = find_new_name(instr['dest'], instr['type'], cloud, rename)
                    else:
                        dest = instr['dest']

                    instr_new = {"args": [
                                    arg
                                ],
                                "dest": dest,
                                "op": "id",
                                "type": instr['type']
                                }
                    
                    new_instrs.append(instr_new)
                # If the value is already computed, just use it
                elif value in table:
                    if 'dest' in instr:
                        num, dest = table[value]

                        instr_new = {"args": [
                                    dest
                                ],
                                "dest": instr['dest'],
                                "op": "id",
                                "type": instr['type']
                                }
                        new_instrs.append(instr_new)
                    else:
                        new_instrs.append(instr)

                # If the value is not in the table, but it there
                else:
                    num = len(table)
                    if 'dest' in instr:
                        if instr['dest'] in cloud:
                            dest = find_new_name(instr['dest'], instr['type'], cloud, rename)
                        else:
                            dest = instr['dest']

                        table[value] = num, dest
                        num2var[num] = dest
                        instr['dest'] = dest

                    if 'args' in instr:
                        for i, arg in enumerate(instr['args']):
                            instr['args'][i] = num2var[cloud[arg]]

                    new_instrs.append(instr)
                # Update the cloud
                if 'dest' in new_instrs[-1]:
                    cloud[new_instrs[-1]['dest']] = num

        func['instrs'] = new_instrs
    return local_json_data



func_names = []
func_labels = []
d = json.load(sys.stdin)
stop = False
old_d = copy.deepcopy(d)
inter = 0
while not stop and inter < 10:
    inter += 1
    new_d = local_value_numbering_optimization(old_d)
    new_d = delete_unused_assignments(new_d)
    new_d = delete_unused_variables(new_d)
    if new_d == old_d:
        stop = True
    old_d = copy.deepcopy(new_d)
inter = 0
while not stop and inter < 10:
    inter += 1
    new_d = delete_unused_assignments(new_d)
    new_d = delete_unused_variables(new_d)
    if new_d == old_d:
        stop = True
    old_d = copy.deepcopy(new_d)


print(json.dumps(new_d, indent=4))

