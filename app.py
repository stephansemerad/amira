from msilib.schema import SelfReg
import os
import csv
from datetime import datetime
from sqlite3 import Timestamp
import sqlite3
from turtle import title
from flask import Flask
from flask import request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from helpers.allowed_files import ALLOWED_EXTENSIONS, allowed_file
from sqlalchemy import String, Numeric, Integer, Float, DateTime
import base64
from io import BytesIO
from flask import Flask
from matplotlib.figure import Figure
import numpy as np
import seaborn as sns
import pandas as pd
from glob import glob; from os.path import expanduser

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


@app.route("/")
def index():
    return render_template("index.html")


def data_table_exists():
    headers = [x[1] for x in db.session.execute(f"PRAGMA table_info(data)")]
    return True if headers else False


def adjust_data_types(df):
    data_types = df.dtypes.apply(lambda x: x.name).to_dict()
    for i in data_types:
        if data_types[i] == "object":
            data_types[i] = String
        elif data_types[i] == "int64":
            data_types[i] = Integer
        elif data_types[i] == "float64":
            data_types[i] = Float
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
    print("data_table_exists")
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

        print("headers:", headers)

        # 2 - get data from table
        sql = f"select * from data"
        data = db.session.execute(sql)
        data = [list(x) for x in data]

        data = {
            "headers": headers,
            "data": data,
        }
        return jsonify(data)


def get_column_null_and_not_null_count(table_name):
    sql = f"""
    select
    (select count(1) from data) as count,
    (select count(1) from data where {table_name} is not null) as filled
    """
    result = db.session.execute(sql).first()
    return result


@app.route("/display_table_meta", methods=["GET"])
def display_table_meta():
    if not data_table_exists:
        return jsonify([])
    else:
        # 1 - get table description
        sql = f"PRAGMA table_info(data)"
        result = db.session.execute(sql)

        data = []
        for x in result:

            values = get_column_null_and_not_null_count(x[1])
            count_ = values[0]
            filled_ = values[1]
            percentage_ = values[1] / values[0]
            row = []
            row.append(x[1])
            row.append(x[2])
            row.append(count_)
            row.append(filled_)
            row.append("{0:.0%}".format(percentage_))

            data.append(row)

        return jsonify(data)


@app.route("/change_column_type", methods=["PUT"])
def change_column_type():

    data = request.json
    column = data.get("column", None)
    datatype = data.get("datatype", None)

    print()
    print("change_column_type")
    print("column: ", column)
    print("datatype: ", datatype)

    df = pd.read_sql_query("SELECT * from data", con=db.engine)

    mapping = {
        "VARCHAR": "object",
        "INTEGER": "int64",
        "FLOAT": "float64",
    }

    try:
        df[column] = df[column].astype(mapping[datatype])
    except Exception as e:
        return jsonify(
            {
                "status": "notok",
                "msg": f"column {column} can not be changed to {datatype}, {e}",
            }
        )

    result = db.session.execute(f"drop table data")
    db.session.commit()

    data_types = adjust_data_types(df)
    df.to_sql("data", con=db.engine, index=False, dtype=data_types)

    return jsonify(
        {
            "status": "ok",
            "msg": f"column {column} was changed to {datatype}",
        }
    )


@app.route("/delete_column", methods=["DELETE"])
def delete_column():
    print("delete_column")
    data = request.args
    column = data.get("column", None)
    print("column: ", column)

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


@app.route("/get_column_names_from_database", methods=["GET"])
def get_column_names_from_database():
    sql = f"PRAGMA table_info(data)"
    data = db.session.execute(sql)
    headers = [x[1] for x in data]
    return jsonify(headers)


