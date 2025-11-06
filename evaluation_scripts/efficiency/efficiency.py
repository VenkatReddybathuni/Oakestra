def calculate_metrics(results):
    wasted_time = 0
    total_tasks = len(results)
    killed_tasks = 0

    for task_id, start, end, killed in results:
        if killed:
            wasted_time += end - start
            killed_tasks += 1

    efficiency = (wasted_time / (sum(end - start for _, start, end, killed in results))) if total_tasks > 0 else 0

    return {
        'Total Tasks': total_tasks,
        'Killed Tasks': killed_tasks,
        'Wasted Time': wasted_time,
        'Efficiency (%)': 100 * (1 - efficiency)
    }