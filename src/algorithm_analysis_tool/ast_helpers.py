from .function_visitor import FunctionDependencyVisitor

def resolve_helpers(entry_name, function_map):
    resolved = set()
    to_visit = [entry_name]

    while to_visit:
        current = to_visit.pop()
        if current in resolved:
            continue

        resolved.add(current)
        fn_node = function_map[current]

        visitor = FunctionDependencyVisitor(function_map.keys())
        visitor.visit(fn_node)

        for dep in visitor.called:
            if dep not in resolved:
                to_visit.append(dep)

    return resolved
