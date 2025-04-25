import json
import sys
import copy

def stitch(json_data, trace_file, function_name):
    json_data_local = {'functions': []}
    for func in json_data['functions']:
        if func['name'] != function_name:
            json_data_local['functions'].append(func)
        else:
            func_new = copy.deepcopy(func)
            func_new['instrs'] = []
            func_new['instrs'].append({'op': 'speculate', 'args': []})
            with open(trace_file, 'r') as f:
                while line := f.readline():
                    line = line.strip()
                    d = json.loads(line)
                    func_new['instrs'].append(d)
            last_instr = func_new['instrs'][-1]
            func_new['instrs'].append({'op': 'commit', 'args': []})
            func_new['instrs'].append({'op': 'jmp', 'labels': ["merge"]})
            func_new['instrs'].append({'label': "default"})

            last_instr_idx = func['instrs'].index(last_instr)

            for i in range(last_instr_idx + 1):
                func_new['instrs'].append(func['instrs'][i])
            func_new['instrs'].append({'label': "merge"})
            for i in range(last_instr_idx + 1, len(func['instrs'])):
                func_new['instrs'].append(func['instrs'][i])

            json_data_local['functions'].append(func_new)
                

    return json_data_local
    

#Read command line arguments
function_name = sys.argv[1]

d = json.load(sys.stdin)
new_d = stitch(d, 'trace.txt', function_name)
print(json.dumps(new_d, indent=4))