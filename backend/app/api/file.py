import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

file_bp = Blueprint('file', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads')
ALLOWED_EXTENSIONS = {'docx', 'pdf', 'tex', 'txt', 'md'}

# 内存存储
uploaded_files = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{file_id}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        file_info = {
            'id': file_id,
            'filename': secure_filename(file.filename),
            'storedName': filename,
            'size': os.path.getsize(filepath),
            'type': ext,
            'uploadedAt': datetime.now().isoformat()
        }
        uploaded_files[file_id] = file_info

        return jsonify({
            'success': True,
            'file': file_info
        })

    return jsonify({'error': 'File type not allowed'}), 400


@file_bp.route('/list', methods=['GET'])
def list_files():
    """列出所有文件"""
    return jsonify({
        'success': True,
        'files': list(uploaded_files.values())
    })


@file_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """下载文件"""
    file_info = uploaded_files.get(file_id)
    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    return send_from_directory(UPLOAD_FOLDER, file_info['storedName'],
                               as_attachment=True,
                               download_name=file_info['filename'])


@file_bp.route('/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """删除文件"""
    file_info = uploaded_files.get(file_id)
    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    filepath = os.path.join(UPLOAD_FOLDER, file_info['storedName'])
    if os.path.exists(filepath):
        os.remove(filepath)

    del uploaded_files[file_id]
    return jsonify({'success': True})
