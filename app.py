import os
import csv
from datetime import datetime
from sqlite3 import Timestamp
from turtle import title
from flask import Flask
from flask import request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import json
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from helpers.allowed_files import allowed_file
from sqlalchemy import String, Numeric, Integer, Float, DateTime

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


def data_table_exists():
    sql = f"PRAGMA table_info(data)"
    headers = db.session.execute(sql)
    headers = [x[1] for x in headers]
    if headers:
        return True
    else:
        return False


def adjust_data_types(df):
    data_types = df.dtypes.apply(lambda x: x.name).to_dict()
    for i in data_types:
        if data_types[i] == "object":
            data_types[i] = String
        elif data_types[i] == "int64":
            data_types[i] = Integer
        elif data_types[i] == "float64":
            data_types[i] = Numeric
        elif data_types[i] == "datetime64[ns]":
            data_types[i] = DateTime
        else:
            data_types[i] = String
    return data_types


def csv_to_table(file_path):
    print("csv_to_table")
    # 1 check if table exists if yes delete it.
    # 2. delete table if exists - so that we can upload new.
    if data_table_exists():
        try:
            result = db.session.execute(f"drop table data")
            db.session.commit()
        except Exception as e:
            print(e)

    df = pd.read_csv(file_path)
    data_types = adjust_data_types(df)
    df.to_sql("data", con=db.engine, index=False, dtype=data_types)

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
    print('data_table_exists')
    print(data_table_exists())
    if not data_table_exists():
        return jsonify(
            data={
                "headers": [],
                "data": [],
            }
        )
    else:
        # 1 - get table description

        sql = f"PRAGMA table_info(data)"
        headers = db.session.execute(sql)
        headers = [x[1] for x in headers]

        print('headers:', headers)

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
    if not data_table_exists:
        return jsonify([])
    else:
        # 1 - get table description
        sql = f"PRAGMA table_info(data)"
        result = db.session.execute(sql)
        result = [[x[1], x[2]] for x in result]

        return jsonify(result)


@app.route("/change_column_type", methods=["PUT"])
def change_column_type():

    data = request.json
    column = data.get("column", None)
    datatype = data.get("datatype", None)

    print()
    print("change_column_type")
    print('column: ', column)
    print('datatype: ', datatype)

    df = pd.read_sql_query("SELECT * from data", con=db.engine)

    mapping = {
        'VARCHAR': "object",
        'INTEGER': "int64",
        'FLOAT': "float64",
    }

    try:
        df[column] = df[column].astype(mapping[datatype])
    except Exception as e:
        return jsonify({"status": "notok",  "msg": f"column {column} can not be changed to {datatype}, {e}"})

    result = db.session.execute(f"drop table data")
    db.session.commit()

    data_types = adjust_data_types(df)
    df.to_sql("data", con=db.engine, index=False, dtype=data_types)

    return jsonify({"status": "ok",  "msg": f"column {column} was changed to {datatype}", })


@app.route("/delete_column", methods=["DELETE"])
def delete_column():
    print("delete_column")
    data = request.args
    column = data.get("column", None)
    print('column: ', column)

    sql = f"PRAGMA table_info(data)"
    data = db.session.execute(sql)
    data = [x[1] for x in data]
    print(data)

    # check if its the last column.
    if [column] == data:
        result = db.session.execute(f"drop table data")
        db.session.commit()
    else:
        result = db.session.execute(f"alter table data drop column {column}")
        db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "msg": f"file deleted",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