@app.route("/get_chart", methods=["GET"])
def get_chart():
    """'
    chart_types:
    pie_chart
    bar_chart
    line_chart
    histogram_chat
    """

    print("")
    print("*********")
    print("get_chart")
    # http://127.0.0.1:5000/get_chart?chart_type=pie_chart&dimension_1=IDBIAT&dimension_2=IDBIAT
    # http://127.0.0.1:5000/get_chart?chart_type=bar_chart&dimension_1=IDBIAT&dimension_2=IDBIAT

    # Fetch data from frontend
    chart_type = request.args.get("chart_type", None)
    dimension_1 = request.args.get("dimension_1", None)
    dimension_2 = request.args.get("dimension_2", None)
    dimension_3 = request.args.get("dimension_3", None)
    dimension_4 = request.args.get("dimension_4", None)

    if chart_type == None:
        return "Missing Chart Type"

    print("chart_type: ", chart_type)
    print("dimension_1: ", dimension_1)
    print("dimension_2: ", dimension_2)

    def get_types_of_data_from_db():
        dictionary = {}
        data = db.session.execute(f"PRAGMA table_info(data)")
        for i in data:
            dictionary[i.name] = i.type
        return dictionary

    if chart_type == "pie_chart":
        # Take Data Types of Columns of Datatabase
        dictionary = get_types_of_data_from_db()

        # We check data type of Dimension 2 and do either sum or count group by
        if dictionary[dimension_2] == "VARCHAR":
            data = db.session.execute(f"""select {dimension_1}, count({dimension_2}) as value from data  group by {dimension_1}""")
        else:
            data = db.session.execute(f"""select {dimension_1}, sum({dimension_2}) as value from data  group by {dimension_1}""")

        fig = Figure()
        labels = []  # Dimension 1
        sizes = []  # Dimension 2
        for i in data:
            labels.append(str(i[0]))
            sizes.append(i[1])

        print("labels: ", labels)
        print("sizes: ", sizes)
        ax = fig.subplots()
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", shadow=True, startangle=90)

    if chart_type == "bar_chart":
        # TODO LOOK HERE AMIRA !!!
        # https://www.w3schools.com/python/matplotlib_bars.asp

        # 1. Get Data
        x_array = []
        y_array = []
        data = db.session.execute(f"""select {dimension_1}, {dimension_2} from data """)

        for i in data:
            x_array.append(str(i[0]))
            y_array.append(i[1])

        # 2. Create the Graph
        fig = Figure()
        x = np.array(x_array)  # Dimension 1
        y = np.array(y_array)  # Dimension 2
        ax = fig.subplots()
        ax.bar(x, y)

    if chart_type == "line_chart":
        # TODO AMIRA
        # https://www.w3schools.com/python/matplotlib_line.asp
        # 1. Get Data
        x_array = []
        y_array = []
        data = db.session.execute(f"""select {dimension_1}, {dimension_2} from data """)

        for i in data:
            x_array.append(str(i[0]))
            y_array.append(i[1])

        # 2. Create the Graph
        fig = Figure()
        x = np.array(x_array)  # Dimension 1
        y = np.array(y_array)  # Dimension 2
        ax = fig.subplots()
        chart= sns.countplot(x, hue=y ,ax=ax)
        chart.set(xlabel="Activity sector")
        chart.set(title="Distribution of the default rate by sector of activity")
       
        


    if chart_type == "histogram_chat":
        # https://www.w3schools.com/python/matplotlib_histograms.asp
        x_array = []
        # y_array = []
        data = db.session.execute(f"""select {dimension_1} from data """)
        for i in data:
            x_array.append(str(i[0]))
        # 2. Create the Graph
        fig = Figure()
        x = np.array(x_array)  # Dimension 1
        ax = fig.subplots()
        ax.hist(x)

    # 2. Save to buffer
    buf = BytesIO()
    fig.savefig(buf, format="png")
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"

conn = sqlite3.connect('database.db')
cursor = conn.cursor()
dat = pd.read_sql(f"select * from data" ,conn)
dat.to_csv('csvdata.csv', index=False)
dataf=pd.read_csv("csvdata.csv")



numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
quanti= dataf.select_dtypes(include=numerics)
print(quanti)
quanti_columns= quanti.columns.values.tolist()
print(quanti_columns)



                                                           # Analyse des valeurs extremes OUTLIERS
