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
                    add_to_map(i, i+1, successors, predeseccors)
        else:
            if i != len(basic_blocks) - 1:
                add_to_map(i, i+1, successors, predeseccors)

    return basic_blocks, predeseccors, successors

def get_dominators(json_data):
    local_json_data = copy.deepcopy(json_data)
    doms_all = []
    basic_blocks_all = []
    predeseccors_all = []
    successors_all = []
    for func in local_json_data['functions']:
        basic_blocks, predeseccors, successors = get_build_cfg(func)

        doms = [set([j for j in range(len(basic_blocks))]) for i in range(len(basic_blocks))]
        # doms = [set() for i in range(len(basic_blocks))]
        doms[0] = set([0])
        doms_new = [set() for i in range(len(basic_blocks))]

        continue_flag = True
        while continue_flag:
            doms_new = copy.deepcopy(doms)
            for i in range(1, len(basic_blocks)):
                if i in predeseccors and len(predeseccors[i]) != 0:
                    doms_new[i] = copy.deepcopy(doms[predeseccors[i][0]])
                    for j in range(1, len(predeseccors[i])):
                        doms_new[i] = doms_new[i].intersection(doms_new[predeseccors[i][j]])
                doms_new[i].add(i)


            if doms_new == doms:
                continue_flag = False
            doms = copy.deepcopy(doms_new)
            

        doms_all.append(doms)
        basic_blocks_all.append(basic_blocks)
        predeseccors_all.append(predeseccors)
        successors_all.append(successors)

    return doms_all, basic_blocks_all, predeseccors_all, successors_all

def build_dominator_tree(doms_all, basic_blocks_all):
    dom_tree_all = []
    for func_num, func_blocks in enumerate(basic_blocks_all):
        dom_tree = {}
        doms = doms_all[func_num]
        for i in range(len(func_blocks)):
            for j in doms[i]:
                if j not in dom_tree:
                    dom_tree[j] = []
                dom_tree[j].append(i)

        dom_tree_all.append(dom_tree)
    return dom_tree_all

def build_dominance_frontier(doms_tree_all, successos_all):
    dominance_frontier_all = []
    for func_num, func_blocks in enumerate(basic_blocks_all):
        dominance_frontier = {}
        doms_tree = doms_tree_all[func_num]
        successors = successos_all[func_num]
        for i in doms_tree.keys():
            for j in doms_tree[i]:
                if j != i and j in successors:
                    for k in successors[j]:
                        if k not in doms_tree[i]:
                            if i not in dominance_frontier:
                                dominance_frontier[i] = []
                            dominance_frontier[i].append(k)
        
        dominance_frontier_all.append(dominance_frontier)
    return dominance_frontier_all

def make_graphs(doms_all, basic_blocks_all, predeseccors_all):
    dot = graphviz.Digraph(comment='CFG')
    for func_num, func_blocks in enumerate(basic_blocks_all):
        for i, block in enumerate(func_blocks):
            node_text = "Block number: " + str(i) + '\n'

            for inst in block:
                if 'label' in inst:
                    node_text += '.{}:\n'.format(inst['label'])
                else:
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))

            node_text += '\n'
            node_text += 'Dominators: '
            for dom in doms_all[func_num][i]:
                node_text += str(dom) + ', '

            dot.node(str(func_num) + '_' + str(i), node_text, shape='box')

        for i, block in enumerate(func_blocks):
            if i in predeseccors_all[func_num]:
                for j in predeseccors_all[func_num][i]:
                    dot.edge(str(func_num) + '_' + str(j), str(func_num) + '_' + str(i))

    return dot

def make_dom_tree_graphs(doms_tree_all, doms_all, basic_blocks_all, predeseccors_all):
    dot = graphviz.Digraph(comment='Dominance Tree')
    for func_num, func_blocks in enumerate(basic_blocks_all):
        for i, block in enumerate(func_blocks):
            node_text = "Block number: " + str(i) + '\n'

            for inst in block:
                if 'label' in inst:
                    node_text += '.{}:\n'.format(inst['label'])
                else:
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))

            node_text += '\n'
            node_text += 'Dominators: '
            for dom in doms_all[func_num][i]:
                node_text += str(dom) + ', '

            dot.node(str(func_num) + '_' + str(i), node_text, shape='box')

        for i, block in enumerate(func_blocks):
            if i in doms_tree_all[func_num]:
                for j in doms_tree_all[func_num][i]:
                    dot.edge(str(func_num) + '_' + str(i), str(func_num) + '_' + str(j))

    return dot

def make_dom_frontier_graphs(dominance_frontier_all, doms_all, basic_blocks_all):
    dot = graphviz.Digraph(comment='Dominance Frontier', strict=True)
    for func_num, func_blocks in enumerate(basic_blocks_all):
        for i, block in enumerate(func_blocks):
            node_text = "Block number: " + str(i) + '\n'

            for inst in block:
                if 'label' in inst:
                    node_text += '.{}:\n'.format(inst['label'])
                else:
                    node_text += '  {};\n'.format(briltxt.instr_to_string(inst))

            node_text += '\n'
            node_text += 'Dominators: '
            for dom in doms_all[func_num][i]:
                node_text += str(dom) + ', '

            dot.node(str(func_num) + '_' + str(i), node_text, shape='box')

        for i, block in enumerate(func_blocks):
            if i in dominance_frontier_all[func_num]:
                for j in dominance_frontier_all[func_num][i]:
                    dot.edge(str(func_num) + '_' + str(i), str(func_num) + '_' + str(j))

    return dot

def test_dominators(doms_all, basic_blocks_all, predeseccors_all, successors_all):
    for func_num, func_blocks in enumerate(basic_blocks_all):
        doms = doms_all[func_num]
        predeseccors = predeseccors_all[func_num]
        successors = successors_all[func_num]
        paths = [[] for i in range(len(func_blocks))]
        
        current_paths = []
        current_paths.append([0])
        while len(current_paths) > 0:
            path = current_paths.pop()
            node = path[-1]

            if node in successors:
                for succ in successors[node]:
                    new_path = path.copy()
                    new_path.append(succ)
                    paths[succ].append(new_path)
                    if succ not in path:
                        current_paths.append(new_path)
                        

        for i in range(len(func_blocks)):
            if len(paths[i]) != 0:
                doms_i = paths[i][0]
                if i == 0:
                    doms_i = [0]
                for path in paths[i]:
                    doms_i = set(doms_i).intersection(path)
                if doms_i != doms[i]:
                    # print('Dominators for block ', i, ' are not correct')
                    # print('Expected: ', doms[i])
                    # print('Actual: ', doms_i)
                    return False
    return True


            

d = json.load(sys.stdin)
doms_all, basic_blocks_all, predeseccors_all, successors_all = get_dominators(d)
correct = test_dominators(doms_all, basic_blocks_all, predeseccors_all, successors_all)
if not correct:
    # assert False
    print("Incorrect dominators")
    exit(0)
doms_tree_all = build_dominator_tree(doms_all, basic_blocks_all)
dominance_frontier_all = build_dominance_frontier(doms_tree_all, successors_all)
# print(json.dumps(d))
dot = make_graphs(doms_all, basic_blocks_all, predeseccors_all)
dom_tree_graph = make_dom_tree_graphs(doms_tree_all, doms_all, basic_blocks_all, predeseccors_all)
dom_frontier_graph = make_dom_frontier_graphs(dominance_frontier_all, doms_all, basic_blocks_all)
# dom_frontier_graph.render('./dom_frontier.gv', view=True)
# dom_tree_graph.render('./dom_tree.gv', view=True)
# dot.render('./cfg.gv', view=True)
