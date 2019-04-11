# _*_ coding: utf-8 _*_
'''
Created: 2019-03-09 22:32:21
Author : Beibei
Email : beibei.feng@outlook.com
-----
Description: 
'''
import requests
import bs4
import pandas as pd
import os
import json
from PIL import Image
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('max_colwidth', 1000)

class GSF:
    def __init__(self, username, password, path, content):
        self.username = username
        self.password = password
        self.path = os.path.abspath(path)
        self.content = content
        self.conn = requests.Session()
        self.course = {}
        self.course_ = {}
        self.df = pd.DataFrame()

    def login(self):
        temp_login = self.conn.post(
            url='http://sep.ucas.ac.cn',
            headers={'Host': 'sep.ucas.ac.cn'},
            verify=False
        )

        soup = bs4.BeautifulSoup(temp_login.text, 'lxml')
        verifyText = soup.select('div label')[-1].getText()
        if verifyText == '验证码':
            verify = self.conn.get(
                url = 'http://sep.ucas.ac.cn/changePic',
                headers={'Host': 'sep.ucas.ac.cn'},
                verify=False
            )
            with open('verify.jpg', 'wb') as fd:
                for chunk in verify.iter_content(chunk_size=1024):
                    fd.write(chunk)
            img = Image.open('verify.jpg')
            img.show()
            verify_code = input("Please input the verify code:")
            print(verify_code)
            # post表单
            test = self.conn.post(
                url = 'http://sep.ucas.ac.cn/slogin', 
                data={
                    'userName': self.username,
                    'pwd': self.password,
                    'certCode': verify_code,
                    'sb': 'sb',
                    'rememberMe': 1
                },
                headers={'Host': 'sep.ucas.ac.cn'}
            )
        else:
            print("校园网好啊，不用花流量啊，也不用输验证码呀~")
            # post表单
            self.conn.post(
                url = 'http://sep.ucas.ac.cn/slogin', 
                data={
                    'userName': self.username,
                    'pwd': self.password,
                    'sb': 'sb',
                    'rememberMe': 1
                },
                headers={'Host': 'sep.ucas.ac.cn'}
            )

        # 获取课程网站重定向链接
        coursePanel_resp = self.conn.get(
            url = 'http://sep.ucas.ac.cn/portal/site/16/801',
            headers={'Host': 'sep.ucas.ac.cn'},
            verify=False
        )       

        soup = bs4.BeautifulSoup(coursePanel_resp.text, 'lxml')
        coursePanelLink = soup.select('div h4 a')[0].get('href')
        print("登录成功！ \n")
        
        # 获取资源页面链接
        courseLinks_resp = self.conn.get(
            url = coursePanelLink,
            headers={'Host': 'course.ucas.ac.cn'},
            verify=False
        )
        # 获取所有课程ID
        soup = bs4.BeautifulSoup(courseLinks_resp.text, 'lxml')
        for item in soup.select('ul div a'):
            link = item.get('href')
            name = item.get('title')
            if link.startswith('http://course.ucas.ac.cn/portal/site/1'):
                self.course[name[:-7]] = name[-2:]
                self.course_[link[-6:]] = name[:-7]
        # 获取资源按钮链接
        sourceLink = soup.find('a', attrs={'title':'资源 - 上传、下载课件，发布文档，网址等信息'}).get('href')
        source_resp = self.conn.get(
            url = sourceLink,
            headers={'Host': 'course.ucas.ac.cn'},
            verify=False
        )

        soup = bs4.BeautifulSoup(source_resp.text, 'lxml')
        # 获取collectionId
        collectionId = soup.find('a', attrs={'class': 'Mrphs-userNav__drop-btn Mrphs-userNav__submenuitem--profilepicture'}).get('style').split('/')[-3]
        # print(collectionId)
        # 获取csrf_token
        sakai_csrf_token = soup.find('input', attrs={'name': 'sakai_csrf_token'}).get('value')

        self.conn.post(
            url=sourceLink,
            data={
                'collectionId': '/user/'+collectionId,
                'sakai_action': 'doShowOtherSites',
                'sakai_csrf_token': sakai_csrf_token            
            },
            headers={'Host': 'course.ucas.ac.cn'}
        )
        print('please wait...')
        # 打开所有一级文件夹
        for key in self.course_.keys():
            open_dir_resp = self.conn.post(
                url=sourceLink+'?panel=Main',
                data={
                    'collectionId': '/group/'+key+'/',
                    'sakai_action': 'doExpand_collection',
                    'sakai_csrf_token': sakai_csrf_token
                },
                headers={'Host': 'course.ucas.ac.cn'}
            )

        # 打开所有文件夹
        pathset = set()
        path = []
        while True:
            addset = set()
            soup = bs4.BeautifulSoup(open_dir_resp.text, 'lxml')
            for item in soup.select('tr td input'):
                pathID = item.get('value')
                if pathID.endswith('/') and pathID not in pathset:
                    addset.add(pathID)
            if addset:
                pathset = pathset.union(addset)
                for pathID in addset:
                    open_dir_resp = self.conn.post(
                        url=sourceLink+'?panel=Main',
                        data={
                            'collectionId': pathID,
                            'sakai_action': 'doExpand_collection',
                            'sakai_csrf_token': sakai_csrf_token
                        },
                        headers={'Host': 'course.ucas.ac.cn'}
                    )
            else:
                for item in soup.select('tr td input'):
                    pathID = item.get('value')
                    if pathID.startswith('/group'):
                        path.append(str(self.course_[pathID[7:13]]+pathID[13:]))
                break

        # 获取所有文件下载链接
        soup = bs4.BeautifulSoup(open_dir_resp.text, 'lxml')
        fileLinkTemp = []
        for item in soup.select('tr th a'):
            link = item.get('href')
            if link.startswith('http://course.ucas.ac.cn/access/content/group'):
                fileLinkTemp.append(link)
        fileLink = fileLinkTemp[::2]

        tables = soup.select('table')
        df_list = []
        for table in tables:
            df_list.append(pd.concat(pd.read_html(table.prettify())))
        self.df = pd.concat(df_list)
        if len(self.df.columns) == 12:
            # python3.6
            self.df = self.df.loc[:, ['标题', '创建者', '最后修改时间', '大小']]
        elif len(self.df.columns) == 9:
            # python3.7
            self.df = self.df.loc[:, [2,6,7,8]]
            self.df.columns = ['标题', '创建者', '最后修改时间', '大小']
        else:
            print("python版本可能不支持！")
            exit()
        self.df['link'] = 0
        self.df['path'] = 0
        self.df['tag'] = '春季'
        self.df.dropna(inplace=True) 
        for index in self.df.index:
            if str(self.df.loc[index, '大小']).endswith('B'):
                path_temp = path.pop(0)
                self.df.loc[index, 'link'] = fileLink.pop(0)
                self.df.loc[index, 'path'] = os.path.join(self.path, path_temp)
            elif str(self.df.loc[index, '大小']).endswith('项'):
                path_temp = path.pop(0)
                self.df.loc[index, 'path'] = os.path.join(self.path, path_temp)
            else:
                self.df.drop(index, axis=0, inplace=True)
                continue
            self.df.loc[index, 'tag'] = self.course[path_temp.strip().split('/')[0]]
        if str(self.content).lower != 'all': 
            self.df = self.df[self.df['tag']==self.content]
        self.df.reset_index(drop=True, inplace=True)
        # print(self.df)
        
    def saveFile(self):
        if os.path.exists(self.path):
            for index in self.df.index:
                if not os.path.exists(self.df.iloc[index, 5]):
                    if str(self.df.iloc[index, 3])[-1] == 'B':
                        if not os.path.exists(os.path.split(self.df.iloc[index, 5])[0]):
                            os.makedirs(os.path.split(self.df.iloc[index, 5])[0])
                            print("新建文件夹：  "+os.path.split(self.df.iloc[index, 5])[0])
                        print("开始下载新的文件：  "+self.df.iloc[index, 5]+"......\n")
                        download_resp = self.conn.get(
                            url=self.df.iloc[index, 4],
                            verify=False
                        )
                        with open(self.df.iloc[index, 5], 'wb') as f:
                            for chunk in download_resp.iter_content(chunk_size=1024):
                                f.write(chunk)
                        print("    "+self.df.iloc[index, 5]+"  下载完成!\n")
            print("所有的文件已同步至最新！")
        else:
            print("路径不存在！")

if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    gsf = GSF(config['username'], config['password'], config['path'], config['content'])
    gsf.login()
    gsf.saveFile()