def Tukey_filter(df, quanti_columns):
    Q1=df[quanti_columns].quantile(0.25)
    Q3=df[quanti_columns].quantile(0.75)
    IQR=Q3-Q1
    upper_bound=Q3+(IQR*1.5)
    lower_bound=Q1-(IQR*1.5)
    for val_col in quanti_columns:
        for j in range(df.shape[0]):
          if df[val_col].iloc[j] > upper_bound[val_col]:
             df[val_col].iloc[j] = upper_bound[val_col]
          elif df[val_col].iloc[j] < lower_bound[val_col] :
              df[val_col].iloc[j] = lower_bound[val_col]

    return df

data_cleaning=Tukey_filter(dataf, quanti_columns)
print('here is aaaaaa',data_cleaning)

                                                         
                                                         
                                                         # DETECT OUTLIERS
                                                         
                                                          # OPTION 1:  iqr filter
print('dataf type',dataf.dtypes)

print('quanti type',quanti.dtypes)


def detectOutliers(data,col):
    Q3=data[col].quantile(0.75)
    Q1=data[col].quantile(0.25)
    IQR=Q3-Q1
    lower_range=Q1-1.5*IQR
    upper_range=Q3+1.5*IQR

    print("IQR value for column %s is: %s" % (col, IQR))
    print("lower and upper  value for column %s is: %s,%s" % (col,lower_range,upper_range))

    data['outlier']=np.where((data[col] < lower_range) | (data[col] > upper_range), 1 ,data['outlier'])
    
data=quanti
data['outlier']=1
for i in quanti_columns:
    detectOutliers(data,i)
print('this is the sum',data['outlier'].sum())
                                                           
                                                           # Z score 
                                                           # OPTION 2: z-score filter: z-score < 3
# lim = np.abs((quanti- quanti.mean()) / quanti.std(ddof=0)) < 3
# print('resukt with z score ',lim)

# mean = np.mean(quanti)
# std = np.std(quanti)
# print('mean of the dataset is', mean)
# print('std. deviation is', std)
# threshold = 3
# outlier = []
# for i in quanti:
#     z = abs((i-mean)/std)
#     if z > threshold or z < threshold:
#         outlier.append(i)
# print('outlier in dataset is', outlier)

                                                           
                                                           
                                                           
print(dataf.describe())
a_list = [['10', 1400], ['20', 2], ['30', 3]]

dff = pd.DataFrame(a_list, columns=['dog', 'cat'])

def outlier_detect(df):
    
    for i in df.select_dtypes('number').columns:
        Q1=df.describe().at['25%',i]
        Q3=df.describe().at['75%',i]
        IQR=Q3 - Q1
        LTV=Q1 - 1.5 * IQR
        UTV=Q3 + 1.5 * IQR
        x=np.array(df[i])
        p=[]
        for j in x:
            if j < LTV or j>UTV:
                p.append(j)
    return len(p)

print('mmmmmmmmmmmmmmmmmmmmmmmmmmm',outlier_detect(dataf))

# print(dataf.describe())
# print(dataf.shape)

# ######################################################
# # Removing the outliers

# def removeOutliers(data, col):
#     Q3 = np.quantile(data[col], 0.75)
#     Q1 = np.quantile(data[col], 0.25)
#     IQR = Q3 - Q1

#     print("IQR value for column %s is: %s" % (col, IQR))
#     global outlier_free_list
#     global filtered_data

#     lower_range = Q1 - 1.5 * IQR
#     upper_range = Q3 + 1.5 * IQR
#     outlier_free_list = [x for x in data[col] if (
#         (x > lower_range) & (x < upper_range))]
#     filtered_data = data.loc[data[col].isin(outlier_free_list)]
    


# for i in quanti_columns:
#      removeOutliers(quanti, i)
# dataf = filtered_data
  
# # Assigning filtered data back to our original variable
# print('new data', dataf )
# print("Shape of data after outlier removal is: ", dataf.shape)











if __name__ == "__main__":
    app.run(debug=True)
