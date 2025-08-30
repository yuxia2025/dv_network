from flask import Flask, render_template, request, jsonify
import json
import os
import qrcode
from io import BytesIO
from base64 import b64encode

app = Flask(__name__)
DATA_FILE = 'users.json'

# 确保数据文件存在
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)


def calculate_jaccard(set1, set2):
    """计算两个集合的 Jaccard 相似度"""
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union) if union else 0


@app.route('/')
def form():
    """渲染表单页面"""
    return render_template('form.html')


@app.route('/submit', methods=['POST'])
def submit():
    """处理表单提交"""
    data = request.json
    nickname = data.get('nickname')
    interests = [i.strip().lower() for i in data.get('interests', []) if i.strip()]

    if not nickname or len(interests) != 5:
        return jsonify({'error': '昵称和5个兴趣爱好都是必填项'}), 400

    # 读取现有用户
    with open(DATA_FILE, 'r') as f:
        users = json.load(f)

    # 检查昵称是否已存在（可选）
    if any(user['nickname'].lower() == nickname.lower() for user in users):
        return jsonify({'error': '该昵称已存在，请换一个'}), 400

    # 添加新用户
    users.append({'nickname': nickname, 'interests': interests})
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    return jsonify({'message': '提交成功！'})


@app.route('/network')
def network():
    """渲染网络图页面"""
    return render_template('network.html')


@app.route('/data')
def get_data():
    """为 D3.js 提供网络图数据"""
    with open(DATA_FILE, 'r') as f:
        users = json.load(f)

    nodes = []
    links = []

    # 创建节点
    for user in users:
        nodes.append({
            'id': user['nickname'],
            'name': user['nickname'],
            'interests': user['interests']
        })

    # 创建边（基于 Jaccard 相似度）
    threshold = 0.0  # 即使只有1个共同兴趣也连接
    for i, user1 in enumerate(users):
        for j, user2 in enumerate(users):
            if i >= j:  # 避免重复和自连
                continue
            set1 = set(user1['interests'])
            set2 = set(user2['interests'])
            intersection = set1.intersection(set2)
            similarity = calculate_jaccard(set1, set2)
            if similarity > threshold:
                links.append({
                    'source': user1['nickname'],
                    'target': user2['nickname'],
                    'value': (similarity ** 2) * 20,  # ✅ 平方放大，增强粗细对比
                    'commonCount': len(intersection)   # ✅ 返回共同爱好数量
                })

    return jsonify({'nodes': nodes, 'links': links})


@app.route('/qrcode')
def qrcode_image():
    """生成并返回二维码图片"""
    # 🚨 请将此URL修改为你的实际公网地址，例如：
    # url = "https://your-app.up.railway.app"
    url = "http://localhost:5000"  # 本地测试用，部署后必须修改！
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # 将图片转换为 base64 字符串
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = b64encode(buffered.getvalue()).decode()
    return jsonify({'image': f'data:image/png;base64,{img_str}'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
