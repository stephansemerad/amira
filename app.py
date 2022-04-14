import os, csv
from datetime import datetime
from sqlite3 import Timestamp
from flask import Flask
from flask import request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import json
import pandas as pd
from sqlalchemy import engine_from_config

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from helpers.allowed_files import allowed_file

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


def data_table_exists():
    sql = f"SELECT * FROM sqlite_master WHERE name='data';"
    result = db.session.execute(sql)
    result = [x for x in result]
    if result:
        return True
    else:
        return False


def csv_to_table(file_path):
    print("csv_to_table")

    # 1 check if table exists if yes delete it.
    # 2. delete table if exists - so that we can upload new.
    if data_table_exists:
        sql = f"drop table data"
        result = db.session.execute(sql)
        db.session.commit()

    # 3. creation on the table based on csv
    df = pd.read_csv(file_path)
    headers = list(df.columns.values)
    data_types = list(df.dtypes.astype("str"))

    # 4. send datafram to database
    df.to_sql("data", con=db.engine, index=False)

    return {
        "status": "ok",
        "msg": f"file {os.path.basename(file_path)} has been uploaded and converted",
    }


@app.route("/file_upload", methods=["GET", "POST"])
def file_upload():
    print("file_upload")
    file = request.files["files"]
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join("./static/csv", secure_filename(file_name))
        file.save(file_path)
        if os.path.exists(file_path):
            msg = csv_to_table(file_path)
            return jsonify(msg)
        else:
            return jsonify({"status": "notok", "msg": f"file could not be converted"})
    else:
        return jsonify(
            {
                "status": "notok",
                "msg": f"file can not be accepted, allowed extensions: {str(ALLOWED_EXTENSIONS)}",
            }
        )


@app.route("/diplay_table_data", methods=["GET"])
def diplay_table_data():

    # 1 - get table description
    sql = f"PRAGMA table_info(data)"
    headers = db.session.execute(sql)
    headers = [x[1] for x in headers]

    # 2 - get data from table
    sql = f"select * from data"
    data = db.session.execute(sql)
    data = [list(x) for x in data]

    data = {
        "headers": headers,
        "data": data,
    }
    return jsonify(data)


@app.route("/display_table_meta", methods=["GET"])
def display_table_meta():
    # 1 - get table description
    sql = f"PRAGMA table_info(data)"
    result = db.session.execute(sql)
    result = [[x[1], x[2]] for x in result]

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
