import subprocess
from io import StringIO

benchmarks_dir = "../../Bril/benchmarks/core/"
benchmarks = ['birthday.bril', 'gcd.bril', 'sum-sq-diff.bril']
function_names = ['probability', 'main', 'squareOfSum']
args = [[["3"], ["4"], ["5"], ["6"]], 
        [["10", "20"], ["15", "25"], ["9", "42"], ["12", "18"]],
        [["100"], ["200"], ["300"], ["400"]]]

for i in range(len(benchmarks)):
    correct_outputs = []
    baseline_perfromance = []
    jitted_outputs = []
    jitted_performance = []
    # Trace for the first argument
    file = open(benchmarks_dir + benchmarks[i], "r")
    output = subprocess.check_output(["bril2json"], stdin = file)
    output = subprocess.check_output(["brili", "-trace", "-f", function_names[i]] + args[i][0], input = output)
    
    file = open(benchmarks_dir + benchmarks[i], "r")
    output = subprocess.check_output(["bril2json"], stdin = file)
    output = subprocess.check_output(["python3", "stitch.py", function_names[i]], input = output)
    output = subprocess.check_output(["bril2txt"], input = output)
    file.close()
    output_file = open("jitted.bril", "w")
    output_file.write(output.decode("utf-8"))
    output_file.close()

    for j in range(len(args[i])):
        # Compute correct outputs and timings without jitting
        file = open(benchmarks_dir + benchmarks[i], "r")
        output = subprocess.check_output(["bril2json"], stdin = file)
        file.close()
        err_file = open("tmp.err", "w")
        output = subprocess.check_output(["brili", "-p"] + args[i][j], input = output, stderr=err_file)
        err_file.close()
        err_file = open("tmp.err", "r")
        string_err = err_file.readline()
        err_file.close()
        baseline_perfromance.append(int(string_err.split()[1]))
        correct_outputs.append(float(output))

    for j in range(len(args[i])):
        # Compute outputs and timings with jitting
        file = open('jitted.bril', "r")
        output = subprocess.check_output(["bril2json"], stdin = file)
        file.close()
        err_file = open("tmp.err", "w")
        output = subprocess.check_output(["brili", "-p"] + args[i][j], input = output, stderr=err_file)
        err_file.close()
        err_file = open("tmp.err", "r")
        string_err = err_file.readline()
        err_file.close()
        jitted_performance.append(int(string_err.split()[1]))
        jitted_outputs.append(float(output))

        

    print("Correct outputs for benchmark " + benchmarks[i] + ":")
    print(correct_outputs)
    print("Baseline performance for benchmark " + benchmarks[i] + ":")
    print(baseline_perfromance)

    print("Jitted outputs for benchmark " + benchmarks[i] + ":")
    print(jitted_outputs)

    print("Jitted performance for benchmark " + benchmarks[i] + ":")
    print(jitted_performance)

    for j in range(len(args[i])):
        if correct_outputs[j] != jitted_outputs[j]:
            print("Error: outputs do not match for benchmark " + benchmarks[i] + " with input " + str(args[i][j]))
            assert False