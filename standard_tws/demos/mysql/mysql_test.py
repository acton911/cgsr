import pymysql.cursors
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Connect to the database
connection = pymysql.connect(host='10.66.98.85',
                             user='auto',
                             password='auto',
                             database='auto',
                             cursorclass=pymysql.cursors.DictCursor)

with connection:

    with connection.cursor() as cursor:
        # Read a single record
        sql = 'select mbim_driver_name from SDX55 where ati="RG500QEAAAR11A05M4G" and csub="V02";'
        cursor.execute(sql)
        result = cursor.fetchone()
        logger.info('type(result): {}'.format(type(result)))
        logger.info('result: {}'.format(result))
