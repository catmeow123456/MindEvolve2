import os
import dotenv
import signal
import threading
import importlib
import core.task.plugin as plugin
from flask import Flask, jsonify, request, after_this_request

app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

is_running = True

from core.base.config import TaskConfig

task_config = TaskConfig.from_yaml("core/task/config.yaml")
PluginClass = getattr(plugin, task_config.plugin_name)

plugin = PluginClass(task_config, "core/task")
evaluator = plugin.create_evaluator()

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': 'Service is running normally'
    }), 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """优雅关闭服务接口"""
    global is_running
    is_running = False
    
    @after_this_request
    def shutdown_after_request(response):
        # 确保响应发送完成后再关闭
        threading.Thread(target=lambda: os.kill(os.getpid(), signal.SIGINT)).start()
        return response
    
    return jsonify({
        'status': 'shutting down',
        'message': 'Server is shutting down gracefully'
    }), 200

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    code = data.get('code')
    if not code or not isinstance(code, str):
        return jsonify({'error': 'JSON data format wrong, code not provided'}), 400
    result, metadata = evaluator.evaluate(code)
    return jsonify({
        'result': result,
        'metadata': metadata
    }), 200

@app.before_request
def check_service_status():
    """在所有请求前检查服务状态"""
    if not is_running:
        return jsonify({
            'status': 'shutting down',
            'message': 'Service is shutting down and not accepting new requests'
        }), 503

if __name__ == '__main__':
    dotenv.load_dotenv()
    app.run(host='0.0.0.0', port=os.environ.get('REQUEST_PORT', 9000), threaded=True)
