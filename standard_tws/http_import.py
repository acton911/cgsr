import importlib.abc
import importlib.util
import urllib.error
import urllib.request
from typing import cast
import sys
import logging


__all__ = ['UrlMetaFinder', 'url_import']


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check(url: str) -> bool:
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request):
            return True
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


class UrlModuleLoader(importlib.abc.SourceLoader):  # 查找包资源和路径

    def __init__(self, baseurl: str) -> None:
        self._baseurl = baseurl

    def get_data(self, path) -> bytes:  # 必须实现，返回bytes code，OSError：路径未找到
        path = cast(str, path)
        try:
            with urllib.request.urlopen(path) as page:
                return page.read()
        except (urllib.error.HTTPError, urllib.error.URLError):
            raise OSError(f"Can't load {path}")

    def get_filename(self, fullname: str) -> str:  # 必须实现，返回包文件名，ImportError：如果路径不存在
        if fullname.startswith(self._baseurl):
            return fullname
        return self._baseurl + '/' + fullname.split('.')[-1] + '.py'

    def is_package(self, fullname: str) -> bool:
        return False

    def module_repr(self, module) -> str:
        return f'<url module {module.__name__} from {module.__file__}>'


class UrlPackageLoader(UrlModuleLoader):

    def get_filename(self, fullname: str) -> str:
        if fullname.startswith(self._baseurl):
            return fullname
        return self._baseurl + '/' + fullname.split('.')[-1] + '/__init__.py'

    def is_package(self, fullname: str) -> bool:
        return True


class UrlMetaFinder(importlib.abc.MetaPathFinder):

    def __init__(self, base_url: str, module: str = '') -> None:
        self.base_url = base_url
        self.module = module

    def find_spec(self, fullname, path, target=None):

        logger.debug(f'find spec path: {path}')
        if path is None:
            base_url = self.base_url
        else:
            if not path[0].startswith(self.base_url):
                logger.debug(f'find spec path[0]: {path[0]}')
                return None
            base_url = path[0]

        logging.debug(f'find spec base url: {base_url}')

        if self.module:
            base_url = f"{base_url}/{self.module}"

        logging.debug(f'find spec base url: {base_url}')

        parts = fullname.split('.')
        basename = parts[-1]
        logging.debug(f'find spec parts: {parts}')
        logging.debug(f'find spec basename: {basename}')

        module_url = f"{base_url}/{basename}.py"
        package_url = f"{base_url}/{basename}/__init__.py"
        logging.debug(f'find spec module_url: {module_url}')
        logging.debug(f'find spec package_url: {package_url}')

        logging.debug(f'find spec check: {check(module_url)}')
        logging.debug(f'find spec check: {check(package_url)}')

        if check(module_url):
            loader = UrlModuleLoader(base_url)
        elif check(package_url):
            loader = UrlPackageLoader(base_url)
        else:
            return None

        origin = base_url
        return importlib.util.spec_from_loader(fullname, loader, origin=origin)


def url_import(url: str) -> None:
    url_finder = UrlMetaFinder(url)
    sys.meta_path.append(url_finder)


# if __name__ == '__main__':
#     url_import('http://10.66.98.85/pylite_base')
#     from pylite_base.driver import get_port_list  # noqa
#     logger.info(get_port_list())
