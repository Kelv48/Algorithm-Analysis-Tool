from src.algorithm_analysis_tool.ast_visitor import ASTVisitor, count_arith, count_assign, count_call, count_compare, count_index, COUNTERS

def test_simple_assignment():
    result = ASTVisitor.run_code("x = 5")

    assert result["assignments"] == 1