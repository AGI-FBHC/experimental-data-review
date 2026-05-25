import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..services import extract_statistics, run_grim_tests, run_cross_reference_audit, run_domain_audit, generate_html_report

review_bp = Blueprint('review', __name__)

# 内存存储（生产环境改用数据库）
review_tasks = {}


@review_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建审查任务"""
    data = request.get_json()
    file_id = data.get('file_id')
    domain = data.get('domain', 'general')
    dual_model = data.get('dual_model', False)
    
    if not file_id:
        return jsonify({'error': 'file_id is required'}), 400
    
    task_id = str(uuid.uuid4())
    task = {
        'id': task_id,
        'file_id': file_id,
        'domain': domain,
        'dual_model': dual_model,
        'status': 'pending',
        'progress': 0,
        'result': None,
        'created_at': datetime.now().isoformat(),
        'completed_at': None
    }
    review_tasks[task_id] = task
    
    # 异步执行审查（简化版，实际应使用 Celery）
    try:
        task['status'] = 'processing'
        task['progress'] = 10
        
        # 1. 提取统计量
        file_path = os.path.join('/tmp/uploads', f"{file_id}.docx")
        stats = extract_statistics(file_path)
        task['progress'] = 30
        
        # 2. GRIM 测试
        grim_results = run_grim_tests(stats)
        task['progress'] = 50
        
        # 3. 交叉审查
        cross_results = run_cross_reference_audit(stats)
        task['progress'] = 70
        
        # 4. 领域审查
        domain_results = run_domain_audit(stats, domain)
        task['progress'] = 90
        
        # 5. 生成报告
        report_html = generate_html_report(stats, grim_results, cross_results, domain_results)
        
        # 保存报告
        report_path = os.path.join('/tmp/reports', f"{task_id}.html")
        os.makedirs('/tmp/reports', exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        task['status'] = 'completed'
        task['progress'] = 100
        task['result'] = {
            'stats_summary': {
                'total_stats': len(stats),
                'p_values': len([s for s in stats if s.get('type') == 'p_value']),
                'means': len([s for s in stats if s.get('type') == 'mean']),
                'other': len([s for s in stats if s.get('type') not in ['p_value', 'mean']])
            },
            'grim_issues': len([g for g in grim_results if g.get('is_error')]),
            'cross_issues': len([c for c in cross_results if c.get('is_error')]),
            'domain_issues': len([d for d in domain_results if d.get('is_error')]),
            'report_url': f"/api/review/reports/{task_id}"
        }
        task['completed_at'] = datetime.now().isoformat()
        
    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
    
    return jsonify({'task_id': task_id, 'status': task['status']}), 202


@review_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """查询任务状态"""
    task = review_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify({
        'id': task['id'],
        'status': task['status'],
        'progress': task['progress'],
        'domain': task['domain'],
        'dual_model': task['dual_model'],
        'result': task.get('result'),
        'error': task.get('error'),
        'created_at': task['created_at'],
        'completed_at': task.get('completed_at')
    })


@review_bp.route('/reports/<task_id>', methods=['GET'])
def get_report(task_id):
    """获取审查报告"""
    report_path = os.path.join('/tmp/reports', f"{task_id}.html")
    if not os.path.exists(report_path):
        return jsonify({'error': 'Report not found'}), 404
    
    with open(report_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    return html


@review_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    return jsonify(list(review_tasks.values()))
