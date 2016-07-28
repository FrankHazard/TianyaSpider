#!/usr/bin/python3

import os
import requests
import json

def crawl_user(user):
    # if user is 0, skip it
    if user is 0:
        return

    def req_relationship(user, method, url='http://www.tianya.cn/api/tw', page_size=4000):
        result = []
        total = None

        req_params = {
            'params.userId': user,
            'params.pageNo': 1,
            'params.pageSize': page_size
        }

        if method != 'follower' and method != 'following':
            return None
        
        req_params['method'] = method + '.ice.select'

        count = 1
        while count > 0:
            retry = True
            while retry:
                retry = False
                try:
                    r = requests.get(url, req_params)
                except requests.exceptions.ConnectionError:
                    retry = True
                    continue

                if r.status_code != 200:
                    print("Error: %s : %s : requests error" % (user, method))
                    retry = True
                    continue

                try:
                    data = r.json()
                except json.decoder.JSONDecodeError:
                    try:
                        data = eval(r.text.strip())
                    except json.decoder.JSONDecodeError:
                        print("Error: %s : %s : JSONDecodeError" % (user, method))
                        return None
                
                if data['success'] != 1:
                    print("Error: %s : %s : get failed" % (user, method))
                    retry = True
                    continue

                if not total:
                    total = data['data']['total']
                    print("total: %s : %s" % (user, total))
                    # 循环次数的计算
                    count = total // page_size
                    if count % page_size > 0:
                        count = count + 1
                # 可能动态变化的数据
                elif data['data']['total'] != total:
                    print("Warning: %s : %s : abnormal size :: before: %s : after: %s" % (user, method, total, data['data']['total']))

                # if data['data']['total'] >= page_size or \
                # len(data['data']['user']) != data['data']['total']:
                #     print("Warning: %s : %s : abnormal size" % (user, req_params['method']))
                
                result.extend(data['data']['user'])
                print("%s : %s : Page No: %s" % (user, method, req_params['params.pageNo']))
                req_params['params.pageNo'] = req_params['params.pageNo'] + 1
            
            count = count - 1

        if total != len(result):
            print('Warning: %s : %s : total abnormal size :: total: %s | read: %s' % (user, method, total, len(result)))

        return result

    relationship = {}
    relationship['following'] = req_relationship(user, 'following')
    relationship['follower'] = req_relationship(user, 'follower')

    with open(os.path.join('relationship', str(user) + '.json'), 'w') as f:
        f.write(json.dumps(relationship, indent=4))

    print('End Request: %s' % user)

def main():
    print('Openning user.json...')
    with open('users.json', 'r') as uf:
        users = uf.read()

    print('Starting Crawl...')
    for user in json.loads(users):
        crawl_user(user)

    print('All data saved.')

if __name__ == '__main__':
    main()
