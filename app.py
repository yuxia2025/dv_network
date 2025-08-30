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
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

def calculate_jaccard(set1, set2):
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union) if union else 0

@app.route('/')
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    nickname = data.get('nickname', '').strip()
    province = data.get('province', '').strip()
    interests = [i.strip() for i in data.get('interests', []) if i.strip()]
    # 校验省份和兴趣格式
    if not nickname or not province or len(interests) != 2:
        return jsonify({'error': '所有字段都是必填的！'}), 400
    if any(word in province for word in ["省", "市", "自治区"]):
        return jsonify({'error': '省份不能包含“省/市/自治区”等字样'}), 400
    if interests[0] == interests[1]:
        return jsonify({'error': '两个兴趣爱好不能相同！'}), 400
    if not all(len(i) == 2 for i in interests):
        return jsonify({'error': '兴趣爱好必须为两个字'}), 400

    # 加载并写入数据
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = []
    # （可选：昵称唯一）
    if any(user['nickname'] == nickname for user in users):
        return jsonify({'error': '该昵称已存在，请换一个'}), 400
    users.append({'nickname': nickname, 'province': province, 'interests': interests})
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False)
    return jsonify({'message': '提交成功！'})

@app.route('/data')
def get_data():
    type_choice = request.args.get('type', 'province')
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)

    nodes = []
    links = []

    if type_choice == 'province':
        province_users = {}
        for user in users:
            province_users.setdefault(user['province'], []).append(user['nickname'])
            nodes.append({'id': user['nickname'], 'province': user['province']})
        # 省内两两连线
        for province, names in province_users.items():
            for i in range(len(names)):
                for j in range(i+1, len(names)):
                    links.append({
                        'source': names[i], 'target': names[j], 'label': province
                    })
    else:  # 基于兴趣
        nodes = [{'id': user['nickname'], 'interests': user['interests']} for user in users]
        for i, u1 in enumerate(users):
            for j, u2 in enumerate(users):
                if i >= j:
                    continue
                common = set(u1.get('interests', [])) & set(u2.get('interests', []))
                if common:
                    links.append({
                        'source': u1['nickname'],
                        'target': u2['nickname'],
                        'label': ','.join(common)
                    })
    return jsonify({'nodes': nodes, 'links': links})

@app.route('/network')
def network():
    return render_template('network.html')

@app.route('/qrcode')
def qrcode_image():
    # 替换成你的实际线上网址！
    url = "https://dv-network-production.up.railway.app"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = b64encode(buffered.getvalue()).decode()
    return jsonify({'image': f'data:image/png;base64,{img_str}'})

# 可选（调试用）：查看所有数据
@app.route('/view-data')
def view_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'count': len(data), 'users': data})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
