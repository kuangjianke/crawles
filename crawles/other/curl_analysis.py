import inspect
import os.path
import re
from re import findall
from urllib import parse


def head_format(header_data):  # 请求数据格式化函数
    head_dict = {}
    for data in header_data.splitlines():  # 将文本以行进行分割
        data = data.lstrip()  # 去重字符串左边的空格
        if not data:  # 过滤掉空的数据 ''  '    '
            continue
        if data[0] == ':':  # 去重字符串的第一个冒号
            data = data[1:]
        html = findall('([a-zA-Z-]*?)\s*:\s*(.*?$)', data)

        for k, v in html:
            if 'Accept-Encoding' == k:  # 过滤掉Accept-Encoding参数
                continue
            head_dict[k] = str(v).replace('^', '')

    return head_dict


def url_data(curl_str):
    """url和请求参数的获取"""
    data_dict = {}
    curl = re.findall('''curl\s*['"](.*?)['"]''', curl_str)
    if curl:
        curl_data = curl[0]
        if '?' in curl_data:
            data_args = str(curl_data).split('?')  # 分割数据
            if len(data_args) == 2:
                url = data_args[0]
                data_str = data_args[1]
                for i in data_str.split('&'):
                    key, value = i.split('=')
                    data_dict[key] = parse.unquote(str(value).replace('^', ''))
            else:
                raise ValueError('链接解析失败，识别到了多个参数')
        else:
            url = curl_data
    else:
        raise ValueError('没有解析到curl数据')

    return url, data_dict


def headers_get(curl_str):
    """headers cookies"""

    head_data = re.findall('''-H\s*['"](.*?)['"]''', curl_str)

    if head_data:
        head_text = ''
        for i in head_data:
            head_text += i + '\n'
        headers = head_format(head_text)
    else:
        raise ValueError('没有请求参数')

    cookies = {}
    if headers.get('cookie') or headers.get('Cookie'):
        if 'Cookie' in headers:
            cookie_key = 'Cookie'
        else:
            cookie_key = 'cookie'
        cookie = headers[cookie_key]
        del headers[cookie_key]
        cookie_list = [str(c).strip().split('=', 1) for c in str(cookie).split(';')]
        cookies = {i[0]: i[1] for i in cookie_list}
    return headers, cookies


def data_get(curl_str):
    """method and data"""
    data = {}
    if '--data' in curl_str:
        data_str = re.findall('''--data.*?\s*['"](.*?)['"]''', curl_str, re.S)
        if data_str:
            for i in data_str[0].split('&'):
                key, value = i.split('=')
                data[key] = parse.unquote(str(value).replace('^', ''))
        else:
            raise ValueError('data参数获取失败')
        method = 'post'
    else:
        method = 'get'

    return method, data


def code_generation(method, url, data, headers, cookies):
    code_data = '# coding = utf-8\nimport crawles\n\n'

    code_data += f'url = "{url}"\n\n'

    code_data += 'cookies = {\n'
    for k, v in cookies.items():
        code_data += f'\t"{k}": "{v}",\n'
    code_data += '}\n\n'

    code_data += 'headers = {\n'
    for k, v in headers.items():
        if v == '\\':
            code_data += f'\t"{k}": "{v}{v}",\n'
        else:
            code_data += f'\t"{k}": "{v}",\n'
    code_data += '}\n\n'

    code_data += 'data = {\n'
    for k, v in data.items():
        code_data += f'\t"{k}": "{v}",\n'
    code_data += '}\n\n'

    if method == 'post':
        args = 'data'
    else:
        args = 'params'
    code_data += f'response = crawles.{method}(url, headers=headers, {args}=data, cookies=cookies)\n'
    code_data += 'print(response.text)\n'

    return code_data


def curl_analy(curl_str):
    url, data = url_data(curl_str)
    headers, cookies = headers_get(curl_str)
    method, data_dict = data_get(curl_str)
    data.update(data_dict)
    code_data = code_generation(method, url, data, headers, cookies)
    return code_data


def curl_analysis(curl_str):
    frame_info = inspect.stack()[1]
    filepath = frame_info[1]
    del frame_info

    filepath = os.path.abspath(filepath)

    code_data = curl_analy(curl_str)

    f = open(filepath, 'w+', encoding='utf-8')
    f.write(code_data)
    f.close()
