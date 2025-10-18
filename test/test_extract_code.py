"""测试增强的 extract_code 函数"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evolution.main import EvolutionEngine

def test_extract_code():
    """测试各种代码提取场景"""
    
    print("=" * 60)
    print("测试增强的 extract_code 函数")
    print("=" * 60)
    
    # 测试用例1: 标准格式 - 完整的代码块
    test1 = """```python
def hello():
    print("Hello, World!")
```"""
    result1 = EvolutionEngine.extract_code(test1)
    print("\n[测试1] 标准格式 (```python...```)")
    print(f"输入: {repr(test1)}")
    print(f"输出: {repr(result1)}")
    assert "def hello():" in result1
    assert "```" not in result1
    print("✓ 通过")
    
    # 测试用例2: 只有结尾标记
    test2 = """def hello():
    print("Hello, World!")
```"""
    result2 = EvolutionEngine.extract_code(test2)
    print("\n[测试2] 只有结尾标记 (code```)")
    print(f"输入: {repr(test2)}")
    print(f"输出: {repr(result2)}")
    assert "def hello():" in result2
    assert "```" not in result2
    print("✓ 通过")
    
    # 测试用例3: 只有开头标记
    test3 = """```python
def hello():
    print("Hello, World!")"""
    result3 = EvolutionEngine.extract_code(test3)
    print("\n[测试3] 只有开头标记 (```python...)")
    print(f"输入: {repr(test3)}")
    print(f"输出: {repr(result3)}")
    assert "def hello():" in result3
    assert "```" not in result3
    print("✓ 通过")
    
    # 测试用例4: 无标记
    test4 = """def hello():
    print("Hello, World!")"""
    result4 = EvolutionEngine.extract_code(test4)
    print("\n[测试4] 无标记 (纯代码)")
    print(f"输入: {repr(test4)}")
    print(f"输出: {repr(result4)}")
    assert "def hello():" in result4
    assert "```" not in result4
    print("✓ 通过")
    
    # 测试用例5: 多个代码块
    test5 = """```python
def hello():
    print("Hello")
```

Some text here

```python
def world():
    print("World")
```"""
    result5 = EvolutionEngine.extract_code(test5)
    print("\n[测试5] 多个代码块")
    print(f"输入: {repr(test5)}")
    print(f"输出: {repr(result5)}")
    assert "def hello():" in result5
    assert "def world():" in result5
    assert "```" not in result5
    print("✓ 通过")
    
    # 测试用例6: 使用 ``` 而不是 ```python
    test6 = """```
def hello():
    print("Hello, World!")
```"""
    result6 = EvolutionEngine.extract_code(test6)
    print("\n[测试6] 使用 ``` 而不是 ```python")
    print(f"输入: {repr(test6)}")
    print(f"输出: {repr(result6)}")
    assert "def hello():" in result6
    assert "```" not in result6
    print("✓ 通过")
    
    # 测试用例7: 没有换行符的代码块
    test7 = """```python def hello(): print("Hello")```"""
    result7 = EvolutionEngine.extract_code(test7)
    print("\n[测试7] 没有换行符的代码块")
    print(f"输入: {repr(test7)}")
    print(f"输出: {repr(result7)}")
    assert "def hello():" in result7
    assert "```" not in result7
    print("✓ 通过")
    
    # 测试用例8: 前后有额外文本
    test8 = """Here is the code:

```python
def hello():
    print("Hello, World!")
```

This is the end."""
    result8 = EvolutionEngine.extract_code(test8)
    print("\n[测试8] 前后有额外文本")
    print(f"输入: {repr(test8)}")
    print(f"输出: {repr(result8)}")
    assert "def hello():" in result8
    assert "```" not in result8
    assert "Here is the code:" not in result8
    assert "This is the end." not in result8
    print("✓ 通过")
    
    print("\n" + "=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)

if __name__ == "__main__":
    test_extract_code()
