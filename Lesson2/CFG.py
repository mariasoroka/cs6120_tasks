import json
import sys
import graphviz

def is_terminator(inst):
    return inst['op'] in ['br', 'ret', 'jmp']

basic_blocks = []
labels_to_blocks = {}
cfg_edges = []

args = sys.argv
filename = args[1]

with open(filename) as f:
    d = json.load(f)
    for func in d['functions']:
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
                cfg_edges.append((i, labels_to_blocks[label]))
        elif block[-1]['op'] == 'ret':
            pass
        else:
            if i != len(basic_blocks) - 1:
                cfg_edges.append((i, i+1))
    else:
        if i != len(basic_blocks) - 1:
            cfg_edges.append((i, i+1))
    

dot = graphviz.Digraph(comment='CFG')

for i, block in enumerate(basic_blocks):
    node_text = ""
    for inst in block:
        if 'label' in inst:
            node_text += inst['label'] + '\n'
        elif 'op' in inst:
            node_text += inst['op']
            if 'dest' in inst:
                node_text += ' ' + inst['dest']
            if 'args' in inst:
                node_text += ' ' + ' '.join(inst['args'])
            node_text += '\n'
        else:
            node_text += str(inst) + '\n'
    dot.node(str(i), node_text)
for edge in cfg_edges:
    dot.edge(str(edge[0]), str(edge[1]))

dot.render('./cfg.gv', view=True)