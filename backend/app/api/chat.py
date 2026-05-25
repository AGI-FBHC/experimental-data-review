import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..services.chat_service import get_chat_service

chat_bp = Blueprint('chat', __name__)

# 内存存储
conversations = {}
messages = {}


@chat_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """创建新对话"""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    
    service = get_chat_service()
    conv_id = service.create_conversation(task_id)
    
    return jsonify({
        'conversation_id': conv_id,
        'task_id': task_id,
        'created_at': datetime.now().isoformat()
    })


@chat_bp.route('/conversations/<conv_id>/messages', methods=['POST'])
def send_message(conv_id):
    """发送消息"""
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'content is required'}), 400
    
    service = get_chat_service()
    conv = service.get_conversation(conv_id)
    
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get review context if task_id is associated
    review_context = None
    if conv.task_id:
        # In production, fetch actual review results
        review_context = {'task_id': conv.task_id}
    
    # Generate response
    response = service.generate_response(
        conv_id=conv_id,
        user_message=data['content'],
        review_context=review_context
    )
    
    return jsonify({
        'conversation_id': conv_id,
        'response': response,
        'timestamp': datetime.now().isoformat()
    })


@chat_bp.route('/conversations/<conv_id>/messages', methods=['GET'])
def get_messages(conv_id):
    """获取对话历史"""
    service = get_chat_service()
    history = service.get_conversation_history(conv_id)
    
    return jsonify({
        'conversation_id': conv_id,
        'messages': history
    })


@chat_bp.route('/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    """获取对话信息"""
    service = get_chat_service()
    conv = service.get_conversation(conv_id)
    
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify({
        'id': conv.id,
        'task_id': conv.task_id,
        'message_count': len(conv.messages),
        'created_at': conv.created_at,
        'updated_at': conv.updated_at
    })
