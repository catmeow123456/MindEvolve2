import importlib.util
def load_model_module(model_path: str):
    """Load a model module from file path"""
    # 1. 根据文件路径创建模块规范（spec）
    spec = importlib.util.spec_from_file_location("model", model_path)
    
    # 2. 根据规范创建一个新的模块对象
    model = importlib.util.module_from_spec(spec)
    
    # 3. 执行模块的代码（加载模块内容）
    spec.loader.exec_module(model)
    
    # 4. 返回加载后的模块对象
    return model

loaded_module = load_model_module("./my_model.py")
model_instance = loaded_module.MyModel()
print(model_instance.predict(3))  # 输出: 6

