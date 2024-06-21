# -*- encoding=utf-8 -*-
from flask import Flask, request
import logging
import pymysql


class MySQL:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def fetchone(self, sql):
        # 进行查询
        connection = pymysql.connect(host=self.host,
                                     user=self.user,
                                     password=self.password,
                                     database=self.database,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result


# setting logger
formatter = "%(asctime)s %(levelname)s %(lineno)d %(message)s"
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

# flask app
app = Flask(__name__)

# set gpio status list
gpio = list()


@app.post("/query")
def query_params():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/get post data must be JSON"}, 415

    data = request.get_json()
    sql = data.get('sql', None)

    logger.info(f"sql: {sql}")

    if sql is None:
        return {"error": "Request on http://127.0.0.1:port/get post data must contain id"}, 415

    try:
        sql_result = mysql.fetchone(sql)
    except Exception as fail_reason:
        return {"error": fail_reason}, 200

    return sql_result, 200


if __name__ == "__main__":
    params = {
        'host': '10.66.98.85',
        'user': 'auto',
        'password': 'auto',
        'database': 'auto'
    }
    mysql = MySQL(**params)

    # run flask
    app.run(
        host='0.0.0.0',
        port=55556,
    )
