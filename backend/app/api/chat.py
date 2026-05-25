import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

chat_bp = Blueprint('chat', __name__)

# 内存存储
conversations = {}
messages = {}


@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """列出所有对话"""
    return jsonify({
        'success': True,
        'conversations': list(conversations.values())
    })


@chat_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """创建新对话"""
    data = request.get_json()
    conv_id = str(uuid.uuid4())
    conversation = {
        'id': conv_id,
        'title': data.get('title', '新对话'),
        'model': data.get('model', 'claude'),
        'createdAt': datetime.now().isoformat(),
        'updatedAt': datetime.now().isoformat()
    }
    conversations[conv_id] = conversation
    messages[conv_id] = []

    return jsonify({
        'success': True,
        'conversation': conversation
    })


@chat_bp.route('/conversations/<conv_id>/messages', methods=['GET'])
def get_messages(conv_id):
    """获取对话消息"""
    if conv_id not in conversations:
        return jsonify({'error': 'Conversation not found'}), 404
    return jsonify({
        'success': True,
        'messages': messages.get(conv_id, [])
    })


@chat_bp.route('/conversations/<conv_id>/messages', methods=['POST'])
def send_message(conv_id):
    """发送消息"""
    if conv_id not in conversations:
        return jsonify({'error': 'Conversation not found'}), 404

    data = request.get_json()
    content = data.get('content', '')

    # 用户消息
    user_msg = {
        'id': str(uuid.uuid4()),
        'role': 'user',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    messages[conv_id].append(user_msg)

    # TODO: 调用 AI 模型获取回复
    # 这里先返回占位回复
    assistant_msg = {
        'id': str(uuid.uuid4()),
        'role': 'assistant',
        'content': f'[AI 回复占位] 收到消息: {content[:50]}...',
        'timestamp': datetime.now().isoformat()
    }
    messages[conv_id].append(assistant_msg)

    conversations[conv_id]['updatedAt'] = datetime.now().isoformat()

    return jsonify({
        'success': True,
        'message': assistant_msg
    })


@chat_bp.route('/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    """删除对话"""
    if conv_id not in conversations:
        return jsonify({'error': 'Conversation not found'}), 404

    del conversations[conv_id]
    if conv_id in messages:
        del messages[conv_id]

    return jsonify({'success': True})
