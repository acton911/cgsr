import os
from utils import lackey
from utils.logger.logging_handles import all_logger
import sys
import traceback


def pic_compare(path_to_pic, confidence=0.95):
    """
    检查某个图片是否存在。
    :param path_to_pic: 相对脚本运行目录的路径。
    :param confidence: 置信度，就是图片对比的相似度。
    :return: True:图标的置信度大于设置的值；False：图片的置信度小于设置的值。
    """
    try:
        all_logger.info("pic_compare: {}".format(path_to_pic))
        screen = lackey.Screen()
        all_logger.info('sys.path[0]: {}'.format(sys.path[0]))
        icon_score = screen.find_pic_in_folder_and_get_score(os.path.join(sys.path[0], path_to_pic))
        all_logger.info('icon_score:{}'.format(icon_score))
        if icon_score >= confidence:
            return True
        else:
            return False
    except Exception as e:
        all_logger.error(e)
        all_logger.error(traceback.format_exc())
        return False
