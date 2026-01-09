import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# database file
DB_FILE = "passcodes.db"

# allow cross-origin requests (frontend)
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://localhost:	xxxxx"}})

# index file route in flask
@app.route('/')
def index():
    return render_template('index.html')

# get all passcodes
@app.route('/api/passcodes', methods=['GET'])
def get_passcodes():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # access as dictionary for simple payload delivery
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM passcodes ORDER BY created DESC")  # fetch all passcodes, sorted by date
    passcodes = [dict(row) for row in cursor.fetchall()]  # convert each row to dictionary
    conn.close()
    return jsonify(passcodes)  # return in JSON format

# update full passcode entry
@app.route('/api/passcodes/<int:passcode_id>', methods=['PUT'])
def update_passcode(passcode_id):
    data = request.json
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # get current values
    cursor.execute("SELECT passcode, Name FROM passcodes WHERE id = ?", (passcode_id,))
    existing_entry = cursor.fetchone()

    if not existing_entry:
        conn.close()
        return jsonify({"success": False, "message": "not found"}), 404

    existing_passcode, existing_name = existing_entry

    # get new entries, fallback to existing
    new_passcode = data.get('passcode', existing_passcode)
    new_name = data.get('name', existing_name)

    fields = []
    values = []

    if new_passcode != existing_passcode:
        fields.append("passcode = ?")
        values.append(new_passcode)
    if new_name != existing_name:
        fields.append("Name = ?")
        values.append(new_name)

    if not fields:
        conn.close()
        return jsonify({"success": False, "message": "no changes provided (FROM SCRIPTmsg)"}), 400

    values.append(passcode_id)
    query = f"UPDATE passcodes SET {', '.join(fields)} WHERE id = ?"

    cursor.execute(query, tuple(values))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()

    if success:
        return jsonify({"success": True, "message": "passcode updated"})
    else:
        return jsonify({"success": False, "message": "update failed"}), 500

# update only the name
@app.route('/api/passcodes/<int:passcode_id>/name', methods=['PUT'])
def update_passcode_name(passcode_id):
    data = request.json
    new_name = data.get('name', '').strip()

    if not new_name:
        return jsonify({"success": False, "message": "name is required"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    last_access = datetime.now().isoformat()
    cursor.execute("UPDATE passcodes SET Name = ?, lastAccess = ? WHERE id = ?", (new_name, last_access, passcode_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()

    if success:
        return jsonify({"success": True, "message": "name updated successfully"})
    else:
        return jsonify({"success": False, "message": "passcode not found"}), 404

# delete a passcode
@app.route('/api/passcodes/<int:passcode_id>', methods=['DELETE'])
def delete_passcode(passcode_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM passcodes WHERE id = ?", (passcode_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()

    if rows_affected > 0:
        return jsonify({"success": True, "message": f"passcode {passcode_id} deleted"})
    else:
        return jsonify({"success": False, "message": "passcode not found"}), 404

# run flask server
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
