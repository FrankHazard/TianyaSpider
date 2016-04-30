import re
import sys
import queue
import json
import requests
from urllib.parse import unquote        # urldecode
from bs4 import BeautifulSoup
pattern = re.compile(r'http://bbs\.tianya\.cn/post-(?P<bid>\w+)-(?P<pid>\d+)-(?P<page>\d+).shtml', re.I)


def starturl_constructor(blockid, postid):
    res = "http://bbs.tianya.cn/post-"
    res += str(blockid)
    res += '-' + str(postid)
    res += '-1.shtml'
    return res


def process(blockid, postid):
    data = dict()
    data['reply'] = list()
    for x in get_all_page(blockid, postid):
        match_res = re.match(pattern, x.url)
        if match_res and match_res.group('page') == '1':
            data['post'] = parse_mainbody(x.text)   # 处理主贴
        data['reply'].append(parse_reply(x.text))   # 处理评论

    with open(blockid + '-' + str(postid) + '.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4))
    print("parsed:", 'blockid=', blockid, 'postid=', postid)


def parse_mainbody(html):
    result = dict()
    soup = BeautifulSoup(html, "html.parser")
    attrs = soup.find('div', class_='atl-menu clearfix js-bbs-act')
    result['title'] = unquote(attrs.get('js_title_gbk'), encoding='gbk')
    result['blockid'] = attrs.get('js_blockid').strip()
    result['postid'] = int(attrs.get('js_postid'))
    result['posttime'] = int(attrs.get('js_posttime'))
    result['replycount'] = int(attrs.get('js_replycount'))
    result['clickcount'] = int(attrs.get('js_clickcount'))
    result['activityuserid'] = int(attrs.get('js_activityuserid'))
    result['activityurl'] = attrs.get('js_activityurl').strip()
    result['content'] = soup.find('div', class_='bbs-content clearfix').get_text().strip()

    return result


def parse_reply(html):
    soup = BeautifulSoup(html, 'html.parser')
    blockid = soup.find('div', class_='atl-menu clearfix js-bbs-act').get('js_blockid').strip()
    postid = int(soup.find('div', class_='atl-menu clearfix js-bbs-act').get('js_postid'))

    def proc_item(x):
        item = dict()
        info1 = x.find('a', class_='reportme a-link')
        item['replyid'] = int(info1.get('replyid'))
        item['replytime'] = info1.get('replytime')
        item['uid'] = int(info1.get('authorid'))
        info2 = x.find('a', class_='a-link-2 ir-remark')
        item['floor'] = int(info2.get('floor'))
        ircount = re.findall(r'(\d+)', info2.get_text().strip())    # reply count
        item['ircount'] = int(ircount[0]) if ircount else 0
        item['content'] = x.find('div', class_='bbs-content').get_text().strip()
        item['itemreply'] = parse_itemreply(blockid, postid, item['replyid'], item['ircount'])
        return item

    return list(map(proc_item, [x.parent.parent for x in soup.find_all('div', class_='atl-head-reply')]))


def parse_itemreply(blockid, postid, replyid, replycount):
    if replycount is 0:
        return []
    # 请求参数
    req_params = {
        'method': 'bbs.api.getCommentList',
        'params.item': blockid,
        'params.articleId': postid,
        'params.replyId': replyid,
        'params.pageNum': 1
    }
    url = 'http://bbs.tianya.cn/api'

    print('requesting:', 'blockid=' + req_params['params.item'], 'postid=' + str(req_params['params.articleId']), 'replyid=' + str(req_params['params.replyId']))

    results = list()
    while True:
        resp = json.loads(requests.get(url, req_params).text)
        # 请求失败则重试，否则准备下一页的请求
        if int(resp['success']) is not 1:
            print('warning:', 'request exception', 'pagenum=' + req_params['params.pageNum'])
            print('blockid=' + req_params['params.item'], 'postid=' + str(req_params['params.articleId']), 'replyid=' + str(req_params['params.replyId']))
            continue
        else:
            req_params['params.pageNum'] += 1

        if len(resp['data']) is 0:
            break
        else:
            results.extend(resp['data'])
    return results


def parse_links(response, blockid, postid):
    soup = BeautifulSoup(response.text, "html.parser")

    def link_filter(url):
        if url:
            url = url.strip()
            if url.startswith("/post-" + str(blockid) + "-" + str(postid)):
                return True
        return False

    links = map(lambda x: x.strip(), filter(link_filter, [x.get('href') for x in soup.find_all('a')]))
    return sorted(list(set(list(links))))  # 去重排序返回


def get_all_page(blockid, postid):
    start_url = starturl_constructor(blockid, postid)
    page_list = list()       # 下载的页面
    resp_url_list = list()
    wait_down_queue = queue.Queue()
    wait_down_queue.put(start_url)

    url_prefix = "http://bbs.tianya.cn"

    while not wait_down_queue.empty():
        url = wait_down_queue.get()
        # 下载
        print("downloading:", url)
        r = requests.get(url)
        page_list.append(r)
        resp_url_list.append(r.url)
        link_list = list(filter(lambda x: x not in resp_url_list, [url_prefix + x for x in parse_links(r, blockid, postid)]))  # 去重
        resp_url_list.extend(link_list)
        for x in link_list:
            wait_down_queue.put(x)

    return sorted(page_list, key=lambda x: x.url)


def parse_url(url):
    res = re.match(pattern, url)
    blockid = res.group('bid')
    postid = res.group('pid')
    return blockid, postid

if __name__ == '__main__':
    with open(sys.argv[1]) as urlin:
        url = urlin.readline().strip()
        while url:
            info = parse_url(url)
            process(info[0], info[1])

            url = urlin.readline().strip()

