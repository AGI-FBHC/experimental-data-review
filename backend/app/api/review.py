import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

review_bp = Blueprint('review', __name__)

# 内存存储（生产环境改用数据库）
review_tasks = {}


@review_bp.route('/submit', methods=['POST'])
def submit_review():
    """提交审查任务"""
    data = request.get_json()
    file_id = data.get('fileId')
    domain = data.get('domain', 'general')
    dual_model = data.get('dualModel', False)
    model_a = data.get('modelA', 'claude')
    model_b = data.get('modelB', 'gemini')

    if not file_id:
        return jsonify({'error': 'fileId is required'}), 400

    task_id = str(uuid.uuid4())
    task = {
        'id': task_id,
        'fileId': file_id,
        'domain': domain,
        'dualModel': dual_model,
        'modelA': model_a,
        'modelB': model_b,
        'status': 'pending',
        'progress': 0,
        'result': None,
        'createdAt': datetime.now().isoformat(),
        'completedAt': None
    }
    review_tasks[task_id] = task

    # TODO: 启动异步审查任务
    # 这里先返回任务ID，实际应该用 Celery/Redis 做异步

    return jsonify({
        'success': True,
        'taskId': task_id,
        'message': 'Review task submitted'
    })


@review_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """查询审查状态"""
    task = review_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)


@review_bp.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    """获取审查结果"""
    task = review_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    if task['status'] != 'completed':
        return jsonify({'error': 'Task not completed'}), 400

    return jsonify({
        'success': True,
        'result': task['result']
    })


@review_bp.route('/list', methods=['GET'])
def list_reviews():
    """列出所有审查任务"""
    return jsonify({
        'success': True,
        'tasks': list(review_tasks.values())
    })
