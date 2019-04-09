# get-sep-file
同步课程网站课件脚本

## Config

`username`：国科大邮箱

`password`: 课程网站登录密码

`path`: 存放文件的路径

`content`: 同步内容范围，可选"春季"、"秋季"和"all"



## Install

1. 本项目使用python3，使用前请安装相关packet：

    ```bash
    $ pip install -r requirments.txt
    ```

2. 配置config文件中的用户名、密码、存放路径和同步的内容（默认为春季课程）

3. 终端中运行:

    ```bash 
    $ python get-sep-file.py
    ```





