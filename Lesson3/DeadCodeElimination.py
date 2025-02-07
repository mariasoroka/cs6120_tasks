import json
import sys
import copy

# args = sys.argv

def is_terminator(inst):
    return inst['op'] in ['br', 'ret', 'jmp']
def is_commutative(op):
    return op in ['add', 'mul', 'eq', 'and', 'or', 'fadd', 'fmul', 'feq']

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


def delete_unused_assignments(json_data):
    json_data_local = copy.deepcopy(json_data)
    for func in json_data_local['functions']:
        used = set()
        do_not_remove = set()
        new_instrs = []
        for inst in reversed(func['instrs']):
            if 'label' in inst:
                # if it is a label, start a new block from the next instruction
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
                # here we are in the middle of the block
                if 'args' in inst:
                    # if there are arguments, add them to the sets
                    for arg in inst['args']:
                        used.add(arg)
                        do_not_remove.add(arg)
            
                if 'dest' not in inst:
                    # if there is no destination, just add the instruction
                    new_instrs.append(inst)
                else:
                    if inst['dest'] not in used:
                        # if the destination is not used in the block, keep the instruction
                        new_instrs.append(inst)

                    elif inst['dest'] in do_not_remove:
                        # if the destination is in do_not_remove set, keep the instruction
                        new_instrs.append(inst)
                        do_not_remove.remove(inst['dest'])
                    
        func['instrs'] = list(reversed(new_instrs))
    return json_data_local

def find_new_name(instr_name, cloud, rename):
    if instr_name in rename:
        add_string = str(rename[instr_name]) 
        rename[instr_name] += 1
    else:
        add_string = '0'
        rename[instr_name] = 1

    while instr_name + add_string in cloud:
        add_string = str(rename[instr_name])
        rename[instr_name] += 1

    
    return instr_name + add_string

def local_value_numbering_optimization(json_data):
    local_json_data = copy.deepcopy(json_data)

    for func in local_json_data['functions']:
        cloud = {}
        # the list will contain numbers, tuples and canonical variables
        table = {}
        num2var = {}
        rename = {}

        new_instrs = []

        if 'args' in func:
            for i, arg in enumerate(func['args']):
                cloud[arg['name']] = i
                num2var[i] = arg['name']
                table[('input_' + str(i),)] = i, arg['name']

        for instr in func['instrs']:
                
            if 'label' in instr or is_terminator(instr):
                # start new block
                table = {}
                num2var = {}
                for i, key in enumerate(cloud):
                    table[('input_' + str(i),)] = i, key
                    cloud[key] = i
                    num2var[i] = key

            if not 'op' in instr:
                new_instrs.append(instr)

            else: 
                value = (instr['op'],)
                if 'args' in instr:
                    new_args = []
                    for arg in instr['args']:
                        if arg in rename:
                            add_string = str(rename[arg] - 1)
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

                    
                if 'value' in instr:
                    value += (instr['value'],)
                


                if instr['op'] == 'id':
                    num = cloud[instr['args'][0]]
                    arg = num2var[num]
                    
                    if instr['dest'] in cloud:        
                        dest = find_new_name(instr['dest'], cloud, rename)
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
                    # new_instrs.append(instr)

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
                else:
                    # A newly computed value.
                    num = len(table)

                    
                    if 'dest' in instr:
                        if instr['dest'] in cloud:
                            
                            dest = find_new_name(instr['dest'], cloud, rename)
                        else:
                            dest = instr['dest']

                        table[value] = num, dest
                        num2var[num] = dest
                        instr['dest'] = dest

                    if 'args' in instr:
                        for i, arg in enumerate(instr['args']):
                            instr['args'][i] = num2var[cloud[arg]]

                    new_instrs.append(instr)

                if 'dest' in new_instrs[-1]:
                    cloud[new_instrs[-1]['dest']] = num

        func['instrs'] = new_instrs
        

    return local_json_data



# for filename in args[1:]:
# print(filename)
func_names = []
func_labels = []
d = json.load(sys.stdin)
# with open(filename) as f:
# d = json.load(f)
stop = False
old_d = copy.deepcopy(d)
inter = 0

new_d = local_value_numbering_optimization(old_d)
# while not stop:
#     inter += 1
#     new_d = delete_unused_assignments(old_d)
#     # new_d = delete_unused_variables(old_d)
#     if new_d == old_d:
#         stop = True
#     old_d = copy.deepcopy(new_d)


# new_filename = '.'.join(filename.split('.')[:-1]) + '_new.json'
# with open(new_filename, 'w') as f:
#     json.dump(new_d, f, indent=4)

print(json.dumps(new_d, indent=4))

