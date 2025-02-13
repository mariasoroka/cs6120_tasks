import json
import sys
import copy
import graphviz

sys.path.append('/Users/ms3663/Courses/CS6120/Bril/bril-txt/')
import briltxt
# Is the instruction a terminator?
def is_terminator(inst):
    return inst['op'] in ['br', 'ret', 'jmp']

def add_to_map(i, j, successors, predeseccors):
    if j not in predeseccors:
        predeseccors[j] = [i]
    else:
        predeseccors[j].append(i)

    if i not in successors:
        successors[i] = [j]
    else:
        successors[i].append(j)

def add_instr_number(json_data):
    json_data_local = copy.deepcopy(json_data)
    line_number = 0
    for func in json_data_local['functions']:
        for inst in func['instrs']:
            inst['line_number'] = line_number
            line_number += 1
    return json_data_local

def get_build_cfg(func):
    basic_blocks = []
    labels_to_blocks = {}
    predeseccors = {}
    successors = {}

    curr_block = []
    curr_label = None
    for inst in func['instrs']:
        if 'label' in inst:
            if len(curr_block) > 0:
                basic_blocks.append(curr_block)
                if curr_label is not None:
                    labels_to_blocks[curr_label] = len(basic_blocks) - 1
            curr_block = [inst]
            curr_label = inst['label']
            
        elif is_terminator(inst):
            curr_block.append(inst)
            basic_blocks.append(curr_block)
            if curr_label is not None:
                labels_to_blocks[curr_label] = len(basic_blocks) - 1
            curr_block = []
            curr_label = None
        else:
            curr_block.append(inst)

    if len(curr_block) > 0:
        basic_blocks.append(curr_block)
        if curr_label is not None:
            labels_to_blocks[curr_label] = len(basic_blocks) - 1

    for i, block in enumerate(basic_blocks):
        if "op" in block[-1]:
            if (block[-1]['op'] == 'br' or block[-1]['op'] == 'jmp'):
                for label in block[-1]['labels']:
                    add_to_map(i, labels_to_blocks[label], successors, predeseccors)
                        
            elif block[-1]['op'] == 'ret':
                pass
            else:
                if i != len(basic_blocks) - 1:
                    # cfg_edges.append((i, i+1))
                    add_to_map(i, i+1, successors, predeseccors)
        else:
            if i != len(basic_blocks) - 1:
                # cfg_edges.append((i, i+1))
                add_to_map(i, i+1, successors, predeseccors)

    return basic_blocks, predeseccors, successors

    

class reachable:
    def merge(self, outs, predeseccors):
        new_in = {}
        for p in predeseccors:
            for key in outs[p]:
                new_in[key] = outs[p][key]
        return new_in
    def transfer(self, basic_block, ins):
        delete = set()
        add = {}
        new_outs = copy.deepcopy(ins)
        for j, inst in enumerate(basic_block):
            if 'dest' in inst:
                for key in new_outs:
                    if 'dest' in new_outs[key] and new_outs[key]['dest'] == inst['dest']:
                        delete.add(key)

                add[str(inst['line_number'])] = inst
        for key in delete:
            new_outs.pop(key)

        new_outs.update(add)

        return new_outs
    def analyze(self, json_data):
        local_json_data = copy.deepcopy(json_data)
        ins_all = []
        outs_all = []
        basic_blocks_all = []
        predeseccors_all = []
        for func in local_json_data['functions']:
            basic_blocks, predeseccors, successors = get_build_cfg(func)

            ins = [{} for _ in range(len(basic_blocks))]
            outs = [{} for _ in range(len(basic_blocks))]

            if 'args' in func:
                for arg in func['args']:
                    ins[0][arg['name']] = {'op' : 'function argument', "dest":  arg['name']}

            worklist = set(range(len(basic_blocks)))


            while len(worklist) > 0:
                b = worklist.pop()
                if b in predeseccors:
                    ins[b] = self.merge(outs, predeseccors[b])
                new_outs = self.transfer(basic_blocks[b], ins[b])

                if new_outs != outs[b]:
                    outs[b] = new_outs
                    if b in successors:
                        for a in successors[b]:
                            # worklist.append(a)
                            worklist.add(a)

            ins_all.append(ins)
            outs_all.append(outs)
            basic_blocks_all.append(basic_blocks)
            predeseccors_all.append(predeseccors)

        return ins_all, outs_all, basic_blocks_all, predeseccors_all

def make_graphs(ins_all, outs_all, basic_blocks_all, predeseccors_all):
    dot = graphviz.Digraph(comment='CFG')
    for func_num, func_blocks in enumerate(basic_blocks_all):
        for i, block in enumerate(func_blocks):
            node_text = "in: \n"
            for var in ins_all[func_num][i]:
                inst = ins_all[func_num][i][var]
                if 'op' in inst and not 'function argument' in inst['op']:
                    node_text += '({}) '.format(inst['line_number'])
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))
                else:
                    node_text += 'function argument {};\n'.format(inst['dest'])
            node_text += '\n'

            for inst in block:
                node_text += '({}) '.format(inst['line_number'])
                if 'label' in inst:
                    node_text += '.{}:\n'.format(inst['label'])
                else:
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))


            node_text += '\n'
            node_text += 'out: \n'
            for var in outs_all[func_num][i]:
                inst = outs_all[func_num][i][var]
                if 'op' in inst and not 'function argument' in inst['op']:
                    node_text += '({}) '.format(inst['line_number'])
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))
                else:
                    node_text += 'function argument {};\n'.format(inst['dest'])

            dot.node(str(func_num) + '_' + str(i), node_text, shape='box')

        for i, block in enumerate(func_blocks):
            if i in predeseccors_all[func_num]:
                for j in predeseccors_all[func_num][i]:
                    dot.edge(str(func_num) + '_' + str(j), str(func_num) + '_' + str(i))

    return dot


d = json.load(sys.stdin)
d_numbered = add_instr_number(d)
df_class = reachable()
ins_all, outs_all, basic_blocks_all, predeseccors_all = df_class.analyze(d_numbered)
print(json.dumps(d))
dot = make_graphs(ins_all, outs_all, basic_blocks_all, predeseccors_all)
dot.render('./cfg.gv', view=True)
