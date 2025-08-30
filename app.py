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

@app.route('/')
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    nickname = data.get('nickname', '').strip()
    province = data.get('province', '').strip()
    interests = [i.strip() for i in data.get('interests', []) if i.strip()]
    if not nickname or not province or len(interests) != 2:
        return jsonify({'error': '所有字段都是必填的！'}), 400
    if any(word in province for word in ["省", "市", "自治区"]):
        return jsonify({'error': '省份不能包含“省/市/自治区”等字样'}), 400
    if interests[0] == interests[1]:
        return jsonify({'error': '两个兴趣爱好不能相同！'}), 400
    if not all(len(i) == 2 for i in interests):
        return jsonify({'error': '兴趣爱好必须为两个字'}), 400

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = []
    # 不允许昵称重复
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
        # 省份网络
        province_users = {}
        for user in users:
            province_users.setdefault(user['province'], []).append(user['nickname'])
            nodes.append({'id': user['nickname'], 'province': user['province']})
        for province, names in province_users.items():
            for i in range(len(names)):
                for j in range(i+1, len(names)):
                    links.append({
                        'source': names[i],
                        'target': names[j],
                        'label': province  # 线上的标注内容
                    })
    else:  # 兴趣网络
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
                        'label': f"{len(common)}/{','.join(common)}"  # 线上的标注内容：数量/兴趣名
                    })
    return jsonify({'nodes': nodes, 'links': links})

@app.route('/network')
def network():
    return render_template('network.html')

@app.route('/qrcode')
def qrcode_image():
    url = "https://dv-network-production.up.railway.app" # 替换为线上的地址
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = b64encode(buffered.getvalue()).decode()
    return jsonify({'image': f'data:image/png;base64,{img_str}'})
