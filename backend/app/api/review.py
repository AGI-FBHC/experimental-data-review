import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..services import extract_statistics, run_grim_tests, run_cross_reference_audit, run_domain_audit, generate_html_report
from ..services.dual_model_validator import get_validator, ConsensusStatus
from ..config import AVAILABLE_MODELS, validate_model_selection

review_bp = Blueprint('review', __name__)

# 内存存储（生产环境改用数据库）
review_tasks = {}


@review_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建审查任务"""
    data = request.get_json()
    file_id = data.get('file_id')
    domain = data.get('domain', 'general')
    
    # 模型选择（用户自选）
    model_a = data.get('model_a', 'kimi-coding')
    model_b = data.get('model_b', '')  # 空字符串 = 单模型
    
    # 验证模型选择
    valid, msg = validate_model_selection(model_a, model_b)
    if not valid:
        return jsonify({'error': msg}), 400
    
    if not file_id:
        return jsonify({'error': 'file_id is required'}), 400
    
    task_id = str(uuid.uuid4())
    task = {
        'id': task_id,
        'file_id': file_id,
        'domain': domain,
        'model_a': model_a,
        'model_b': model_b,
        'dual_model': bool(model_b),
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
        if not os.path.exists(file_path):
            for ext in ['.pdf', '.txt', '.md']:
                alt_path = os.path.join('/tmp/uploads', f"{file_id}{ext}")
                if os.path.exists(alt_path):
                    file_path = alt_path
                    break
        
        stats = extract_statistics(file_path)
        task['progress'] = 25
        
        # 2. GRIM 测试
        grim_results = run_grim_tests(stats)
        task['progress'] = 40
        
        # 3. 交叉审查
        cross_results = run_cross_reference_audit(stats)
        task['progress'] = 55
        
        # 4. 领域审查
        domain_results = run_domain_audit(stats, domain)
        task['progress'] = 70
        
        # 5. LLM 校验（用户选择的模型）
        dual_result = None
        if model_a:
            validator = get_validator(model_a, model_b or None)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            dual_result = validator.validate(text, domain, stats)
            task['progress'] = 90
        
        # 6. 生成报告
        report_html = generate_html_report(stats, grim_results, cross_results, domain_results)
        
        report_path = os.path.join('/tmp/reports', f"{task_id}.html")
        os.makedirs('/tmp/reports', exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        task['status'] = 'completed'
        task['progress'] = 100
        
        # Build result
        result = {
            'stats_summary': {
                'total_stats': len(stats),
                'p_values': len([s for s in stats if s.get('type') == 'p_value']),
                'means': len([s for s in stats if s.get('type') == 'mean']),
                'other': len([s for s in stats if s.get('type') not in ['p_value', 'mean']])
            },
            'grim_issues': len([g for g in grim_results if g.get('is_error')]),
            'cross_issues': len([c for c in cross_results if c.get('is_error')]),
            'domain_issues': len([d for d in domain_results if d.get('is_error')]),
            'report_url': f"/api/review/reports/{task_id}",
            'models_used': {
                'model_a': model_a,
                'model_b': model_b or None
            }
        }
        
        # Add LLM validation results
        if dual_result:
            result['llm_review'] = {
                'consensus': dual_result.status.value,
                'validator_a': {
                    'model': dual_result.validator_a.model_name,
                    'passed': dual_result.validator_a.passed,
                    'issues_count': len(dual_result.validator_a.issues),
                    'confidence': dual_result.validator_a.confidence
                },
                'validator_b': {
                    'model': dual_result.validator_b.model_name,
                    'passed': dual_result.validator_b.passed,
                    'issues_count': len(dual_result.validator_b.issues),
                    'confidence': dual_result.validator_b.confidence
                } if dual_result.validator_b else None,
                'disagreement_areas': dual_result.disagreement_areas,
                'recommendation': dual_result.recommendation
            }
        
        task['result'] = result
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
        'model_a': task['model_a'],
        'model_b': task['model_b'],
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


@review_bp.route('/models', methods=['GET'])
def get_models():
    """获取可用模型列表"""
    models = []
    for key, config in AVAILABLE_MODELS.items():
        models.append({
            'key': key,
            'name': config['name'],
            'provider': config['provider'],
            'description': config['description']
        })
    
    return jsonify({
        'models': models,
        'recommendations': [
            '单模型审查：选择 Kimi 或 DeepSeek-v4-pro',
            '双模型审查：Kimi + DeepSeek（推荐，提高多样性）',
            '不推荐同时使用两个 DeepSeek 模型'
        ]
    })


@review_bp.route('/config', methods=['GET'])
def get_config():
    """获取审查配置"""
    from ..config import CONSENSUS_THRESHOLD, AUTO_ESCALATE, DOMAIN_PRESETS
    
    return jsonify({
        'consensus_threshold': CONSENSUS_THRESHOLD,
        'auto_escalate': AUTO_ESCALATE,
        'domain_presets': DOMAIN_PRESETS
    })


@review_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取校验统计"""
    validator = get_validator()
    return jsonify(validator.get_statistics())
