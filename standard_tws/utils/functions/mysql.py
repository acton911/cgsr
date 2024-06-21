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


if __name__ == '__main__':
    test_sql = "select * from SDX55_GIT;"
    params = {
        'host': '10.66.98.85',
        'user': 'auto',
        'password': 'auto',
        'database': 'auto'
    }
    s = MySQL(**params)
    print(s.fetchone(test_sql))
