import glob
import pprint
import sys


def get_list_item_counts(l: list[str]) -> list[int]:
    counts = {}
    for i in l:
        counts[i] = l.count(i)
    return list(counts.values())


files = [f for f in glob.glob("./res/logs/my_approach/*") if "actions" not in f]
results = []
for file in files:
    if "petclinic" not in file:
        continue
    project_code = file.split('/')[-1].split('_')[0]
    per_minute_failures = []

    failure_lines = [line for line in
                     open(file, 'r').read().split('WARNING  Finished')[0].split('WARNING  Starting')[1].split('\n') if
                     "ERROR    Failure" in line]
    actions = ["".join(line.split(',')[1:-2]).strip() for line in
               open(f'{file.split(".log")[0]}_actions.log', 'r').readlines()]

    curr_minute = failure_lines[0][14:16]
    unique_failures = []
    for failure_line in failure_lines:
        minute = failure_line[14:16]
        failure_text = failure_line[19:]
        if minute != curr_minute:
            per_minute_failures.append(len(unique_failures))
            curr_minute = minute
        if failure_text not in unique_failures:
            unique_failures.append(failure_text)
    per_minute_failures.append(len(unique_failures))

    traces = []
    current_trace_actions = []
    redundant_actions_within_count = 0
    redundant_actions_between_count = 0
    action_count = 0
    redundancy_within_occurance = 0
    for action in actions:
        if action == 'None':
            if len(current_trace_actions) > 0:
                counts = get_list_item_counts(current_trace_actions)
                redundants = (sum(counts) - len(counts))
                redundant_actions_within_count = redundant_actions_within_count + redundants
                if redundants > 0:
                    redundancy_within_occurance = redundancy_within_occurance + 1
                traces.append(current_trace_actions)
            current_trace_actions = []
        else:
            action_count = action_count + 1
            current_trace_actions.append(action)

    if len(current_trace_actions) > 0:
        redundant_actions_within_count = redundant_actions_within_count + (
                sum(get_list_item_counts(current_trace_actions)) - len(current_trace_actions))
        traces.append(current_trace_actions)

    counts = get_list_item_counts([str(trace) for trace in traces])
    redundant_actions_between_count = sum(counts) - len(counts)

    results.append({
        'project': project_code,
        'total_failure': len(failure_lines),
        'unqiue_failures': per_minute_failures,
        'redundancy(within)_percentage': (redundant_actions_within_count * 100.00) / action_count,
        'redundancy(within)_occurance_percentage': (redundancy_within_occurance * 100.00) / len(traces),
        'redundancy(between)': (redundant_actions_between_count * 100.00) / len(traces)
    })

pprint.pprint(results)
