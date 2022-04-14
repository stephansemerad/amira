import os, csv
from datetime import datetime
from sqlite3 import Timestamp
from flask import Flask
from flask import request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import json
import pandas as pd
from sqlalchemy import engine_from_config
from sqlalchemy import String
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
        try:
            result = db.session.execute(f"drop table data")
            db.session.commit()
        except Exception as e:
            print(e)

    df = pd.read_csv(file_path)
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
            return jsonify(csv_to_table(file_path))
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


@app.route("/change_column_type", methods=["PUT"])
def change_column_type():
    print("change_column_type")

    data = request.json
    column = data.get("column", None)
    datatype = data.get("datatype", None)
    column = column[0][0] if column else None

    df = pd.read_sql_query("SELECT * from data", con=db.engine)

    print("-----------------------------")
    print("BEFORE")
    print(df.dtypes)

    # try:
    if datatype == "BIGINT":
        print("changing to BIGINT")
        df[column] = df[column].astype("int64")

    if datatype == "TEXT":
        print("changing to TEXT")
        df[column] = df[column].astype("object")

    if datatype == "FLOAT":
        print("changing to FLOAT")
        df[column] = df[column].astype("float64")

    print("AFTER")
    print(df.dtypes)

    # except Exception as e:
    #     return jsonify(
    #         {
    #             "status": "notok",
    #             "msg": f"column {column} can not be changed to data type {datatype}",
    #         }
    #     )

    try:
        result = db.session.execute(f"drop table data")
        db.session.commit()
    except Exception as e:
        print(e)

    df.to_sql("data", con=db.engine, index=False, dtype={"IDBIAT": String})

    db.session.commit()

    print("AFTER AFTER ")
    df = pd.read_sql_query("SELECT * from data", con=db.engine)
    print(df.dtypes)

    print("-----------------------------")

    return jsonify(
        {
            "status": "ok",
            "msg": f"column was changed",
        }
    )


@app.route("/delete_column", methods=["GET"])
def delete_column():
    print("delete_column")
    data = request.json
    print(request.args)
    print(request.form)

    # column = data.get("column", None)

    # print("column: ", column)

    return jsonify(
        {
            "status": "ok",
            "msg": f"file deleted",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
